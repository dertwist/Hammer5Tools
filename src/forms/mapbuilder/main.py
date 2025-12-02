"""
Enhanced Map Builder Dialog with complete preset management,
real-time output parsing, and dynamic UI generation.
"""
import sys
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QApplication, QMessageBox, QInputDialog,
    QListWidgetItem, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QColor, QIcon

# Import UI and custom modules
from src.forms.mapbuilder.ui_main import Ui_mapbuilder_dialog
from src.forms.mapbuilder.system_monitor import SystemMonitor
from src.forms.mapbuilder.preset_manager import PresetManager, BuildPreset, BuildSettings
from src.forms.mapbuilder.output_parser import OutputParser, CompilationPhase, CompilationMessage
from src.forms.mapbuilder.widgets import SettingsPanel, PresetButton
from src.settings.main import get_addon_name, get_settings_value, get_addon_dir, get_cs2_path
from src.common import enable_dark_title_bar


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
        self.parser = OutputParser()
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

                    # Parse line
                    message, progress = self.parser.parse_line(line)

                    if message:
                        self.messageReceived.emit(message)

                    if progress:
                        self.progressUpdated.emit(progress)

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

        # Initialize managers
        presets_file = Path(self.addon_path) / ".hammer5tools" / "build_presets.json"
        self.preset_manager = PresetManager(presets_file)

        # Current state
        self.current_preset: BuildPreset = None
        self.compilation_thread: CompilationThread = None
        self.is_compiling = False
        self.last_build_time = 0.0

        # Setup UI
        self.setup_settings_panel()
        self.setup_preset_buttons()
        self.setup_system_monitor()
        self.setup_connections()

        # Load first preset
        presets = self.preset_manager.get_all_presets()
        if presets:
            self.load_preset(presets[0])

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
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, p=preset: self.show_preset_context_menu(pos, p)
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

    def show_preset_context_menu(self, pos, preset: BuildPreset):
        """Show context menu for preset button"""
        menu = QMenu(self)

        # Save changes
        save_action = menu.addAction("Save Changes")
        save_action.triggered.connect(lambda: self.save_preset_changes(preset))

        if not preset.is_default:
            # Rename
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self.rename_preset(preset))

            # Delete
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self.delete_preset(preset))

        menu.exec_(self.sender().mapToGlobal(pos))

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

        # Validate mappath
        if not settings.mappath or not Path(settings.mappath).exists():
            QMessageBox.warning(self, "Invalid Map", "Please select a valid map file")
            return

        # Generate command
        command = settings.to_command_line(self.addon_path, self.cs2_path)

        # Clear outputs
        self.ui.report_widget.clear()
        self.ui.output_list_widget.clear()

        # Reset progress bars
        self.ui.current_state_progressbar.setValue(0)
        self.ui.global_state_progressbar.setValue(0)

        # Create compilation thread
        self.compilation_thread = CompilationThread(command, self.addon_path)
        self.compilation_thread.outputReceived.connect(self.on_output_received)
        self.compilation_thread.progressUpdated.connect(self.on_progress_updated)
        self.compilation_thread.messageReceived.connect(self.on_message_received)
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
        # Add to logs tab
        self.add_log_message(line)

    def on_progress_updated(self, progress):
        """Handle progress update"""
        # Update progress bars
        phase_pct = int(progress.phase_progress * 100)
        global_pct = int(progress.global_progress * 100)

        self.ui.current_state_progressbar.setValue(phase_pct)
        self.ui.global_state_progressbar.setValue(global_pct)

        # Update labels
        self.ui.current_state_label.setText(
            f"{progress.current_phase_name}: {progress.current_operation[:30]}"
        )

        # Estimate remaining time
        if self.compilation_thread and self.compilation_thread.start_time:
            elapsed = time.time() - self.compilation_thread.start_time
            if progress.global_progress > 0.01:
                estimated_total = elapsed / progress.global_progress
                remaining = estimated_total - elapsed

                elapsed_str = self.format_time(elapsed)
                remaining_str = self.format_time(remaining)

                self.ui.global_state_label.setText(
                    f"Global Progress ({elapsed_str} elapsed, ~{remaining_str} remaining)"
                )

    def on_message_received(self, message: CompilationMessage):
        """Handle warning/error message"""
        item = QListWidgetItem(message.message)

        if message.severity == "error":
            item.setForeground(QColor(255, 100, 100))
            item.setIcon(QIcon(":/icons/error_24dp_FF6464_FILL0_wght400_GRAD0_opsz24.svg"))
        elif message.severity == "warning":
            item.setForeground(QColor(255, 200, 100))
            item.setIcon(QIcon(":/icons/warning_24dp_FFC864_FILL0_wght400_GRAD0_opsz24.svg"))
        else:
            item.setForeground(QColor(200, 200, 200))

        self.ui.report_widget.addItem(item)

    def on_compilation_finished(self, exit_code: int, elapsed_time: float):
        """Handle compilation finished"""
        self.is_compiling = False
        self.ui.build_button.setEnabled(True)
        self.ui.abort_button.setEnabled(False)

        # Update last build time
        self.last_build_time = elapsed_time
        time_str = self.format_time(elapsed_time)
        self.ui.last_build_stats_label.setText(f"Last Build Time: {time_str}")

        # Show result
        if exit_code == 0:
            QMessageBox.information(
                self, "Compilation Complete",
                f"Map compiled successfully in {time_str}"
            )
            self.add_log_message(f"✓ Compilation completed successfully ({time_str})")
        else:
            QMessageBox.warning(
                self, "Compilation Failed",
                f"Compilation failed with exit code {exit_code}"
            )
            self.add_log_message(f"✗ Compilation failed with exit code {exit_code}")

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

        launch_cmd = f'"{cs2_exe}" -tools -addon {addon_name} +map {map_name}'

        self.add_log_message(f"Launching: {launch_cmd}")

        # Launch in separate process
        subprocess.Popen(launch_cmd, shell=True)

    def add_log_message(self, message: str):
        """Add message to logs tab"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.output_list_widget.addItem(f"[{timestamp}] {message}")
        self.ui.output_list_widget.scrollToBottom()

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
