"""Taskbar identity for the GUI window.

The taskbar button always belongs to the process that owns the window
(Hammer5ToolsGUI.exe), so "Pin to taskbar" would otherwise pin the child
process. The shell relaunch properties override that: the pin, its name and
its icon come from the launcher, and a launcher-started window docks into the
same pinned button because both share one AppUserModelID.
"""

import ctypes
from ctypes import wintypes
import sys

APP_USER_MODEL_ID = "Hammer5Tools"
DISPLAY_NAME = "Hammer 5 Tools"


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", wintypes.DWORD)]


class _PROPVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", wintypes.WORD),
        ("reserved1", wintypes.WORD),
        ("reserved2", wintypes.WORD),
        ("reserved3", wintypes.WORD),
        ("value", ctypes.c_ubyte * 16),
    ]


# PSGUID_APPUSERMODEL {9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}
_APPUSERMODEL = _GUID(0x9F4C2855, 0x9F79, 0x4B39,
                      (ctypes.c_ubyte * 8)(0xA8, 0xD0, 0xE1, 0xD4, 0x2D, 0xE1, 0xD5, 0xF3))
# IID_IPropertyStore {886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}
_IPROPERTYSTORE = _GUID(0x886D8EEB, 0x8CF2, 0x4446,
                        (ctypes.c_ubyte * 8)(0x8D, 0x02, 0xCD, 0xBA, 0x1D, 0xBD, 0xCF, 0x99))

_PID_ID = 5
_PID_RELAUNCH_COMMAND = 2
_PID_RELAUNCH_ICON = 3
_PID_RELAUNCH_DISPLAY_NAME = 4


def _method(store, index, *argument_types):
    vtable = ctypes.cast(store, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    prototype = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *argument_types)
    return prototype(vtable[index])


def _set_property(store, pid, value):
    variant = _PROPVARIANT()
    init = ctypes.windll.propsys.InitPropVariantFromString
    init.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(_PROPVARIANT)]
    init.restype = ctypes.HRESULT
    init(value, ctypes.byref(variant))
    try:
        key = _PROPERTYKEY(_APPUSERMODEL, pid)
        set_value = _method(store, 6, ctypes.POINTER(_PROPERTYKEY), ctypes.POINTER(_PROPVARIANT))
        set_value(store, ctypes.byref(key), ctypes.byref(variant))
    finally:
        ctypes.windll.ole32.PropVariantClear(ctypes.byref(variant))


def apply_taskbar_identity(window) -> None:
    """Point the taskbar button of `window` at the launcher. Call before show()."""
    if sys.platform != "win32":
        return
    try:
        from core.runtime_paths import resolve_runtime_paths
        launcher = resolve_runtime_paths().install_root / "Hammer5Tools.exe"
        if not launcher.is_file():
            return  # development run: no launcher to relaunch through

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)

        get_store = ctypes.windll.shell32.SHGetPropertyStoreForWindow
        get_store.argtypes = [wintypes.HWND, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)]
        get_store.restype = ctypes.HRESULT
        store = ctypes.c_void_p()
        get_store(wintypes.HWND(int(window.winId())), ctypes.byref(_IPROPERTYSTORE), ctypes.byref(store))
        try:
            _set_property(store, _PID_ID, APP_USER_MODEL_ID)
            _set_property(store, _PID_RELAUNCH_COMMAND, f'"{launcher}"')
            _set_property(store, _PID_RELAUNCH_DISPLAY_NAME, DISPLAY_NAME)
            _set_property(store, _PID_RELAUNCH_ICON, f'{launcher},0')
            _method(store, 7)(store)  # Commit
        finally:
            _method(store, 2)(store)  # Release
    except Exception:
        pass  # taskbar polish is never worth failing startup over


if __name__ == "__main__":
    # Wrong struct layouts would corrupt memory instead of failing loudly.
    assert ctypes.sizeof(_GUID) == 16
    assert ctypes.sizeof(_PROPERTYKEY) == 20
    assert ctypes.sizeof(_PROPVARIANT) == (24 if ctypes.sizeof(ctypes.c_void_p) == 8 else 16)
    print("ok")
