import os.path
import re
import ast

from PySide6.QtWidgets import (
    QMainWindow,
    QTreeWidgetItem,
    QFileDialog,
    QMenu,
    QWidget,
    QApplication,
    QHeaderView,
    QTreeWidget
)
from PySide6.QtGui import (
    QAction,
    QKeyEvent,
    QUndoStack,
    QKeySequence
)
from PySide6.QtCore import Qt, QTimer, Signal
from src.settings.main import get_settings_value, get_settings_bool

from keyvalues3 import kv3_to_json
from src.editors.smartprop_editor.ui_document import Ui_MainWindow
from src.settings.main import settings
from src.editors.smartprop_editor.variable_frame import VariableFrame
from src.editors.smartprop_editor.objects import (
    variables_list,
    variable_prefix,
    elements_list,
    operators_list,
    selection_criteria_list,
    filters_list
)
from src.editors.smartprop_editor.ui_variables_viewport import Ui_Form
from src.editors.smartprop_editor.vsmart import VsmartOpen, VsmartSave, serialization_hierarchy_items, deserialize_hierarchy_item
from src.editors.smartprop_editor.property_frame import PropertyFrame
from src.editors.smartprop_editor.properties_group_frame import PropertiesGroupFrame
from src.editors.smartprop_editor.choices import AddChoice, AddVariable, AddOption
from src.widgets.popup_menu.main import PopupMenu
from src.editors.smartprop_editor.commands import GroupElementsCommand
from src.forms.replace_dialog.main import FindAndReplaceDialog
from src.widgets import ErrorInfo, on_three_hierarchyitem_clicked, HierarchyItemModel
from src.widgets.element_id import ElementIDGenerator
from src.editors.smartprop_editor._common import (
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
from src.widgets.tree import HierarchyTreeWidget

class SmartPropEditorVariableViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.element_id_generator = parent.element_id_generator

        self.ui.add_new_variable_button.clicked.connect(self.add_new_variable)
        self.ui.variables_scroll_area_searchbar.textChanged.connect(self.search_variables)
        self.ui.paste_variable_button.clicked.connect(self.paste_variable)

        # Add variable classes to combobox
        for item in variables_list:
            self.ui.add_new_variable_combobox.addItem(item)


    # ======================================[Variables Actions]========================================
    def add_variable(
            self,
            name,
            var_class,
            var_value,
            var_visible_in_editor,
            var_display_name,
            index: int = None
    ):
        variable = VariableFrame(
            name=name,
            widget_list=self.ui.variables_scrollArea,
            var_value=var_value,
            var_class=var_class,
            var_visible_in_editor=var_visible_in_editor,
            var_display_name=var_display_name
        )
        variable.duplicate.connect(self.duplicate_variable)
        if index is None:
            index = (self.ui.variables_scrollArea.count()) - 1
        else:
            index = index + 1
        self.ui.variables_scrollArea.insertWidget(index, variable)

    def duplicate_variable(self, __data, __index):
        __data[2] = self.element_id_generator.update_value(__data[2], force=True)
        self.add_variable(__data[0], __data[1], __data[2], __data[3], __data[4], __index)

    def add_new_variable(self):
        name = "new_var"
        existing_variables = []
        variables_ = self.get_variables(self.ui.variables_scrollArea)
        for key, value in variables_.items():
            existing_variables.append(value[0])

        if name in existing_variables:
            suffix = 1
            while f"{name}_{suffix}" in existing_variables:
                suffix += 1
            name = f"{name}_{suffix}"

        var_class = self.ui.add_new_variable_combobox.currentText()
        var_name = name
        var_display_name = None
        var_visible_in_editor = False
        var_value = {"default": None, "min": None, "max": None, "model": None}
        var_value = self.element_id_generator.update_value(var_value, force=True)
        self.add_variable(
            name=var_name,
            var_value=var_value,
            var_visible_in_editor=var_visible_in_editor,
            var_class=var_class,
            var_display_name=var_display_name
        )

    # ======================================[Variables Other]========================================
    def search_variables(self, search_term=None):
        for i in range(self.ui.variables_scrollArea.layout().count()):
            widget = self.ui.variables_scrollArea.layout().itemAt(i).widget()
            if widget:
                if search_term.lower() in widget.name.lower():
                    widget.show()
                else:
                    widget.hide()

    def get_variables(self, layout, only_names=False):
        if only_names:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    item_ = {i: [widget.name, widget.var_class, widget.var_display_name]}
                    data_out.update(item_)
            return data_out
        else:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    item_ = {
                        i: [
                            widget.name,
                            widget.var_class,
                            widget.var_value,
                            widget.var_visible_in_editor,
                            widget.var_display_name
                        ]
                    }
                    data_out.update(item_)
            return data_out

    # ======================================[Variables Context menu]========================================
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        if self.ui.variables_QscrollArea is QApplication.focusWidget():
            paste_action = QAction("Paste Variable", self)
            paste_action.triggered.connect(self.paste_variable)
            context_menu.addAction(paste_action)

        context_menu.exec_(event.globalPos())

    def paste_variable(self):
        clipboard = QApplication.clipboard()
        try:
            m_data = kv3_to_json(clipboard.text())
            if not isinstance(m_data, dict):
                ErrorInfo(text="Clipboard data format is not valid.", details=m_data).exec()
                return

            if 'm_Variables' not in m_data:
                ErrorInfo(text="No variables found in clipboard data.").exec()
                return

            for variable in m_data['m_Variables']:
                _class = variable.get('_class', '')
                if not _class.startswith('CSmartPropVariable_'):
                    continue

                var_class = _class.replace('CSmartPropVariable_', '')
                var_name = variable.get('m_VariableName', '')
                var_visible = variable.get('m_bExposeAsParameter', False)

                var_value = {
                    'default': variable.get('m_DefaultValue'),
                    'min': variable.get('m_flParamaterMinValue'),
                    'max': variable.get('m_flParamaterMaxValue'),
                    'model': variable.get('m_sModelName')
                }

                self.element_id_generator.update_value(var_value, force=True)

                self.add_variable(
                    name=var_name,
                    var_class=var_class,
                    var_value=var_value,
                    var_visible_in_editor=var_visible,
                    var_display_name=variable.get('m_ParameterName')
                )

        except Exception as e:
            ErrorInfo(text="Failed to paste variable data.", details=str(e)).exec()