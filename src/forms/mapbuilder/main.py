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

        self.addon_path = get_addon_dir()
        self.cs2_path = get_cs2_path()
        self.ui.splitter.setSizes([200, 300])

        if not self.cs2_path:
            raise ValueError("CS2 path not found. Please set CS2 installation path in settings.")

        self.cs2_path = str(self.cs2_path)

        presets_file = Path(self.addon_path) / ".hammer5tools" / "build_presets.json"
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

        last_time_str = get_settings_value("MapBuilder", "LastBuildTime", default="")
        if last_time_str:
            try:
                self.ui.last_build_stats_label.setText(f"Last Build Time: {last_time_str}")
            except Exception:
                pass

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

        self.log_phase('<b>Skybox Map Rules:</b>')
        self.log_info('  • Compiled without -nav, -vis, and -audio flags')
        self.log_info('  • Lightmap resolution limited to 2048')

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
        if self.is_compiling and self.compilation_thread:
            reply = QMessageBox.question(
                self,
                "Abort Compilation?",
                "Compilation is currently running.\n\n"
                "Do you want to abort the compilation and close this dialog?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.build_was_aborted = True
                self.log_warning("User closed dialog - aborting compilation")
                self.compilation_thread.abort()
                self.compilation_thread.wait(2000)
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

        self.ui.output_list_widget.clear()

        if len(self.map_queue) > 1:
            self.log_separator()
            self.log_phase(f'Batch compilation - queued {len(self.map_queue)} maps')
            self.log_separator()
        else:
            pass

        self.process_next_map()

    def _update_elapsed_display(self):
        if self.is_compiling and self.elapsed_tracker.start_time:
            elapsed = self.elapsed_tracker.get_elapsed()
            time_with_dots = self.elapsed_tracker.format_with_dots(elapsed, self.dot_cycle)
            self.ui.last_build_stats_label.setText(f"Compiling: [{time_with_dots}]")
            self.dot_cycle += 1

    def abort_compilation(self):
        if self.compilation_thread:
            self.build_was_aborted = True
            self.elapsed_timer.stop()
            self.compilation_thread.abort()
            self.log_warning("Aborting compilation")

    def on_output_received(self, line: str):
        self.add_log_message(line)

    def on_compilation_finished(self, exit_code: int, elapsed_time: float):
        self.elapsed_timer.stop()
        self.is_compiling = False
        self.ui.build_button.setEnabled(True)
        self.ui.abort_button.setEnabled(False)

        self.last_build_time = elapsed_time
        time_str = self.format_time(elapsed_time)
        self.ui.last_build_stats_label.setText(f"Last Build Time: {time_str}")

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
            self.current_map_stats = self.current_map_stats or {}
            self.current_map_stats['Total'] = self.format_time(elapsed_time)
            self.build_stats.append(self.current_map_stats)
            map_name = Path(self.map_queue[self.current_map_index - 1]).stem
            self.log_success(f'{map_name} compiled successfully')
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
            mappath_abs = os.path.join(self.addon_path, rel)

            if not os.path.exists(mappath_abs):
                self.log_error(f'Map file not found: {mappath_abs}')
                self.current_map_index += 1
                self.process_next_map()
                return

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

            command = single_settings.to_command_line(self.addon_path, self.cs2_path)

            self.compilation_thread = CompilationThread(command, self.addon_path)
            self.compilation_thread.outputReceived.connect(self.on_output_received)
            self.compilation_thread.finished.connect(self.on_compilation_finished)

            self.is_compiling = True
            self.ui.build_button.setEnabled(False)
            self.ui.abort_button.setEnabled(True)

            self.elapsed_tracker.start()
            self.dot_cycle = 0
            self.elapsed_timer.start(500)

            if len(self.map_queue) > 1:
                self.log_phase(f'Compiling ({self.current_map_index}/{len(self.map_queue)}): {rel}')
            else:
                self.log_phase(f'Starting compilation: {rel}')

            self.log_info(f'Map file: {mappath_abs}')
            self.log_info(f'Command: {command}')
            self.compilation_thread.start()

        except Exception as e:
            self.log_error(f'Compilation error: {e}')
            self.finish_build()

    def launch_map_after_build(self, map_list: list):
        if self.build_was_aborted:
            self.log_info("Skipping map launch - build was aborted")
            return

        filtered_maps = [m for m in map_list if not is_skybox_map(m)]

        if not filtered_maps:
            self.log_warning("No non-skybox maps to launch")
            return

        map_to_launch = filtered_maps[-1]
        map_name = Path(map_to_launch).stem

        try:
            addon_name = get_addon_name()
            cs2_exe = Path(self.cs2_path) / "game" / "bin" / "win64" / "cs2.exe"

            commands = get_settings_value("LAUNCH", "commands")
            if not commands:
                commands = default_commands
                set_settings_value("LAUNCH", "commands", commands)

            def assemble_commands(commands: str, addon_name):
                return commands.replace('addon_name', addon_name)

            commands = assemble_commands(commands, addon_name)
            launch_cmd = f'"{cs2_exe}" {commands} +map_workshop {addon_name} {map_name}'

            self.log_phase(f'Launching map: {launch_cmd}')
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
            if settings.load_in_engine_after_build and self.map_queue:
                self.launch_map_after_build(self.map_queue)

        except Exception as e:
            self.log_error(f'Error finishing build: {e}')

    def run_map(self):
        settings = self.settings_panel.get_settings()
        if not settings.mappath:
            QMessageBox.warning(self, "No Map", "No map file specified")
            return

        map_name = Path(settings.mappath).stem
        cs2_exe = Path(self.cs2_path) / "game" / "bin" / "win64" / "cs2.exe"
        addon_name = get_addon_name()
        commands = get_settings_value("LAUNCH", "commands")

        if not commands:
            commands = default_commands
            set_settings_value("LAUNCH", "commands", commands)

        def assemble_commands(commands: str, addon_name):
            return commands.replace('addon_name', addon_name)

        commands = assemble_commands(commands, addon_name)
        launch_cmd = f'"{cs2_exe}" {commands} +map_workshop {addon_name} {map_name}'

        self.log_phase(f'Launching: {launch_cmd}')
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
