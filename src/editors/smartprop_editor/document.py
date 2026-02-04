import os.path
import re
import ast

from PySide6.QtWidgets import (
    QMainWindow,
    QTreeWidgetItem,
    QFileDialog,
    QMenu,
    QApplication,
    QHeaderView,
    QTreeWidget,
    QSpinBox,
    QHBoxLayout,
    QLabel,
    QWidget
)
from PySide6.QtGui import (
    QAction,
    QKeyEvent,
    QUndoStack,
    QKeySequence
)
import uuid
import traceback, ctypes
from PySide6.QtCore import Qt, QTimer, Signal

from src.settings.common import get_addon_dir
from src.settings.main import get_settings_value, get_settings_bool

from keyvalues3 import kv3_to_json
from src.editors.smartprop_editor.ui_document import Ui_MainWindow
from src.settings.main import settings
from src.editors.smartprop_editor.objects import (
    variables_list,
    variable_prefix,
    elements_list,
    operators_list,
    selection_criteria_list,
    filters_list
)
from src.editors.smartprop_editor.vsmart import VsmartOpen, VsmartSave, serialization_hierarchy_items, deserialize_hierarchy_item
from src.editors.smartprop_editor.property_frame import PropertyFrame
from src.editors.smartprop_editor.properties_group_frame import PropertiesGroupFrame
from src.editors.smartprop_editor.choices import AddChoice, AddVariable, AddOption
from src.widgets.popup_menu.main import PopupMenu
from src.editors.smartprop_editor.commands import GroupElementsCommand, BulkModelImportCommand, NewFromPresetCommand, PasteItemsCommand
from src.forms.replace_dialog.main import FindAndReplaceDialog
from src.widgets import ErrorInfo, on_three_hierarchyitem_clicked, HierarchyItemModel, error, exception_handler
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
from src.editors.smartprop_editor.variables_viewport import SmartPropEditorVariableViewport

cs2_path = get_cs2_path()

#TODO Future improvement: Implement a node view for elements.
# In the node view, users will click on a node to edit its properties, triggering a context menu similar to that found in the Hammer editor (using, for example, Alt+Enter) or just show and hide properties in the viewport.
# The node view should be arranged vertically. All node-related information will be stored within the elements themselves.
# Nodes that are not connected via the Child input (i.e. isolated nodes) will be automatically attached as children of the root.

