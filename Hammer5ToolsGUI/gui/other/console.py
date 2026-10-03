"""Windows console window allocation, shared by startup (--console) and the
Preferences 'Open Console' button."""
import ctypes
import logging
import sys

SW_SHOW = 5
SW_RESTORE = 9

SC_CLOSE = 0xF060
MF_BYCOMMAND = 0x00000000
MF_GRAYED = 0x00000001


def _attach_logging_stream() -> None:
    """Route application log records to the current console."""
    root = logging.getLogger()
    for handler in root.handlers:
        if getattr(handler, "_h5t_console", False):
            handler.stream = sys.stderr
            return
        if getattr(handler, "_h5t", False) and type(handler) is logging.StreamHandler:
            handler.stream = sys.stderr
            handler._h5t_console = True
            return

    try:
        from gui.logs import _FORMAT
        fmt = _FORMAT
    except Exception:
        fmt = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter(fmt))
    console_handler._h5t = True
    console_handler._h5t_console = True
    root.addHandler(console_handler)


def allocate_console() -> int | None:
    """Allocate and configure a Windows console window.

    In packaged release builds launched with CREATE_NO_WINDOW, Windows attaches
    an invisible console without a window. FreeConsole() detaches from that
    windowless console so AllocConsole() can create a visible one.
    """
    if sys.platform != "win32":
        return None

    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if not hwnd:
        ctypes.windll.kernel32.FreeConsole()
        if not ctypes.windll.kernel32.AllocConsole():
            return None
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()

    if hwnd:
        ctypes.windll.kernel32.SetConsoleTitleW("Hammer 5 Tools Console")
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)

        # Disable the close ('X') button so closing the console does not kill
        # the entire Hammer 5 Tools process.
        hmenu = ctypes.windll.user32.GetSystemMenu(hwnd, False)
        if hmenu:
            ctypes.windll.user32.EnableMenuItem(hmenu, SC_CLOSE, MF_BYCOMMAND | MF_GRAYED)

    try:
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
    except OSError:
        pass
    try:
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
    except OSError:
        pass
    try:
        sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
    except OSError:
        pass

    _attach_logging_stream()
    try:
        from gui.other.audio_device import log_current_system_audio_devices
        log_current_system_audio_devices()
    except Exception:
        pass
    return hwnd


def open_console() -> int | None:
    """Show the console window, allocating one first if none exists yet."""
    if sys.platform != "win32":
        return None

    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if not hwnd:
        hwnd = allocate_console()

    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
        ctypes.windll.user32.SetForegroundWindow(hwnd)

    return hwnd

