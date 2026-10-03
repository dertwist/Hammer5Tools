"""Audio output device discovery, system volume inspection, validation, and console logging."""
from __future__ import annotations

import ctypes
import logging
import sys
from typing import Any, Optional
import weakref

from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioOutput, QMediaDevices, QMediaPlayer

log = logging.getLogger(__name__)

_media_devices_monitor: Optional[QMediaDevices] = None
_monitored_outputs: list[weakref.ref[QAudioOutput]] = []


# ---------------------------------------------------------------------------
# Windows WASAPI / Core Audio COM Definitions (ctypes)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    from ctypes import HRESULT, POINTER, Structure, byref, c_float, c_int, c_uint, c_void_p, wintypes

    class _GUID(Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

        def __init__(self, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8):
            super().__init__(l, w1, w2, (wintypes.BYTE * 8)(b1, b2, b3, b4, b5, b6, b7, b8))

    _CLSID_MMDeviceEnumerator = _GUID(
        0xBCDE0395, 0xE52F, 0x467C, 0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E
    )
    _IID_IMMDeviceEnumerator = _GUID(
        0xA95664D2, 0x9614, 0x4F35, 0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6
    )
    _IID_IAudioEndpointVolume = _GUID(
        0x5CDF2C82, 0x841E, 0x4546, 0x97, 0x22, 0x0C, 0xF7, 0x40, 0x78, 0x22, 0x9A
    )
    _IID_IAudioSessionManager = _GUID(
        0xBFA971F1, 0x4D5E, 0x40BB, 0x93, 0x5E, 0x96, 0x70, 0x39, 0xBF, 0xBE, 0xE4
    )
    _IID_ISimpleAudioVolume = _GUID(
        0x87CE5498, 0x68D6, 0x44E5, 0xAC, 0x21, 0xAB, 0x24, 0x91, 0x04, 0x52, 0x63
    )
    _IID_IAudioMeterInformation = _GUID(
        0xC02216F6, 0x8C67, 0x4B5B, 0x9D, 0x00, 0xD0, 0x08, 0xE7, 0x3E, 0x00, 0x64
    )

    class _IUnknownVtbl(Structure):
        _fields_ = [
            ("QueryInterface", c_void_p),
            ("AddRef", ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)),
            ("Release", ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)),
        ]

    class _IMMDeviceEnumeratorVtbl(Structure):
        _fields_ = [
            ("QueryInterface", c_void_p),
            ("AddRef", c_void_p),
            ("Release", ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)),
            ("EnumAudioEndpoints", c_void_p),
            ("GetDefaultAudioEndpoint", ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_int, c_int, POINTER(c_void_p))),
        ]

    class _IMMDeviceVtbl(Structure):
        _fields_ = [
            ("QueryInterface", c_void_p),
            ("AddRef", c_void_p),
            ("Release", ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)),
            ("Activate", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(_GUID), wintypes.DWORD, c_void_p, POINTER(c_void_p))),
        ]

    class _IAudioEndpointVolumeVtbl(Structure):
        _fields_ = [
            ("QueryInterface", c_void_p),
            ("AddRef", c_void_p),
            ("Release", ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)),
            ("RegisterControlChangeNotify", c_void_p),
            ("UnregisterControlChangeNotify", c_void_p),
            ("GetChannelCount", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_uint))),
            ("SetMasterVolumeLevel", c_void_p),
            ("SetMasterVolumeLevelScalar", c_void_p),
            ("GetMasterVolumeLevel", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))),
            ("GetMasterVolumeLevelScalar", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))),
            ("SetChannelVolumeLevel", c_void_p),
            ("SetChannelVolumeLevelScalar", c_void_p),
            ("GetChannelVolumeLevel", ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_uint, POINTER(c_float))),
            ("GetChannelVolumeLevelScalar", ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_uint, POINTER(c_float))),
            ("SetMute", c_void_p),
            ("GetMute", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(wintypes.BOOL))),
            ("GetVolumeStepInfo", c_void_p),
            ("VolumeStepUp", c_void_p),
            ("VolumeStepDown", c_void_p),
            ("QueryHardwareSupport", c_void_p),
            ("GetVolumeRange", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float), POINTER(c_float), POINTER(c_float))),
        ]

    class _IAudioSessionManagerVtbl(Structure):
        _fields_ = [
            ("QueryInterface", c_void_p),
            ("AddRef", c_void_p),
            ("Release", ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)),
            ("GetAudioSessionControl", c_void_p),
            ("GetSimpleAudioVolume", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(_GUID), wintypes.DWORD, POINTER(c_void_p))),
        ]

    class _ISimpleAudioVolumeVtbl(Structure):
        _fields_ = [
            ("QueryInterface", c_void_p),
            ("AddRef", c_void_p),
            ("Release", ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)),
            ("SetMasterVolume", ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_float, POINTER(_GUID))),
            ("GetMasterVolume", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))),
            ("SetMute", ctypes.WINFUNCTYPE(HRESULT, c_void_p, wintypes.BOOL, POINTER(_GUID))),
            ("GetMute", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(wintypes.BOOL))),
        ]

    class _IAudioMeterInformationVtbl(Structure):
        _fields_ = [
            ("QueryInterface", c_void_p),
            ("AddRef", c_void_p),
            ("Release", ctypes.WINFUNCTYPE(wintypes.ULONG, c_void_p)),
            ("GetPeakValue", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))),
            ("GetMeteringChannelCount", ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_uint))),
            ("GetChannelsPeakValues", ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_uint, POINTER(c_float))),
            ("QueryHardwareSupport", c_void_p),
        ]

    def _release_com_ptr(ptr: c_void_p) -> None:
        if ptr and ptr.value:
            try:
                vtbl = ctypes.cast(ctypes.cast(ptr, POINTER(c_void_p)).contents, POINTER(_IUnknownVtbl)).contents
                vtbl.Release(ptr)
            except Exception:
                pass


