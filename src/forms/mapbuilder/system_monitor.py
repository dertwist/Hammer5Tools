import sys
import re
import subprocess
from collections import deque

import psutil
import GPUtil

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
)
from PySide6.QtCore import QTimer, Qt, QThread, QObject, Signal, Slot
from PySide6.QtGui import QColor, QFont

# Matplotlib embed
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


# Design System Colors (Hammer5Tools)
class DesignColors:
    """Hammer5Tools design system color palette"""
    # Backgrounds
    BG_PRIMARY = "#1F2121"  # Charcoal-700
    BG_SURFACE = "#262828"  # Charcoal-800

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


# Helper: safe numeric parse
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


def _find_col(headers, names):
    """Return the index of the first CSV header containing any of the given
    substrings (case-insensitive), or -1 if none match. Makes parsing robust
    against vendor tools that reorder columns or add timestamp/device prefixes.
    """
    for i, h in enumerate(headers):
        for n in names:
            if n in h:
                return i
    return -1


# Worker for GPU stats (runs in separate thread)
class GPUStatsWorker(QObject):
    """Worker object for fetching GPU stats in a separate thread"""
    statsReady = Signal(object, object, object, object)  # usage, used_gb, total_gb, vendor
    finished = Signal()

    def __init__(self):
        super().__init__()
        self._running = True

    @Slot()
    def fetch_gpu_stats(self):
        """Fetch GPU stats - runs in worker thread"""
        # Check if we're in the correct thread context
        if QThread.currentThread().loopLevel() > 0:
            # We're in an event loop, safe to proceed
            pass

        usage, used_gb, total_gb, vendor = self._get_gpu_stats()
        self.statsReady.emit(usage, used_gb, total_gb, vendor)
        self.finished.emit()

    def _get_gpu_stats(self):
        """Try NVIDIA first, then Intel, then AMD, then GPUtil fallback.

        Order rationale: NVIDIA (nvidia-smi) and Intel (xpu-smi, oneAPI/Level
        Zero) are the most reliable cross-platform CLIs. AMD's rocm-smi is
        Linux/data-center oriented, so it is tried last. GPUtil is a final
        NVIDIA-only fallback.
        """
        n = self._get_nvidia_stats()
        if n:
            return n[0], n[1], n[2], "NVIDIA"

        i = self._get_intel_stats()
        if i:
            return i[0], i[1], i[2], "Intel"

        a = self._get_amd_stats()
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

    def _get_nvidia_stats(self):
        """Use nvidia-smi CSV query for robust GPU stats"""
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ]
            # Run silently with no window (CREATE_NO_WINDOW on Windows)
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2,
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
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

    def _get_intel_stats(self):
        """Query Intel GPU (oneAPI / Level Zero) via xpu-smi.

        Uses xpu-smi dump with --number 1 for a single snapshot (the command
        loops continuously by default) and metric IDs 0 (GPU Utilization %),
        7 (Memory Used, MiB) and 8 (Memory Free, MiB). Output is parsed
        position-independently by matching column headers so it survives
        timestamp/device prefixes and column reordering across versions.
        """
        try:
            cmd = [
                "xpu-smi",
                "dump",
                "-d", "0",
                "-m", "0,7,8",
                "-n", "1",  # single snapshot; otherwise it loops forever
                "--format", "csv,noheader,nounits",
            ]
            # To also support the common "GPU Utilization" + "Memory Used"
            # only flavor, fall back to metrics 0,7 if 8 is unsupported.
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3,
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            out = (proc.stdout or "").strip()
            if not out:
                return None

            # First non-empty line is the data row for the single device.
            first_line = None
            for line in out.splitlines():
                s = line.strip()
                if s:
                    first_line = s
                    break
            if not first_line:
                return None

            parts = [p.strip() for p in first_line.split(",")]

            # With --noheader we have no header to key off; the metric order is
            # whatever we requested, optionally prefixed by timestamp/device
            # columns. Determine how many leading columns precede the metrics.
            # Timestamps look like a date/time; device ids are small integers.
            # We scan from the right and take the last three numeric-looking
            # values as utilization, mem_used, mem_free.
            numeric = []
            for p in parts:
                try:
                    numeric.append(float(p))
                except Exception:
                    numeric.append(None)

            # Walk from the right collecting the three metric values.
            tail = [x for x in numeric if x is not None][-3:]

            if len(tail) < 2:
                # Output without --noheader (header + data): re-run the parse
                # by locating columns via header names.
                return self._parse_intel_headered(out)

            usage_pct = _clamp_percent(tail[0])
            mem_used_mb = tail[1]
            if len(tail) >= 3:
                mem_free_mb = tail[2]
                total_mb = mem_used_mb + mem_free_mb
            else:
                total_mb = None

            if total_mb is None:
                # Only utilization + memory used available; cannot report total.
                return usage_pct, (mem_used_mb / 1024.0), None

            used_gb = mem_used_mb / 1024.0
            total_gb = total_mb / 1024.0
            if total_gb <= 0:
                return None
            return usage_pct, used_gb, total_gb
        except Exception:
            return None

    def _parse_intel_headered(self, out):
        """Fallback parser for xpu-smi output that still includes headers.
        Matches columns by name so reordering/timestamps don't break it.
        """
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        if len(lines) < 2:
            return None
        headers = [h.strip().lower() for h in lines[0].split(",")]
        values = [v.strip() for v in lines[1].split(",")]

        u_idx = _find_col(headers, ["gpu utilization", "utilization"])
        m_idx = _find_col(headers, ["memory used", "mem used"])
        f_idx = _find_col(headers, ["memory free", "mem free"])

        usage_pct = None
        used_mb = None
        total_mb = None

        if 0 <= u_idx < len(values):
            usage_pct = _clamp_percent(_safe_float(values[u_idx]))
        if 0 <= m_idx < len(values):
            used_mb = _safe_float(values[m_idx])
        if 0 <= f_idx < len(values):
            free_mb = _safe_float(values[f_idx])
            if used_mb is not None:
                total_mb = used_mb + free_mb

        if usage_pct is None or used_mb is None or total_mb is None:
            return None
        if total_mb <= 0:
            return None
        return usage_pct, (used_mb / 1024.0), (total_mb / 1024.0)

    def _get_amd_stats(self):
        """Try to parse rocm-smi output for AMD GPU stats"""
        try:
            proc = subprocess.run(
                ["rocm-smi"],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
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

    def stop(self):
        """Stop the worker gracefully"""
        self._running = False


# History graph widget
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

        self.ax.plot(list(self.values), color=self.color, linewidth=2, alpha=0.9)
        self.ax.fill_between(range(len(self.values)), list(self.values), alpha=0.15, color=self.color)

        self.canvas.draw_idle()


# Main System Monitor Widget
class SystemMonitor(QWidget):
    """System resource monitor with design system styling and threaded GPU queries"""

    # Signal to trigger GPU fetch in worker thread
    requestGPUStats = Signal()

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

        # Setup GPU worker thread (modern Qt pattern)
        self.gpu_thread = QThread()
        self.gpu_worker = GPUStatsWorker()
        self.gpu_worker.moveToThread(self.gpu_thread)

        # Connect signals
        self.requestGPUStats.connect(self.gpu_worker.fetch_gpu_stats)
        self.gpu_worker.statsReady.connect(self.handle_gpu_stats)
        self.gpu_thread.finished.connect(self.gpu_worker.deleteLater)

        self.gpu_thread.start()

        # Timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)  # Update every second

        self.update_stats()

    @Slot()
    def update_stats(self):
        """Update CPU and RAM stats (fast), trigger GPU fetch in thread"""
        # CPU (fast, run in main thread)
        cpu = psutil.cpu_percent(interval=0.0)
        self.cpu_graph.update_value(cpu)

        # RAM (fast, run in main thread)
        ram = psutil.virtual_memory().percent
        self.ram_graph.update_value(ram)

        # GPU (slow subprocess, run in worker thread)
        # Only trigger if thread is running and has event loop
        if self.gpu_thread.isRunning():
            self.requestGPUStats.emit()

    @Slot(object, object, object, object)
    def handle_gpu_stats(self, usage, used_gb, total_gb, vendor):
        """Handle GPU stats from worker thread (runs in main thread)"""
        if usage is not None:
            suffix = ""
            if used_gb is not None and total_gb is not None:
                suffix = f" ({used_gb:.1f} GB / {total_gb:.1f} GB)"
            else:
                suffix = f" ({vendor})" if vendor else ""
            self.gpu_graph.update_value(usage, suffix)
        else:
            self.gpu_graph.update_value(0.0, " (No GPU detected)")

    def closeEvent(self, event):
        """Clean shutdown of worker thread"""
        self.timer.stop()
        self.gpu_worker.stop()
        self.gpu_thread.quit()
        self.gpu_thread.wait()
        event.accept()


# Demo/Test
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SystemMonitor()
    win.show()
    sys.exit(app.exec())
