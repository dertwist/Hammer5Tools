import sys, os
from src.preferences import get_addon_name, get_cs2_path
from src.soundevent_editor.ui_preset_manager import Ui_MainWindow
from src.explorer.main import Explorer
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu, QApplication
from src.preferences import settings
from src.soundevent_editor.properties_window import SoundEventEditorPropertiesWindow
from src.common import app_dir, Kv3ToJson, JsonToKv3, SoundEventEditor_Preset_Path
from src.widgets import ExpetionErrorDialog, ErrorInfo


class SoundEventEditorPresetManagerWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.opened_file = ""

        self.PropertiesWindow = SoundEventEditorPropertiesWindow()
        self.ui.frame.layout().addWidget(self.PropertiesWindow)

        # Connections
        self.ui.open_folder_button.clicked.connect(self.open_folder)
        self.ui.new_button.clicked.connect(self.create_new_preset)
        self.ui.open_button.clicked.connect(self.open_preset)
        self.ui.save_button.clicked.connect(self.save_preset)

    #==============================================================<  Explorer  >===========================================================
        self.tree_directory = SoundEventEditor_Preset_Path
        if os.path.exists(self.tree_directory):
            pass
        else:
            def make_dir():
                os.makedirs(self.tree_directory)
            ExpetionErrorDialog(make_dir)
        if self.tree_directory == '':
            ErrorInfo('Could not create presets directory')
        self.mini_explorer = Explorer(tree_directory=self.tree_directory, addon=get_addon_name(), editor_name='SoundEvent_Editor_PresetManager', parent=self.ui.explorer_layout_widget)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

    #=======================================================<  Preset Manager Actions  >====================================================
    def explorer_status(self):
        """Displays current opened preset"""
        __filepath = self.opened_file
        if __filepath == '':
            self.ui.ExplorerDockWidget.setWindowTitle('Preset Explorer')
        else:
            __filename = os.path.basename(__filepath)
            self.ui.ExplorerDockWidget.setWindowTitle(f'Preset Explorer ({__filename})')
    def create_new_preset(self):
        """Create a blank preset."""
        # Convert an empty dictionary to KV3 format
        data = JsonToKv3({})

        # Define a base name for the new preset
        new_name = "SE_Preset"
        unique_digit = 1

        # Generate a unique file name by checking existing files
        while True:
            filepath = os.path.join(self.tree_directory, f"{new_name}_{unique_digit}.kv3")
            if not os.path.exists(filepath):
                break
            unique_digit += 1

        # Write the data to the new file
        with open(filepath, 'w') as file:
            file.write(data)

    def open_folder(self):
        """Opening preset folder path"""
        os.startfile(self.tree_directory)
    def open_preset(self):
        """Loads a preset into the Window Properties"""
        index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
        __filepath = self.mini_explorer.tree.model().filePath(index)

        with open(__filepath, 'r') as file:
            __data = file.read()
        __data = Kv3ToJson(__data)

        self.PropertiesWindow.properties_clear()
        self.PropertiesWindow.properties_groups_show()
        self.PropertiesWindow.populate_properties(__data)

        self.opened_file = __filepath
        print(f'Opened file: {__filepath}')
        self.explorer_status()
    def save_preset(self):
        """Saving preset"""
        __filepath = self.opened_file
        self.PropertiesWindow.on_update()
        __data = self.PropertiesWindow.value
        __data = JsonToKv3(__data)
        with open(__filepath, 'w') as file:
            file.write(__data)
        print(f'Saved file: {__filepath}')
    #=======================================================<  Properties Window  >=====================================================

    #======================================[Window State]========================================
    def _restore_user_prefs(self):
        """Restore window state"""
        geo = self.settings.value("SoundEventEditorPresetManagerWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SoundEventEditorPresetManagerWindow/windowState")
        if state:
            self.restoreState(state)

    def _save_user_prefs(self):
        """Save window state"""
        self.settings.setValue("SoundEventEditorPresetManagerWindow/geometry", self.saveGeometry())
        self.settings.setValue("SoundEventEditorPresetManagerWindow/windowState", self.saveState())
    def closeEvent(self, event):
        self._save_user_prefs()
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = SoundEventEditorPresetManagerWindow()
    main_window.show()
    sys.exit(app.exec())