def get_system_volume_info() -> dict[str, Any]:
    """Query Windows WASAPI master endpoint volume, hardware channel levels, and app mixer session volume.

    Returns a dict with master_volume_pct, master_volume_db, master_muted, channel_count,
    channel_volumes, app_mixer_volume_pct, app_mixer_muted, and hardware_peak_level.
    """
    info: dict[str, Any] = {
        "master_volume_pct": None,
        "master_volume_db": None,
        "master_volume_min_db": None,
        "master_volume_max_db": None,
        "master_muted": None,
        "channel_count": 0,
        "channel_volumes": [],
        "app_mixer_volume_pct": None,
        "app_mixer_muted": None,
        "hardware_peak_level": None,
    }

    if sys.platform != "win32":
        return info

    try:
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)

        enumerator = c_void_p()
        if ole32.CoCreateInstance(
            byref(_CLSID_MMDeviceEnumerator), None, 1, byref(_IID_IMMDeviceEnumerator), byref(enumerator)
        ) != 0:
            return info

        enum_vtbl = ctypes.cast(
            ctypes.cast(enumerator, POINTER(c_void_p)).contents, POINTER(_IMMDeviceEnumeratorVtbl)
        ).contents

        device = c_void_p()
        # 0 = eRender, 0 = eConsole (multimedia/communications)
        if enum_vtbl.GetDefaultAudioEndpoint(enumerator, 0, 0, byref(device)) != 0:
            _release_com_ptr(enumerator)
            return info

        dev_vtbl = ctypes.cast(
            ctypes.cast(device, POINTER(c_void_p)).contents, POINTER(_IMMDeviceVtbl)
        ).contents

        # 1. Master endpoint volume & channel levels
        endpoint_volume = c_void_p()
        CLSCTX_ALL = 23
        if dev_vtbl.Activate(device, byref(_IID_IAudioEndpointVolume), CLSCTX_ALL, None, byref(endpoint_volume)) == 0:
            vol_vtbl = ctypes.cast(
                ctypes.cast(endpoint_volume, POINTER(c_void_p)).contents, POINTER(_IAudioEndpointVolumeVtbl)
            ).contents

            vol_scalar = c_float()
            if vol_vtbl.GetMasterVolumeLevelScalar(endpoint_volume, byref(vol_scalar)) == 0:
                info["master_volume_pct"] = int(round(vol_scalar.value * 100))

            vol_db = c_float()
            if vol_vtbl.GetMasterVolumeLevel(endpoint_volume, byref(vol_db)) == 0:
                info["master_volume_db"] = round(vol_db.value, 1)

            min_db = c_float()
            max_db = c_float()
            step_db = c_float()
            if vol_vtbl.GetVolumeRange(endpoint_volume, byref(min_db), byref(max_db), byref(step_db)) == 0:
                info["master_volume_min_db"] = round(min_db.value, 1)
                info["master_volume_max_db"] = round(max_db.value, 1)

            mute = wintypes.BOOL()
            if vol_vtbl.GetMute(endpoint_volume, byref(mute)) == 0:
                info["master_muted"] = bool(mute.value)

            ch_count = c_uint()
            if vol_vtbl.GetChannelCount(endpoint_volume, byref(ch_count)) == 0:
                info["channel_count"] = ch_count.value
                ch_vols = []
                for ch in range(ch_count.value):
                    cv = c_float()
                    if vol_vtbl.GetChannelVolumeLevelScalar(endpoint_volume, ch, byref(cv)) == 0:
                        ch_vols.append(int(round(cv.value * 100)))
                info["channel_volumes"] = ch_vols

            _release_com_ptr(endpoint_volume)

        # 2. Windows Volume Mixer app-session volume (ISimpleAudioVolume)
        session_mgr = c_void_p()
        if dev_vtbl.Activate(device, byref(_IID_IAudioSessionManager), CLSCTX_ALL, None, byref(session_mgr)) == 0:
            mgr_vtbl = ctypes.cast(
                ctypes.cast(session_mgr, POINTER(c_void_p)).contents, POINTER(_IAudioSessionManagerVtbl)
            ).contents

            simple_vol = c_void_p()
            if mgr_vtbl.GetSimpleAudioVolume(session_mgr, None, 0, byref(simple_vol)) == 0:
                sav_vtbl = ctypes.cast(
                    ctypes.cast(simple_vol, POINTER(c_void_p)).contents, POINTER(_ISimpleAudioVolumeVtbl)
                ).contents

                app_vol = c_float()
                if sav_vtbl.GetMasterVolume(simple_vol, byref(app_vol)) == 0:
                    info["app_mixer_volume_pct"] = int(round(app_vol.value * 100))

                app_mute = wintypes.BOOL()
                if sav_vtbl.GetMute(simple_vol, byref(app_mute)) == 0:
                    info["app_mixer_muted"] = bool(app_mute.value)

                _release_com_ptr(simple_vol)
            _release_com_ptr(session_mgr)

        # 3. Hardware Peak Meter (IAudioMeterInformation)
        meter = c_void_p()
        if dev_vtbl.Activate(device, byref(_IID_IAudioMeterInformation), CLSCTX_ALL, None, byref(meter)) == 0:
            meter_vtbl = ctypes.cast(
                ctypes.cast(meter, POINTER(c_void_p)).contents, POINTER(_IAudioMeterInformationVtbl)
            ).contents
            peak = c_float()
            if meter_vtbl.GetPeakValue(meter, byref(peak)) == 0:
                info["hardware_peak_level"] = round(peak.value, 3)
            _release_com_ptr(meter)

        _release_com_ptr(device)
        _release_com_ptr(enumerator)
    except Exception as exc:
        log.debug("WASAPI volume query error: %s", exc)

    return info


