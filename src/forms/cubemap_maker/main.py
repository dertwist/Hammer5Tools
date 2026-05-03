import sys
import os
import re
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, 
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QFormLayout,
    QDialog, QProgressBar, QWidget, QGridLayout
)
from PySide6.QtCore import Qt

from src.styles.common import apply_stylesheets
from src.settings.main import get_addon_name, get_addon_dir, get_settings_value, set_settings_value
from src.widgets import enable_dark_title_bar

from .worker import CaptureWorker

class CubemapMakerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CS2 Cubemap Maker")
        self.setMinimumWidth(500)
        enable_dark_title_bar(self)
        
        self.init_ui()
        apply_stylesheets(self)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Info Label
        info_label = QLabel("To capture cubemap, load map in game.")
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info_label)

        # Capture Configuration
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(10)
        
        # HDR
        self.hdr_check = QCheckBox("Enable HDR (Multi-EV)")
        config_layout.addWidget(self.hdr_check)
        
        # Mode
        config_layout.addWidget(QLabel("Layout Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["CrossHLayout", "Equirectangular", "Individual Faces"])
        config_layout.addWidget(self.mode_combo)
        
        # Game Resolution
        config_layout.addWidget(QLabel("Game Resolution (e.g. 1920x1080):"))
        self.game_res_edit = QLineEdit(get_settings_value('CUBEMAP', 'game_res', "1920x1080"))
        config_layout.addWidget(self.game_res_edit)
        
        # Face Resolution
        config_layout.addWidget(QLabel("Max Face Resolution:"))
        self.face_res_spin = QSpinBox()
        self.face_res_spin.setRange(256, 4096)
        self.face_res_spin.setSingleStep(256)
        self.face_res_spin.setValue(int(get_settings_value('CUBEMAP', 'face_res', "1024")))
        config_layout.addWidget(self.face_res_spin)

        # Position Row (Vertical inside)
        config_layout.addWidget(QLabel("Position (X Y Z):"))
        pos_h = QHBoxLayout()
        self.pos_x = QDoubleSpinBox(); self.pos_x.setRange(-1e6, 1e6); self.pos_x.setDecimals(2); self.pos_x.setButtonSymbols(QSpinBox.NoButtons)
        self.pos_y = QDoubleSpinBox(); self.pos_y.setRange(-1e6, 1e6); self.pos_y.setDecimals(2); self.pos_y.setButtonSymbols(QSpinBox.NoButtons)
        self.pos_z = QDoubleSpinBox(); self.pos_z.setRange(-1e6, 1e6); self.pos_z.setDecimals(2); self.pos_z.setButtonSymbols(QSpinBox.NoButtons)
        
        # Load last position
        self.pos_x.setValue(float(get_settings_value('CUBEMAP', 'last_pos_x', "0")))
        self.pos_y.setValue(float(get_settings_value('CUBEMAP', 'last_pos_y', "0")))
        self.pos_z.setValue(float(get_settings_value('CUBEMAP', 'last_pos_z', "0")))
        
        pos_h.addWidget(self.pos_x); pos_h.addWidget(self.pos_y); pos_h.addWidget(self.pos_z)
        
        paste_btn = QPushButton("Paste")
        paste_btn.setFixedWidth(60)
        paste_btn.clicked.connect(self.paste_position)
        pos_h.addWidget(paste_btn)
        config_layout.addLayout(pos_h)
        
        layout.addWidget(config_group)

        # Output Path
        layout.addWidget(QLabel("Output Path (Relative to Addon):"))
        out_h = QHBoxLayout()
        
        addon_dir = get_addon_dir()
        if addon_dir:
            default_out = os.path.join(addon_dir, "materials", "lighting", "cubemaps")
            display_path = os.path.relpath(default_out, addon_dir)
        else:
            default_out = "materials/lighting/cubemaps"
            display_path = default_out
            
        self.out_edit = QLineEdit(display_path)
        self.out_edit.setToolTip(default_out)
        out_h.addWidget(self.out_edit)
        
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self.browse_folder)
        out_h.addWidget(browse_btn)
        layout.addLayout(out_h)

        # Actions
        self.capture_btn = QPushButton("CAPTURE CUBEMAP")
        self.capture_btn.setFixedHeight(40)
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5a27;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3d7a35; }
        """)
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)
        
        # Progress Bar (Map Builder Style)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Idle")
        self.progress_bar.setFixedHeight(18)
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
        layout.addWidget(self.progress_bar)

    def paste_position(self):
        clipboard = QApplication.clipboard().text()
        # Try to find "origin" = "X Y Z"
        match = re.search(r'origin\s*=\s*"([^"]+)"', clipboard)
        if match:
            pos_str = match.group(1).split()
        else:
            # Try raw space-separated numbers
            pos_str = clipboard.strip().split()
            
        if len(pos_str) >= 3:
            try:
                self.pos_x.setValue(float(pos_str[0]))
                self.pos_y.setValue(float(pos_str[1]))
                self.pos_z.setValue(float(pos_str[2]))
            except ValueError:
                pass

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if path:
            self.out_edit.setText(path)

    def save_settings(self):
        set_settings_value('CUBEMAP', 'game_res', self.game_res_edit.text())
        set_settings_value('CUBEMAP', 'face_res', str(self.face_res_spin.value()))

    def start_capture(self):
        self.save_settings()
        
        # Resolve output path (could be relative or absolute)
        out_path = self.out_edit.text()
        if not os.path.isabs(out_path):
            addon_dir = get_addon_dir()
            if addon_dir:
                out_path = os.path.join(addon_dir, out_path)
        
        set_settings_value('CUBEMAP', 'last_pos_x', str(self.pos_x.value()))
        set_settings_value('CUBEMAP', 'last_pos_y', str(self.pos_y.value()))
        set_settings_value('CUBEMAP', 'last_pos_z', str(self.pos_z.value()))
        
        config = {
            'hdr': self.hdr_check.isChecked(),
            'game_res': self.game_res_edit.text(),
            'res': self.face_res_spin.value(),
            'mode': self.mode_combo.currentText(),
            'pos': (self.pos_x.value(), self.pos_y.value(), self.pos_z.value()),
            'out': out_path
        }
        
        self.capture_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("Starting...")
        
        self.worker = CaptureWorker(config)
        self.worker.progress.connect(self.progress_bar.setFormat)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_error(self, msg):
        self.capture_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFormat("Error")
        QMessageBox.critical(self, "Capture Error", msg)

    def on_finished(self, msg):
        self.capture_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Finished")
        QMessageBox.information(self, "Success", msg)
        self.progress_bar.setFormat("Idle")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = CubemapMakerDialog()
    dlg.show()
    sys.exit(app.exec())
