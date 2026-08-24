import sys
import re
import subprocess
import os
import ctypes
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
    TEXT_SECONDARY = "#aeb0b0"  # Gray-300 (dimmed)

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
    CHART_TEXT = "#aeb0b0"


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


# Worker for GPU stats (runs in separate thread)
class GPUStatsWorker(QObject):
    """Worker object for fetching GPU stats in a separate thread"""
    statsReady = Signal(object, object, object, object)  # usage, used_gb, total_gb, vendor
    finished = Signal()

    def __init__(self):
        super().__init__()
        self._running = True
        self._intel_prev_active = None
        self._intel_prev_timestamp = None

    def stop(self):
        """Signal worker to stop running"""
        self._running = False

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
        """Try NVIDIA first, then AMD, then Intel, then GPUtil fallback"""
        n = self._get_nvidia_stats()
        if n:
            return n[0], n[1], n[2], "NVIDIA"

        a = self._get_amd_stats()
        if a:
            return a[0], a[1], a[2], "AMD"

        i = self._get_intel_stats()
        if i:
            return i[0], i[1], i[2], "Intel"

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

    def _get_intel_stats(self):
        """Try to get Intel ARC/Xe GPU stats using oneAPI Level-Zero Sysman"""
        try:
            # Set the environment variable required for Sysman
            os.environ["ZES_ENABLE_SYSMAN"] = "1"

            # Try to load Level-Zero library
            lib_names = []
            if sys.platform == "win32":
                lib_names = ["ze_loader.dll"]
            else:
                lib_names = ["libze_loader.so.1", "libze_loader.so"]

            ze = None
            for name in lib_names:
                try:
                    ze = ctypes.CDLL(name)
                    break
                except Exception:
                    continue

            if ze is None:
                return None

            # Declare structures
            class ZesEngineStats(ctypes.Structure):
                _fields_ = [
                    ("activeTime", ctypes.c_uint64),
                    ("timestamp", ctypes.c_uint64),
                ]

            class ZesEngineProperties(ctypes.Structure):
                _fields_ = [
                    ("stype", ctypes.c_int),
                    ("pNext", ctypes.c_void_p),
                    ("type", ctypes.c_int),
                    ("onSubdevice", ctypes.c_uint32),
                    ("subdeviceId", ctypes.c_uint32),
                ]

            class ZesMemProperties(ctypes.Structure):
                _fields_ = [
                    ("stype", ctypes.c_int),
                    ("pNext", ctypes.c_void_p),
                    ("type", ctypes.c_int),
                    ("onSubdevice", ctypes.c_uint32),
                    ("subdeviceId", ctypes.c_uint32),
                    ("location", ctypes.c_int),
                    ("physicalSize", ctypes.c_uint64),
                    ("busWidth", ctypes.c_int32),
                    ("numChannels", ctypes.c_int32),
                ]

            class ZesMemState(ctypes.Structure):
                _fields_ = [
                    ("stype", ctypes.c_int),
                    ("pNext", ctypes.c_void_p),
                    ("health", ctypes.c_int),
                    ("free", ctypes.c_uint64),
                    ("size", ctypes.c_uint64),
                ]

            # Set function argtypes & restypes
            ze.zesInit.argtypes = [ctypes.c_uint32]
            ze.zesInit.restype = ctypes.c_int

            ze.zesDriverGet.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)]
            ze.zesDriverGet.restype = ctypes.c_int

            ze.zesDeviceGet.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)]
            ze.zesDeviceGet.restype = ctypes.c_int

            ze.zesDeviceEnumEngineGroups.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)]
            ze.zesDeviceEnumEngineGroups.restype = ctypes.c_int

            ze.zesEngineGetProperties.argtypes = [ctypes.c_void_p, ctypes.POINTER(ZesEngineProperties)]
            ze.zesEngineGetProperties.restype = ctypes.c_int

            ze.zesEngineGetActivity.argtypes = [ctypes.c_void_p, ctypes.POINTER(ZesEngineStats)]
            ze.zesEngineGetActivity.restype = ctypes.c_int

            ze.zesDeviceEnumMemoryModules.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)]
            ze.zesDeviceEnumMemoryModules.restype = ctypes.c_int

            ze.zesMemoryGetProperties.argtypes = [ctypes.c_void_p, ctypes.POINTER(ZesMemProperties)]
            ze.zesMemoryGetProperties.restype = ctypes.c_int

            ze.zesMemoryGetState.argtypes = [ctypes.c_void_p, ctypes.POINTER(ZesMemState)]
            ze.zesMemoryGetState.restype = ctypes.c_int

            # Initialize Sysman
            if ze.zesInit(0) != 0:
                # Also try zeInit(0) / zeInit(1) as backup just in case
                if hasattr(ze, "zeInit"):
                    ze.zeInit.argtypes = [ctypes.c_uint32]
                    ze.zeInit.restype = ctypes.c_int
                    ze.zeInit(1)
                else:
                    return None

            # Get drivers
            drivers_count = ctypes.c_uint32(0)
            if ze.zesDriverGet(ctypes.byref(drivers_count), None) != 0 or drivers_count.value == 0:
                return None

            drivers = (ctypes.c_void_p * drivers_count.value)()
            if ze.zesDriverGet(ctypes.byref(drivers_count), drivers) != 0:
                return None

            # Find the first device of the first driver
            hDevice = None
            for hDriver in drivers:
                devices_count = ctypes.c_uint32(0)
                if ze.zesDeviceGet(hDriver, ctypes.byref(devices_count), None) == 0 and devices_count.value > 0:
                    devices = (ctypes.c_void_p * devices_count.value)()
                    if ze.zesDeviceGet(hDriver, ctypes.byref(devices_count), devices) == 0:
                        hDevice = devices[0]
                        break

            if hDevice is None:
                return None

            # 1. Query VRAM usage
            used_gb, total_gb = None, None
            mem_count = ctypes.c_uint32(0)
            if ze.zesDeviceEnumMemoryModules(hDevice, ctypes.byref(mem_count), None) == 0 and mem_count.value > 0:
                mem_modules = (ctypes.c_void_p * mem_count.value)()
                if ze.zesDeviceEnumMemoryModules(hDevice, ctypes.byref(mem_count), mem_modules) == 0:
                    total_size = 0
                    total_free = 0
                    for hMem in mem_modules:
                        mem_props = ZesMemProperties()
                        mem_props.stype = 11  # ZES_STRUCTURE_TYPE_MEM_PROPERTIES
                        mem_props.pNext = None
                        if ze.zesMemoryGetProperties(hMem, ctypes.byref(mem_props)) == 0:
                            # Only local VRAM on-board the device
                            if mem_props.location == 1:  # ZES_MEM_LOC_DEVICE
                                mem_state = ZesMemState()
                                mem_state.stype = 30  # ZES_STRUCTURE_TYPE_MEM_STATE
                                mem_state.pNext = None
                                if ze.zesMemoryGetState(hMem, ctypes.byref(mem_state)) == 0:
                                    total_free += mem_state.free
                                    total_size += mem_state.size if mem_state.size > 0 else mem_props.physicalSize
                    if total_size > 0:
                        total_gb = total_size / (1024.0 * 1024.0 * 1024.0)
                        used_gb = (total_size - total_free) / (1024.0 * 1024.0 * 1024.0)

            # 2. Query GPU Usage (Engine Activity)
            usage_pct = None
            engines_count = ctypes.c_uint32(0)
            if ze.zesDeviceEnumEngineGroups(hDevice, ctypes.byref(engines_count), None) == 0 and engines_count.value > 0:
                engines = (ctypes.c_void_p * engines_count.value)()
                if ze.zesDeviceEnumEngineGroups(hDevice, ctypes.byref(engines_count), engines) == 0:
                    selected_engine = None
                    for hEngine in engines:
                        props = ZesEngineProperties()
                        props.stype = 5  # ZES_STRUCTURE_TYPE_ENGINE_PROPERTIES
                        props.pNext = None
                        if ze.zesEngineGetProperties(hEngine, ctypes.byref(props)) == 0:
                            if props.type == 0:  # ZES_ENGINE_GROUP_ALL
                                selected_engine = hEngine
                                break
                    if selected_engine is None and len(engines) > 0:
                        selected_engine = engines[0]

                    if selected_engine is not None:
                        stats = ZesEngineStats()
                        if ze.zesEngineGetActivity(selected_engine, ctypes.byref(stats)) == 0:
                            if self._intel_prev_active is not None and self._intel_prev_timestamp is not None:
                                delta_active = stats.activeTime - self._intel_prev_active
                                delta_timestamp = stats.timestamp - self._intel_prev_timestamp
                                if delta_timestamp > 0 and delta_active >= 0:
                                    usage_pct = _clamp_percent((delta_active / delta_timestamp) * 100.0)
                                else:
                                    usage_pct = 0.0
                            else:
                                usage_pct = 0.0
                            self._intel_prev_active = stats.activeTime
                            self._intel_prev_timestamp = stats.timestamp

            if usage_pct is not None or used_gb is not None:
                # Return tuple
                return usage_pct if usage_pct is not None else 0.0, used_gb, total_gb

        except Exception as e:
            if os.environ.get("DEBUG_SYSTEM_MONITOR"):
                import traceback
                traceback.print_exc()
            pass

        return None

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
