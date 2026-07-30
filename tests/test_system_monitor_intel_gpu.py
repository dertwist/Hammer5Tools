"""
Verification for Intel GPU (oneAPI / xpu-smi) support added to the Map Builder
system monitor.

Regression this guards against: before this change, GPUStatsWorker had no Intel
path, so Intel-Arc/Xe machines reported "No GPU detected". The parsing must also
be robust to xpu-smi's column reordering, timestamp/device prefixes, and the
fact that `xpu-smi dump` loops forever unless given `-n 1`.

These tests never call a real xpu-smi / nvidia-smi binary; subprocess.run is
monkeypatched, so they run on any machine without an Intel GPU installed.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_dir = os.path.join(root_dir, "src")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import subprocess
from unittest.mock import patch

import pytest

from PySide6.QtWidgets import QApplication

from src.forms.mapbuilder.system_monitor import GPUStatsWorker


app = QApplication.instance() or QApplication([])


class _FakeProc:
    """Stand-in for subprocess.CompletedProcess with just what the code reads."""
    def __init__(self, stdout="", stderr=""):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = 0


def _make_worker():
    # QObject needs the QApplication (created above) to exist.
    return GPUStatsWorker()


def _run_map(commands_to_outputs):
    """Return a fake subprocess.run that maps a cmd list to a canned stdout.

    `commands_to_outputs`: dict mapping a key substring (e.g. "xpu-smi") to
    either a stdout string or a _FakeProc. Any unknown command returns empty
    output (simulating "binary not present").
    """
    def fake_run(cmd, *args, **kwargs):
        joined = " ".join(cmd)
        for key, out in commands_to_outputs.items():
            if key in joined:
                proc = out if isinstance(out, _FakeProc) else _FakeProc(stdout=out)
                return proc
        return _FakeProc(stdout="")
    return fake_run


# ---------------------------------------------------------------------------
# Intel parsing
# ---------------------------------------------------------------------------

def test_intel_noheader_with_timestamp_and_device_prefix():
    """xpu-smi may prepend timestamp + device columns before the 3 metrics."""
    worker = _make_worker()
    out = "2026-07-30 10:00:00, 0, 42, 7168, 7168\n"
    with patch("src.forms.mapbuilder.system_monitor.subprocess.run",
               side_effect=_run_map({"xpu-smi": out})):
        res = worker._get_intel_stats()
    assert res is not None
    usage, used_gb, total_gb = res
    assert usage == 42.0
    assert used_gb == pytest.approx(7168 / 1024.0)
    assert total_gb == pytest.approx((7168 + 7168) / 1024.0)


def test_intel_noheader_metrics_only():
    """Some xpu-smi versions emit only the requested metric columns."""
    worker = _make_worker()
    with patch("src.forms.mapbuilder.system_monitor.subprocess.run",
               side_effect=_run_map({"xpu-smi": "55, 3072, 5120"})):
        res = worker._get_intel_stats()
    assert res is not None
    usage, used_gb, total_gb = res
    assert usage == 55.0
    assert total_gb == pytest.approx((3072 + 5120) / 1024.0)


def test_intel_empty_output_returns_none():
    """No xpu-smi installed / empty response -> no crash, returns None."""
    worker = _make_worker()
    with patch("src.forms.mapbuilder.system_monitor.subprocess.run",
               side_effect=_run_map({"xpu-smi": ""})):
        assert worker._get_intel_stats() is None


def test_intel_headered_fallback_parses_by_column_name():
    """If a build emits headers, columns are matched by name (reordering-safe)."""
    worker = _make_worker()
    headered = (
        "Timestamp,Device ID,GPU Memory Free (MiB),GPU Utilization (%),"
        "GPU Memory Used (MiB)\n"
        "2026-07-30 10:00:00,0,7168,42,7168\n"
    )
    with patch("src.forms.mapbuilder.system_monitor.subprocess.run",
               side_effect=_run_map({"xpu-smi": headered})):
        res = worker._get_intel_stats()
    assert res is not None
    usage, used_gb, total_gb = res
    assert usage == 42.0
    assert used_gb == pytest.approx(7168 / 1024.0)
    assert total_gb == pytest.approx((7168 + 7168) / 1024.0)


# ---------------------------------------------------------------------------
# Dispatch ordering
# ---------------------------------------------------------------------------

def test_dispatch_picks_intel_when_nvidia_absent():
    """If nvidia-smi is absent but xpu-smi responds, vendor should be Intel."""
    worker = _make_worker()
    with patch("src.forms.mapbuilder.system_monitor.subprocess.run",
               side_effect=_run_map({
                   "nvidia-smi": "",   # no NVIDIA
                   "xpu-smi": "30, 2048, 6144",
               })):
        usage, used_gb, total_gb, vendor = worker._get_gpu_stats()
    assert vendor == "Intel"
    assert usage == 30.0


def test_dispatch_nvidia_takes_precedence_over_intel():
    """NVIDIA is tried first; Intel is only a fallback when NVIDIA is absent."""
    worker = _make_worker()
    with patch("src.forms.mapbuilder.system_monitor.subprocess.run",
               side_effect=_run_map({
                   "nvidia-smi": "70, 4096, 8192",  # present -> wins
                   "xpu-smi": "30, 2048, 6144",
               })):
        usage, used_gb, total_gb, vendor = worker._get_gpu_stats()
    assert vendor == "NVIDIA"
    assert usage == 70.0


def test_dispatch_returns_none_when_nothing_present():
    """No NVIDIA, no Intel, no AMD, GPUtil finds nothing -> all None."""
    worker = _make_worker()
    with patch("src.forms.mapbuilder.system_monitor.subprocess.run",
               side_effect=_run_map({"nvidia-smi": "", "xpu-smi": "", "rocm-smi": ""})), \
         patch("src.forms.mapbuilder.system_monitor.GPUtil.getGPUs", return_value=[]):
        res = worker._get_gpu_stats()
    assert res == (None, None, None, None)
