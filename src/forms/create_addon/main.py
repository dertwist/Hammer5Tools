from PySide6.QtWidgets import QDialog, QMessageBox
import shutil, os, re
from src.settings.main import get_cs2_path, get_settings_value, set_settings_value, debug
from src.forms.create_addon.ui_main import Ui_Create_addon_Dialog
from src.widgets import exception_handler
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from src.common import Presets_Path
from src.common import enable_dark_title_bar
from src.dotnet import extract_vmap_thumbnail
from PySide6.QtGui import QPixmap
import binascii

# noinspection PyTypeChecker
class Create_addon_Dialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Create_addon_Dialog()
        self.ui.setupUi(self)
        self.ui.create_addon_button.clicked.connect(self.create_addon)
        enable_dark_title_bar(self)

        self.ui.lineEdit_addon_name.textChanged.connect(self.validate_addon_name_input)
        self._invalid_input_shown = False

        presets_path = Presets_Path
        if os.path.exists(presets_path) and os.path.isdir(presets_path):
            for folder_name in os.listdir(presets_path):
                folder_path = os.path.join(presets_path, folder_name)
                if os.path.isdir(folder_path):
                    self.ui.presets_comobox.addItem(folder_name)
            if not get_settings_value('PRESETS', 'preset_name'):
                set_settings_value('PRESETS', 'preset_name', self.ui.presets_comobox.itemText(0))
        self.ui.presets_comobox.setCurrentText(get_settings_value('PRESETS', 'preset_name'))
        self.ui.presets_comobox.currentIndexChanged.connect(self.set_preset_name_on_change)

        self.update_thumbnail()

    @exception_handler
    def validate_addon_name_input(self, text):
        # Valid pattern: lowercase letters, digits, underscore
        if re.fullmatch(r"[a-z0-9_]*", text):
            self._invalid_input_shown = False  # Reset flag when valid
        else:
            if not self._invalid_input_shown:
                QMessageBox.warning(self, "Invalid Characters",
                                    "Only lowercase letters, numbers, and underscores are allowed.")
                self._invalid_input_shown = True
    @exception_handler
    def update_thumbnail(self):
        preset = get_settings_value('PRESETS', 'preset_name')
        vmap_path = os.path.join(Presets_Path, preset, 'content', 'maps', 'xxx_mapname_xxx.vmap')
        debug(f'Extracting thumbnail from {vmap_path}')

        thumbnail_hex, fxt = extract_vmap_thumbnail(vmap_path)
        debug(f'Thumbnail extracted: {fxt}, size: {len(thumbnail_hex)} bytes')

        # Convert hex to raw image bytes
        image_bytes = binascii.unhexlify(thumbnail_hex)

        # Load image into QPixmap
        pixmap = QPixmap()
        success = pixmap.loadFromData(image_bytes)
        if success:
            self.ui.label.setPixmap(pixmap)
        else:
            debug("QPixmap failed to load image from data.")

    @exception_handler
    def set_preset_name_on_change(self, index):
        set_settings_value('PRESETS', 'preset_name', self.ui.presets_comobox.itemText(index))
        self.update_thumbnail()

    @exception_handler
    def create_addon(self):
        preset = get_settings_value('PRESETS', 'preset_name')
        presets_path = Presets_Path
        cs2_path = get_cs2_path()
        new_addon_name = self.ui.lineEdit_addon_name.text()

        if not new_addon_name:
            QMessageBox.warning(self, "Input Error", "Please enter an addon name.")
            return

        if self._invalid_input_shown:
            QMessageBox.warning(self, "Input Error", "Please enter a valid addon name (lowercase letters, numbers, underscores).")
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

    @exception_handler
    def replace_filenames(self, directory, new_addon_name):
        pattern = re.compile(r'xxx_mapname_xxx')
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if pattern.search(filename):
                    new_filename = pattern.sub(new_addon_name, filename)
                    os.rename(os.path.join(root, filename), os.path.join(root, new_filename))

