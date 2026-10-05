"""Tests for audio output device description, validation, and console logging."""
import logging
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtMultimedia import QAudioFormat
from gui.other import audio_device


def test_channel_config_name():
    assert audio_device.channel_config_name(QAudioFormat.ChannelConfigStereo) == "Stereo"
    assert audio_device.channel_config_name(QAudioFormat.ChannelConfigMono) == "Mono"
    assert audio_device.channel_config_name(QAudioFormat.ChannelConfigSurround5Dot1) == "5.1 Surround"
    assert audio_device.channel_config_name(QAudioFormat.ChannelConfigSurround7Dot1) == "7.1 Surround"


def test_describe_audio_device_null():
    fake_dev = MagicMock()
    fake_dev.isNull.return_value = True
    assert audio_device.describe_audio_device(fake_dev) == "None (no device)"


def test_describe_audio_device_valid():
    fake_dev = MagicMock()
    fake_dev.isNull.return_value = False
    fake_dev.description.return_value = "Headphones (HyperX Cloud III)"
    fake_dev.channelConfiguration.return_value = QAudioFormat.ChannelConfigStereo
    fake_dev.maximumChannelCount.return_value = 2
    fake_dev.isDefault.return_value = True

    desc = audio_device.describe_audio_device(fake_dev)
    assert "Headphones (HyperX Cloud III)" in desc
    assert "Stereo, 2 channels" in desc
    assert "[Default]" in desc


def test_describe_audio_output():
    fake_dev = MagicMock()
    fake_dev.isNull.return_value = False
    fake_dev.description.return_value = "Speakers"
    fake_dev.channelConfiguration.return_value = QAudioFormat.ChannelConfigStereo
    fake_dev.maximumChannelCount.return_value = 2
    fake_dev.isDefault.return_value = False

    fake_out = MagicMock()
    fake_out.device.return_value = fake_dev
    fake_out.volume.return_value = 0.85
    fake_out.isMuted.return_value = False

    desc = audio_device.describe_audio_output(fake_out)
    assert "Speakers" in desc
    assert "Volume: 85%" in desc
    assert "Unmuted" in desc


def test_ensure_valid_audio_output_recovers_null_device():
    fake_dev = MagicMock()
    fake_dev.isNull.return_value = True

    default_dev = MagicMock()
    default_dev.isNull.return_value = False
    default_dev.description.return_value = "Default Speakers"
    default_dev.channelConfiguration.return_value = QAudioFormat.ChannelConfigStereo
    default_dev.maximumChannelCount.return_value = 2
    default_dev.isDefault.return_value = True

    fake_out = MagicMock()
    fake_out.device.return_value = fake_dev
    fake_out.isMuted.return_value = False
    fake_out.volume.return_value = 1.0

    with patch.object(audio_device.QMediaDevices, "defaultAudioOutput", return_value=default_dev), \
         patch.object(audio_device.QMediaDevices, "audioOutputs", return_value=[default_dev]):
        switched = audio_device.ensure_valid_audio_output(fake_out, context="Test")

    assert switched is True
    fake_out.setDevice.assert_called_once_with(default_dev)


def test_ensure_valid_audio_output_unmutes_and_resets_zero_volume():
    fake_dev = MagicMock()
    fake_dev.isNull.return_value = False
    fake_dev.id.return_value = b"dev1"

    fake_out = MagicMock()
    fake_out.device.return_value = fake_dev
    fake_out.isMuted.return_value = True
    fake_out.volume.return_value = 0.0

    with patch.object(audio_device.QMediaDevices, "audioOutputs", return_value=[fake_dev]):
        switched = audio_device.ensure_valid_audio_output(fake_out, context="Test")

    assert switched is False
    fake_out.setMuted.assert_called_once_with(False)
    fake_out.setVolume.assert_called_once_with(1.0)


def test_log_audio_playback(caplog):
    fake_dev = MagicMock()
    fake_dev.isNull.return_value = False
    fake_dev.description.return_value = "Headphones"
    fake_dev.channelConfiguration.return_value = QAudioFormat.ChannelConfigStereo
    fake_dev.maximumChannelCount.return_value = 2
    fake_dev.isDefault.return_value = True

    fake_out = MagicMock()
    fake_out.device.return_value = fake_dev
    fake_out.volume.return_value = 1.0
    fake_out.isMuted.return_value = False

    with caplog.at_level(logging.INFO):
        audio_device.log_audio_playback(fake_out, context="TestPlayer")

    assert "[TestPlayer] Playing on audio channel: Headphones [Stereo, 2 channels] [Default]" in caplog.text


