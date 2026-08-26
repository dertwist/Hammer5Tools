"""Windows console window allocation, shared by startup (--console) and the
Preferences 'Open Console' button."""
import sys
import ctypes

SW_SHOW = 5


def allocate_console():
    if not ctypes.windll.kernel32.GetConsoleWindow():
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")


def open_console():
    """Show the console window, allocating one first if none exists yet."""
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if not hwnd:
        allocate_console()
    else:
        ctypes.windll.user32.ShowWindow(hwnd, SW_SHOW)
