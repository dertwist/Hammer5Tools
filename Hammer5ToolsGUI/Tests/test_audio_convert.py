"""Tests for audio decoding and level-envelope helpers used by the sound editors."""
import wave

import lameenc
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from gui.editors.soundevent_editor import audio_convert

RATE = 44100
AMPLITUDE = 10 ** (-12 / 20)  # a tone normalised to -12 dBFS


def _tone(channels=2, seconds=1.0):
    t = np.arange(int(RATE * seconds)) / RATE
    mono = np.sin(2 * np.pi * 440 * t) * AMPLITUDE
    return np.stack([mono] * channels, axis=1)


def _peak_db(samples):
    return 20 * np.log10(np.abs(samples).max())


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("sampwidth", [1, 2, 3, 4])
def test_pcm_to_float_keeps_level_for_every_bit_depth(sampwidth):
    tone = _tone()
    if sampwidth == 1:
        raw = (tone * 127 + 128).astype(np.uint8).tobytes()
    else:
        full_scale = (1 << (8 * sampwidth - 1)) - 1
        wide = (tone * full_scale).astype("<i8")
        raw = wide.view(np.uint8).reshape(-1, 8)[:, :sampwidth].tobytes()

    samples = audio_convert.pcm_to_float(raw, sampwidth)

    assert samples.shape == (tone.size,)
    assert _peak_db(samples) == pytest.approx(-12, abs=0.2)
    assert samples.min() < 0 < samples.max()  # sign survives the 24-bit widening


def test_peak_envelope_reports_loudest_channel():
    samples = np.zeros((RATE, 2), np.float32)
    samples[:, 1] = AMPLITUDE  # right channel only

    env, frame_seconds = audio_convert.peak_envelope(samples, RATE)

    assert frame_seconds == pytest.approx(0.03)
    assert 20 * np.log10(env.max()) == pytest.approx(-12, abs=0.01)


def test_mp3_decodes_at_original_level_and_length(tmp_path, qt_app):
    tone = _tone(seconds=2.0)
    encoder = lameenc.Encoder()
    encoder.set_in_sample_rate(RATE)
    encoder.set_channels(2)
    encoder.silence()
    mp3 = tmp_path / "tone.mp3"
    pcm = audio_convert.float_to_pcm16(tone)
    mp3.write_bytes(encoder.encode(pcm) + encoder.flush())

    samples, rate = audio_convert.decode_to_float(str(mp3))

    assert rate == RATE
    assert samples.shape[1] == 2
    # Misreading float output as int16 doubled the frame count and hit 0 dBFS.
    assert len(samples) == pytest.approx(len(tone), rel=0.05)
    assert _peak_db(samples) == pytest.approx(-12, abs=0.5)


def test_convert_24bit_wav_to_mp3_and_back(tmp_path, qt_app):
    tone = _tone()
    packed = (tone * 8388607).astype("<i4").view(np.uint8).reshape(-1, 4)[:, :3]
    src = tmp_path / "tone.wav"
    with wave.open(str(src), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(3)
        w.setframerate(RATE)
        w.writeframes(packed.tobytes())

    mp3 = audio_convert.convert_audio(str(src), "mp3")
    samples, _rate = audio_convert.decode_to_float(mp3)

    assert _peak_db(samples) == pytest.approx(-12, abs=0.5)


def test_pcm_to_float_handles_unaligned_tail_and_invalid_width():
    raw = b"\x00\x40\xff"  # 3 bytes: 1 valid 16-bit sample + 1 trailing byte
    samples = audio_convert.pcm_to_float(raw, 2)
    assert samples.shape == (1,)
    with pytest.raises(KeyError):
        audio_convert.pcm_to_float(b"\x00\x00", 5)


def test_float_to_pcm16_handles_nan_inf_and_clipping():
    arr = np.array([-2.0, -np.inf, np.nan, np.inf, 2.0], dtype=np.float32)
    pcm = np.frombuffer(audio_convert.float_to_pcm16(arr), dtype="<i2")
    assert pcm.tolist() == [-32767, -32767, 0, 32767, 32767]


def test_peak_envelope_short_clip_under_frame_ms():
    samples = np.full((100, 2), 0.5, dtype=np.float32)  # ~2.2ms at 44.1kHz
    env, dur = audio_convert.peak_envelope(samples, RATE, frame_ms=30)
    assert env is not None and len(env) == 1
    assert env[0] == pytest.approx(0.5, abs=1e-5)
    assert dur == pytest.approx(100 / RATE)


def test_convert_mp3_to_wav_and_multichannel_to_mp3(tmp_path, qt_app):
    tone = _tone(channels=4, seconds=0.5)
    src = tmp_path / "quad.wav"
    with wave.open(str(src), "wb") as w:
        w.setnchannels(4)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(audio_convert.float_to_pcm16(tone))

    mp3 = audio_convert.convert_audio(str(src), "mp3")
    assert mp3.endswith(".mp3")
    wav_back = audio_convert.convert_audio(mp3, "wav")
    assert wav_back.endswith(".wav")
