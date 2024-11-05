import subprocess
import os
from pydoc import importfile


from src.preferences import get_addon_name, get_cs2_path, debug
from src.soudevent_editor.ui_main import Ui_MainWindow
from src.explorer.main import Explorer
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu, QDialog, QTreeWidget, QIntList
from src.widgets import HierarchyItemModel
from src.preferences import settings
from src.soudevent_editor.properties_window import SoundEventEditorPropertiesWindow
from src.soudevent_editor.preset_manager import SoundEventEditorPresetManagerWindow
from src.common import JsonToKv3,Kv3ToJson

class LoadSoundEvents:
    def __init__(self, tree: QTreeWidget, path: str):
        super().__init__()
        data = open(path, "r")
        data = Kv3ToJson(data.read())
        self.tree = tree
        self.tree.clear()
        self.root = self.tree.invisibleRootItem()
        print(f'FD12: {data}')
        for key in data:
            new_item = HierarchyItemModel(_data=data[key], _name=key)
            self.root.addChild(new_item)
class SoundEventEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.realtime_save = False

        # Variables
        self.filepath_vsndevts = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents','soundevents_addon.vsndevts')
        self.filepath_sounds = os.path.join(get_cs2_path(), 'content', 'csgo_addons', get_addon_name(), 'soundevents','soundevents_addon.vsndevts')

        # Variables debug
        debug(f"self.filepath_vsndevts : {self.filepath_vsndevts}")
        debug(f"self.filepath_sounds : {self.filepath_sounds}")

        # Init
        LoadSoundEvents(tree=self.ui.hierarchy_widget, path=self.filepath_vsndevts)
        self.PropertiesWindowInit()

        # Connections
        self.ui.open_preset_manager_button.clicked.connect(self.OpenPresetManager)

        # Explorer
        self.tree_directory = os.path.join(get_cs2_path(), "content", "csgo_addons", get_addon_name(), 'sounds')
        if os.path.exists(self.tree_directory):
            pass
        else:
            os.makedirs(self.tree_directory)
        self.mini_explorer = Explorer(tree_directory=self.tree_directory, addon=get_addon_name(), editor_name='SoundEvent_Editor', parent=self.ui.explorer_layout_widget)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

    #=======================================================<  Properties Window  >=====================================================

    def PropertiesWindowInit(self):
        PropertiesWindow = SoundEventEditorPropertiesWindow()
        self.ui.frame.layout().addWidget(PropertiesWindow)
    def UpdatePropertiesWindow(self):
        pass

    #================================================================<  Hierarchy  >=============================================================

    def update_hierarchy_item(self):
        pass

    #===========================================================<  Preset Manager  >========================================================
    def OpenPresetManager(self):
        self.PresetManager = SoundEventEditorPresetManagerWindow()
        self.PresetManager.show()

    #======================================[Window State]========================================
    def _restore_user_prefs(self):
        """Restore window state"""
        geo = self.settings.value("SoundEventEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SoundEventEditorMainWindow/windowState")
        if state:
            self.restoreState(state)

    def _save_user_prefs(self):
        """Save window state"""
        self.settings.setValue("SoundEventEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SoundEventEditorMainWindow/windowState", self.saveState())
    def closeEvent(self, event):
        self._save_user_prefs()