def set_windows_mixer_volume(level: float = 1.0) -> bool:
    """Set this application's volume in the Windows Volume Mixer (0.0 to 1.0) and unmute it."""
    if sys.platform != "win32":
        return False
    try:
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)
        enumerator = c_void_p()
        if ole32.CoCreateInstance(
            byref(_CLSID_MMDeviceEnumerator), None, 1, byref(_IID_IMMDeviceEnumerator), byref(enumerator)
        ) != 0:
            return False
        enum_vtbl = ctypes.cast(
            ctypes.cast(enumerator, POINTER(c_void_p)).contents, POINTER(_IMMDeviceEnumeratorVtbl)
        ).contents
        device = c_void_p()
        if enum_vtbl.GetDefaultAudioEndpoint(enumerator, 0, 0, byref(device)) != 0:
            _release_com_ptr(enumerator)
            return False
        dev_vtbl = ctypes.cast(ctypes.cast(device, POINTER(c_void_p)).contents, POINTER(_IMMDeviceVtbl)).contents
        session_mgr = c_void_p()
        if dev_vtbl.Activate(device, byref(_IID_IAudioSessionManager), 23, None, byref(session_mgr)) != 0:
            _release_com_ptr(device)
            _release_com_ptr(enumerator)
            return False
        mgr_vtbl = ctypes.cast(
            ctypes.cast(session_mgr, POINTER(c_void_p)).contents, POINTER(_IAudioSessionManagerVtbl)
        ).contents
        simple_vol = c_void_p()
        success = False
        if mgr_vtbl.GetSimpleAudioVolume(session_mgr, None, 0, byref(simple_vol)) == 0:
            sav_vtbl = ctypes.cast(
                ctypes.cast(simple_vol, POINTER(c_void_p)).contents, POINTER(_ISimpleAudioVolumeVtbl)
            ).contents
            clamped = max(0.0, min(1.0, float(level)))
            hr_vol = sav_vtbl.SetMasterVolume(simple_vol, c_float(clamped), None)
            hr_mute = sav_vtbl.SetMute(simple_vol, wintypes.BOOL(False), None)
            success = hr_vol == 0 and hr_mute == 0
            _release_com_ptr(simple_vol)
        _release_com_ptr(session_mgr)
        _release_com_ptr(device)
        _release_com_ptr(enumerator)
        return success
    except Exception as exc:
        log.warning("Could not set Windows mixer volume: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Channel & Device Formatting Helpers
# ---------------------------------------------------------------------------
def channel_config_name(config: QAudioFormat.ChannelConfig) -> str:
    """Return a clean human-readable name for an audio channel configuration."""
    name = config.name if hasattr(config, "name") else str(config)
    clean = name.replace("ChannelConfig", "")
    mapping = {
        "Unknown": "Unknown",
        "Mono": "Mono",
        "Stereo": "Stereo",
        "2Dot1": "2.1 Surround",
        "Surround5Dot1": "5.1 Surround",
        "Surround7Dot1": "7.1 Surround",
    }
    return mapping.get(clean, clean)


def describe_audio_device(device: QAudioDevice) -> str:
    """Format audio device description, channel configuration, and default status."""
    if device.isNull():
        return "None (no device)"
    name = device.description() or "Unknown Audio Device"
    cfg = channel_config_name(device.channelConfiguration())
    channels = device.maximumChannelCount()
    ch_str = f"{channels} channel" if channels == 1 else f"{channels} channels"
    is_default = " [Default]" if device.isDefault() else ""
    return f"{name} [{cfg}, {ch_str}]{is_default}"


def describe_audio_output(audio_output: QAudioOutput) -> str:
    """Return detailed description of a QAudioOutput including volume and mute status."""
    dev = audio_output.device()
    dev_desc = describe_audio_device(dev)
    vol = int(round(audio_output.volume() * 100))
    muted_str = "MUTED" if audio_output.isMuted() else "Unmuted"
    return f"{dev_desc} (Volume: {vol}%, {muted_str})"


def describe_system_volume(audio_output: Optional[QAudioOutput] = None) -> list[str]:
    """Build a comprehensive multi-line summary of all system and application volume levels."""
    sys_vol = get_system_volume_info()
    lines = []

    # Windows Master Volume
    if sys_vol.get("master_volume_pct") is not None:
        db_str = f" ({sys_vol['master_volume_db']} dB)" if sys_vol.get("master_volume_db") is not None else ""
        mute_str = "MUTED" if sys_vol.get("master_muted") else "Unmuted"
        lines.append(f"Windows Master Volume: {sys_vol['master_volume_pct']}%{db_str} [{mute_str}]")

        # Per-channel volume breakdown
        ch_vols = sys_vol.get("channel_volumes", [])
        if ch_vols and len(ch_vols) > 1:
            ch_names = ["Left", "Right", "Center", "LFE", "Surround L", "Surround R", "Rear L", "Rear R"]
            entries = []
            for idx, cv in enumerate(ch_vols):
                label = ch_names[idx] if idx < len(ch_names) else f"Ch {idx}"
                entries.append(f"{label}: {cv}%")
            lines.append(f"  - Hardware Channels: {', '.join(entries)}")

    # Windows Volume Mixer (Application Session Volume)
    if sys_vol.get("app_mixer_volume_pct") is not None:
        app_mute_str = "MUTED" if sys_vol.get("app_mixer_muted") else "Unmuted"
        mixer_line = f"Windows Volume Mixer (Hammer 5 Tools): {sys_vol['app_mixer_volume_pct']}% [{app_mute_str}]"
        if sys_vol.get("app_mixer_muted") or (sys_vol["app_mixer_volume_pct"] <= 5):
            mixer_line += " [WARNING] [CRITICALLY LOW/MUTED: Audio may be inaudible!]"
        lines.append(mixer_line)

    # Qt Application Player Volume
    if audio_output is not None:
        qt_vol = int(round(audio_output.volume() * 100))
        qt_mute = "MUTED" if audio_output.isMuted() else "Unmuted"
        lines.append(f"Internal Player Volume: {qt_vol}% [{qt_mute}]")

        # Effective Volume calculation
        master = (sys_vol.get("master_volume_pct") or 100) / 100.0
        mixer = (sys_vol.get("app_mixer_volume_pct") or 100) / 100.0
        player = audio_output.volume()
        effective_pct = round(master * mixer * player * 100, 1)
        lines.append(f"Effective Volume Level: {effective_pct}% (Master {int(master*100)}% x Mixer {int(mixer*100)}% x Player {int(player*100)}%)")

    # Hardware Peak Level
    if sys_vol.get("hardware_peak_level") is not None:
        lines.append(f"Hardware Output Activity: Peak level {sys_vol['hardware_peak_level']:.3f}")

    return lines


def log_current_system_audio_devices() -> None:
    """Log the current default device, system volume hierarchy, and available devices to the console."""
    try:
        default_dev = QMediaDevices.defaultAudioOutput()
        log.info("Default audio output device: %s", describe_audio_device(default_dev))

        # Log detailed system volume information
        volume_lines = describe_system_volume()
        for vline in volume_lines:
            log.info("  %s", vline)

        all_devs = QMediaDevices.audioOutputs()
        if all_devs:
            summary = ", ".join(f"'{d.description()}'" for d in all_devs if not d.isNull())
            log.info("Available audio devices (%d): %s", len(all_devs), summary)
    except Exception as exc:
        log.warning("Could not query system audio devices: %s", exc)


def ensure_valid_audio_output(audio_output: QAudioOutput, context: str = "") -> bool:
    """Verify that audio_output is attached to a valid, connected device.

    If the device was disconnected, unplugs, or became null, falls back to the
    current system default audio output so playback is not silently dropped.
    Also detects and recovers from Windows Volume Mixer muting or zero volume.
    Returns True if the device had to be re-routed.
    """
    dev = audio_output.device()
    try:
        available_ids = [d.id() for d in QMediaDevices.audioOutputs()]
    except Exception:
        available_ids = []

    switched = False
    if dev.isNull() or (available_ids and dev.id() not in available_ids):
        default_dev = QMediaDevices.defaultAudioOutput()
        log.warning(
            "%sAudio output device '%s' is unavailable/disconnected. Re-routing to default: %s",
            f"[{context}] " if context else "",
            dev.description() if not dev.isNull() else "None",
            describe_audio_device(default_dev),
        )
        audio_output.setDevice(default_dev)
        switched = True

    # Unmute Qt player if accidentally muted
    if audio_output.isMuted():
        log.warning("%sPlayer was muted; unmuting for playback.", f"[{context}] " if context else "")
        audio_output.setMuted(False)

    if audio_output.volume() <= 0.0:
        log.warning("%sPlayer volume was 0%%; resetting to 100%%.", f"[{context}] " if context else "")
        audio_output.setVolume(1.0)

    # Check Windows Volume Mixer for this app
    sys_vol = get_system_volume_info()
    if sys_vol.get("app_mixer_muted"):
        log.warning(
            "%sHammer 5 Tools is MUTED in Windows Volume Mixer! Unmuting in Windows mixer...",
            f"[{context}] " if context else "",
        )
        set_windows_mixer_volume(level=(sys_vol.get("app_mixer_volume_pct") or 100) / 100.0)

    app_mixer_vol = sys_vol.get("app_mixer_volume_pct")
    if app_mixer_vol is not None and app_mixer_vol <= 5:
        log.warning(
            "%sHammer 5 Tools is set to %d%% in Windows Volume Mixer! Sounds may be inaudible while the VU meter moves.",
            f"[{context}] " if context else "",
            app_mixer_vol,
        )

    return switched


def log_audio_playback(audio_output: QAudioOutput, context: str = "") -> None:
    """Log the current audio output device, channel configuration, and volume levels to the console."""
    prefix = f"[{context}] " if context else ""
    dev = audio_output.device()
    dev_desc = describe_audio_device(dev)
    player_vol = int(round(audio_output.volume() * 100))

    sys_vol = get_system_volume_info()
    mixer_vol = sys_vol.get("app_mixer_volume_pct")
    master_vol = sys_vol.get("master_volume_pct")

    parts = [f"Player: {player_vol}%"]
    if mixer_vol is not None:
        parts.append(f"Win Mixer: {mixer_vol}%")
    if master_vol is not None:
        parts.append(f"Master: {master_vol}%")

    if mixer_vol is not None and master_vol is not None:
        effective = round((player_vol / 100.0) * (mixer_vol / 100.0) * (master_vol / 100.0) * 100, 1)
        parts.append(f"Effective: {effective}%")

    log.info("%sPlaying on audio channel: %s (%s)", prefix, dev_desc, ", ".join(parts))

    if mixer_vol is not None and mixer_vol <= 5:
        log.warning(
            "%s[WARNING] Windows Volume Mixer has Hammer 5 Tools set to only %d%%! If inaudible, raise volume in Windows Volume Mixer.",
            prefix,
            mixer_vol,
        )


def bind_audio_output_monitoring(
    audio_output: QAudioOutput,
    player: Optional[QMediaPlayer] = None,
    context: str = "",
) -> None:
    """Set up reactive monitoring and error logging for a QAudioOutput and QMediaPlayer."""
    global _media_devices_monitor

    if _media_devices_monitor is None:
        try:
            _media_devices_monitor = QMediaDevices()
            _media_devices_monitor.audioOutputsChanged.connect(_on_audio_outputs_changed)
        except Exception as exc:
            log.warning("Could not initialize QMediaDevices monitor: %s", exc)

    existing_refs = [r() for r in _monitored_outputs if r() is not None]
    if audio_output not in existing_refs:
        _monitored_outputs.append(weakref.ref(audio_output))

        def _on_device_changed():
            log.info(
                "%sAudio output device changed to: %s",
                f"[{context}] " if context else "",
                describe_audio_output(audio_output),
            )

        audio_output.deviceChanged.connect(_on_device_changed)

    if player is not None:
        def _on_error(error, error_string):
            log.error(
                "%sPlayer error (%s): %s",
                f"[{context}] " if context else "",
                error,
                error_string,
            )

        player.errorOccurred.connect(_on_error)


def _on_audio_outputs_changed() -> None:
    """Handler for OS audio device changes (plugging/unplugging headphones, etc.)."""
    log.info("System audio devices changed. Updating active audio outputs...")
    default_dev = QMediaDevices.defaultAudioOutput()
    log.info("New system default audio output: %s", describe_audio_device(default_dev))

    for vline in describe_system_volume():
        log.info("  %s", vline)

    active_refs = []
    for ref in _monitored_outputs:
        out = ref()
        if out is not None:
            active_refs.append(ref)
            try:
                ensure_valid_audio_output(out, context="DeviceChange")
            except Exception:
                pass

    _monitored_outputs[:] = active_refs
