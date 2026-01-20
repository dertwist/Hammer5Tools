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

# Import UI and custom modules
from src.forms.mapbuilder.ui_main import Ui_mapbuilder_dialog
from src.forms.mapbuilder.system_monitor import SystemMonitor
from src.forms.mapbuilder.output_formater import OutputFormatter
from src.forms.mapbuilder.preset_manager import PresetManager, BuildPreset, BuildSettings
from src.forms.mapbuilder.widgets import SettingsPanel, PresetButton
from src.settings.main import get_addon_name, get_settings_value, get_addon_dir, get_cs2_path, set_settings_value
from src.common import enable_dark_title_bar, app_dir
from src.other.addon_functions import launch_addon


class CompilationThread(QThread):
    """Thread for running compilation process"""

    outputReceived = Signal(str)  # Raw output line
    finished = Signal(int, float)  # exit code, elapsed time

    def __init__(self, command: str, working_dir: str):
        super().__init__()
        self.command = command
        self.working_dir = working_dir
        self.process = None
        self.should_abort = False
        self.start_time = None

    def run(self):
        """Run compilation process and stream output real-time"""
        self.start_time = time.time()

        try:
            # Start process with unbuffered output
            popen_kwargs = dict(
                args=self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,  # Unbuffered binary stream
                cwd=self.working_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            self.process = subprocess.Popen(**popen_kwargs)

            # Buffer to accumulate characters until we find a break
            buffer = bytearray()

            while True:
                if self.should_abort:
                    self.process.terminate()
                    break

                # Read 1 byte at a time to ensure we never block waiting for a full line
                byte = self.process.stdout.read(1)

                # If read returns empty and process is dead, we are done
                if not byte and self.process.poll() is not None:
                    break

                if byte:
                    buffer.extend(byte)

                    # Check if we have a complete "visual" line
                    # The compiler uses both \n and <br/> (or <br>) as delimiters
                    current_str = ""
                    try:
                        current_str = buffer.decode('utf-8', errors='ignore')
                    except:
                        pass  # Wait for more bytes if decoding fails

                    # Check for delimiters
                    is_newline = current_str.endswith('\n')
                    is_html_br = current_str.endswith('<br/>') or current_str.endswith('<br>')

                    if is_newline or is_html_br:
                        # Decode fully
                        try:
                            line = buffer.decode('utf-8', errors='replace')
                        except:
                            line = buffer.decode('latin-1', errors='replace')

                        # Clean up the line for display
                        # We strip the trailing breaks because append() adds its own new paragraph
                        line = line.replace('<br/>', '').replace('<br>', '').rstrip()

                        if line:
                            self.outputReceived.emit(line)
                            # Tiny sleep to let the main thread process the event
                            self.msleep(1)

                        # Clear buffer
                        buffer = bytearray()

            # Emit any remaining text in buffer
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
                if self.process.returncode is None:  # Still alive
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)],
                                   capture_output=True, check=False)
                else:
                    print(f"Process {pid} already finished")
            except:
                pass
            finally:
                self.process = None  # Reset immediately


