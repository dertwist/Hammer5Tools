"""mp3 <-> wav conversion using QtMultimedia (decode) and lameenc (mp3 encode)."""
import os
import wave

import lameenc
import numpy as np
from PySide6.QtCore import QEventLoop, QUrl
from PySide6.QtMultimedia import QAudioDecoder, QAudioFormat


def decode_to_pcm16(src_path):
    """Decode any QtMultimedia-supported audio file to (samples int16 (N, ch), sample_rate)."""
    decoder = QAudioDecoder()
    fmt = QAudioFormat()
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    decoder.setAudioFormat(fmt)
    decoder.setSource(QUrl.fromLocalFile(src_path))

    chunks = []
    info = {"channels": 1, "rate": 44100}
    errors = []
    loop = QEventLoop()

    def _on_buffer():
        buf = decoder.read()
        info["channels"] = buf.format().channelCount()
        info["rate"] = buf.format().sampleRate()
        chunks.append(np.frombuffer(bytes(buf.constData()), dtype="<i2").copy())

    def _on_finished():
        loop.quit()

    def _on_error(_code):
        errors.append(decoder.errorString())
        loop.quit()

    decoder.bufferReady.connect(_on_buffer)
    decoder.finished.connect(_on_finished)
    decoder.error.connect(_on_error)
    decoder.start()
    loop.exec()

    if errors:
        raise RuntimeError(f"Failed to decode {src_path}: {errors[0]}")

    samples = np.concatenate(chunks) if chunks else np.zeros(0, dtype="<i2")
    return samples.reshape(-1, info["channels"]), info["rate"]


def convert_audio(src_path, dst_ext, overwrite=True):
    """Convert ``src_path`` to a sibling file with ``dst_ext`` ('wav' or 'mp3').

    Returns the output path. Raises FileExistsError if the target exists and
    overwrite is False, or RuntimeError if decoding fails.
    """
    dst_ext = dst_ext.lower().lstrip(".")
    dst_path = os.path.splitext(src_path)[0] + "." + dst_ext
    if os.path.abspath(dst_path) == os.path.abspath(src_path):
        raise ValueError("source and destination are the same file")
    if not overwrite and os.path.exists(dst_path):
        raise FileExistsError(dst_path)

    samples, sample_rate = decode_to_pcm16(src_path)
    channels = samples.shape[1] if samples.ndim == 2 else 1
    pcm_bytes = samples.astype("<i2").tobytes()

    if dst_ext == "wav":
        with wave.open(dst_path, "wb") as w:
            w.setnchannels(channels)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm_bytes)
    elif dst_ext == "mp3":
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(190)  # ~190 kbps VBR-equivalent quality
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(channels)
        encoder.set_quality(2)
        mp3_data = encoder.encode(pcm_bytes)
        mp3_data += encoder.flush()
        with open(dst_path, "wb") as f:
            f.write(mp3_data)
    else:
        raise ValueError(f"Unsupported destination extension: {dst_ext!r}")

    return dst_path