class SmartPropDocument(QMainWindow):
    _edited = Signal()
    def __init__(self, parent=None, update_title=None):
        super().__init__()
        self.parent = parent
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.element_id_generator = ElementIDGenerator()
        self.opened_file = None
        self.update_title = update_title
        enable_dark_title_bar(self)

        self.undo_stack = QUndoStack(self)

        #Viewports
        self.variable_viewport = SmartPropEditorVariableViewport(self)
        self.ui.VariableDockWidgetContent.layout().addWidget(self.variable_viewport)

        # Track changes
        self._modified = False
        
        
        # Hierarchy tree wdiget setup
        self.ui.tree_hierarchy_widget.deleteLater()
        self.ui.tree_hierarchy_widget = HierarchyTreeWidget(self.undo_stack)
        self.ui.frame_2.layout().addWidget(self.ui.tree_hierarchy_widget)
        
        self.ui.tree_hierarchy_widget.setColumnCount(4)
        self.ui.tree_hierarchy_widget.setHeaderLabels(["Label", "Data", "Class", "ID"])

        self.ui.tree_hierarchy_widget.installEventFilter(self)

        self.ui.tree_hierarchy_widget.hideColumn(1)
        self.ui.tree_hierarchy_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tree_hierarchy_widget.customContextMenuRequested.connect(self.open_hierarchy_menu)
        self.ui.tree_hierarchy_widget.currentItemChanged.connect(self.on_tree_current_item_changed)
        self.ui.tree_hierarchy_widget.itemClicked.connect(on_three_hierarchyitem_clicked)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.ui.tree_hierarchy_widget.setDragEnabled(True)
        self.ui.tree_hierarchy_widget.setAcceptDrops(True)
        self.ui.tree_hierarchy_widget.setDropIndicatorShown(True)
        self.ui.tree_hierarchy_widget.setDragDropMode(QTreeWidget.InternalMove)

        # Content version
        self.content_version_spinbox = QSpinBox()
        self.content_version_label = QLabel("Content Version")
        self.content_version_layout = QHBoxLayout()
        self.content_version_layout.setContentsMargins(0,0,0,0)
        self.content_version_layout.addWidget(self.content_version_label)
        self.content_version_layout.addWidget(self.content_version_spinbox)
        content_version_widget = QWidget()
        content_version_widget.setContentsMargins(0,0,0,0)
        content_version_widget.setLayout(self.content_version_layout)
        self.ui.frame_2.layout().addWidget(content_version_widget)

        # Choices setup
        self.ui.choices_tree_widget.hideColumn(2)
        self.ui.choices_tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.choices_tree_widget.customContextMenuRequested.connect(self.open_MenuChoices)

        # Groups setup
        self.properties_groups_init()

        self.ui.tree_hierarchy_search_bar_widget.textChanged.connect(
            lambda text: self.search_hierarchy(text, self.ui.tree_hierarchy_widget.invisibleRootItem())
        )

        self._restore_user_prefs()

        # Group dockwidgets
        self.addDockWidget(Qt.RightDockWidgetArea, self.ui.VariablesDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ui.HierarchyDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ui.ChoicesDock)
        self.splitDockWidget(self.ui.VariablesDock, self.ui.HierarchyDock, Qt.Vertical)
        self.tabifyDockWidget(self.ui.HierarchyDock, self.ui.ChoicesDock)
        self.ui.HierarchyDock.raise_()

        set_qdock_tab_style(self.findChildren)

    def is_modified(self):
        return self._modified

    # ======================================[Properties groups]========================================
    def properties_groups_init(self):
        self.modifiers_group_instance = PropertiesGroupFrame(
            widget_list=self.ui.properties_layout,
            name=str("Modifiers")
        )
        self.ui.properties_layout.insertWidget(0, self.modifiers_group_instance)
        self.modifiers_group_instance.add_signal.connect(self.add_an_operator)
        self.modifiers_group_instance.paste_signal.connect(self.paste_operator)

        self.selection_criteria_group_instance = PropertiesGroupFrame(
            widget_list=self.ui.properties_layout,
            name=str("Section criteria")
        )
        self.selection_criteria_group_instance.add_signal.connect(self.add_a_selection_criteria)
        self.ui.properties_layout.insertWidget(1, self.selection_criteria_group_instance)
        self.selection_criteria_group_instance.paste_signal.connect(self.paste_selection_criteria)

        self.properties_groups_hide()

    def properties_groups_hide(self):
        self.ui.properties_spacer.hide()
        self.ui.properties_placeholder.show()
        self.modifiers_group_instance.hide()
        self.selection_criteria_group_instance.hide()

    def properties_groups_show(self):
        self.ui.properties_placeholder.hide()
        self.ui.properties_spacer.show()
        self.modifiers_group_instance.show()
        self.selection_criteria_group_instance.show()

    # ======================================[Tree Hierarchy updating]========================================
    def on_tree_current_item_changed(self, current_item, previous_item):
        # Use the new selection command for selection changes
        if current_item is not None:
            self.ui.tree_hierarchy_widget.setSelectedItemsWithUndo([current_item])
        else:
            self.ui.tree_hierarchy_widget.setSelectedItemsWithUndo([])

        item = current_item
        if current_item is not None:
            self.properties_groups_show()
        else:
            self.properties_groups_hide()

        try:
            # Remove any existing PropertyFrame widgets
            for i in range(self.ui.properties_layout.count()):
                widget = self.ui.properties_layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    widget.deleteLater()
            for i in range(self.modifiers_group_instance.layout.count()):
                widget = self.modifiers_group_instance.layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    widget.deleteLater()
            for i in range(self.selection_criteria_group_instance.layout.count()):
                widget = self.selection_criteria_group_instance.layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    widget.deleteLater()
        except Exception as error:
            print(error)

        try:
            data = item.data(0, Qt.UserRole)
            data_modif = data.get("m_Modifiers", {})
            data_sel_criteria = data.get("m_SelectionCriteria", {})
            data.pop("m_Modifiers", None)
            data.pop("m_SelectionCriteria", None)
            property_instance = PropertyFrame(
                widget_list=self.ui.properties_layout,
                value=data,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                element=True,
                tree_hierarchy=self.ui.tree_hierarchy_widget,
                element_id_generator=self.element_id_generator
            )
            property_instance.edited.connect(self.update_tree_item_value)
            self.ui.properties_layout.insertWidget(0, property_instance)

            if data_modif:
                for entry in reversed(data_modif):
                    prop_instance = PropertyFrame(
                        widget_list=self.modifiers_group_instance.layout,
                        value=entry,
                        variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                        tree_hierarchy=self.ui.tree_hierarchy_widget,
                        element_id_generator=self.element_id_generator
                    )
                    prop_instance.edited.connect(self.update_tree_item_value)
                    self.modifiers_group_instance.layout.insertWidget(0, prop_instance)

            if data_sel_criteria:
                for entry in reversed(data_sel_criteria):
                    prop_instance = PropertyFrame(
                        widget_list=self.selection_criteria_group_instance.layout,
                        value=entry,
                        variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                        tree_hierarchy=self.ui.tree_hierarchy_widget,
                        element_id_generator=self.element_id_generator
                    )
                    prop_instance.edited.connect(self.update_tree_item_value)
                    self.selection_criteria_group_instance.layout.insertWidget(0, prop_instance)
        except Exception as error:
            print(error)

    def update_tree_item_value(self, item=None):
        if item is None:
            item = self.ui.tree_hierarchy_widget.currentItem()
        if item:
            output_value = {}
            modifiers = []
            selection_criteria = []

            # Collect modifiers
            for i in range(self.modifiers_group_instance.layout.count()):
                widget = self.modifiers_group_instance.layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    if value is not None:
                        modifiers.append(value)

            # Collect selection criteria
            for i in range(self.selection_criteria_group_instance.layout.count()):
                widget = self.selection_criteria_group_instance.layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    if value is not None:
                        selection_criteria.append(value)

            # Collect main properties
            for i in range(self.ui.properties_layout.count()):
                widget = self.ui.properties_layout.itemAt(i).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    if value is not None:
                        output_value.update(value)

            try:
                if modifiers[0] is None:
                    modifiers = []
            except:
                pass
            try:
                if selection_criteria[0] is None:
                    selection_criteria = []
            except:
                pass

            output_value.update({"m_Modifiers": modifiers})
            output_value.update({"m_SelectionCriteria": selection_criteria})
            item.setData(0, Qt.UserRole, output_value)

            # Mark document as modified
            self._modified = True
            self._edited.emit()

    # ======================================[Event Filter]========================================
    def eventFilter(self, source, event):
        if event.type() == QKeyEvent.KeyPress:
            if source == self.ui.tree_hierarchy_widget:
                if event.matches(QKeySequence.Copy):
                    self.copy_item(self.ui.tree_hierarchy_widget)
                    return True
                if event.matches(QKeySequence.Cut):
                    self.cut_item(self.ui.tree_hierarchy_widget)
                    return True
                if event.matches(QKeySequence.Paste):
                    self.paste_item(self.ui.tree_hierarchy_widget)
                    return True
                if event.matches(QKeySequence.Delete):
                    self.ui.tree_hierarchy_widget.DeleteSelectedItems()
                    return True
                if event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_V:
                    self.new_item_with_replacement(QApplication.clipboard().text())
                    return True
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_G:
                    self.undo_stack.push(GroupElementsCommand(self.ui.tree_hierarchy_widget))
                    return True
                if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
                    self.ui.tree_hierarchy_widget.DuplicateSelectedItems(self.element_id_generator)
                    return True
                if event.matches(QKeySequence.Undo):
                    self.undo_stack.undo()
                    return True
                if event.matches(QKeySequence.Redo):
                    self.undo_stack.redo()
                    return True
                if source.viewport().underMouse():
                    if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                        self.add_an_element()
                        return True
        return super().eventFilter(source, event)

    # ======================================[Tree Widget Hierarchy New Element]========================================
    def add_preset(self):
        presets = []
        for root, dirs, files in os.walk(SmartPropEditor_Preset_Path):
            for file in files:
                presets.append({file: os.path.join(root, file)})
        self.popup_menu = PopupMenu(presets, add_once=False, window_name="SPE_elements_presets")
        self.popup_menu.add_property_signal.connect(lambda name, value: self.load_preset(name, value))
        self.popup_menu.show()

    def file_deserialization(self, __data: dict, to_parent: bool = False):
        def populate_tree(data, parent=None):
            if parent is None:
                parent = self.ui.tree_hierarchy_widget.invisibleRootItem()
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == "m_Children" and isinstance(value, list):
                        for item in value:
                            item_class = item.get("_class")
                            value_dict = item.copy()
                            value_dict.pop("m_Children", None)
                            self.element_id_generator.update_value(value_dict)
                            value_dict = self.element_id_generator.update_child_value(value_dict, force=True)
                            child_item = HierarchyItemModel(
                                _name=value_dict.get("m_sLabel", get_label_id_from_value(value_dict)),
                                _data=value_dict,
                                _class=get_clean_class_name(item_class),
                                _id=self.element_id_generator.get_key(value_dict)
                            )
                            if to_parent and parent.parent() is not None:
                                parent.parent().addChild(child_item)
                            elif to_parent:
                                self.ui.tree_hierarchy_widget.invisibleRootItem().addChild(child_item)
                            else:
                                parent.addChild(child_item)
                            populate_tree(item, child_item)

        def populate_choices(data):
            if data is None:
                print("No choices")
                return
            for choice in data:
                name = choice["m_Name"]
                default = choice.get("m_DefaultOption", None)
                options = choice.get("m_Options", None)
                new_choice = AddChoice(
                    name=name,
                    tree=self.ui.choices_tree_widget,
                    default=default,
                    variables_scrollArea=self.variable_viewport.ui.variables_scrollArea
                ).item
                if options:
                    for option in options:
                        option_item = AddOption(parent=new_choice, name=option["m_Name"]).item
                        variables_list_ = option["m_VariableValues"]
                        for variable in variables_list_:
                            AddVariable(
                                parent=option_item,
                                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                                name=variable["m_TargetName"],
                                type=variable.get("m_DataType", ""),
                                value=variable["m_Value"]
                            )

        def populate_variables(data):
            if isinstance(data, list):
                for item in data:
                    var_class = (item["_class"]).replace(variable_prefix, "")
                    var_name = item.get("m_VariableName", None)
                    var_display_name = item.get("m_DisplayName", None)
                    if var_display_name is None:
                        var_display_name = item.get("m_ParameterName", None)
                    var_visible_in_editor = bool(item.get("m_bExposeAsParameter", None))
                    var_value = {
                        "default": item.get("m_DefaultValue", None),
                        "model": item.get("m_sModelName", None),
                        "m_nElementID": item.get("m_nElementID", None),
                        'm_HideExpression': item.get("m_HideExpression", None)
                    }
                    if var_class == "Float":
                        var_value.update({
                            "min": item.get("m_flParamaterMinValue", None),
                            "max": item.get("m_flParamaterMaxValue", None)
                        })
                    elif var_class == "Int":
                        var_value.update({
                            "min": item.get("m_nParamaterMinValue", None),
                            "max": item.get("m_nParamaterMaxValue", None)
                        })
                    else:
                        var_value.update({"min": None, "max": None})

                    existing_variables = self.get_variables(layout=self.variable_viewport.ui.variables_scrollArea, only_names=True)
                    variable_exists = False
                    for index, variable in existing_variables.items():
                        name_ = variable[0]
                        if name_ == var_name:
                            variable_exists = True
                            break

                    if not variable_exists:
                        self.add_variable(
                            name=var_name,
                            var_value=var_value,
                            var_visible_in_editor=var_visible_in_editor,
                            var_class=var_class,
                            var_display_name=var_display_name
                        )

        if self.ui.tree_hierarchy_widget.currentItem() is None:
            parent_item = self.ui.tree_hierarchy_widget.invisibleRootItem()
        else:
            parent_item = self.ui.tree_hierarchy_widget.currentItem()

        populate_tree(__data, parent_item)
        populate_choices(__data.get("m_Choices", None))
        populate_variables(__data.get("m_Variables"))

    def load_preset(self, name: str = None, path: str = None):
        with open(path, "r") as file:
            __data = file.read()
        __data = Kv3ToJson(__data)
        self.file_deserialization(__data, to_parent=False)

    def add_an_element(self):
        self.popup_menu = PopupMenu(elements_list, add_once=False, window_name="SPE_elements")
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_element(name, value))
        self.popup_menu.show()

    def new_element(self, element_class, element_value):
        element_value = ast.literal_eval(element_value)
        self.element_id_generator.update_value(element_value)
        new_element_item = HierarchyItemModel(
            _name=get_label_id_from_value(element_value),
            _data=element_value,
            _class=get_clean_class_name_value(element_value),
            _id=self.element_id_generator.get_key(element_value)
        )
        self.ui.tree_hierarchy_widget.AddItem(new_element_item)

    # ======================================[Properties operator]========================================
    def new_operator(self, element_class, element_value):
        operator_instance = PropertyFrame(
            widget_list=self.modifiers_group_instance.layout,
            value=element_value,
            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
            tree_hierarchy=self.ui.tree_hierarchy_widget,
            element_id_generator=self.element_id_generator
        )
        operator_instance.edited.connect(self.update_tree_item_value)
        self.modifiers_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()

    def add_an_operator(self):
        """
        Combines operators and filters, determines which classes already exist,
        excludes duplicates unless an item is forced, and then displays a popup
        menu to add new operators.
        """
        operators_and_filters = operators_list + filters_list
        elements_in_popupmenu = []
        exists_classes = []
        force_items_names = ["SetVariable", "SaveState", 'Comment']
        force_items = []
        for item in operators_and_filters:
            for key in item.keys():
                if key in force_items_names:
                    force_items.append(item)
        for i in range(self.modifiers_group_instance.layout.count()):
            widget = self.modifiers_group_instance.layout.itemAt(i).widget()
            if isinstance(widget, PropertyFrame):
                exists_classes.append(widget.name)
        for class_name in force_items_names:
            if class_name in exists_classes:
                exists_classes.remove(class_name)
        for item in operators_and_filters:
            for key in item.keys():
                if key not in exists_classes:
                    if item not in elements_in_popupmenu:
                        elements_in_popupmenu.append(item)
        for item in force_items:
            if item not in elements_in_popupmenu:
                elements_in_popupmenu.append(item)
        self.popup_menu = PopupMenu(
            elements_in_popupmenu,
            add_once=True,
            window_name="SPE_operators",
            ignore_list=force_items_names
        )
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_operator(name, value))
        self.popup_menu.show()

    def paste_operator(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(";;")

        if clipboard_data[0] == "hammer5tools:smartprop_editor_property":
            data = ast.literal_eval(clipboard_data[2])
            data = self.element_id_generator.update_value(data, force=True)
            operator_instance = PropertyFrame(
                widget_list=self.modifiers_group_instance.layout,
                value=data,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                tree_hierarchy=self.ui.tree_hierarchy_widget,
                element_id_generator=self.element_id_generator
            )
            operator_instance.edited.connect(self.update_tree_item_value)
            self.modifiers_group_instance.layout.insertWidget(1, operator_instance)
        else:
            print("Clipboard data format is not valid.")
        self.update_tree_item_value()

    # ======================================[Properties Selection Criteria]========================================
    def add_a_selection_criteria(self):
        elements_in_popupmenu = []
        exists_classes = []
        for i in range(self.selection_criteria_group_instance.layout.count()):
            widget = self.selection_criteria_group_instance.layout.itemAt(i).widget()
            if isinstance(widget, PropertyFrame):
                exists_classes.append(widget.name)
        for item in selection_criteria_list:
            for key, value in item.items():
                if key not in exists_classes:
                    elements_in_popupmenu.append(item)
        self.popup_menu = PopupMenu(elements_in_popupmenu, add_once=True, window_name="SPE_selection_criteria")
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_selection_criteria(name, value))
        self.popup_menu.show()

    def new_selection_criteria(self, element_class, element_value):
        operator_instance = PropertyFrame(
            widget_list=self.selection_criteria_group_instance.layout,
            value=element_value,
            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
            tree_hierarchy=self.ui.tree_hierarchy_widget,
            element_id_generator=self.element_id_generator
        )
        operator_instance.edited.connect(self.update_tree_item_value)
        self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()

    def paste_selection_criteria(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(";;")

        if clipboard_data[0] == "hammer5tools:smartprop_editor_property":
            data = ast.literal_eval(clipboard_data[2])
            data = self.element_id_generator.update_value(data, force=True)
            operator_instance = PropertyFrame(
                widget_list=self.selection_criteria_group_instance.layout,
                value=data,
                variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                tree_hierarchy=self.ui.tree_hierarchy_widget,
                element_id_generator=self.element_id_generator
            )
            operator_instance.edited.connect(self.update_tree_item_value)
            self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        else:
            print("Clipboard data format is not valid.")
        self.update_tree_item_value()

    # ======================================[Open File]========================================
    @exception_handler
    def open_file(self, filename):
        self.opened_file = filename
        vsmart_instance = VsmartOpen(
            element_id_generator= self.element_id_generator,
            filename=filename,
            tree=self.ui.tree_hierarchy_widget,
            choices_tree=self.ui.choices_tree_widget,
            variables_scrollArea=self.variable_viewport.ui.variables_scrollArea
        )
        variables = vsmart_instance.variables
        self.content_version_spinbox.setValue(vsmart_instance.content_version)

        # Clear existing variables
        index = 0
        while index < self.variable_viewport.ui.variables_scrollArea.count() - 1:
            item = self.variable_viewport.ui.variables_scrollArea.takeAt(index)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                index += 1

        # Rebuild variables
        if isinstance(variables, list):
            for item in variables:
                var_class = (item["_class"]).replace(variable_prefix, "")
                var_name = item.get("m_VariableName", None)
                var_display_name = item.get("m_DisplayName", None)
                if var_display_name is None:
                    var_display_name = item.get("m_ParameterName", None)
                var_visible_in_editor = bool(item.get("m_bExposeAsParameter", None))

                var_value = {
                    "default": item.get("m_DefaultValue", None),
                    "model": item.get("m_sModelName", None),
                    "m_nElementID": item.get("m_nElementID", None),
                    'm_HideExpression': item.get("m_HideExpression", None)
                }
                element_id = var_value['m_nElementID']
                if element_id is not None:
                    self.element_id_generator.add_id(element_id)
                else:
                    var_value = self.element_id_generator.update_value(var_value)
                if var_class == "Float":
                    var_value.update({
                        "min": item.get("m_flParamaterMinValue", None),
                        "max": item.get("m_flParamaterMaxValue", None)
                    })
                elif var_class == "Int":
                    var_value.update({
                        "min": item.get("m_nParamaterMinValue", None),
                        "max": item.get("m_nParamaterMaxValue", None)
                    })
                else:
                    var_value.update({"min": None, "max": None})
                self.add_variable(
                    name=var_name,
                    var_value=var_value,
                    var_visible_in_editor=var_visible_in_editor,
                    var_class=var_class,
                    var_display_name=var_display_name
                )

        # Reset modification tracking
        self._modified = False

    # ======================================[Save File]========================================
    def save_file(self, external=False, realtime_save=False):
        if external:
            if not self.opened_file:
                filename = None
            else:
                filename = self.opened_file
        else:
            if self.opened_file:
                filename = self.opened_file
                external = False
            else:
                filename = None
                external = True

        if external:
            current_folder = self.parent.mini_explorer.get_current_folder(True)
            filename, _ = QFileDialog.getSaveFileName(
                None,
                "Save File",
                current_folder,
                "VSmart Files (*.vsmart);;All Files (*)"
            )
        self.get_variables(self.variable_viewport.ui.variables_scrollArea)
        content_version = self.content_version_spinbox.value()
        if filename:
            if not realtime_save:
                try:
                    VsmartSaveInstance = VsmartSave(filename=filename, tree=self.ui.tree_hierarchy_widget,choices_tree=self.ui.choices_tree_widget,variables_layout=self.variable_viewport.ui.variables_scrollArea, content_version=content_version)
                except Exception as e:
                    error_message = f"An error while saving Vsmart File: {e}"
                    error_details = traceback.format_exc()
                    error(error_message)

                    # Ensure the dialog is executed in the main thread
                    app = QApplication.instance()
                    if app is not None:
                        ErrorInfo(text=error_message, details=error_details).exec_()
                    else:
                        print("Error: QApplication instance is not available.")
            else:
                VsmartSaveInstance = VsmartSave(filename=filename,tree=self.ui.tree_hierarchy_widget,choices_tree=self.ui.choices_tree_widget, variables_layout=self.variable_viewport.ui.variables_scrollArea, content_version=content_version)

            self.opened_file = VsmartSaveInstance.filename
            if self.update_title:
                self.update_title("saved", filename)
            # Mark document as unmodified after saving
            self._modified = False

    # ======================================[Choices Context Menu]========================================
    def open_MenuChoices(self, position):
        menu = QMenu()
        item = self.ui.choices_tree_widget.itemAt(position)
        add_choice = menu.addAction("Add Choice")
        add_choice.triggered.connect(
            lambda: AddChoice(tree=self.ui.choices_tree_widget, variables_scrollArea=self.variable_viewport.ui.variables_scrollArea)
        )

        if item:
            if item.text(2) == "choice":
                add_option = menu.addAction("Add Option")
                add_option.triggered.connect(lambda: AddOption(parent=item, name="Option"))
            elif item.text(2) == "option":
                add_variable = menu.addAction("Add Variable")
                add_variable.triggered.connect(
                    lambda: AddVariable(
                        parent=item,
                        variables_scrollArea=self.variable_viewport.ui.variables_scrollArea,
                        name="default",
                        value="",
                        type="",
                        element_id_generator=self.element_id_generator
                    )
                )

        menu.addSection("")
        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")
        move_up_action.triggered.connect(lambda: self.move_tree_item(self.ui.choices_tree_widget, -1))
        move_down_action.triggered.connect(lambda: self.move_tree_item(self.ui.choices_tree_widget, 1))
        menu.addSection("")

        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self.remove_tree_item(self.ui.choices_tree_widget))

        menu.exec(self.ui.choices_tree_widget.viewport().mapToGlobal(position))

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
        self.variable_viewport.add_variable(name, var_class, var_value, var_visible_in_editor, var_display_name, index)
        self._modified = True
        self._edited.emit()

    def duplicate_variable(self, __data, __index):
        self.variable_viewport.duplicate_variable(__data, __index)

    def add_new_variable(self):
        self.variable_viewport.add_new_variable()

    # ======================================[Variables Other]========================================

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

    # ======================================[Tree widget hierarchy filter]========================================
    def search_hierarchy(self, filter_text, parent_item):
        self.filter_tree_item(parent_item, filter_text.lower(), True)

    def filter_tree_item(self, item, filter_text, is_root=False):
        if not isinstance(item, QTreeWidgetItem):
            return False

        item_text = item.text(0).lower()
        item_visible = filter_text in item_text

        if is_root:
            item.setHidden(False)
        else:
            item.setHidden(not item_visible)

        any_child_visible = False

        for i in range(item.childCount()):
            child_item = item.child(i)
            child_visible = self.filter_tree_item(child_item, filter_text, False)
            if child_visible:
                any_child_visible = True

        if any_child_visible:
            item.setHidden(False)
            item.setExpanded(True)

        return item_visible or any_child_visible

    def open_bulk_model_importer(self):
        from src.editors.smartprop_editor.actions.bulk_model_importer import BulkModelImporterDialog
        from src.editors.smartprop_editor._common import get_clean_class_name_value, get_label_id_from_value
        from src.widgets import HierarchyItemModel
        import copy, os
        dialog = BulkModelImporterDialog(self, current_folder=self.parent.mini_explorer.get_current_folder(True))
        def on_accept(files, create_ref, ref_index):
            addon_path = get_addon_dir()
            ref_id = None
            parent_item = self.ui.tree_hierarchy_widget.currentItem()
            if parent_item is None:
                parent_item = self.ui.tree_hierarchy_widget.invisibleRootItem()
            items = []
            for index, file_path in enumerate(files):
                rel_path = os.path.relpath(file_path, addon_path).replace(os.path.sep, '/')
                base_name, _ = os.path.splitext(os.path.basename(file_path))
                element_dict = {
                    "_class": "CSmartPropElement_Model",
                    "m_sModelName": rel_path,
                    "m_Modifiers": [],
                    "m_SelectionCriteria": []
                }
                is_reference = create_ref and (index == ref_index)
                if is_reference:
                    element_dict["m_sLabel"] = f"{base_name}_REF"
                else:
                    element_dict["m_sLabel"] = base_name
                    if create_ref and ref_id is not None:
                        element_dict["m_nReferenceID"] = ref_id
                        element_dict["m_sReferenceObjectID"] = str(uuid.uuid4())
                element_value = copy.deepcopy(element_dict)
                self.element_id_generator.update_value(element_value)
                label = element_value.get("m_sLabel", get_label_id_from_value(element_value))
                new_item = HierarchyItemModel(
                    _name=label,
                    _data=element_value,
                    _class=get_clean_class_name_value(element_value),
                    _id=self.element_id_generator.get_key(element_value)
                )
                items.append(new_item)
                if is_reference:
                    try:
                        ref_id = element_value.get("m_nElementID")
                    except Exception:
                        ref_id = None
            self.undo_stack.push(BulkModelImportCommand(self, parent_item, items))
            self._modified = True
            self._edited.emit()
        dialog.accepted_data.connect(on_accept)
        dialog.exec()

    # ======================================[Tree widget hierarchy context menu]========================================
    def open_hierarchy_menu(self, position):
        menu = QMenu()
        add_new_action = menu.addAction("New element")
        add_new_action.triggered.connect(self.add_an_element)
        add_new_action.setShortcut(QKeySequence("Ctrl+F"))

        add_preset_action = menu.addAction("New from preset")
        add_preset_action.triggered.connect(self.add_preset)

        menu.addSeparator()

        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self.ui.tree_hierarchy_widget.DeleteSelectedItems())
        remove_action.setShortcut(QKeySequence("Delete"))

        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self.ui.tree_hierarchy_widget.DuplicateSelectedItems(self.element_id_generator))
        duplicate_action.setShortcut(QKeySequence("Ctrl+D"))

        grouping_action = menu.addAction("Group selected")
        grouping_action.triggered.connect(lambda: self.undo_stack.push(GroupElementsCommand(self.ui.tree_hierarchy_widget)))
        grouping_action.setShortcut(QKeySequence("Ctrl+G"))

        menu.addSeparator()

        copy_action = menu.addAction("Copy")
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(lambda: self.copy_item(self.ui.tree_hierarchy_widget))

        copy_action = menu.addAction("Cut")
        copy_action.setShortcut(QKeySequence.Cut)
        copy_action.triggered.connect(lambda: self.cut_item(self.ui.tree_hierarchy_widget))

        paste_action = menu.addAction("Paste")
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(lambda: self.paste_item(self.ui.tree_hierarchy_widget))

        paste_replace_action = menu.addAction("Paste with replacement")
        paste_replace_action.setShortcut(QKeySequence("Ctrl+Shift+V"))
        paste_replace_action.triggered.connect(lambda: self.new_item_with_replacement(QApplication.clipboard().text()))

        bulk_import_action = menu.addAction("Bulk Model Importer")
        bulk_import_action.triggered.connect(self.open_bulk_model_importer)

        menu.exec(self.ui.tree_hierarchy_widget.viewport().mapToGlobal(position))

    # ======================================[Tree widget functions]========================================
    def new_item_with_replacement(self, data):
        instance = FindAndReplaceDialog(data=data)
        instance.accepted_output.connect(lambda text: self.paste_item(self.ui.tree_hierarchy_widget, data_input=text))
        instance.exec()

    def move_tree_item(self, tree, direction):
        selected_items = tree.selectedItems()
        if not selected_items:
            return

        parent_to_items = {}
        for itm in selected_items:
            parent = itm.parent() or tree.invisibleRootItem()
            if parent not in parent_to_items:
                parent_to_items[parent] = []
            parent_to_items[parent].append(itm)

        for parent, items in parent_to_items.items():
            items.sort(key=lambda it_: parent.indexOfChild(it_), reverse=(direction > 0))
            for it_ in items:
                current_index = parent.indexOfChild(it_)
                new_index = current_index + direction
                if 0 <= new_index < parent.childCount():
                    parent.takeChild(current_index)
                    parent.insertChild(new_index, it_)

        tree.clearSelection()
        for it_ in selected_items:
            it_.setSelected(True)
        tree.scrollToItem(selected_items[-1] if direction > 0 else selected_items[0])

    def copy_item(self, tree, copy_to_clipboard=True):
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]
        selected_items = list(set(selected_items))
        root_data = {"m_Children": []}

        for tree_item in selected_items:
            item_data = serialization_hierarchy_items(item=tree_item)
            if item_data and "m_Children" in item_data:
                root_data["m_Children"].extend(item_data["m_Children"])

        if root_data["m_Children"]:
            if copy_to_clipboard:
                clipboard = QApplication.clipboard()
                clipboard.setText(JsonToKv3(root_data))
                return None
            else:
                return JsonToKv3(root_data)
        else:
            return None

    def cut_item(self, tree: QTreeWidget):
        self.copy_item(tree)
        self.ui.tree_hierarchy_widget.DeleteSelectedItems()

    def paste_item(self, tree, data_input=None, paste_to_parent=False):
        from src.common import Kv3ToJson
        from src.editors.smartprop_editor.vsmart import deserialize_hierarchy_item
        if data_input is None:
            data_input = QApplication.clipboard().text()
        try:
            obj = Kv3ToJson(self.fix_format(data_input))
            items = []
            parent = tree.currentItem() or tree.invisibleRootItem()
            if paste_to_parent:
                parent = parent.parent() or tree.invisibleRootItem()
            if "m_Children" in obj:
                for child in obj["m_Children"]:
                    item = deserialize_hierarchy_item(child, self.element_id_generator)
                    items.append(item)
            else:
                items.append(deserialize_hierarchy_item(obj, self.element_id_generator))
            self.undo_stack.push(PasteItemsCommand(tree, parent, items))
            self._modified = True
            self._edited.emit()
        except Exception as error:
            error_message = str(error)
            error_dialog = ErrorInfo(
                text="Wrong format of the pasting content",
                details=error_message
            )
            error_dialog.exec()

    def remove_tree_item(self, tree):
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]
        for itm in selected_items:
            if itm:
                if itm == itm.treeWidget().invisibleRootItem():
                    pass
                else:
                    parent = itm.parent() or itm.treeWidget().invisibleRootItem()
                    idx = parent.indexOfChild(itm)
                    parent.takeChild(idx)
        self._modified = True
        self._edited.emit()

    # ======================================[Window State]========================================
    def _restore_user_prefs(self):
        geo = self.settings.value("SmartPropEditorMainWindow/geometry")
        if geo:
            self.restoreGeometry(geo)

        state = self.settings.value("SmartPropEditorMainWindow/windowState")
        if state:
            self.restoreState(state)

        saved_index = self.settings.value("SmartPropEditorMainWindow/currentComboBoxIndex")
        if saved_index is not None:
            self.variable_viewport.ui.add_new_variable_combobox.setCurrentIndex(int(saved_index))

    def _save_user_prefs(self):
        current_index = self.ui.add_new_variable_combobox.currentIndex()
        self.settings.setValue("SmartPropEditorMainWindow/currentComboBoxIndex", current_index)
        self.settings.setValue("SmartPropEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SmartPropEditorMainWindow/windowState", self.saveState())

    def closeEvent(self, event):
        self._save_user_prefs()

    # ======================================[Other]========================================
    def fix_format(self, file_content):
        pattern = re.compile(r"= resource_name:")
        modified_content = re.sub(pattern, "= ", file_content)
        modified_content = modified_content.replace("null,", "")
        return modified_content