def test_get_system_volume_info_structure():
    info = audio_device.get_system_volume_info()
    assert isinstance(info, dict)
    expected_keys = {
        "master_volume_pct",
        "master_volume_db",
        "master_volume_min_db",
        "master_volume_max_db",
        "master_muted",
        "channel_count",
        "channel_volumes",
        "app_mixer_volume_pct",
        "app_mixer_muted",
        "hardware_peak_level",
    }
    assert expected_keys.issubset(info.keys())


def test_describe_system_volume_formatting():
    fake_info = {
        "master_volume_pct": 73,
        "master_volume_db": -4.7,
        "master_volume_min_db": -65.2,
        "master_volume_max_db": 0.0,
        "master_muted": False,
        "channel_count": 2,
        "channel_volumes": [73, 73],
        "app_mixer_volume_pct": 80,
        "app_mixer_muted": False,
        "hardware_peak_level": 0.125,
    }

    fake_out = MagicMock()
    fake_out.volume.return_value = 1.0
    fake_out.isMuted.return_value = False

    with patch.object(audio_device, "get_system_volume_info", return_value=fake_info):
        lines = audio_device.describe_system_volume(fake_out)

    text = "\n".join(lines)
    assert "Windows Master Volume: 73% (-4.7 dB) [Unmuted]" in text
    assert "Hardware Channels: Left: 73%, Right: 73%" in text
    assert "Windows Volume Mixer (Hammer 5 Tools): 80% [Unmuted]" in text
    assert "Internal Player Volume: 100% [Unmuted]" in text
    assert "Effective Volume Level: 58.4% (Master 73% x Mixer 80% x Player 100%)" in text
    assert "Hardware Output Activity: Peak level 0.125" in text


def test_describe_system_volume_warning_on_critically_low_mixer():
    fake_info = {
        "master_volume_pct": 100,
        "master_volume_db": 0.0,
        "master_volume_min_db": -65.2,
        "master_volume_max_db": 0.0,
        "master_muted": False,
        "channel_count": 2,
        "channel_volumes": [100, 100],
        "app_mixer_volume_pct": 1,
        "app_mixer_muted": False,
        "hardware_peak_level": None,
    }

    with patch.object(audio_device, "get_system_volume_info", return_value=fake_info):
        lines = audio_device.describe_system_volume()

    text = "\n".join(lines)
    assert "[WARNING] [CRITICALLY LOW/MUTED: Audio may be inaudible!]" in text


def test_ensure_valid_audio_output_recovers_mixer_muted():
    fake_dev = MagicMock()
    fake_dev.isNull.return_value = False
    fake_dev.id.return_value = b"dev1"

    fake_out = MagicMock()
    fake_out.device.return_value = fake_dev
    fake_out.isMuted.return_value = False
    fake_out.volume.return_value = 1.0

    fake_info = {
        "master_volume_pct": 80,
        "app_mixer_volume_pct": 50,
        "app_mixer_muted": True,
    }

    with patch.object(audio_device.QMediaDevices, "audioOutputs", return_value=[fake_dev]), \
         patch.object(audio_device, "get_system_volume_info", return_value=fake_info), \
         patch.object(audio_device, "set_windows_mixer_volume") as mock_set_mixer:
        audio_device.ensure_valid_audio_output(fake_out, context="Test")

    mock_set_mixer.assert_called_once_with(level=0.5)


def test_log_audio_playback_effective_calculation(caplog):
    fake_dev = MagicMock()
    fake_dev.isNull.return_value = False
    fake_dev.description.return_value = "Headphones"
    fake_dev.channelConfiguration.return_value = QAudioFormat.ChannelConfigStereo
    fake_dev.maximumChannelCount.return_value = 2
    fake_dev.isDefault.return_value = True

    fake_out = MagicMock()
    fake_out.device.return_value = fake_dev
    fake_out.volume.return_value = 0.5
    fake_out.isMuted.return_value = False

    fake_info = {
        "master_volume_pct": 80,
        "app_mixer_volume_pct": 50,
    }

    with patch.object(audio_device, "get_system_volume_info", return_value=fake_info), \
         caplog.at_level(logging.INFO):
        audio_device.log_audio_playback(fake_out, context="TestPlayer")

    # 0.5 player * 0.5 mixer * 0.8 master = 0.20 -> 20.0%
    assert "Effective: 20.0%" in caplog.text
    assert "Player: 50%" in caplog.text
    assert "Win Mixer: 50%" in caplog.text
    assert "Master: 80%" in caplog.text


def test_log_current_system_audio_devices(caplog):
    with caplog.at_level(logging.INFO):
        audio_device.log_current_system_audio_devices()

    assert "Default audio output device:" in caplog.text

