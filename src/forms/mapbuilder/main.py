"""
Enhanced Map Builder Dialog with complete preset management,
real-time output parsing, and dynamic UI generation.
"""
import os.path
import sys
import subprocess
import threading
import pathlib
import os
import time
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QApplication, QMessageBox, QInputDialog,
    QMenu, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QPoint
from PySide6.QtGui import QColor, QIcon, QTextDocument, QTextCursor
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

# Import UI and custom modules
from src.forms.mapbuilder.ui_main import Ui_mapbuilder_dialog
from src.forms.mapbuilder.system_monitor import SystemMonitor
from src.forms.mapbuilder.output_formater import OutputFormatter
from src.forms.mapbuilder.preset_manager import PresetManager, BuildPreset, BuildSettings
from src.forms.mapbuilder.widgets import SettingsPanel, PresetButton
from src.settings.main import get_addon_name, get_settings_value, get_addon_dir, get_cs2_path, set_settings_value
from src.common import enable_dark_title_bar, app_dir


class CompilationThread(QThread):
    """Thread for running compilation process"""

    outputReceived = Signal(str)  # Raw output line
    progressUpdated = Signal(object)  # CompilationProgress object
    messageReceived = Signal(object)  # CompilationMessage object
    finished = Signal(int, float)  # exit code, elapsed time

    def __init__(self, command: str, working_dir: str):
        super().__init__()
        self.command = command
        self.working_dir = working_dir
        self.process = None
        self.should_abort = False
        self.start_time = None

    def run(self):
        """Run compilation process and parse output"""
        self.start_time = time.time()

        try:
            # Start process
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=self.working_dir,
                universal_newlines=True
            )

            # Read output line by line
            for line in iter(self.process.stdout.readline, ''):
                if self.should_abort:
                    self.process.terminate()
                    break

                line = line.rstrip()
                if line:
                    self.outputReceived.emit(line)

            # Wait for process to complete
            self.process.wait()
            exit_code = self.process.returncode
            elapsed = time.time() - self.start_time

            self.finished.emit(exit_code, elapsed)

        except Exception as e:
            print(f"Compilation error: {e}")
            self.finished.emit(-1, 0)

    def abort(self):
        """Abort compilation"""
        self.should_abort = True
        if self.process:
            self.process.terminate()


class MapBuilderDialog(QDialog):
    """
    Enhanced Map Builder Dialog for CS2 map compilation.
    Features:
    - Preset-based build configurations
    - Real-time output parsing with progress tracking
    - System resource monitoring
    - Warning/Error reporting
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_mapbuilder_dialog()
        self.ui.setupUi(self)
        enable_dark_title_bar(self)

        # Get paths from settings
        self.addon_path = get_addon_dir()
        self.cs2_path = get_cs2_path()
        
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
        """Start map compilation"""
        if self.is_compiling:
            QMessageBox.warning(self, "Already Compiling", "Compilation already in progress")
            return

        # Get current settings
        settings = self.settings_panel.get_settings()
        mappath = os.path.join(get_addon_dir(), settings.mappath)
        # Validate mappath
        if not mappath or not Path(mappath).exists():
            QMessageBox.warning(self, "Invalid Map", "Please select a valid map file")
            return

        # Generate command
        command = settings.to_command_line(self.addon_path, self.cs2_path)

        self.ui.output_list_widget.clear()

        # Create compilation thread
        self.compilation_thread = CompilationThread(command, self.addon_path)
        self.compilation_thread.outputReceived.connect(self.on_output_received)
        self.compilation_thread.finished.connect(self.on_compilation_finished)

        # Update UI state
        self.is_compiling = True
        self.ui.build_button.setEnabled(False)
        self.ui.abort_button.setEnabled(True)

        # Start compilation
        self.compilation_thread.start()

        # Log to output tab
        self.add_log_message(f"Starting compilation: {settings.mappath}")
        self.add_log_message(f"Command: {command}")

    def abort_compilation(self):
        """Abort running compilation"""
        if self.compilation_thread:
            self.compilation_thread.abort()
            self.add_log_message("Aborting compilation...")

    def on_output_received(self, line: str):
        """Handle raw output line"""
        # Add to output list; line may already be HTML (e.g., resourcecompiler -html)
        self.add_log_message(line)


    def on_compilation_finished(self, exit_code: int, elapsed_time: float):
        """Handle compilation finished"""
        self.is_compiling = False
        self.ui.build_button.setEnabled(True)
        self.ui.abort_button.setEnabled(False)

        self.last_build_time = elapsed_time
        time_str = self.format_time(elapsed_time)
        self.ui.last_build_stats_label.setText(f"Last Build Time: {time_str}")
        # Persist last build duration string in settings for display on next load
        try:
            set_settings_value("MapBuilder", "LastBuildTime", time_str)
        except Exception as e:
            print(f"Failed to save LastBuildTime: {e}")

        if exit_code == 0:
            QMessageBox.information(
                self, "Compilation Complete",
                f"Map compiled successfully in {time_str}\n\n"
            )
            self.add_log_message(f"✓ Compilation completed successfully ({time_str})")


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

        launch_cmd = f'"{cs2_exe}" -tools -addon {addon_name} +map_workshop {addon_name} {map_name}'

        self.add_log_message(f"Launching: {launch_cmd}")

        # Launch in separate process
        subprocess.Popen(launch_cmd, shell=True)

    def add_log_message(self, message: str):
        """Append a timestamped, styled HTML message to the output panel (no wrapping)."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Enhance message (may contain HTML spans, links, etc.)
        formatted_message = OutputFormatter.parse_output_line(message)

        # Compose line HTML with timestamp styling
        line_html = (f"<span style='color:#9aa0a6; font-size: 11px;'>[{timestamp}]</span> "
                     f"{formatted_message}<br/>")

        # Insert HTML at the end and scroll to bottom
        cursor = self.ui.output_list_widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.ui.output_list_widget.setTextCursor(cursor)
        self.ui.output_list_widget.insertHtml(line_html)
        self.ui.output_list_widget.moveCursor(QTextCursor.End)
        self.ui.output_list_widget.ensureCursorVisible()

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
