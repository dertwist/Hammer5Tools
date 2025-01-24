from PySide6.QtWidgets import QDialog, QMessageBox
import shutil, os, re
from src.settings.main import get_cs2_path, get_config_value, set_config_value
from src.create_addon.ui_create_addon_dialog import Ui_Create_addon_Dialog
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from src.common import Presets_Path
from src.common import enable_dark_title_bar

# noinspection PyTypeChecker
class Create_addon_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Create_addon_Dialog()
        self.ui.setupUi(self)
        self.ui.create_addon_button.clicked.connect(self.create_addon)
        enable_dark_title_bar(self)

        regex = QRegularExpression("[a-z0-9_]*")
        validator = QRegularExpressionValidator(regex, self.ui.lineEdit_addon_name)
        self.ui.lineEdit_addon_name.setValidator(validator)

        presets_path = Presets_Path
        if os.path.exists(presets_path) and os.path.isdir(presets_path):
            for folder_name in os.listdir(presets_path):
                folder_path = os.path.join(presets_path, folder_name)
                if os.path.isdir(folder_path):
                    self.ui.presets_comobox.addItem(folder_name)
            if not get_config_value('PRESETS', 'preset_name'):
                set_config_value('PRESETS', 'preset_name', self.ui.presets_comobox.itemText(0))
        self.ui.presets_comobox.setCurrentText(get_config_value('PRESETS', 'preset_name'))
        self.ui.presets_comobox.currentIndexChanged.connect(self.set_preset_name_on_change)

    def set_preset_name_on_change(self, index):
        set_config_value('PRESETS', 'preset_name', self.ui.presets_comobox.itemText(index))
    def create_addon(self):
        preset = get_config_value('PRESETS', 'preset_name')
        presets_path = Presets_Path
        cs2_path = get_cs2_path()
        new_addon_name = self.ui.lineEdit_addon_name.text()

        if not new_addon_name:
            QMessageBox.warning(self, "Input Error", "Please enter an addon name.")
            return

        preset_src = os.path.join(presets_path, preset, 'content')
        preset_dist = os.path.join(cs2_path, 'content', 'csgo_addons', new_addon_name)

        try:
            shutil.copytree(preset_src, preset_dist, dirs_exist_ok=True)
            self.replace_filenames(preset_dist,new_addon_name)

        except Exception as e:
            QMessageBox.critical(self, "Copy Error", f"An error occurred while copying content: {str(e)}")
            return

        preset_src = os.path.join(presets_path, preset, 'game')
        preset_dist = os.path.join(cs2_path, 'game', 'csgo_addons', new_addon_name)
        if os.path.exists(preset_src):
            try:
                shutil.copytree(preset_src, preset_dist, dirs_exist_ok=True)
                self.replace_filenames(preset_dist, new_addon_name)
            except Exception as e:
                QMessageBox.critical(self, "Copy Error", f"An error occurred while copying content: {str(e)}")
                return
        QMessageBox.information(self, "Info", f"Addon {str(new_addon_name)} was created")
        self.close()

    def replace_filenames(self, directory, new_addon_name):
        pattern = re.compile(r'xxx_mapname_xxx')
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if pattern.search(filename):
                    new_filename = pattern.sub(new_addon_name, filename)
                    os.rename(os.path.join(root, filename), os.path.join(root, new_filename))

