import sys
import os.path
import re
import ast

from distutils.util import strtobool

from PySide6.QtWidgets import (
    QMainWindow,
    QTreeWidgetItem,
    QFileDialog,
    QMenu,
    QApplication,
    QHeaderView,
    QTreeWidget,
    QTabBar
)
from PySide6.QtGui import (
    QAction,
    QKeyEvent,
    QUndoStack,
    QKeySequence
)
from PySide6.QtCore import Qt, QTimer
from src.settings.main import get_settings_value, get_settings_bool

from keyvalues3 import kv3_to_json
from src.smartprop_editor.ui_main import Ui_MainWindow
from src.settings.main import get_addon_name, settings
from src.smartprop_editor.variable_frame import VariableFrame
from src.smartprop_editor.objects import (
    variables_list,
    variable_prefix,
    elements_list,
    operators_list,
    selection_criteria_list,
    filters_list
)
from src.smartprop_editor.vsmart import VsmartOpen, VsmartSave, serialization_hierarchy_items, \
    deserialize_hierarchy_item
from src.smartprop_editor.property_frame import PropertyFrame
from src.smartprop_editor.properties_group_frame import PropertiesGroupFrame
from src.smartprop_editor.choices import AddChoice, AddVariable, AddOption
from src.popup_menu.main import PopupMenu
from src.smartprop_editor.commands import DeleteTreeItemCommand, GroupElementsCommand
from src.replace_dialog.main import FindAndReplaceDialog
from src.explorer.main import Explorer
from src.smartprop_editor.document import SmartPropDocument
from src.widgets import ErrorInfo, on_three_hierarchyitem_clicked, HierarchyItemModel
from src.smartprop_editor.element_id import (
    update_value_ElementID,
    update_child_ElementID_value,
    get_ElementID_key,
    reset_ElementID
)
from src.smartprop_editor._common import (
    get_clean_class_name_value,
    get_clean_class_name,
    get_label_id_from_value,
    unique_counter_name
)
from src.common import (
    enable_dark_title_bar,
    Kv3ToJson,
    JsonToKv3,
    get_cs2_path,
    SmartPropEditor_Preset_Path,
    set_qdock_tab_style
)

cs2_path = get_cs2_path()

class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, parent=None, update_title=None):
        super().__init__()
        self.parent = parent
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.realtime_save = False
        self.opened_file = None
        self.update_title = update_title
        enable_dark_title_bar(self)

        # Initialize file explorer
        self.init_explorer()

        # Initialize button signals
        self.buttons()

        set_qdock_tab_style(self.findChildren)

        self.undo_stack = QUndoStack(self)

    def open_preset_manager(self):
        """Creating another instance of this window with a different Explorer path
           for preset management."""
        self.new_instance = SmartPropEditorMainWindow(update_title=self.update_title)
        self.new_instance.mini_explorer.deleteLater()
        self.new_instance.mini_explorer.frame.deleteLater()
        tree_directory = SmartPropEditor_Preset_Path
        self.new_instance.init_explorer(tree_directory, "SmartPropEditorPresetManager")
        self.new_instance.show()

    def init_explorer(self, dir: str = None, editor_name: str = None):
        if dir is None:
            self.tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
        else:
            self.tree_directory = dir
        if editor_name is None:
            editor_name = "SmartPropEditor"

        self.mini_explorer = Explorer(
            tree_directory=self.tree_directory,
            addon=get_addon_name(),
            editor_name=editor_name,
            parent=self.ui.explorer_layout_widget
        )
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

    def buttons(self):
        self.ui.open_file_button.clicked.connect(lambda: self.open_file())
        self.ui.open_file_as_button.clicked.connect(lambda: self.open_file(external=True))
        self.ui.save_file_button.clicked.connect(lambda: self.save_file())
        self.ui.save_as_file_button.clicked.connect(lambda: self.save_file(external=True))
        self.ui.cerate_file_button.clicked.connect(self.create_new_file)
        self.ui.realtime_save_checkbox.clicked.connect(self.realtime_save_action)

    def realtime_save_action(self):
        self.realtime_save = self.ui.realtime_save_checkbox.isChecked()
        if get_settings_bool('SmartPropEditor', 'enable_transparency_window', True):
            if self.realtime_save:
                transparency = float(get_settings_value('SmartPropEditor', 'transparency_window', 70))/100
                self.parent.setWindowOpacity(transparency)
            else:
                self.parent.setWindowOpacity(1)

    def create_new_file(self):
        self.ui.DocumentTabWidget.addTab(SmartPropDocument(self), "New SmartProp")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    import qtvscodestyle as qtvsc

    stylesheet = qtvsc.load_stylesheet(qtvsc.Theme.DARK_VS)
    app.setStyleSheet(stylesheet)
    window.show()
    sys.exit(app.exec())
