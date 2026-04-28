import os.path
import sys
import subprocess
import threading
import pathlib
import os
import time
import signal
import winsound
import re
from pathlib import Path
from datetime import datetime
from dataclasses import fields
from PySide6.QtWidgets import (
    QDialog, QApplication, QMessageBox, QInputDialog,
    QMenu, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QFileDialog, QMainWindow, QLabel
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPoint

from src.forms.mapbuilder.ui_main import Ui_mapbuilder_dialog
from src.forms.mapbuilder.system_monitor import SystemMonitor
from src.forms.mapbuilder.output_formater import OutputFormatter
from src.forms.mapbuilder.preset_manager import PresetManager, BuildPreset, BuildSettings
from src.forms.mapbuilder.widgets import SettingsPanel, PresetButton
from src.settings.main import get_addon_name, get_settings_value, get_addon_dir, get_cs2_path, set_settings_value
from src.common import enable_dark_title_bar, app_dir, default_commands
from src.other.addon_functions import launch_addon
from src.other.cs2_netcon import CS2Netcon


class BuildHistoryCache:
    def __init__(self):
        from src.common import user_data_dir
        self.cache_file = user_data_dir / "MapBuilder" / "build_history.json"
        self.cache = self._load()

    def _load(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return __import__('json').load(f)
        except Exception:
            pass
        return {}

    def _save(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                __import__('json').dump(self.cache, f, indent=4)
        except Exception as e:
            print(f"Error saving build history: {e}")

    def get_estimated_time(self, map_path: str, settings) -> float:
        data = self.cache.get(map_path)
        if not data:
            return -1.0
            
        total = 0.0
        
        world = data.get("world", {}).get("average", -1.0)
        if world < 0: return -1.0
        total += world
        
        if settings.build_vis:
            vis = data.get("vis", {}).get("average", -1.0)
            if vis < 0: return -1.0
            total += vis
            
        if settings.build_nav:
            nav = data.get("nav", {}).get("average", -1.0)
            if nav < 0: return -1.0
            total += nav
            
        if settings.build_reverb:
            audio = data.get("audio", {}).get("average", -1.0)
            if audio < 0: audio = 0  # Reverb takes minimal time, fallback safely
            total += audio
            
        if settings.bake_lighting:
            if settings.no_light_calculations:
                total += 0.1
            else:
                light_key = f"light_Q{settings.lightmap_quality}_{settings.lightmap_max_resolution}_F{int(settings.lightmap_filtering)}_LB{int(settings.vrad3_large_block_size)}"
                light = data.get(light_key, {}).get("average", -1.0)
                
                if light < 0:
                    best_match = None
                    best_score = -1
                    for key, val in data.items():
                        if key.startswith("light_Q"):
                            try:
                                parts = key.replace("light_Q", "").split("_")
                                q = int(parts[0])
                                res = int(parts[1])
                                
                                known_f = True
                                known_lb = False
                                for p in parts[2:]:
                                    if p.startswith("F"): known_f = bool(int(p[1:]))
                                    if p.startswith("LB"): known_lb = bool(int(p[2:]))
                                    
                                avg = val.get("average", -1.0)
                                if avg > 0:
                                    score = 0
                                    if res == settings.lightmap_max_resolution:
                                        score += 10000
                                    else:
                                        score += res
                                        
                                    if q == settings.lightmap_quality:
                                        score += 1000
                                        
                                    if score > best_score:
                                        best_score = score
                                        best_match = (q, res, known_f, known_lb, avg)
                            except Exception:
                                pass
                                
                    if best_match:
                        known_q, known_res, known_f, known_lb, known_avg = best_match
                        res_ratio = settings.lightmap_max_resolution / float(known_res)
                        if res_ratio >= 1.0:
                            res_factor = res_ratio ** 1.65
                        else:
                            res_factor = res_ratio ** 1.65
                        
                        q_weights = {0: 1.0, 1: 1.43, 2: 3.57, 3: 7.0}
                        q_target = q_weights.get(settings.lightmap_quality, 3.57)
                        q_known = q_weights.get(known_q, 3.57)
                        q_factor = q_target / q_known
                        
                        light = known_avg * res_factor * q_factor
                        
                        if settings.lightmap_filtering and not known_f:
                            light *= 1.25
                        elif not settings.lightmap_filtering and known_f:
                            light *= 0.80
                            
                if light < 0: return -1.0
                total += light
            
        return total

    def record_phase_time(self, map_path: str, phase_name: str, elapsed: float):
        if elapsed <= 0: return
        data = self.cache.get(map_path, {})
        phase_data = data.get(phase_name, {"average": elapsed, "history": []})
        
        phase_data["history"].append(elapsed)
        phase_data["history"] = phase_data["history"][-5:]
        phase_data["average"] = sum(phase_data["history"]) / len(phase_data["history"])
        
        data[phase_name] = phase_data
        self.cache[map_path] = data
        self._save()


class BuildCubemapsThread(QThread):
    """Thread that launches CS2 once, then builds cubemaps for every map in
    the queue sequentially – without relaunching the game between maps.

    Flow:
      1. Launch CS2 (no map on the command line – just tools mode).
      2. Wait for the netcon TCP port to become reachable.
      3. Wait for CS2 to finish initialising (``Source2Init OK`` sentinel).
      4. Query ``r_always_render_all_windows`` and save the user's value.
      5. Set ``r_always_render_all_windows true``.
      6. For each map in the queue:
         a. Send ``map_workshop <addon> <map>`` via netcon.
         b. Wait for the map to fully load (``Host activate: Loading``).
         c. Send ``buildcubemaps`` and wait until the build completes.
            CS2 disconnects its internal game server during cubemap baking,
            which drops the netcon TCP connection. When the connection
            closes we reconnect and wait for the map to reload, which
            signals that the cubemap VPK has been written.
      7. Restore ``r_always_render_all_windows`` to the original value.
      8. Leave CS2 running.
    """
    outputReceived = Signal(str)
    mapFinished = Signal(str, bool)   # (map_name, success)
    finished = Signal(bool)           # True = all succeeded, False = failure/abort

    # CS2 prints this once the main menu is fully up and ready.
    INIT_DONE_SENTINEL = "CSGO_GAME_UI_STATE_MAINMENU"
    # Printed when a map is fully loaded and the player is in-game.
    MAP_LOADED_SENTINEL = "Host activate: Loading"

    CONNECT_TIMEOUT = 180            # seconds – wait for netcon port
    INIT_TIMEOUT = 300               # seconds – wait for main menu
    MAP_LOAD_TIMEOUT = 300           # seconds – wait for map to fully load
    BUILD_TIMEOUT = 600              # seconds – wait for cubemap build
    RECONNECT_TIMEOUT = 60           # seconds – wait for netcon after cubemap disconnect

    def __init__(self, cs2_exe: str, launch_args: str,
                 map_data: list[tuple[str, str]]):
        super().__init__()
        self.cs2_exe = cs2_exe
        self.launch_args = launch_args
        self.map_data = list(map_data)  # [(addon, map_name), ...]
        self._stop_event = __import__('threading').Event()

    # -----------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------
    def _wait_for_netcon(self, timeout: float) -> bool:
        """Block until the netcon TCP port is reachable."""
        import time as _time
        import socket as _socket

        host, port = CS2Netcon._get_target()
        deadline = _time.time() + timeout
        while _time.time() < deadline:
            if self._stop_event.is_set():
                return False
            try:
                with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect((host, port))
                return True
            except (ConnectionRefusedError, TimeoutError, OSError):
                _time.sleep(2)
        return False

    def _listen_for(self, command: str, sentinel: str, timeout: float) -> bool:
        """Send *command* and listen until *sentinel* appears in the output."""
        return CS2Netcon.send_and_listen(
            command=command,
            sentinel=sentinel,
            on_line=lambda line: self.outputReceived.emit(f"[CS2] {line}"),
            timeout=timeout,
            stop_event=self._stop_event,
        )

    # -----------------------------------------------------------------
    # main entry
    # -----------------------------------------------------------------
    def run(self):
        import subprocess as _subprocess
        import time as _time

        # Group maps by addon
        addon_groups = {}
        for addon_name, map_name in self.map_data:
            if addon_name not in addon_groups:
                addon_groups[addon_name] = []
            addon_groups[addon_name].append(map_name)

        all_ok = True
        addons_list = list(addon_groups.keys())

        for idx, addon_name in enumerate(addons_list):
            if self._stop_event.is_set():
                self.outputReceived.emit("Cubemap build aborted by user")
                all_ok = False
                break

            maps = addon_groups[addon_name]
            
            # --- 1. Launch CS2 for this addon ---
            commands = self.launch_args.replace('addon_name', addon_name)
            launch_cmd = f'"{self.cs2_exe}" {commands}'
            self.outputReceived.emit(f"Closing existing CS2 instances...")
            _subprocess.run(['taskkill', '/F', '/IM', 'cs2.exe'], capture_output=True, check=False)
            _time.sleep(1)
            self.outputReceived.emit(f"Launching CS2 for addon '{addon_name}': {launch_cmd}")
            
            process = None
            try:
                process = _subprocess.Popen(launch_cmd, shell=True)
            except Exception as e:
                self.outputReceived.emit(f"Failed to launch CS2: {e}")
                self.finished.emit(False)
                return

            # --- 2. Wait for the netcon port ---
            self.outputReceived.emit("Waiting for CS2 to accept netcon connections...")
            if not self._wait_for_netcon(self.CONNECT_TIMEOUT):
                self.outputReceived.emit(
                    "Timed out waiting for CS2 netcon – is the game running?")
                all_ok = False
                continue

            self.outputReceived.emit(
                "CS2 netcon connected. Waiting for the main menu to fully load...")

            # --- 3. Wait for CS2 to reach main menu ---
            init_ok = self._listen_for(
                "echo h5t_waiting_for_init", self.INIT_DONE_SENTINEL,
                self.INIT_TIMEOUT,
            )
            if not init_ok:
                if self._stop_event.is_set():
                    self.outputReceived.emit("Cubemap build aborted during CS2 init")
                else:
                    self.outputReceived.emit(
                        "Timed out waiting for CS2 to reach the main menu")
                all_ok = False
                continue

            self.outputReceived.emit(f"CS2 main menu loaded for '{addon_name}'. Preparing for cubemap builds...")

            # Give the main menu a moment to fully settle (configs, GC, etc.).
            _time.sleep(5)

            # --- 4. Save user's r_always_render_all_windows and force it to true ---
            original_render_all = CS2Netcon.query("r_always_render_all_windows")
            if original_render_all is None:
                # Retry once after a short delay if the first query failed
                _time.sleep(2)
                original_render_all = CS2Netcon.query("r_always_render_all_windows")
            if original_render_all is None:
                original_render_all = "false"
                self.outputReceived.emit(
                    "Could not query r_always_render_all_windows, "
                    "assuming default 'false'")
            self.outputReceived.emit(
                f"Saved r_always_render_all_windows = {original_render_all}")
            CS2Netcon.send("r_always_render_all_windows true")
            self.outputReceived.emit("Set r_always_render_all_windows = true (for cubemap baking)")

            # --- 5. Build cubemaps for each map in this addon ---
            for map_name in maps:
                if self._stop_event.is_set():
                    self.outputReceived.emit("Cubemap build aborted by user")
                    all_ok = False
                    break

                ok = self._build_one_map(addon_name, map_name)
                self.mapFinished.emit(map_name, ok)
                if not ok:
                    all_ok = False
                    if self._stop_event.is_set():
                        break

            # --- 6. Restore r_always_render_all_windows ---
            restore_ok = CS2Netcon.send(f"r_always_render_all_windows {original_render_all}")
            if not restore_ok:
                # Retry: wait for netcon to be available and try again
                _time.sleep(2)
                if self._wait_for_netcon(10):
                    restore_ok = CS2Netcon.send(
                        f"r_always_render_all_windows {original_render_all}")
            if restore_ok:
                self.outputReceived.emit(
                    f"Restored r_always_render_all_windows = {original_render_all}")
            else:
                self.outputReceived.emit(
                    f"WARNING: Could not restore r_always_render_all_windows to "
                    f"'{original_render_all}' – CS2 may be unreachable")

            # --- 7. Close CS2 if there are more addons to process ---
            if idx < len(addons_list) - 1:
                self.outputReceived.emit(f"Closing CS2 for addon '{addon_name}' to switch to next addon...")
                CS2Netcon.send("quit")
                _time.sleep(5)
                # Ensure process is dead
                if process:
                    try:
                        process.terminate()
                    except:
                        pass
                # wait a bit for port to free up
                _time.sleep(2)

        self.finished.emit(all_ok)

    # -----------------------------------------------------------------
    def _build_one_map(self, addon_name: str, map_name: str) -> bool:
        """Load *map_name* in CS2 and run buildcubemaps.  Returns True on
        success."""
        import time as _time

        self.outputReceived.emit(f"Loading map '{map_name}' from addon '{addon_name}' via netcon...")

        # Send map_workshop to load the map
        map_cmd = f"map_workshop {addon_name} {map_name}"
        map_loaded = self._listen_for(
            map_cmd, self.MAP_LOADED_SENTINEL, self.MAP_LOAD_TIMEOUT)

        if not map_loaded:
            if self._stop_event.is_set():
                self.outputReceived.emit(
                    f"Cubemap build aborted while loading map '{map_name}'")
            else:
                self.outputReceived.emit(
                    f"Timed out waiting for map '{map_name}' to load")
            return False

        # Small extra delay to let the game fully stabilize after map load
        self.outputReceived.emit(
            f"Map '{map_name}' loaded! Waiting a moment before building cubemaps...")
        _time.sleep(5)

        if self._stop_event.is_set():
            return False

        # Send buildcubemaps.
        # CS2 disconnects its internal game server while baking cubemaps,
        # which usually drops the netcon TCP connection.  We detect
        # completion by looking for the sentinel OR by reconnecting after
        # the connection drops and waiting for the map to reload.
        self.outputReceived.emit(f"Sending buildcubemaps for '{map_name}'...")
        sentinel_found = self._listen_for(
            "buildcubemaps", "Re-loading map", self.BUILD_TIMEOUT)

        if sentinel_found:
            self.outputReceived.emit(
                f"Cubemap build completed for '{map_name}'!")
            return True

        if self._stop_event.is_set():
            self.outputReceived.emit(f"Cubemap build aborted for '{map_name}'")
            return False

        # The TCP connection was likely dropped during the cubemap bake.
        # Reconnect and wait for the map to reload (signals the VPK was
        # written and CS2 is back in-game with the new cubemaps).
        self.outputReceived.emit(
            "Netcon connection dropped during cubemap build. "
            "Reconnecting to verify completion...")

        if not self._wait_for_netcon(self.RECONNECT_TIMEOUT):
            self.outputReceived.emit(
                f"Could not reconnect to CS2 after cubemap build for '{map_name}'")
            return False

        # After reconnecting, wait for the map to finish reloading.
        reload_ok = self._listen_for(
            "echo h5t_cubemap_reconnect",
            self.MAP_LOADED_SENTINEL,
            self.MAP_LOAD_TIMEOUT,
        )

        if reload_ok:
            self.outputReceived.emit(
                f"Cubemap build completed for '{map_name}'! "
                "(confirmed after reconnect)")
            return True

        # If the map-loaded sentinel fires very quickly (before our
        # reconnect), the reload may already be done.  Accept that as
        # success – the VPK was written.
        self.outputReceived.emit(
            f"Cubemap build for '{map_name}' likely completed "
            "(reconnected but map-load sentinel not re-detected)")
        return True

    def abort(self):
        self._stop_event.set()


class CompilationThread(QThread):
    outputReceived = Signal(str)
    finished = Signal(int, float)

    def __init__(self, command: str, working_dir: str):
        super().__init__()
        self.command = command
        self.working_dir = working_dir
        self.process = None
        self.should_abort = False
        self.start_time = None

    def run(self):
        self.start_time = time.time()

        try:
            popen_kwargs = dict(
                args=self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                cwd=self.working_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            self.process = subprocess.Popen(**popen_kwargs)
            buffer = bytearray()

            while True:
                if self.should_abort:
                    self.process.terminate()
                    break

                byte = self.process.stdout.read(1)

                if not byte and self.process.poll() is not None:
                    break

                if byte:
                    buffer.extend(byte)
                    current_str = ""
                    try:
                        current_str = buffer.decode('utf-8', errors='ignore')
                    except:
                        pass

                    is_newline = current_str.endswith('\n')
                    is_html_br = current_str.endswith('<br/>') or current_str.endswith('<br>')

                    if is_newline or is_html_br:
                        try:
                            line = buffer.decode('utf-8', errors='replace')
                        except:
                            line = buffer.decode('latin-1', errors='replace')

                        line = line.replace('<br/>', '').replace('<br>', '').rstrip()

                        if line:
                            self.outputReceived.emit(line)
                            self.msleep(1)

                        buffer = bytearray()

            if buffer:
                try:
                    line = buffer.decode('utf-8', errors='replace').rstrip()
                    if line:
                        self.outputReceived.emit(line)
                except:
                    pass

            self.process.wait()
            exit_code = self.process.returncode
            elapsed = time.time() - self.start_time

            self.finished.emit(exit_code, elapsed)

        except Exception as e:
            print(f"Compilation error: {e}")
            self.finished.emit(-1, 0)

    def abort(self):
        self.should_abort = True
        if self.process and hasattr(self.process, 'pid') and self.process.pid:
            pid = self.process.pid
            try:
                self.process.poll()
                if self.process.returncode is None:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                                   capture_output=True, check=False)
                else:
                    print(f"Process {pid} already finished")
            except:
                pass
            finally:
                self.process = None


class ElapsedTimeTracker:
    def __init__(self):
        self.start_time = None
        self.paused_time = 0.0

    def start(self):
        self.start_time = time.time()
        self.paused_time = 0.0

    def get_elapsed(self) -> float:
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) - self.paused_time

    def format_time(self, seconds: float) -> str:
        if seconds < 0:
            seconds = 0

        if seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def format_with_dots(self, seconds: float, dot_cycle: int) -> str:
        time_str = self.format_time(seconds)
        dots = '.' * ((dot_cycle % 3) + 1)
        return f"{time_str}{dots}"


def is_skybox_map(mappath: str) -> bool:
    map_name = Path(mappath).stem
    return map_name.endswith('skybox')


class MapBuilderDialog(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_mapbuilder_dialog()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)
        self.cs2_path = get_cs2_path()
        self.ui.splitter.setSizes([200, 300])

        if not self.cs2_path:
            raise ValueError("CS2 path not found. Please set CS2 installation path in settings.")

        self.cs2_path = str(self.cs2_path)

        presets_file = Path(get_addon_dir()) / ".hammer5tools" / "build_presets.json"
        self.preset_manager = PresetManager(presets_file)

        self.ui.output_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.output_list_widget.customContextMenuRequested.connect(self._output_context_menu)

        self.current_preset: BuildPreset = None
        self.compilation_thread: CompilationThread = None
        self.is_compiling = False
        self.last_build_time = 0.0
        self.build_was_aborted = False

        self.elapsed_tracker = ElapsedTimeTracker()
        self.elapsed_timer = QTimer()
        self.elapsed_timer.timeout.connect(self._update_elapsed_display)
        self.dot_cycle = 0

        self.ui.last_build_stats_label.setText("")
        self.ui.last_build_stats_label.setVisible(False)

        from PySide6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar(self.ui.layoutWidget1)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Idle")
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #505050;
                border-radius: 2px;
                text-align: center;
                color: white;
                font-size: 10px;
                background-color: #1C1C1C;
            }
            QProgressBar::chunk {
                background-color: #1a528a;
                margin: 0px;
                width: 1px;
            }
        """)
        self.ui.verticalLayout_3.addWidget(self.progress_bar)
        
        self.total_progress_bar = QProgressBar(self.ui.layoutWidget1)
        self.total_progress_bar.setTextVisible(True)
        self.total_progress_bar.setFormat("Idle")
        self.total_progress_bar.setFixedHeight(14)
        self.total_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #505050;
                border-radius: 2px;
                text-align: center;
                color: white;
                font-size: 10px;
                background-color: #1C1C1C;
            }
            QProgressBar::chunk {
                background-color: #1a528a;
                margin: 0px;
                width: 1px;
            }
        """)
        self.total_progress_bar.setVisible(False)
        self.ui.verticalLayout_3.addWidget(self.total_progress_bar)

        self.setup_settings_panel()
        self.setup_preset_buttons()
        self.setup_system_monitor()
        self.setup_connections()

        presets = self.preset_manager.get_all_presets()
        if presets:
            self.load_preset(presets[0])

        self.current_build_logs = []
        self.current_build_timestamp = None
        self.map_queue = []
        self.current_map_index = 0
        self.build_stats = []
        self.current_map_stats = {}
        self.build_start_time = None
        self.build_history = BuildHistoryCache()
        self.current_build_sig = ""
        self.current_est_time = -1.0

        # Cubemap queue state
        self.cubemap_queue = []
        self.cubemap_index = 0
        self.cubemap_thread: BuildCubemapsThread = None
        self.is_building_cubemaps = False

        self.log_phase('<b>Skybox Map Rules:</b>')
        self.log_info('  • Compiled without -nav, -vis, and -audio flags')
        self.log_info('  • Lightmap resolution limited to 2048')

    def _get_build_signature(self, mappath: str, settings: BuildSettings) -> str:
        sig = f"{mappath}"
        if settings.bake_lighting:
            sig += f"_L{settings.lightmap_max_resolution}_Q{settings.lightmap_quality}"
        else:
            sig += "_NoLight"
        if settings.build_vis: sig += "_Vis"
        if settings.build_nav: sig += "_Nav"
        if settings.build_reverb: sig += "_Reverb"
        return sig

    def _parse_map_path(self, absolute_path: str) -> tuple[str, str, str]:
        """Returns (addon_name, addon_dir, map_name_relative_to_maps)"""
        try:
            p = Path(absolute_path)
            parts = p.parts
            addon_name = get_addon_name()
            addon_dir = get_addon_dir()

            if 'csgo_addons' in parts:
                idx = parts.index('csgo_addons')
                if idx + 1 < len(parts):
                    addon_name = parts[idx + 1]
                    addon_dir = str(Path(*parts[:idx + 2]))

            # Get map name relative to maps/
            map_name = p.stem
            try:
                if 'maps' in parts:
                    m_idx = parts.index('maps')
                    map_name = Path(*parts[m_idx + 1:]).with_suffix('').as_posix()
            except Exception:
                pass

            return addon_name, addon_dir, map_name
        except Exception:
            return get_addon_name(), get_addon_dir(), Path(absolute_path).stem

    def setup_settings_panel(self):
        self.settings_panel = SettingsPanel()

        while self.ui.build_settings_content.count():
            item = self.ui.build_settings_content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.ui.build_settings_content.addWidget(self.settings_panel)
        self.ui.build_settings_content.addStretch()

    def setup_preset_buttons(self):
        preset_layout = self.ui.build_presets.widget().layout()
        while preset_layout.count() > 1:
            item = preset_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.preset_buttons = {}
        for preset in self.preset_manager.get_all_presets():
            btn = PresetButton(preset.name, preset.is_default)
            btn.presetClicked.connect(self.on_preset_clicked)
            btn.contextMenuRequested.connect(
                lambda data, p=preset: self.show_preset_context_menu(data, p)
            )
            preset_layout.insertWidget(preset_layout.count() - 1, btn)
            self.preset_buttons[preset.name] = btn

        new_btn = PresetButton("+", False)
        new_btn.setText("+")
        new_btn.setToolTip("Create new preset")
        new_btn.presetClicked.connect(self.create_new_preset)
        preset_layout.insertWidget(preset_layout.count() - 1, new_btn)

    def setup_system_monitor(self):
        while self.ui.system_monitor.layout() and self.ui.system_monitor.layout().count():
            item = self.ui.system_monitor.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.system_monitor = SystemMonitor()

        if not self.ui.system_monitor.layout():
            from PySide6.QtWidgets import QVBoxLayout
            layout = QVBoxLayout(self.ui.system_monitor)
            layout.setContentsMargins(0, 0, 0, 0)

        self.ui.system_monitor.layout().addWidget(self.system_monitor)

    def setup_connections(self):
        self.ui.build_button.clicked.connect(self.start_compilation)
        self.ui.run_button.clicked.connect(self.run_map)
        self.ui.abort_button.clicked.connect(self.abort_compilation)
        self.ui.abort_button.setEnabled(False)

    def closeEvent(self, event):
        if (self.is_compiling and self.compilation_thread) or self.is_building_cubemaps:
            reply = QMessageBox.question(
                self,
                "Abort?",
                "A build is currently running.\n\n"
                "Do you want to abort and close this dialog?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.build_was_aborted = True
                self.log_warning("User closed dialog - aborting")
                if self.compilation_thread and self.compilation_thread.isRunning():
                    self.compilation_thread.abort()
                    self.compilation_thread.wait(2000)
                if self.cubemap_thread and self.cubemap_thread.isRunning():
                    self.cubemap_thread.abort()
                    self.cubemap_thread.wait(2000)
                self.elapsed_timer.stop()
                event.accept()
                self.hide()
            else:
                event.ignore()
        else:
            event.accept()
            self.hide()

    def on_preset_clicked(self, preset_name: str):
        preset = self.preset_manager.get_preset(preset_name)
        if preset:
            self.load_preset(preset)

    def load_preset(self, preset: BuildPreset):
        self.current_preset = preset
        self.settings_panel.set_settings(preset.settings)

        for name, btn in self.preset_buttons.items():
            btn.set_active(name == preset.name)

        self.setWindowTitle(f"Map Builder - {preset.name}")

    def show_preset_context_menu(self, signal_data, preset: BuildPreset):
        button, local_pos = signal_data
        menu = QMenu(self)

        save_action = menu.addAction("Save Changes")
        save_action.triggered.connect(lambda: self.save_preset_changes(preset))

        if not preset.is_default:
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self.rename_preset(preset))

            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self.delete_preset(preset))

        global_pos = button.mapToGlobal(local_pos)
        menu.exec_(global_pos)

    def create_new_preset(self):
        name, ok = QInputDialog.getText(self, "New Preset", "Enter preset name:")

        if ok and name:
            current_settings = self.settings_panel.get_settings()
            new_preset = BuildPreset(
                name=name,
                settings=current_settings,
                is_default=False,
                description=f"Created {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

            if self.preset_manager.add_preset(new_preset):
                self.setup_preset_buttons()
                self.load_preset(new_preset)
            else:
                QMessageBox.warning(self, "Error", "Preset with this name already exists")

    def save_preset_changes(self, preset: BuildPreset):
        current_settings = self.settings_panel.get_settings()
        self.preset_manager.update_preset(preset.name, current_settings)
        QMessageBox.information(self, "Success", f"Preset '{preset.name}' updated")

    def rename_preset(self, preset: BuildPreset):
        new_name, ok = QInputDialog.getText(
            self, "Rename Preset", "Enter new name:", text=preset.name
        )

        if ok and new_name and new_name != preset.name:
            if self.preset_manager.rename_preset(preset.name, new_name):
                self.setup_preset_buttons()
                preset.name = new_name
                self.load_preset(preset)
            else:
                QMessageBox.warning(self, "Error", "Could not rename preset")

    def delete_preset(self, preset: BuildPreset):
        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Delete preset '{preset.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.preset_manager.delete_preset(preset.name):
                self.setup_preset_buttons()
                presets = self.preset_manager.get_all_presets()
                if presets:
                    self.load_preset(presets[0])

    def start_compilation(self):
        if self.is_compiling:
            QMessageBox.warning(self, "Already Compiling", "Compilation already in progress")
            return

        settings = self.settings_panel.get_settings()
        mappaths = [p for p in str(settings.mappath).split(';') if p]

        if not mappaths:
            QMessageBox.warning(self, "Invalid Map", "Please select a valid map file")
            return

        self.map_queue = mappaths
        self.current_map_index = 0
        self.build_stats = []
        self.build_start_time = time.time()
        self.build_was_aborted = False
        
        self.total_est_time = 0.0
        for rel in self.map_queue:
            mappath_abs = os.path.abspath(rel)
            single_settings = BuildSettings(**{f.name: getattr(settings, f.name) for f in fields(BuildSettings)})
            single_settings.mappath = mappath_abs
            if is_skybox_map(rel):
                single_settings.build_nav = False
                single_settings.build_vis = False
                single_settings.lightmap_max_resolution = 2048
            est = self.build_history.get_estimated_time(mappath_abs, single_settings)
            if est > 0:
                self.total_est_time += est
            else:
                self.total_est_time = -1.0
                break

        self.ui.output_list_widget.clear()

        if len(self.map_queue) > 1:
            self.total_progress_bar.setVisible(True)
            if self.total_est_time > 0:
                self.total_progress_bar.setRange(0, int(self.total_est_time))
            else:
                self.total_progress_bar.setRange(0, 100)
            self.total_progress_bar.setValue(0)
            self.total_progress_bar.setFormat(f"Total Progress: 0/{len(self.map_queue)}")
            
            self.log_separator()
            self.log_phase(f'Batch compilation - queued {len(self.map_queue)} maps')
            self.log_separator()
        else:
            self.total_progress_bar.setVisible(False)

        self.process_next_map()

    def _update_elapsed_display(self):
        if self.is_compiling and self.elapsed_tracker.start_time:
            elapsed = self.elapsed_tracker.get_elapsed()
            
            cur_str = self.elapsed_tracker.format_time(elapsed)
            est_str = self.elapsed_tracker.format_time(self.current_est_time) if getattr(self, 'current_est_time', -1.0) > 0 else "?"
            
            addon_prefix = getattr(self, 'current_addon_prefix', '')
            map_base = getattr(self, 'current_map_base', '')
            
            if getattr(self, 'current_est_time', -1.0) > 0:
                self.progress_bar.setValue(min(int(elapsed), int(self.current_est_time)))
                self.progress_bar.setFormat(f"[{addon_prefix}] {map_base} | {cur_str} / {est_str}")
            else:
                self.progress_bar.setValue((self.progress_bar.value() + 1) % 100)
                self.progress_bar.setFormat(f"[{addon_prefix}] {map_base} | {cur_str} / ?")
            
            if len(self.map_queue) > 1 and self.build_start_time:
                total_elapsed = time.time() - self.build_start_time
                total_cur_str = self.elapsed_tracker.format_time(total_elapsed)
                
                if getattr(self, 'total_est_time', -1.0) > 0:
                    self.total_progress_bar.setValue(min(int(total_elapsed), int(self.total_est_time)))
                    total_est_str = self.elapsed_tracker.format_time(self.total_est_time)
                    self.total_progress_bar.setFormat(f"Total Progress ({self.current_map_index}/{len(self.map_queue)}): {total_cur_str} / {total_est_str}")
                else:
                    self.total_progress_bar.setValue((self.total_progress_bar.value() + 1) % 100)
                    self.total_progress_bar.setFormat(f"Total Progress ({self.current_map_index}/{len(self.map_queue)}): {total_cur_str} / ?")

    def abort_compilation(self):
        self.build_was_aborted = True
        self.elapsed_timer.stop()
        if self.compilation_thread and self.compilation_thread.isRunning():
            self.compilation_thread.abort()
            self.log_warning("Aborting compilation")
        if self.cubemap_thread and self.cubemap_thread.isRunning():
            self.cubemap_thread.abort()
            self.log_warning("Aborting cubemap build")

    def on_output_received(self, line: str):
        self.add_log_message(line)
        
        if not hasattr(self, 'phase_times'):
            self.phase_times = {}
        
        # Strip HTML tags for reliable parsing
        clean_line = re.sub(r'<[^>]+>', '', line)
            
        t = time.time()
        
        if "... Building 'nav'" in clean_line:
            self.phase_times["nav_start"] = t
        elif "... Building 'sareverb'" in clean_line or "--> Map build finished" in clean_line:
            if "nav_start" in self.phase_times and "nav_end" not in self.phase_times:
                self.phase_times["nav_end"] = t
            if "-->" not in clean_line:
                self.phase_times["audio_start"] = t
                
        if "--> Map build finished" in clean_line:
            if "audio_start" in self.phase_times:
                self.phase_times["audio_end"] = t
                
        # vis
        vis_match = re.search(r'Visibility complete in ([\d\.]+)s', clean_line)
        if vis_match:
            self.phase_times["vis"] = float(vis_match.group(1))
            
        # light
        if 'Baked Lighting Total Time' in clean_line:
            light_match = re.search(r'(\d+)\s*hrs?\s+(\d+)\s*mins?\s+(\d+)\s*seconds?', clean_line)
            if light_match:
                self.phase_times["light"] = float(int(light_match.group(1))*3600 + int(light_match.group(2))*60 + int(light_match.group(3)))
            else:
                print(f"[DEBUG] Light regex failed on: {repr(clean_line)}")
                print(f"[DEBUG] Raw line was: {repr(line)}")

    def on_compilation_finished(self, exit_code: int, elapsed_time: float):
        self.elapsed_timer.stop()
        self.is_compiling = False
        self.ui.build_button.setEnabled(True)
        self.ui.abort_button.setEnabled(False)

        self.last_build_time = elapsed_time
        time_str = self.format_time(elapsed_time)
        self.ui.last_build_stats_label.setText("")

        if self.build_was_aborted:
            self.log_separator()
            self.log_warning('Compilation aborted by user')
            self.log_separator()
            self.finish_build()
            return

        self.log_separator()
        self.log_phase(f'Compilation completed in {time_str}')
        self.log_separator()

        try:
            set_settings_value("MapBuilder", "LastBuildTime", time_str)
        except Exception as e:
            print(f"Failed to save LastBuildTime: {e}")

        if exit_code == 0:
            map_path = os.path.abspath(self.map_queue[self.current_map_index - 1])
            settings = getattr(self, 'current_map_settings', self.settings_panel.get_settings())
            
            if hasattr(self, 'phase_times'):
                vis = self.phase_times.get("vis", 0)
                light = self.phase_times.get("light", 0)
                nav = self.phase_times.get("nav_end", 0) - self.phase_times.get("nav_start", 0)
                audio = self.phase_times.get("audio_end", 0) - self.phase_times.get("audio_start", 0)
                
                world_base = max(0.1, elapsed_time - vis - light - nav - audio)
                
                self.build_history.record_phase_time(map_path, "world", world_base)
                
                if "vis" in self.phase_times:
                    self.build_history.record_phase_time(map_path, "vis", vis)
                if "nav_start" in self.phase_times and "nav_end" in self.phase_times:
                    self.build_history.record_phase_time(map_path, "nav", nav)
                if "audio_start" in self.phase_times and "audio_end" in self.phase_times:
                    self.build_history.record_phase_time(map_path, "audio", audio)
                if "light" in self.phase_times:
                    if not settings.no_light_calculations:
                        light_key = f"light_Q{settings.lightmap_quality}_{settings.lightmap_max_resolution}_F{int(settings.lightmap_filtering)}_LB{int(settings.vrad3_large_block_size)}"
                        self.build_history.record_phase_time(map_path, light_key, light)

            if self.settings_panel.get_settings().save_build_logs:
                self._save_auto_log(Path(self.map_queue[self.current_map_index - 1]).stem)
            
            self.current_map_stats = self.current_map_stats or {}
            self.current_map_stats['Total'] = self.format_time(elapsed_time)
            self.build_stats.append(self.current_map_stats)
            map_name = Path(self.map_queue[self.current_map_index - 1]).stem
            self.log_success(f'{map_name} compiled successfully')
            
            if len(self.map_queue) > 1:
                # End of map progress will be updated automatically by _update_elapsed_display
                # or handled nicely in the next map.
                pass
        else:
            map_name = Path(self.map_queue[self.current_map_index - 1]).stem
            self.log_error(f'Compilation failed for {map_name}')

        if self.current_map_index < len(self.map_queue):
            self.process_next_map()
        else:
            self.finish_build()

    def process_next_map(self):
        try:
            if self.compilation_thread and self.compilation_thread.isRunning():
                return

            if self.current_map_index >= len(self.map_queue):
                self.finish_build()
                return

            rel = self.map_queue[self.current_map_index]
            mappath_abs = os.path.abspath(rel)

            if not os.path.exists(mappath_abs):
                self.log_error(f'Map file not found: {mappath_abs}')
                self.current_map_index += 1
                self.process_next_map()
                return

            # Extract addon_dir from absolute path
            # Assuming path contains 'csgo_addons'
            addon_dir = get_addon_dir()
            try:
                p = Path(mappath_abs)
                parts = p.parts
                if 'csgo_addons' in parts:
                    idx = parts.index('csgo_addons')
                    if idx + 1 < len(parts):
                        addon_dir = str(Path(*parts[:idx + 2]))
            except Exception:
                pass

            self.current_map_index += 1
            self.current_map_stats = {"Map": Path(rel).stem}

            settings = self.settings_panel.get_settings()
            single_settings = BuildSettings(**{f.name: getattr(settings, f.name) for f in fields(BuildSettings)})
            single_settings.mappath = mappath_abs

            if is_skybox_map(rel):
                single_settings.build_nav = False
                single_settings.build_vis = False
                single_settings.lightmap_max_resolution = 2048
                self.log_phase(f'Skybox map detected: {Path(rel).stem} - disabling nav/vis, setting lightmap to 2048')

            command = single_settings.to_command_line(addon_dir, self.cs2_path)

            self.compilation_thread = CompilationThread(command, addon_dir)
            self.compilation_thread.outputReceived.connect(self.on_output_received)
            self.compilation_thread.finished.connect(self.on_compilation_finished)

            self.is_compiling = True
            self.ui.build_button.setEnabled(False)
            self.ui.abort_button.setEnabled(True)

            self.elapsed_tracker.start()
            self.dot_cycle = 0
            self.elapsed_timer.start(500)

            self.current_map_settings = single_settings
            self.phase_times = {}
            self.current_est_time = self.build_history.get_estimated_time(mappath_abs, single_settings)
            
            self.current_addon_prefix = Path(addon_dir).name
            self.current_map_base = Path(rel).stem
            
            if self.current_est_time > 0:
                self.progress_bar.setRange(0, int(self.current_est_time))
                self.progress_bar.setValue(0)
            else:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(0)

            if len(self.map_queue) > 1:
                self.log_phase(f'Compiling ({self.current_map_index}/{len(self.map_queue)}): {rel}')
            else:
                self.log_phase(f'Starting compilation: {rel}')

            self.log_info(f'Map file: {mappath_abs}')
            self.log_info(f'Addon directory: {addon_dir}')
            self.log_info(f'Command: {command}')
            self.compilation_thread.start()

        except Exception as e:
            self.log_error(f'Compilation error: {e}')
            self.finish_build()

    def _save_auto_log(self, map_name: str):
        try:
            from src.common import user_data_dir
            log_dir = user_data_dir / "MapBuilder" / "build_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            log_file = log_dir / f"{map_name}_{timestamp}.txt"
            
            text = self.ui.output_list_widget.toPlainText()
            log_file.write_text(text, encoding="utf-8")
        except Exception as e:
            print(f"Error saving auto log: {e}")

    def launch_map_after_build(self, map_list: list):
        if self.build_was_aborted:
            self.log_info("Skipping map launch - build was aborted")
            return

        filtered_maps = [m for m in map_list if not is_skybox_map(m)]

        if not filtered_maps:
            self.log_warning("No non-skybox maps to launch")
            return

        map_to_launch = filtered_maps[-1]
        addon_name, addon_dir, map_name = self._parse_map_path(os.path.abspath(map_to_launch))

        try:
            cs2_exe = Path(self.cs2_path) / "game" / "bin" / "win64" / "cs2.exe"

            commands = get_settings_value("LAUNCH", "commands")
            if not commands:
                commands = default_commands
                set_settings_value("LAUNCH", "commands", commands)

            if '-netconport' not in commands:
                commands += ' -netconport 2121'

            # Ensure -disable_workshop_command_filtering is always included (mandatory flag)
            if '-disable_workshop_command_filtering' not in commands:
                commands += ' -disable_workshop_command_filtering'

            def assemble_commands(commands: str, addon_name):
                return commands.replace('addon_name', addon_name)

            commands = assemble_commands(commands, addon_name)
            launch_cmd = f'"{cs2_exe}" {commands} +map_workshop {addon_name} {map_name}'

            self.log_phase(f'Launching map: {launch_cmd}')
            self.log_info('Closing existing CS2 instances...')
            subprocess.run(['taskkill', '/F', '/IM', 'cs2.exe'], capture_output=True, check=False)
            time.sleep(1)
            subprocess.Popen(launch_cmd, shell=True)
        except Exception as e:
            self.log_error(f'Failed to launch map: {e}')

    def finish_build(self):
        try:
            self.is_compiling = False
            self.ui.build_button.setEnabled(True)
            self.ui.abort_button.setEnabled(False)

            if self.build_was_aborted:
                self.log_separator('=', 80)
                self.log_warning('BUILD ABORTED')
                self.log_separator('=', 80)
                return

            self.log_separator('=', 80)
            self.log_phase('BUILD COMPLETE - FINAL SUMMARY')
            self.log_separator('=', 80)

            if self.build_stats:
                header = f"{'Map Name':<20} | {'Total':<12}"
                self.log_info(header)
                self.log_separator('-', 80)

                for entry in self.build_stats:
                    map_name = entry.get('Map', 'unknown')[:20]
                    total = entry.get('Total', 'N/A')[:12]
                    row = f"{map_name:<20} | {total:<12}"
                    self.log_info(row)

                self.log_separator('=', 80)
                self.log_phase(f'Total maps compiled: {len(self.build_stats)}')

                if self.build_start_time:
                    build_elapsed = time.time() - self.build_start_time
                    self.log_phase(f'Total build time: {self.format_time(build_elapsed)}')

                    if len(self.build_stats) > 0:
                        avg_time = build_elapsed / len(self.build_stats)
                        self.log_phase(f'Average time per map: {self.format_time(avg_time)}')

            self.log_separator('=', 80)
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS)

            settings = self.settings_panel.get_settings()

            # --- Cubemap building (runs BEFORE the normal map launch) ---
            if settings.build_cubemaps and self.map_queue:
                filtered = [m for m in self.map_queue if not is_skybox_map(m)]
                if filtered:
                    self.start_cubemap_queue(filtered)
                    return  # cubemap flow will handle the final launch

            # --- Normal map launch ---
            if settings.load_in_engine_after_build and self.map_queue:
                self.launch_map_after_build(self.map_queue)

        except Exception as e:
            self.log_error(f'Error finishing build: {e}')

    # ====================== Cubemap Build Queue =======================

    def start_cubemap_queue(self, map_list: list):
        """Start building cubemaps for every map using a single CS2 instance."""
        self.cubemap_queue = list(map_list)
        self.is_building_cubemaps = True
        self.ui.build_button.setEnabled(False)
        self.ui.abort_button.setEnabled(True)

        self.log_separator()
        self.log_phase(f'Starting cubemap builds for {len(self.cubemap_queue)} map(s)')
        self.log_separator()

        addon_name = get_addon_name()
        cs2_exe = str(Path(self.cs2_path) / "game" / "bin" / "win64" / "cs2.exe")

        commands = get_settings_value("LAUNCH", "commands")
        if not commands:
            commands = default_commands
            set_settings_value("LAUNCH", "commands", commands)

        if '-netconport' not in commands:
            commands += ' -netconport 2121'
        if '-disable_workshop_command_filtering' not in commands:
            commands += ' -disable_workshop_command_filtering'

        # Note: Do not replace 'addon_name' here, as the BuildCubemapsThread
        # will replace it for each addon in the queue.

        # Strip +map_workshop from launch args — the cubemap thread will
        # send map_workshop via netcon after CS2 reaches the main menu.
        commands = re.sub(r'\+map_workshop\s+\S+(?:\s+\S+)?', '', commands).strip()

        # Extract map data (addon, map_name)
        map_data = []
        for rel in self.cubemap_queue:
            abs_path = os.path.abspath(rel)
            addon, _, map_name = self._parse_map_path(abs_path)
            map_data.append((addon, map_name))

        self.cubemap_thread = BuildCubemapsThread(
            cs2_exe, commands, map_data)
        self.cubemap_thread.outputReceived.connect(self.on_cubemap_output)
        self.cubemap_thread.mapFinished.connect(self.on_cubemap_map_finished)
        self.cubemap_thread.finished.connect(self.on_cubemap_queue_finished)
        self.cubemap_thread.start()

    def on_cubemap_output(self, line: str):
        self.add_log_message(line)

    def on_cubemap_map_finished(self, map_name: str, success: bool):
        if success:
            self.log_success(f'Cubemaps built for {map_name}')
        else:
            self.log_error(f'Cubemap build failed/aborted for {map_name}')

    def on_cubemap_queue_finished(self, success: bool):
        self.is_building_cubemaps = False
        self.ui.build_button.setEnabled(True)
        self.ui.abort_button.setEnabled(False)

        self.log_separator()
        self.log_phase('Cubemap build queue finished')
        self.log_separator()

        # CS2 is left running with the last map loaded (cubemaps baked in).
        # No need to relaunch.

    # ==================================================================

    def run_map(self):
        settings = self.settings_panel.get_settings()
        if not settings.mappath:
            QMessageBox.warning(self, "No Map", "No map file specified")
            return

        # Preserve subdirectory structure: "maps\test\1.vmap" → "test/1"
        _first_map = str(settings.mappath).split(';')[0] if ';' in str(settings.mappath) else str(settings.mappath)
        addon_name, addon_dir, map_name = self._parse_map_path(os.path.abspath(_first_map))

        cs2_exe = Path(self.cs2_path) / "game" / "bin" / "win64" / "cs2.exe"
        commands = get_settings_value("LAUNCH", "commands")

        if not commands:
            commands = default_commands
            set_settings_value("LAUNCH", "commands", commands)

        def assemble_commands(commands: str, addon_name):
            return commands.replace('addon_name', addon_name)

        commands = assemble_commands(commands, addon_name)

        # Ensure mandatory flags are always included
        if '-netconport' not in commands:
            commands += ' -netconport 2121'
        if '-disable_workshop_command_filtering' not in commands:
            commands += ' -disable_workshop_command_filtering'

        # Strip any existing +map_workshop before appending ours
        commands = re.sub(r'\+map_workshop\s+\S+(?:\s+\S+)?', '', commands).strip()
        launch_cmd = f'"{cs2_exe}" {commands} +map_workshop {addon_name} {map_name}'

        self.log_phase(f'Launching: {launch_cmd}')
        self.log_info('Closing existing CS2 instances...')
        subprocess.run(['taskkill', '/F', '/IM', 'cs2.exe'], capture_output=True, check=False)
        time.sleep(1)
        subprocess.Popen(launch_cmd, shell=True)

    def log_phase(self, message: str):
        self._log_colored(message, '#4DA6FF')

    def log_success(self, message: str):
        self._log_colored(message, '#00FF00')

    def log_error(self, message: str):
        self._log_colored(message, '#FF4444')

    def log_warning(self, message: str):
        self._log_colored(message, '#FFAA00')

    def log_info(self, message: str):
        self._log_colored(message, '#CCCCCC')

    def log_separator(self, char='=', length=70):
        self._log_colored(char * length, '#666666')

    def _log_colored(self, message: str, color: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = OutputFormatter.parse_output_line(message)
        timestamped_message = f'<span style="color:#808080;">[{timestamp}]</span> <span style="color:{color};">{formatted_message}</span>'
        self.ui.output_list_widget.append(timestamped_message)
        scrollbar = self.ui.output_list_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_log_message(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = OutputFormatter.parse_output_line(message)
        timestamped_message = f'<span style="color:#808080;">[{timestamp}]</span> {formatted_message}'
        self.ui.output_list_widget.append(timestamped_message)
        scrollbar = self.ui.output_list_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _output_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        save_action = menu.addAction("Save log...")
        save_action.triggered.connect(self.save_build_log)
        global_pos = self.ui.output_list_widget.mapToGlobal(pos)
        menu.exec_(global_pos)

    def save_build_log(self):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            default_name = f"{timestamp}.txt"
            text = self.ui.output_list_widget.toPlainText()

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save build log",
                default_name,
                "Text Files (*.txt);;All Files (*)"
            )

            if not filename:
                return

            log_file = pathlib.Path(filename)
            log_file.write_text(text, encoding="utf-8")
            print(f"Build log saved to: {log_file}")

        except Exception as e:
            print(f"Error saving build log: {e}")

    def format_time(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


def main():
    app = QApplication(sys.argv)
    dialog = MapBuilderDialog()
    dialog.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
