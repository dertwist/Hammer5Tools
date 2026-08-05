"""Keep child processes from opening console windows in the frozen build.

A --windowed PyInstaller build has no console of its own, so every console
child process (dotnet for the Unreal bridge, resourcecompiler, ffmpeg,
taskkill, git) gets Windows to hand it a brand new console window. Call sites
that remembered `creationflags=CREATE_NO_WINDOW` are fine; the rest spam
black windows. Patching the default in one place covers every call site,
including psutil.Popen, which subclasses subprocess.Popen.
"""
import sys


def install():
    """Default CREATE_NO_WINDOW for child processes. No-op when this process
    has a console of its own (dev run from a terminal, or --console), so
    non-redirected child output still lands where it can be read."""
    if sys.platform != 'win32':
        return
    import ctypes
    import subprocess
    if ctypes.windll.kernel32.GetConsoleWindow():
        return

    own_console = subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS
    original = subprocess.Popen.__init__

    def __init__(self, *args, **kwargs):
        flags = kwargs.get('creationflags', 0)
        if not flags & own_console:
            kwargs['creationflags'] = flags | subprocess.CREATE_NO_WINDOW
        original(self, *args, **kwargs)

    subprocess.Popen.__init__ = __init__


def demo():
    """Flag arithmetic only — install() itself needs a real windowless process."""
    import subprocess
    own_console = subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS

    def flags_for(given):
        return given if given & own_console else given | subprocess.CREATE_NO_WINDOW

    assert flags_for(0) == subprocess.CREATE_NO_WINDOW
    assert flags_for(subprocess.CREATE_NEW_PROCESS_GROUP) == (
        subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
    assert flags_for(subprocess.CREATE_NEW_CONSOLE) == subprocess.CREATE_NEW_CONSOLE
    assert flags_for(subprocess.DETACHED_PROCESS) == subprocess.DETACHED_PROCESS
    print("no_console demo ok")


if __name__ == "__main__":
    demo()
