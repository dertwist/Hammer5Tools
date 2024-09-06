from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMainWindow, QCheckBox, QVBoxLayout, QWidget, QLineEdit

class SettingsExample(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "DerTwist\\Hammer5Tools", "Te")
        # self.settings.setPath(QSettings.IniFormat, QSettings.UserScope, "settings.cfg")
        # (QString("configs/config.ini"), QSettings::IniFormat);

        self.checkbox = QCheckBox("Enable Feature")
        self.checkbox.setChecked(self.settings.value("enable_feature", False, type=bool))
        self.checkbox.stateChanged.connect(self.save_settings)

        self.editline = QLineEdit()
        self.editline.setText(self.settings.value("editline_text", "", type=str))
        self.editline.textChanged.connect(self.save_editline_settings)

        layout = QVBoxLayout()
        layout.addWidget(self.checkbox)
        layout.addWidget(self.editline)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def save_settings(self, state):
        self.settings.setValue("enable_feature", self.checkbox.isChecked())
        self.settings.sync()

    def save_editline_settings(self, text):
        self.settings.setValue("editline_text", text)
        self.settings.sync()

    def closeEvent(self, event):
        self.save_settings(self.checkbox.isChecked())
        self.save_editline_settings(self.editline.text())
        event.accept()

if __name__ == "__main__":
    app = QApplication([])

    window = SettingsExample()
    window.show()

    app.exec()