class ElapsedTimeTracker:
    """Tracks elapsed time with formatted output and animated dots"""

    def __init__(self):
        self.start_time = None
        self.paused_time = 0.0

    def start(self):
        """Start timing"""
        self.start_time = time.time()
        self.paused_time = 0.0

    def get_elapsed(self) -> float:
        """Get elapsed seconds"""
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) - self.paused_time

    def format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS or HH:MM:SS"""
        if seconds < 0:
            seconds = 0

        if seconds < 3600:  # Less than 1 hour
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def format_with_dots(self, seconds: float, dot_cycle: int) -> str:
        """Format time with animated dots based on cycle"""
        time_str = self.format_time(seconds)
        # Cycle through: . .. ... (repeats)
        dots = '.' * ((dot_cycle % 3) + 1)
        return f"{time_str}{dots}"


def is_skybox_map(mappath: str) -> bool:
    """Check if map name ends with _skybox suffix"""
    map_name = Path(mappath).stem
    return map_name.endswith('_skybox')


class MapBuilderDialog(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_mapbuilder_dialog()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)

        # Get paths from settings
        self.addon_path = get_addon_dir()
        self.cs2_path = get_cs2_path()

        self.ui.splitter.setSizes([200, 300])

        # Ensure cs2_path is a string (not None)
        if not self.cs2_path:
            raise ValueError("CS2 path not found. Please set CS2 installation path in settings.")

        # Convert to string if it's a Path object
        self.cs2_path = str(self.cs2_path)

        # Initialize managers
        presets_file = Path(self.addon_path) / ".hammer5tools" / "build_presets.json"
        self.preset_manager = PresetManager(presets_file)

        self.ui.output_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.output_list_widget.customContextMenuRequested.connect(self._output_context_menu)

        # Current state
        self.current_preset: BuildPreset = None
        self.compilation_thread: CompilationThread = None
        self.is_compiling = False
        self.last_build_time = 0.0

        # Elapsed time tracking
        self.elapsed_tracker = ElapsedTimeTracker()
        self.elapsed_timer = QTimer()
        self.elapsed_timer.timeout.connect(self._update_elapsed_display)
        self.dot_cycle = 0

        # Load last build duration from settings to display on start
        last_time_str = get_settings_value("MapBuilder", "LastBuildTime", default="")
        if last_time_str:
            try:
                self.ui.last_build_stats_label.setText(f"Last Build Time: {last_time_str}")
            except Exception:
                pass

        # Setup UI
        self.setup_settings_panel()
        self.setup_preset_buttons()
        self.setup_system_monitor()
        self.setup_connections()

        # Load first preset
        presets = self.preset_manager.get_all_presets()
        if presets:
            self.load_preset(presets[0])

        # Current build log buffer
        self.current_build_logs = []
        self.current_build_timestamp = None

        self.map_queue = []
        self.current_map_index = 0
        self.build_stats = []
        self.current_map_stats = {}
        self.build_start_time = None

        # Display startup message about skybox maps
        self.add_log_message('<span style="color:#FFFF00;"><b>Note: vmaps with _skybox in the filename will be compiled without nav, vis, and audio, and their lightmap resolution will be set to 2048.</b></span>')

    def setup_settings_panel(self):
        """Setup dynamically generated settings panel"""
        self.settings_panel = SettingsPanel()

        # Clear existing widgets from build_settings_content
        while self.ui.build_settings_content.count():
            item = self.ui.build_settings_content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add settings panel
        self.ui.build_settings_content.addWidget(self.settings_panel)
        self.ui.build_settings_content.addStretch()

    def setup_preset_buttons(self):
        """Setup preset buttons"""
        # Clear existing preset buttons
        preset_layout = self.ui.build_presets.widget().layout()
        while preset_layout.count() > 1:  # Keep spacer
            item = preset_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create buttons for each preset
        self.preset_buttons = {}
        for preset in self.preset_manager.get_all_presets():
            btn = PresetButton(preset.name, preset.is_default)
            btn.presetClicked.connect(self.on_preset_clicked)

            btn.contextMenuRequested.connect(
                lambda data, p=preset: self.show_preset_context_menu(data, p)
            )

            preset_layout.insertWidget(preset_layout.count() - 1, btn)
            self.preset_buttons[preset.name] = btn

        # Add "New Preset" button
        new_btn = PresetButton("+", False)
        new_btn.setText("+")
        new_btn.setToolTip("Create new preset")
        new_btn.presetClicked.connect(self.create_new_preset)
        preset_layout.insertWidget(preset_layout.count() - 1, new_btn)

    def setup_system_monitor(self):
        """Setup system resource monitor"""
        # Remove any existing widgets
        while self.ui.system_monitor.layout() and self.ui.system_monitor.layout().count():
            item = self.ui.system_monitor.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create new system monitor
        self.system_monitor = SystemMonitor()

        # Add to frame
        if not self.ui.system_monitor.layout():
            from PySide6.QtWidgets import QVBoxLayout
            layout = QVBoxLayout(self.ui.system_monitor)
            layout.setContentsMargins(0, 0, 0, 0)

        self.ui.system_monitor.layout().addWidget(self.system_monitor)

    def setup_connections(self):
        """Setup signal connections"""
        self.ui.build_button.clicked.connect(self.start_compilation)
        self.ui.run_button.clicked.connect(self.run_map)
        self.ui.abort_button.clicked.connect(self.abort_compilation)

        # Initially disable abort button
        self.ui.abort_button.setEnabled(False)

    def closeEvent(self, event):
        """Handle dialog close event - check if compilation is running"""
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
                self.add_log_message("⚠ User closed dialog - aborting compilation...")
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
        """Handle preset button click"""
        preset = self.preset_manager.get_preset(preset_name)
        if preset:
            self.load_preset(preset)

    def load_preset(self, preset: BuildPreset):
        """Load preset into UI"""
        self.current_preset = preset
        self.settings_panel.set_settings(preset.settings)

        # Update button states
        for name, btn in self.preset_buttons.items():
            btn.set_active(name == preset.name)

        self.setWindowTitle(f"Map Builder - {preset.name}")

    def show_preset_context_menu(self, signal_data, preset: BuildPreset):
        """Show context menu for preset button"""
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
        """Create new preset from current settings"""
        name, ok = QInputDialog.getText(
            self, "New Preset", "Enter preset name:"
        )

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
        """Save current settings to preset"""
        current_settings = self.settings_panel.get_settings()
        self.preset_manager.update_preset(preset.name, current_settings)
        QMessageBox.information(self, "Success", f"Preset '{preset.name}' updated")

    def rename_preset(self, preset: BuildPreset):
        """Rename preset"""
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
        """Delete preset"""
        reply = QMessageBox.question(
            self, "Delete Preset",
            f"Delete preset '{preset.name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.preset_manager.delete_preset(preset.name):
                self.setup_preset_buttons()
                # Load first available preset
                presets = self.preset_manager.get_all_presets()
                if presets:
                    self.load_preset(presets[0])

    def start_compilation(self):
        """Start map compilation with unified queue-based approach"""
        if self.is_compiling:
            QMessageBox.warning(self, "Already Compiling", "Compilation already in progress")
            return

        # Get current settings
        settings = self.settings_panel.get_settings()
        mappaths = [p for p in str(settings.mappath).split(';') if p]

        if not mappaths:
            QMessageBox.warning(self, "Invalid Map", "Please select a valid map file")
            return

        # Initialize queue for all maps (single or multiple)
        self.map_queue = mappaths
        self.current_map_index = 0
        self.build_stats = []
        self.build_start_time = time.time()

        # Clear logs
        self.ui.output_list_widget.clear()

        # Log start
        if len(self.map_queue) > 1:
            self.add_log_message("=" * 70)
            self.add_log_message(f"Batch compilation - queued {len(self.map_queue)} maps")
            self.add_log_message("=" * 70)
        else:
            self.add_log_message("=" * 70)
            self.add_log_message(f"Starting compilation: {self.map_queue[0]}")
            self.add_log_message("=" * 70)

        # Start processing the queue
        self.process_next_map()

    def _update_elapsed_display(self):
        """Update elapsed time display with animated dots"""
        if self.is_compiling and self.elapsed_tracker.start_time:
            elapsed = self.elapsed_tracker.get_elapsed()
            time_with_dots = self.elapsed_tracker.format_with_dots(elapsed, self.dot_cycle)
            self.ui.last_build_stats_label.setText(f"Compiling: [{time_with_dots}]")
            self.dot_cycle += 1

    def abort_compilation(self):
        """Abort running compilation"""
        if self.compilation_thread:
            self.elapsed_timer.stop()
            self.compilation_thread.abort()
            self.add_log_message("Aborting compilation...")

    def on_output_received(self, line: str):
        """Handle raw output line - called for EACH line"""
        # Add each line immediately
        self.add_log_message(line)

    def on_compilation_finished(self, exit_code: int, elapsed_time: float):
        """Handle compilation finished"""
        # Stop elapsed time tracking
        self.elapsed_timer.stop()

        self.is_compiling = False
        self.ui.build_button.setEnabled(True)
        self.ui.abort_button.setEnabled(False)

        self.last_build_time = elapsed_time
        time_str = self.format_time(elapsed_time)
        self.ui.last_build_stats_label.setText(f"Last Build Time: {time_str}")

        # Add elapsed time to final log
        self.add_log_message(f"\n{'='*60}")
        self.add_log_message(f"Compilation completed in {time_str}")
        self.add_log_message(f"{'='*60}\n")

        # Persist last build duration string in settings for display on next load
        try:
            set_settings_value("MapBuilder", "LastBuildTime", time_str)
        except Exception as e:
            print(f"Failed to save LastBuildTime: {e}")

        # Record stats for current map
        if exit_code == 0:
            self.current_map_stats = self.current_map_stats or {}
            self.current_map_stats['Total'] = self.format_time(elapsed_time)
            self.build_stats.append(self.current_map_stats)
            map_name = Path(self.map_queue[self.current_map_index - 1]).stem
            self.add_log_message(f"✓ {map_name} compiled successfully")
        else:
            map_name = Path(self.map_queue[self.current_map_index - 1]).stem
            self.add_log_message(f"✗ Compilation failed for {map_name}")

        # Process next map or finish
        if self.current_map_index < len(self.map_queue):
            self.process_next_map()
        else:
            self.finish_build()

    def process_next_map(self):
        """Process the next map in the queue"""
        try:
            # Stop re-entry if a compile is running
            if self.compilation_thread and self.compilation_thread.isRunning():
                return

            # If finished with all maps, finish build
            if self.current_map_index >= len(self.map_queue):
                self.finish_build()
                return

            rel = self.map_queue[self.current_map_index]
            self.current_map_index += 1
            self.current_map_stats = {"Map": Path(rel).stem}

            # Build settings for this map
            settings = self.settings_panel.get_settings()
            single_settings = BuildSettings(**{f.name: getattr(settings, f.name) for f in fields(BuildSettings)})
            single_settings.mappath = rel

            # Apply skybox-specific compilation settings
            if is_skybox_map(rel):
                single_settings.build_nav = False
                single_settings.build_vis = False
                single_settings.lightmap_max_resolution = 2048
                self.add_log_message(f"Skybox map detected: {Path(rel).stem} - disabling nav/vis, setting lightmap resolution to 2048")

            command = single_settings.to_command_line(self.addon_path, self.cs2_path)

            # Create and start thread
            self.compilation_thread = CompilationThread(command, self.addon_path)
            self.compilation_thread.outputReceived.connect(self.on_output_received)
            self.compilation_thread.finished.connect(self.on_compilation_finished)

            # Update UI state
            self.is_compiling = True
            self.ui.build_button.setEnabled(False)
            self.ui.abort_button.setEnabled(True)

            self.elapsed_tracker.start()
            self.dot_cycle = 0
            self.elapsed_timer.start(500)

            if len(self.map_queue) > 1:
                self.add_log_message(f"Compiling ({self.current_map_index}/{len(self.map_queue)}): {rel}")
            else:
                self.add_log_message(f"Starting compilation: {rel}")

            self.add_log_message(f"Command: {command}")
            self.compilation_thread.start()
        except Exception as e:
            self.add_log_message(f"Compilation error: {e}")
            self.finish_build()

    def launch_map_after_build(self, map_list: list):
        """Launch map in engine after successful build, filtering out skybox maps"""
        # Filter out skybox maps
        filtered_maps = [m for m in map_list if not is_skybox_map(m)]

        if not filtered_maps:
            self.add_log_message("⚠ No non-skybox maps to launch")
            return

        # Select the last map from filtered list
        map_to_launch = filtered_maps[-1]
        map_name = Path(map_to_launch).stem

        try:
            addon_name = get_addon_name()
            cs2_exe = Path(self.cs2_path) / "game" / "bin" / "win64" / "cs2.exe"

            # Launch addon first
            launch_addon()

            # Execute CS2 launch command
            launch_cmd = f'"{cs2_exe}" -tools -gpuraytracing -addon {addon_name} +map_workshop {addon_name} {map_name}'
            self.add_log_message(f"Launching map: {launch_cmd}")
            subprocess.Popen(launch_cmd, shell=True)
        except Exception as e:
            self.add_log_message(f"Failed to launch map: {e}")

    def finish_build(self):
        """End-of-build summary and statistics"""
        try:
            self.is_compiling = False
            self.ui.build_button.setEnabled(True)
            self.ui.abort_button.setEnabled(False)

            # Build summary table
            self.add_log_message("\n" + "=" * 80)
            self.add_log_message("BUILD COMPLETE - FINAL SUMMARY")
            self.add_log_message("=" * 80)

            if self.build_stats:
                # Header with better formatting
                header = f"{'Map Name':<20} | {'Total':<12}"
                self.add_log_message(header)
                self.add_log_message("-" * 80)

                # Rows for each map
                for entry in self.build_stats:
                    map_name = entry.get('Map', 'unknown')[:20]
                    total = entry.get('Total', 'N/A')[:12]
                    row = f"{map_name:<20} | {total:<12}"
                    self.add_log_message(row)

                self.add_log_message("=" * 80)

                # Statistics
                self.add_log_message(f"Total maps compiled: {len(self.build_stats)}")

                # Calculate total build time
                if self.build_start_time:
                    build_elapsed = time.time() - self.build_start_time
                    self.add_log_message(f"Total build time: {self.format_time(build_elapsed)}")

                    # Average per-map
                    if len(self.build_stats) > 0:
                        avg_time = build_elapsed / len(self.build_stats)
                        self.add_log_message(f"Average time per map: {self.format_time(avg_time)}")

            self.add_log_message("=" * 80)
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS)

            # Launch map if enabled
            settings = self.settings_panel.get_settings()
            if settings.load_in_engine_after_build and self.map_queue:
                self.launch_map_after_build(self.map_queue)

        except Exception as e:
            self.add_log_message(f"Error finishing build: {e}")

    def run_map(self):
        """Run map without building"""
        # Get map name from current settings
        settings = self.settings_panel.get_settings()
        if not settings.mappath:
            QMessageBox.warning(self, "No Map", "No map file specified")
            return

        map_name = Path(settings.mappath).stem

        # Build launch command
        cs2_exe = Path(self.cs2_path) / "game" / "bin" / "win64" / "cs2.exe"
        addon_name = get_addon_name()

        launch_cmd = f'"{cs2_exe}" -tools -gpuraytracing -addon {addon_name} +map_workshop {addon_name} {map_name}'

        self.add_log_message(f"Launching: {launch_cmd}")

        # Launch in separate process
        subprocess.Popen(launch_cmd, shell=True)

    def add_log_message(self, message: str):
        """Append message to the output panel as HTML with timestamp - called for EACH line"""
        # Get current timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Pass through formatter (decodes HTML entities)
        formatted_message = OutputFormatter.parse_output_line(message)

        # Prepend gray timestamp to the message
        timestamped_message = f'<span style="color:#808080;">[{timestamp}]</span> {formatted_message}'

        # Append HTML directly - QTextEdit will handle it
        self.ui.output_list_widget.append(timestamped_message)

        # Ensure scrolled to bottom
        scrollbar = self.ui.output_list_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _output_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        save_action = menu.addAction("Save log...")
        save_action.triggered.connect(self.save_build_log)
        global_pos = self.ui.output_list_widget.mapToGlobal(pos)
        menu.exec_(global_pos)

    def save_build_log(self):
        """Save the current build log to file via Save As dialog"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            default_name = f"{timestamp}.txt"

            # Get the buffer content directly from the plain text editor
            text = self.ui.output_list_widget.toPlainText()

            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save build log",
                default_name,
                "Text Files (*.txt);;All Files (*)"
            )

            if not filename:
                return  # user cancelled

            log_file = pathlib.Path(filename)
            log_file.write_text(text, encoding="utf-8")
            print(f"Build log saved to: {log_file}")

        except Exception as e:
            print(f"Error saving build log: {e}")

    def format_time(self, seconds: float) -> str:
        """Format seconds as human-readable time"""
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
