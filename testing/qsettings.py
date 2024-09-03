


# settings_manager.py
from PySide6.QtCore import QSettings

class SettingsManager:
    def __init__(self, filename='settings.cfg'):
        self.settings = QSettings(filename, QSettings.IniFormat)

    def set_setting(self, name, value, data):
        self.settings.setValue(name, {'value': value, 'data': data})

    def get_setting(self, name):
        setting = self.settings.value(name, {'value': '', 'data': ''})
        return setting['value'], setting['data']

    def get_all_settings(self):
        settings = {}
        for key in self.settings.allKeys():
            settings[key] = self.get_setting(key)
        return settings




# main.py
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem)

class SettingsEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Settings Editor')
        self.setGeometry(100, 100, 400, 300)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.settings_list = QListWidget()
        self.layout.addWidget(self.settings_list)

        self.name_label = QLabel('Name:')
        self.name_edit = QLineEdit()
        self.value_label = QLabel('Value:')
        self.value_edit = QLineEdit()
        self.data_label = QLabel('Data:')
        self.data_edit = QLineEdit()

        self.form_layout = QHBoxLayout()
        self.form_layout.addWidget(self.name_label)
        self.form_layout.addWidget(self.name_edit)
        self.form_layout.addWidget(self.value_label)
        self.form_layout.addWidget(self.value_edit)
        self.form_layout.addWidget(self.data_label)
        self.form_layout.addWidget(self.data_edit)

        self.layout.addLayout(self.form_layout)

        self.add_button = QPushButton('Add/Update Setting')
        self.add_button.clicked.connect(self.add_update_setting)
        self.layout.addWidget(self.add_button)

        self.load_settings()

    def load_settings(self):
        self.settings_list.clear()
        settings = self.settings_manager.get_all_settings()
        for name, (value, data) in settings.items():
            item = QListWidgetItem(f'{name}: {value}, {data}')
            self.settings_list.addItem(item)

    def add_update_setting(self):
        name = self.name_edit.text()
        value = self.value_edit.text()
        data = self.data_edit.text()
        self.settings_manager.set_setting(name, value, data)
        self.load_settings()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = SettingsEditor()
    editor.show()
    sys.exit(app.exec())