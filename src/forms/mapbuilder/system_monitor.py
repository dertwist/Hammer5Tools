import sys
import re
import subprocess
from collections import deque

import psutil
import GPUtil

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont

# Matplotlib embed
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


# -------------------------
# Design System Colors (Hammer5Tools)
# -------------------------
class DesignColors:
    """Hammer5Tools design system color palette"""
    # Backgrounds
    BG_PRIMARY = "#1F2121"  # Charcoal-700
    BG_SURFACE = "#262828"  # Charcoal-800

    # Text
    TEXT_PRIMARY = "#F5F5F5"  # Gray-200
    TEXT_SECONDARY = "#A7A9A9"  # Gray-300 (dimmed)

    # Accents
    PRIMARY = "#32B8C6"  # Teal-300
    PRIMARY_HOVER = "#2DA6B2"  # Teal-400

    # Data visualization
    CPU_COLOR = "#FF5A5A"  # Red (warm)
    GPU_COLOR = "#32B8C6"  # Teal (cool)
    MEMORY_COLOR = "#FFD700"  # Gold (warning)

    # Chart background
    CHART_BG = "#262828"
    CHART_GRID = "#3A3C3C"
    CHART_TEXT = "#A7A9A9"


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
    """Use nvidia-smi CSV query for robust GPU stats"""
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

        first_line = None
        for line in out.splitlines():
            s = line.strip()
            if s:
                first_line = s
                break
        if not first_line:
            return None

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
    """Try to parse rocm-smi output for AMD GPU stats"""
    try:
        proc = subprocess.run(["rocm-smi"], capture_output=True, text=True, timeout=2)
        out = proc.stdout + proc.stderr
        if not out:
            return None

        usage_match = re.search(r"GPU\s*use\s*\(%\)\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)", out, re.IGNORECASE)
        if not usage_match:
            usage_match = re.search(r"GPU\s*use\s*\(%\)\s*[:]\s*([0-9]+(?:\.[0-9]+)?)", out, re.IGNORECASE)

        usage_pct = None
        if usage_match:
            usage_pct = _clamp_percent(_safe_float(usage_match.group(1)))

        mem_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)\s*MiB", out, re.IGNORECASE)
        used_gb = None
        total_gb = None
        if mem_match:
            used_mb = _safe_float(mem_match.group(1))
            total_mb = _safe_float(mem_match.group(2))
            used_gb = used_mb / 1024.0
            total_gb = total_mb / 1024.0

        if usage_pct is not None and used_gb is not None and total_gb is not None:
            return usage_pct, used_gb, total_gb

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
    """Try NVIDIA first, then AMD, then GPUtil fallback"""
    n = get_nvidia_stats()
    if n:
        return n[0], n[1], n[2], "NVIDIA"

    a = get_amd_stats()
    if a:
        return a[0], a[1], a[2], "AMD"

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
    """Graph widget with design system styling"""

    def __init__(self, title, max_points=60, color=DesignColors.PRIMARY):
        super().__init__()
        self.title = title
        self.color = color
        self.setContentsMargins(0, 0, 0, 0)
        self.max_points = max_points
        self.values = deque([0.0] * max_points, maxlen=max_points)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Title label
        self.label = QLabel(self.title)
        label_font = QFont()
        label_font.setPointSize(11)
        label_font.setWeight(QFont.Medium)
        self.label.setFont(label_font)
        self.label.setStyleSheet(f"color: {DesignColors.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(self.label)

        # Matplotlib figure with dark theme
        self.fig = Figure(figsize=(3, 2), facecolor=DesignColors.CHART_BG, edgecolor='none')
        self.fig.patch.set_alpha(1.0)

        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(DesignColors.CHART_BG)
        self.ax.set_ylim(0, 100)
        self.ax.set_xlim(0, max_points)
        self.ax.set_xticks([])
        self.ax.set_ylabel("%", color=DesignColors.CHART_TEXT, fontsize=9)
        self.ax.tick_params(colors=DesignColors.CHART_TEXT, labelsize=8)

        # Grid styling
        self.ax.grid(True, alpha=0.15, color=DesignColors.CHART_GRID, linestyle='--', linewidth=0.5)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color(DesignColors.CHART_GRID)
        self.ax.spines['bottom'].set_color(DesignColors.CHART_GRID)

        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setStyleSheet(f"background-color: {DesignColors.CHART_BG}; border: none;")
        layout.addWidget(self.canvas)

        # Container frame for visual separation
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {DesignColors.BG_SURFACE};
            }}
        """)

        self.setLayout(layout)

    def update_value(self, v, suffix_text=""):
        """Update graph with new value"""
        v = _clamp_percent(v)
        self.values.append(v)

        # Update label with current value
        self.label.setText(f"{self.title} – {v:.1f}%{suffix_text}")

        # Redraw graph
        self.ax.cla()
        self.ax.set_ylim(0, 100)
        self.ax.set_xlim(0, self.max_points)
        self.ax.set_xticks([])
        self.ax.set_ylabel("%", color=DesignColors.CHART_TEXT, fontsize=9)
        self.ax.tick_params(colors=DesignColors.CHART_TEXT, labelsize=8)
        self.ax.grid(True, alpha=0.15, color=DesignColors.CHART_GRID, linestyle='--', linewidth=0.5)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color(DesignColors.CHART_GRID)
        self.ax.spines['bottom'].set_color(DesignColors.CHART_GRID)
        self.ax.set_facecolor(DesignColors.CHART_BG)

        # Plot line with color
        self.ax.plot(list(self.values), color=self.color, linewidth=2, alpha=0.9)
        self.ax.fill_between(range(len(self.values)), list(self.values), alpha=0.15, color=self.color)

        self.canvas.draw_idle()


# -------------------------
# Main System Monitor Widget
# -------------------------
class SystemMonitor(QWidget):
    """System resource monitor with design system styling"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Monitor")
        self.setMinimumWidth(200)
        self.setContentsMargins(0, 0, 0, 0)

        # Apply stylesheet
        self.setStyleSheet(f"""
            SystemMonitor {{
                background-color: {DesignColors.BG_PRIMARY};
            }}
        """)

        # Create graphs with different colors
        self.cpu_graph = HistoryGraph("CPU Usage", color=DesignColors.CPU_COLOR)
        self.ram_graph = HistoryGraph("Memory Usage", color=DesignColors.MEMORY_COLOR)
        self.gpu_graph = HistoryGraph("GPU Usage", color=DesignColors.GPU_COLOR)

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self.cpu_graph)
        layout.addWidget(self.ram_graph)
        layout.addWidget(self.gpu_graph)

        self.setLayout(layout)

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)  # Update every second

        self.update_stats()

    def update_stats(self):
        """Update all system stats"""
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
# Demo/Test
# -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SystemMonitor()
    win.show()
    sys.exit(app.exec())
