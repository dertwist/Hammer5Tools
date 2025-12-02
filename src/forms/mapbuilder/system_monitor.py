import sys
import re
import subprocess
from collections import deque

import psutil
import GPUtil

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import QTimer

# Matplotlib embed
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


# -------------------------
# Helper: safe numeric parse
# -------------------------
def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def _clamp_percent(v):
    try:
        fv = float(v)
    except Exception:
        return 0.0
    if fv != fv:  # NaN
        return 0.0
    if fv < 0:
        return 0.0
    if fv > 100:
        return 100.0
    return fv


# -------------------------
# GPU stat functions
# -------------------------
def get_nvidia_stats():
    """
    Use nvidia-smi CSV query which returns numeric values and is robust.
    Returns tuple (usage_percent, vram_used_gb, vram_total_gb) or None if not available.
    """
    try:
        cmd = [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        out = proc.stdout.strip()
        if not out:
            return None

        # In multi-GPU systems there may be multiple lines; take first non-empty line
        first_line = None
        for line in out.splitlines():
            s = line.strip()
            if s:
                first_line = s
                break
        if not first_line:
            return None

        # CSV without headers, e.g.: "12, 13213, 16384"
        parts = [p.strip() for p in first_line.split(",")]
        if len(parts) < 3:
            return None

        usage_pct = _clamp_percent(_safe_float(parts[0]))
        used_mb = _safe_float(parts[1])
        total_mb = _safe_float(parts[2])

        used_gb = used_mb / 1024.0
        total_gb = total_mb / 1024.0

        return usage_pct, used_gb, total_gb
    except Exception:
        return None


def get_amd_stats():
    """
    Try to parse rocm-smi output robustly for GPU use% and VRAM usage.
    Returns tuple (usage_percent, vram_used_gb, vram_total_gb) or None.
    """
    try:
        proc = subprocess.run(["rocm-smi"], capture_output=True, text=True, timeout=2)
        out = proc.stdout + proc.stderr
        if not out:
            return None

        # Look for usage percentage patterns, like "GPU use (%) : 35"
        usage_match = re.search(r"GPU\s*use\s*\(%\)\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)", out, re.IGNORECASE)
        if not usage_match:
            # alternative pattern: "GPU[0]        : GPU use (%) : 35"
            usage_match = re.search(r"GPU\s*use\s*\(%\)\s*[:]\s*([0-9]+(?:\.[0-9]+)?)", out, re.IGNORECASE)

        usage_pct = None
        if usage_match:
            usage_pct = _clamp_percent(_safe_float(usage_match.group(1)))

        # Look for VRAM lines with "MiB" and " / " like "13213 / 16384 MiB"
        mem_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)\s*MiB", out, re.IGNORECASE)
        used_gb = None
        total_gb = None
        if mem_match:
            used_mb = _safe_float(mem_match.group(1))
            total_mb = _safe_float(mem_match.group(2))
            used_gb = used_mb / 1024.0
            total_gb = total_mb / 1024.0

        # If we found both usage and memory, return them
        if usage_pct is not None and used_gb is not None and total_gb is not None:
            return usage_pct, used_gb, total_gb

        # Some rocm-smi builds provide lines like "VRAM Usage: 1234 MiB"
        # As a fallback try to extract any percent and any two MiB numbers
        if usage_pct is None:
            p = re.search(r"([0-9]{1,3})\s*%", out)
            if p:
                usage_pct = _clamp_percent(_safe_float(p.group(1)))

        if used_gb is None or total_gb is None:
            all_mib = re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*MiB", out, re.IGNORECASE)
            if len(all_mib) >= 2:
                used_gb = _safe_float(all_mib[0]) / 1024.0
                total_gb = _safe_float(all_mib[1]) / 1024.0

        if usage_pct is not None and used_gb is not None and total_gb is not None:
            return usage_pct, used_gb, total_gb

    except Exception:
        pass

    return None


def get_gpu_stats():
    """
    Try NVIDIA (nvidia-smi) first, then AMD (rocm-smi), then GPUtil fallback.
    Returns (usage_pct, used_gb, total_gb, vendor_str) or (None, None, None, None)
    """
    n = get_nvidia_stats()
    if n:
        return n[0], n[1], n[2], "NVIDIA"

    a = get_amd_stats()
    if a:
        return a[0], a[1], a[2], "AMD"

    # Fallback to GPUtil if vendor tools not present (GPUtil reports in MB)
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            g = gpus[0]
            usage = _clamp_percent(g.load * 100)
            used_gb = (g.memoryUsed / 1024.0) if g.memoryUsed is not None else None
            total_gb = (g.memoryTotal / 1024.0) if g.memoryTotal is not None else None
            return usage, used_gb, total_gb, "GPUtil"
    except Exception:
        pass

    return None, None, None, None


# -------------------------
# History graph widget
# -------------------------
class HistoryGraph(QWidget):
    def __init__(self, title, max_points=60):
        super().__init__()
        self.title = title
        self.setContentsMargins(0,0,0,0)
        self.max_points = max_points
        self.values = deque([0.0] * max_points, maxlen=max_points)

        layout = QVBoxLayout()
        self.label = QLabel(self.title)
        self.label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.label)

        self.fig = Figure(figsize=(3, 2))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_ylim(0, 100)
        self.ax.set_xlim(0, max_points)
        self.ax.set_xticks([])
        self.ax.set_ylabel("%")

        self.canvas = FigureCanvasQTAgg(self.fig)
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def update_value(self, v, suffix_text=""):
        v = _clamp_percent(v)
        self.values.append(v)
        # update label
        self.label.setText(f"{self.title} – {v:.1f}%{suffix_text}")
        # redraw
        self.ax.cla()
        self.ax.set_ylim(0, 100)
        self.ax.set_xlim(0, self.max_points)
        self.ax.set_xticks([])
        self.ax.set_ylabel("%")
        self.ax.plot(list(self.values))
        self.canvas.draw()


# -------------------------
# Main window
# -------------------------
class SystemMonitor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Monitor")
        self.setMinimumWidth(200)
        self.setContentsMargins(0,0,0,0)

        self.cpu_graph = HistoryGraph("CPU Usage")
        self.ram_graph = HistoryGraph("Memory Usage")
        self.gpu_graph = HistoryGraph("GPU Usage")

        layout = QHBoxLayout()
        layout.addWidget(self.cpu_graph)
        layout.addWidget(self.ram_graph)
        layout.addWidget(self.gpu_graph)
        self.setLayout(layout)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

        self.update_stats()

    def update_stats(self):
        # CPU
        cpu = psutil.cpu_percent(interval=0.0)
        self.cpu_graph.update_value(cpu)

        # RAM
        ram = psutil.virtual_memory().percent
        self.ram_graph.update_value(ram)

        # GPU
        usage, used_gb, total_gb, vendor = get_gpu_stats()
        if usage is not None:
            suffix = ""
            if used_gb is not None and total_gb is not None:
                suffix = f" ({used_gb:.1f} GB / {total_gb:.1f} GB)"
            else:
                suffix = f" ({vendor})" if vendor else ""
            self.gpu_graph.update_value(usage, suffix)
        else:
            self.gpu_graph.update_value(0.0, " (No GPU detected)")

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SystemMonitor()
    win.show()
    sys.exit(app.exec())
