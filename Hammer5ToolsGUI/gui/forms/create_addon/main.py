from PySide6.QtWidgets import QDialog, QMessageBox
import shutil, os, re
from gui.settings.common import addon_content_dir, addon_game_dir, get_cs2_path, get_settings_value, set_settings_value
from gui.forms.create_addon.ui_main import Ui_Create_addon_Dialog
from gui.widgets import exception_handler
from PySide6.QtCore import Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from gui.common import Presets_Path, Internal_Presets_Path, enable_dark_title_bar, app_dir
from core.bridge import CoreBridge
from PySide6.QtGui import QPixmap
import binascii

# noinspection PyTypeChecker
class CreateAddonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Create_addon_Dialog()
        self.ui.setupUi(self)
        self.ui.create_addon_button.clicked.connect(self.create_addon)
        enable_dark_title_bar(self)

        self.ui.lineEdit_addon_name.textChanged.connect(self.validate_addon_name_input)
        self._invalid_input_shown = False

        # Search for presets in both user data and internal app directory
        self.presets_roots = [Presets_Path, Internal_Presets_Path, app_dir / "Presets"]
        seen_presets = set()
        
        for presets_path in self.presets_roots:
            if os.path.exists(presets_path) and os.path.isdir(presets_path):
                for folder_name in os.listdir(presets_path):
                    if folder_name in seen_presets:
                        continue
                    folder_path = os.path.join(presets_path, folder_name)
                    if os.path.isdir(folder_path):
                        self.ui.presets_comobox.addItem(folder_name)
                        seen_presets.add(folder_name)
                        
        if self.ui.presets_comobox.count() > 0:
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
        if not preset:
            return

        vmap_path = None
        for root in self.presets_roots:
            path = os.path.join(root, preset, 'content', 'maps', 'xxx_mapname_xxx.vmap')
            if os.path.exists(path):
                vmap_path = path
                break
        
        if not vmap_path:
            return


        map_document = CoreBridge.instance().read_valve_map(vmap_path)
        thumbnail_hex = None if map_document.thumbnail is None else map_document.thumbnail.hex().upper()
        fxt = map_document.thumbnail_format
        
        if thumbnail_hex is None:
            return


        try:
            image_bytes = binascii.unhexlify(thumbnail_hex)
        except Exception as e:
            return

        pixmap = QPixmap()
        success = pixmap.loadFromData(image_bytes)
        if success:
            label_size = self.ui.label.size()
            scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.ui.label.setPixmap(scaled_pixmap)
        else:
            pass

    @exception_handler
    def set_preset_name_on_change(self, index):
        set_settings_value('PRESETS', 'preset_name', self.ui.presets_comobox.itemText(index))
        self.update_thumbnail()

    @exception_handler
    def create_addon(self):
        preset = get_settings_value('PRESETS', 'preset_name')
        if not preset:
            QMessageBox.warning(self, "Selection Error", "Please select a preset.")
            return

        cs2_path = get_cs2_path()
        if not cs2_path:
            QMessageBox.warning(self, "CS2 Path Not Set", "CS2 installation path is not set. Please set it in Settings.")
            return
        new_addon_name = self.ui.lineEdit_addon_name.text()

        if not new_addon_name:
            QMessageBox.warning(self, "Input Error", "Please enter an addon name.")
            return

        if self._invalid_input_shown:
            QMessageBox.warning(self, "Input Error", "Please enter a valid addon name (lowercase letters, numbers, underscores).")
            return

        # Find the preset source path
        preset_root = None
        for root in self.presets_roots:
            if os.path.exists(os.path.join(root, preset)):
                preset_root = root
                break
        
        if not preset_root:
            QMessageBox.critical(self, "Error", f"Could not find source for preset: {preset}")
            return

        preset_src = os.path.join(preset_root, preset, 'content')
        preset_dist = str(addon_content_dir(new_addon_name))

        try:
            shutil.copytree(preset_src, preset_dist, dirs_exist_ok=True)
            self.replace_filenames(preset_dist,new_addon_name)

        except Exception as e:
            QMessageBox.critical(self, "Copy Error", f"An error occurred while copying content: {str(e)}")
            return

        preset_src = os.path.join(preset_root, preset, 'game')
        preset_dist = str(addon_game_dir(new_addon_name))
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

