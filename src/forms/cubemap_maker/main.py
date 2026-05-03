import sys
import os
import re
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, 
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QFormLayout,
    QDialog, QProgressBar
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

        # Info Label
        info_label = QLabel("The tool makes cubemaps from ingame screenshots. Please load your map into the game.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaa; font-style: italic; margin-bottom: 5px;")
        layout.addWidget(info_label)

        # Settings Group
        group = QGroupBox("Capture Settings")
        group_layout = QVBoxLayout(group)
        
        # Row 1: HDR and Mode
        row1 = QHBoxLayout()
        self.hdr_check = QCheckBox("Enable HDR (EV Steps)")
        row1.addWidget(self.hdr_check)
        row1.addStretch()
        row1.addWidget(QLabel("Mode / Layout:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["CrossHLayout", "Equirectangular"])
        row1.addWidget(self.mode_combo)
        group_layout.addLayout(row1)
        
        # Row 2: Resolutions
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Game Resolution:"))
        self.game_res_edit = QLineEdit(get_settings_value('CUBEMAP', 'game_res', "1920x1080"))
        row2.addWidget(self.game_res_edit)
        
        row2.addWidget(QLabel("Max Face Resolution:"))
        self.face_res_spin = QSpinBox()
        self.face_res_spin.setRange(256, 4096)
        self.face_res_spin.setSingleStep(256)
        self.face_res_spin.setValue(int(get_settings_value('CUBEMAP', 'face_res', "1024")))
        row2.addWidget(self.face_res_spin)
        group_layout.addLayout(row2)
        
        layout.addWidget(group)

        # Position Group
        # Position Layout
        pos_layout = QHBoxLayout()
        
        self.pos_x = QDoubleSpinBox()
        self.pos_x.setRange(-1000000, 1000000); self.pos_x.setDecimals(4)
        pos_layout.addWidget(QLabel("X:")); pos_layout.addWidget(self.pos_x)
        
        self.pos_y = QDoubleSpinBox()
        self.pos_y.setRange(-1000000, 1000000); self.pos_y.setDecimals(4)
        pos_layout.addWidget(QLabel("Y:")); pos_layout.addWidget(self.pos_y)
        
        self.pos_z = QDoubleSpinBox()
        self.pos_z.setRange(-1000000, 1000000); self.pos_z.setDecimals(4)
        pos_layout.addWidget(QLabel("Z:")); pos_layout.addWidget(self.pos_z)
        
        paste_btn = QPushButton("Paste from Clipboard")
        paste_btn.clicked.connect(self.paste_position)
        pos_layout.addWidget(paste_btn)
        
        layout.addLayout(pos_layout)

        # Output Group
        out_group = QGroupBox("Output")
        out_h = QHBoxLayout(out_group)
        
        addon_dir = get_addon_dir()
        if addon_dir:
            default_out = os.path.join(addon_dir, "materials", "lighting", "cubemaps")
        else:
            default_out = "materials/lighting/cubemaps"
            
        self.out_edit = QLineEdit(default_out)
        out_h.addWidget(self.out_edit)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self.browse_folder)
        out_h.addWidget(browse_btn)
        layout.addWidget(out_group)

        # Actions
        self.capture_btn = QPushButton("Capture Cubemap")
        self.capture_btn.setFixedHeight(40)
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

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
        
        config = {
            'hdr': self.hdr_check.isChecked(),
            'res': self.face_res_spin.value(),
            'mode': self.mode_combo.currentText(),
            'pos': [self.pos_x.value(), self.pos_y.value(), self.pos_z.value()],
            'out': self.out_edit.text()
        }
        
        self.capture_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Starting capture sequence...")
        
        self.worker = CaptureWorker(config)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_error(self, msg):
        self.capture_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Capture Error", msg)
        self.status_label.setText("Error occurred.")

    def on_finished(self, msg):
        self.capture_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Ready")
        QMessageBox.information(self, "Success", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = CubemapMakerDialog()
    dlg.show()
    sys.exit(app.exec())
