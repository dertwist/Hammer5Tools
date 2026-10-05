"""Tests for Windows console window allocation and IPC console forwarding."""
import io
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest
from gui.other import console
from gui.shell.ipc_protocol import IPCCommand, IPCMessage


def test_allocate_console_when_no_window_exists(monkeypatch):
    """When running without a console window (e.g. packaged release build launched
    with CREATE_NO_WINDOW), allocate_console must detach the windowless console,
    allocate a new console, configure window title/CP, disable SC_CLOSE, and route logging."""
    fake_kernel32 = MagicMock()
    fake_user32 = MagicMock()

    # First call returns 0 (windowless), second call returns window handle 4242
    fake_kernel32.GetConsoleWindow.side_effect = [0, 4242]
    fake_kernel32.FreeConsole.return_value = 1
    fake_kernel32.AllocConsole.return_value = 1
    fake_kernel32.SetConsoleTitleW.return_value = 1
    fake_kernel32.SetConsoleOutputCP.return_value = 1
    fake_kernel32.SetConsoleCP.return_value = 1

    fake_hmenu = 9999
    fake_user32.GetSystemMenu.return_value = fake_hmenu
    fake_user32.EnableMenuItem.return_value = 0

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(console.ctypes.windll, "kernel32", fake_kernel32)
    monkeypatch.setattr(console.ctypes.windll, "user32", fake_user32)

    fake_stream = io.StringIO()
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: fake_stream)

    hwnd = console.allocate_console()

    assert hwnd == 4242
    fake_kernel32.FreeConsole.assert_called_once()
    fake_kernel32.AllocConsole.assert_called_once()
    fake_kernel32.SetConsoleTitleW.assert_called_once_with("Hammer 5 Tools Console")
    fake_kernel32.SetConsoleOutputCP.assert_called_once_with(65001)
    fake_kernel32.SetConsoleCP.assert_called_once_with(65001)
    fake_user32.GetSystemMenu.assert_called_once_with(4242, False)
    fake_user32.EnableMenuItem.assert_called_once_with(
        fake_hmenu, console.SC_CLOSE, console.MF_BYCOMMAND | console.MF_GRAYED
    )


def test_open_console_restores_and_focuses_existing_window(monkeypatch):
    """When a console window already exists, open_console restores it and brings it to front."""
    fake_kernel32 = MagicMock()
    fake_user32 = MagicMock()

    fake_kernel32.GetConsoleWindow.return_value = 5555
    fake_user32.ShowWindow.return_value = 1
    fake_user32.SetForegroundWindow.return_value = 1

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(console.ctypes.windll, "kernel32", fake_kernel32)
    monkeypatch.setattr(console.ctypes.windll, "user32", fake_user32)

    hwnd = console.open_console()

    assert hwnd == 5555
    fake_kernel32.AllocConsole.assert_not_called()
    fake_user32.ShowWindow.assert_called_once_with(5555, console.SW_RESTORE)
    fake_user32.SetForegroundWindow.assert_called_once_with(5555)


def test_allocate_console_handles_alloc_failure(monkeypatch):
    """If AllocConsole returns 0, allocate_console gracefully returns None."""
    fake_kernel32 = MagicMock()
    fake_kernel32.GetConsoleWindow.return_value = 0
    fake_kernel32.FreeConsole.return_value = 1
    fake_kernel32.AllocConsole.return_value = 0

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(console.ctypes.windll, "kernel32", fake_kernel32)

    hwnd = console.allocate_console()
    assert hwnd is None


def test_allocate_console_non_windows(monkeypatch):
    """On non-Windows platforms, allocate_console returns None without errors."""
    monkeypatch.setattr(sys, "platform", "linux")
    assert console.allocate_console() is None
    assert console.open_console() is None


def test_attach_logging_stream_updates_existing_handler():
    """_attach_logging_stream redirects root logging stream to sys.stderr."""
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    try:
        dummy_stream = io.StringIO()
        existing_handler = logging.StreamHandler(dummy_stream)
        existing_handler._h5t = True
        root.handlers = [existing_handler]

        target_stderr = io.StringIO()
        with patch.object(sys, "stderr", target_stderr):
            console._attach_logging_stream()
            assert existing_handler.stream is target_stderr
            assert getattr(existing_handler, "_h5t_console", False) is True
    finally:
        root.handlers = old_handlers


def test_ipc_message_create_show_forwards_arguments():
    """IPCMessage.create_show with arguments serializes them into the message payload."""
    serialized = IPCMessage.create_show(["--console"])
    parsed = IPCMessage.parse(serialized.encode("utf-8"))
    assert parsed["protocol_version"] == 1
    assert parsed["command"] == IPCCommand.SHOW_WINDOW.value
    assert parsed["arguments"] == ["--console"]
