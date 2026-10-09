"""Exercise the compile worker without generated UI modules or a CS2 install."""

import ast
import io
import logging
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QEventLoop, QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import QApplication


@pytest.mark.parametrize("exit_code, real_process", [
    (0, False), (1, False), (-1, False), (0xC0000005, False), (0xFFFFFFFF, False),
    pytest.param(0xC0000005, True, marks=pytest.mark.skipif(
        sys.platform != "win32", reason="Windows process crash status",
    )),
])
def test_compiler_exit_code_survives_queued_signal(monkeypatch, exit_code, real_process):
    source = Path(__file__).resolve().parents[1] / "gui/forms/mapbuilder/main.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    worker_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "CompilationThread"
    )
    namespace = dict(
        QThread=QThread, Signal=Signal, subprocess=subprocess, time=time,
        log=logging.getLogger(__name__),
    )
    exec(compile(ast.Module(body=[worker_class], type_ignores=[]), str(source), "exec"), namespace)

    command = "unused"
    output = "Encountered accessviolation. Wrote minidump"
    if real_process:
        command = subprocess.list2cmdline([
            sys.executable, "-c",
            f"import ctypes; print({output!r}, flush=True); "
            f"ctypes.windll.kernel32.ExitProcess({exit_code})",
        ])
    else:
        process = Mock(stdout=io.BytesIO(b""), returncode=exit_code)
        process.poll.return_value = exit_code
        monkeypatch.setattr(subprocess, "Popen", Mock(return_value=process))
        monkeypatch.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0, raising=False)

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    loop = QEventLoop()
    received = []

    def on_finished(code, elapsed):
        received.append((code, elapsed))
        loop.quit()

    worker = namespace["CompilationThread"](command, ".")
    lines = []
    worker.outputReceived.connect(lines.append, Qt.ConnectionType.QueuedConnection)
    worker.finished.connect(on_finished, Qt.ConnectionType.QueuedConnection)
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(5000)
    worker.start()
    loop.exec()
    worker.wait()
    timeout.stop()
    if worker.process is not None:
        worker.process.stdout.close()

    assert app is not None
    assert len(received) == 1
    assert received[0][0] == exit_code
    assert received[0][1] >= 0
    if real_process:
        assert lines == [output]
