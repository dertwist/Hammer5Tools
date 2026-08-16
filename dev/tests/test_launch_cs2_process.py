import os
import sys
from unittest.mock import patch, MagicMock
import pytest

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
src_dir = os.path.join(repo_root, "src")
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.other.addon_functions import launch_cs2_process, assemble_commands


def test_assemble_commands():
    template = " -addon addon_name -tool hammer -asset maps/addon_name.vmap"
    result = assemble_commands(template, "test_addon")
    assert result == " -addon test_addon -tool hammer -asset maps/test_addon.vmap"


def test_launch_cs2_process_com_success():
    mock_shell_com = MagicMock()
    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"win32com": MagicMock(), "win32com.client": MagicMock()}):
        import win32com.client
        win32com.client.Dispatch.return_value = mock_shell_com
        success = launch_cs2_process("C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe", "-tools -steam")
        assert success is True
        mock_shell_com.ShellExecute.assert_called_once()
        args = mock_shell_com.ShellExecute.call_args[0]
        assert args[0] == "C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe"
        assert args[1] == "-tools -steam"


def test_launch_cs2_process_shellexecute_success():
    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"win32com": None, "win32com.client": None}), \
         patch("ctypes.windll.shell32.ShellExecuteW", return_value=42) as mock_shell:
        success = launch_cs2_process("C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe", "-tools -steam")
        assert success is True
        mock_shell.assert_called_once()
        args = mock_shell.call_args[0]
        assert args[0] is None
        assert args[1] == "open"
        assert args[2] == "C:\\Games\\CS2\\game\\bin\\win64\\cs2.exe"
        assert args[3] == "-tools -steam"


def test_launch_cs2_process_shellexecute_fallback_to_popen():
    with patch("sys.platform", "win32"), \
         patch.dict("sys.modules", {"win32com": None, "win32com.client": None}), \
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
        assert kwargs.get("stdout") == -3  # subprocess.DEVNULL is -3 in Python


def test_job_object_limit_flags():
    from src.job_object import install_job_object
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
