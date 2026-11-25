"""mp3 <-> wav conversion using QtMultimedia (decode) and lameenc (mp3 encode)."""
import os
import tempfile
import wave

import lameenc
import numpy as np
from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtMultimedia import QAudioDecoder, QAudioFormat


def pcm_to_float(raw, sampwidth):
    """Little-endian WAV PCM bytes (8/16/24/32-bit) -> float32 in -1..1."""
    if sampwidth not in (1, 2, 3, 4):
        raise KeyError(sampwidth)
    aligned = (len(raw) // sampwidth) * sampwidth
    if aligned == 0:
        return np.zeros(0, np.float32)
    raw = raw[:aligned]
    if sampwidth == 1:  # 8-bit PCM is unsigned, centred at 128
        return (np.frombuffer(raw, np.uint8).astype(np.float32) - 128.0) / 128.0
    if sampwidth == 3:  # numpy has no 24-bit dtype: widen into the top bytes of an int32
        packed = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        wide = np.zeros((len(packed), 4), np.uint8)
        wide[:, 1:] = packed
        return wide.view("<i4").ravel().astype(np.float32) / 2147483648.0
    dtype = {2: "<i2", 4: "<i4"}[sampwidth]
    return np.frombuffer(raw, dtype).astype(np.float32) / float(1 << (8 * sampwidth - 1))


def float_to_pcm16(samples):
    """float32 samples in -1..1 -> 16-bit little-endian PCM bytes."""
    clean = np.nan_to_num(samples, nan=0.0, posinf=1.0, neginf=-1.0)
    return (np.clip(clean, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def peak_envelope(samples, sample_rate, frame_ms=30):
    """Return (envelope, frame_seconds): the 0..1 linear peak of float (N, ch)
    samples per time frame, taken over the loudest channel."""
    if sample_rate <= 0 or len(samples) == 0:
        return None, 0.0
    frame_len = max(1, int(sample_rate * frame_ms / 1000))
    n = len(samples) // frame_len
    if n == 0:
        peak = float(np.abs(samples).max())
        return np.array([peak], dtype=np.float32), len(samples) / float(sample_rate)
    env = np.abs(samples[:n * frame_len]).reshape(n, -1).max(axis=1)
    return env, frame_len / float(sample_rate)


def _buffer_to_float(buf):
    if not buf.isValid() or buf.frameCount() <= 0:
        return None
    # The backend picks the sample format (FFmpeg decodes mp3 to float), so
    # convert from whatever arrived instead of assuming int16.
    fmt = buf.format()
    channels = fmt.channelCount()
    if channels <= 0 or fmt.sampleRate() <= 0:
        return None
    sample_format = fmt.sampleFormat()
    if sample_format == QAudioFormat.SampleFormat.Unknown:
        return None
    raw = bytes(buf.constData())
    if sample_format == QAudioFormat.SampleFormat.Float:
        aligned = (len(raw) // 4) * 4
        if aligned == 0:
            return None
        samples = np.frombuffer(raw[:aligned], "<f4")
    else:
        bps = fmt.bytesPerSample()
        if bps not in (1, 2, 3, 4):
            return None
        samples = pcm_to_float(raw, bps)
    usable = (len(samples) // channels) * channels
    if usable == 0:
        return None
    return samples[:usable].reshape(-1, channels)


def start_decode(decoder, on_done):
    """Start ``decoder`` (source already set) without blocking.

    Calls ``on_done(samples float32 (N, ch), sample_rate, error_or_None)``.
    """
    chunks = []
    rate = [44100]
    done = [False]

    def _on_buffer():
        if done[0]:
            return
        buf = decoder.read()
        arr = _buffer_to_float(buf)
        if arr is None:
            return
        sr = buf.format().sampleRate()
        if sr > 0:
            rate[0] = sr
        chunks.append(arr)

    def _finish(error=None):
        if done[0]:
            return
        done[0] = True
        samples = np.concatenate(chunks) if chunks else np.zeros((0, 1), np.float32)
        chunks.clear()
        on_done(samples, rate[0], error)

    decoder.bufferReady.connect(_on_buffer)
    decoder.finished.connect(lambda: _finish())
    decoder.error.connect(lambda _code: _finish(decoder.errorString()))
    decoder.start()


def decode_to_float(src_path, timeout_ms=60_000):
    """Decode any QtMultimedia-supported audio file to (samples float32 (N, ch), sample_rate)."""
    decoder = QAudioDecoder()
    try:
        decoder.setSource(QUrl.fromLocalFile(src_path))
        loop = QEventLoop()
        results = []
        start_decode(decoder, lambda *result: (results.append(result), loop.quit()))
        if not results:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            timer.start(timeout_ms)
            loop.exec()
            timer.stop()

        if not results:
            raise RuntimeError(f"Timed out decoding {src_path}")

        samples, sample_rate, error = results[0]
        if error:
            raise RuntimeError(f"Failed to decode {src_path}: {error}")
        return samples, sample_rate
    finally:
        decoder.stop()
        decoder.setSource(QUrl())
        decoder.deleteLater()


def convert_audio(src_path, dst_ext, overwrite=True):
    """Convert ``src_path`` to a sibling file with ``dst_ext`` ('wav' or 'mp3').

    Returns the output path. Raises FileExistsError if the target exists and
    overwrite is False, or RuntimeError if decoding fails.
    """
    dst_ext = dst_ext.lower().lstrip(".")
    if dst_ext not in ("wav", "mp3"):
        raise ValueError(f"Unsupported destination extension: {dst_ext!r}")
    dst_path = os.path.splitext(src_path)[0] + "." + dst_ext
    if os.path.abspath(dst_path) == os.path.abspath(src_path):
        raise ValueError("source and destination are the same file")
    if not overwrite and os.path.exists(dst_path):
        raise FileExistsError(dst_path)

    samples, sample_rate = decode_to_float(src_path)
    if sample_rate <= 0 or len(samples) == 0:
        raise RuntimeError(f"Decoded audio is empty for {src_path}")
    channels = samples.shape[1]

    dst_dir = os.path.dirname(os.path.abspath(dst_path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dst_dir, suffix=f".{dst_ext}.tmp")
    os.close(fd)
    try:
        if dst_ext == "wav":
            pcm_bytes = float_to_pcm16(samples)
            with wave.open(tmp_path, "wb") as w:
                w.setnchannels(channels)
                w.setsampwidth(2)
                w.setframerate(sample_rate)
                w.writeframes(pcm_bytes)
        else:
            if channels > 2:
                samples = samples.mean(axis=1, keepdims=True)
                channels = 1
            pcm_bytes = float_to_pcm16(samples)
            encoder = lameenc.Encoder()
            encoder.set_bit_rate(190)  # ~190 kbps VBR-equivalent quality
            encoder.set_in_sample_rate(sample_rate)
            encoder.set_channels(channels)
            encoder.set_quality(2)
            mp3_data = encoder.encode(pcm_bytes)
            mp3_data += encoder.flush()
            with open(tmp_path, "wb") as f:
                f.write(mp3_data)
        os.replace(tmp_path, dst_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return dst_path
