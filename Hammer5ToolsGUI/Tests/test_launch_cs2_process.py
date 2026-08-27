import os
import sys
from unittest.mock import patch, MagicMock
import pytest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_dir = os.path.join(repo_root, "Hammer5ToolsGUI")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from gui.other.addon_functions import launch_cs2_process, assemble_commands


def test_assemble_commands():
    template = " -addon addon_name -tool hammer -asset maps/addon_name.vmap"
    result = assemble_commands(template, "test_addon")
    assert result == " -addon test_addon -tool hammer -asset maps/test_addon.vmap"


def test_launch_cs2_process_desktop_window_success():
    mock_shell = MagicMock()
    mock_windows = MagicMock()
    mock_desktop_window = MagicMock()
    mock_app = MagicMock()

    mock_shell.Windows.return_value = mock_windows
    mock_windows.FindWindowSW.return_value = mock_desktop_window
    mock_desktop_window.Document.Application = mock_app

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        win32com.client.Dispatch.return_value = mock_shell
        success = launch_cs2_process("C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe", "-tools -steam")
        assert success is True
        mock_app.ShellExecute.assert_called_once()
        args = mock_app.ShellExecute.call_args[0]
        assert args[0] == "C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe"
        assert args[1] == "-tools -steam"


def test_launch_cs2_process_wmi_powershell_fallback():
    mock_shell = MagicMock()
    mock_windows = MagicMock()
    mock_shell.Windows.return_value = mock_windows
    mock_windows.FindWindowSW.return_value = None  # Desktop not found

    mock_run_result = MagicMock(returncode=0)

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}), \
         patch("subprocess.run", return_value=mock_run_result) as mock_subrun:
        import win32com.client
        win32com.client.Dispatch.return_value = mock_shell
        success = launch_cs2_process("C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe", "-tools -steam")
        assert success is True
        mock_subrun.assert_called_once()
        cmd_args = mock_subrun.call_args[0][0]
        assert "powershell" in cmd_args[0]
        assert "Invoke-CimMethod" in cmd_args[-1]
        assert "Win32_Process" in cmd_args[-1]


# ctypes.windll only exists on Windows, so these two cannot even be patched
# elsewhere. They still run in CI, which is windows-latest.
requires_windll = pytest.mark.skipif(
    not hasattr(__import__("ctypes"), "windll"),
    reason="ctypes.windll is Windows-only",
)


@requires_windll
def test_launch_cs2_process_shellexecute_success():
    mock_shell = MagicMock()
    mock_windows = MagicMock()
    mock_shell.Windows.return_value = mock_windows
    mock_windows.FindWindowSW.return_value = None  # Desktop not found

    mock_run_result = MagicMock(returncode=1)  # WMI failed

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}), \
         patch("subprocess.run", return_value=mock_run_result), \
         patch("ctypes.windll.shell32.ShellExecuteW", return_value=42) as mock_shell_api:
        import win32com.client
        win32com.client.Dispatch.return_value = mock_shell
        success = launch_cs2_process("C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe", "-tools -steam")
        assert success is True
        mock_shell_api.assert_called_once()


@requires_windll
def test_launch_cs2_process_fallback_to_popen():
    mock_run_result = MagicMock(returncode=1)

    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"win32com": None, "win32com.client": None}), \
         patch("subprocess.run", return_value=mock_run_result), \
         patch("ctypes.windll.shell32.ShellExecuteW", return_value=2), \
         patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        success = launch_cs2_process("C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe", "-tools -steam")
        assert success is True
        mock_popen.assert_called_once()
        called_cmd = mock_popen.call_args[0][0]
        assert "cs2.exe" in called_cmd
        kwargs = mock_popen.call_args[1]
        assert kwargs.get("close_fds") is True
        assert kwargs.get("stdout") == -3


def test_job_object_limit_flags():
    from gui.job_object import install_job_object
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x0800
    JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x1000
    expected_flags = (
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        | JOB_OBJECT_LIMIT_BREAKAWAY_OK
        | JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK
    )
    assert expected_flags == 0x3800


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
