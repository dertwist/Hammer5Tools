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
    QTabBar,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
    QWidgetAction
)
from PySide6.QtGui import (
    QKeyEvent,
    QUndoStack,
    QKeySequence,
    QAction
)
from src.explorer.browser import FileBrowser
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

#TODO Future improvement: Implement a node view for elements.
# In the node view, users will click on a node to edit its properties, triggering a context menu similar to that found in the Hammer editor (using, for example, Alt+Enter) or just show and hide properties in the viewport.
# The node view should be arranged vertically. All node-related information will be stored within the elements themselves.
# Nodes that are not connected via the Child input (i.e. isolated nodes) will be automatically attached as children of the root.

#TODO Add bulk element creation using asset.

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

        # Timer for auto-saving
        self.realtime_save_timer = QTimer(self)
        self.realtime_save_timer.setSingleShot(True)
        self.realtime_save_timer.timeout.connect(self.save_file)

        self.ui.tree_hierarchy_widget.installEventFilter(self)

        # Hierarchy setup
        self.ui.tree_hierarchy_widget.hideColumn(1)
        self.ui.tree_hierarchy_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tree_hierarchy_widget.customContextMenuRequested.connect(self.open_hierarchy_menu)
        self.ui.tree_hierarchy_widget.currentItemChanged.connect(self.on_tree_current_item_changed)
        self.ui.tree_hierarchy_widget.itemClicked.connect(on_three_hierarchyitem_clicked)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.ui.tree_hierarchy_widget.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        # Choices setup
        self.ui.choices_tree_widget.hideColumn(2)
        self.ui.choices_tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.choices_tree_widget.customContextMenuRequested.connect(self.open_MenuChoices)

        # Groups setup
        self.properties_groups_init()

        self.ui.tree_hierarchy_search_bar_widget.textChanged.connect(
            lambda text: self.search_hierarchy(text, self.ui.tree_hierarchy_widget.invisibleRootItem())
        )

        # Add variable classes to combobox
        for item in variables_list:
            self.ui.add_new_variable_combobox.addItem(item)

        # Initialize file explorer
        self.init_explorer()

        # Restore user prefs
        self._restore_user_prefs()

        # Initialize button signals
        self.buttons()

        self.ui.actionFileBrowser.triggered.connect(self.open_filebrowser)

        # Group dockwidgets
        self.tabifyDockWidget(self.ui.dockWidget_4, self.ui.dockWidget_2)
        # Set focus to hierarchy dockwidget
        self.ui.dockWidget_4.raise_()

        set_qdock_tab_style(self.findChildren)

        self.undo_stack = QUndoStack(self)


    def open_preset_manager(self):
        """Creating another instance of this window with a different Explorer path
           for preset management."""
        self.new_instance = SmartPropEditorMainWindow(update_title=self.update_title)
        self.new_instance.mini_explorer.deleteLater()
        self.new_instance.mini_explorer.frame.deleteLater()
        tree_directory = SmartPropEditor_Preset_Path
        self.new_instance.init_explorer(tree_directory, "SmartPropEditorPresetManager", preset_manager=True)
        self.new_instance.ui.preset_manager_button.deleteLater()
        self.new_instance.show()

    def init_explorer(self, dir: str = None, editor_name: str = None, preset_manager: bool = None):
        if dir is None:
            self.tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
        else:
            self.tree_directory = dir
        if editor_name is None:
            editor_name = "SmartPropEditor"
        if preset_manager is None:
            preset_manager = False
        self.mini_explorer = Explorer(
            tree_directory=self.tree_directory,
            addon=get_addon_name(),
            editor_name=editor_name,
            parent=self.ui.explorer_layout_widget
        )
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)
        if preset_manager:
            self.ui.dockWidget_10.show()
            self.ui.toolBar.hide()
        else:
            self.ui.dockWidget_10.hide()
            self.ui.dockWidget_10.deleteLater()

    def buttons(self):
        self.ui.add_new_variable_button.clicked.connect(self.add_new_variable)
        self.ui.open_file_button.clicked.connect(lambda: self.open_file())
        self.ui.open_file_as_button.clicked.connect(lambda: self.open_file(external=True))
        self.ui.save_file_button.clicked.connect(lambda: self.save_file())
        self.ui.save_as_file_button.clicked.connect(lambda: self.save_file(external=True))
        self.ui.variables_scroll_area_searchbar.textChanged.connect(self.search_variables)
        self.ui.cerate_file_button.clicked.connect(self.create_new_file)
        self.ui.paste_variable_button.clicked.connect(self.paste_variable)
        self.ui.realtime_save_checkbox.clicked.connect(self.realtime_save_action)
        self.ui.preset_manager_button.clicked.connect(self.open_preset_manager)

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
            data = ast.literal_eval(item.text(1))
            data_modif = data.get("m_Modifiers", {})
            data_sel_criteria = data.get("m_SelectionCriteria", {})

            data.pop("m_Modifiers", None)
            data.pop("m_SelectionCriteria", None)

            property_instance = PropertyFrame(
                widget_list=self.ui.properties_layout,
                value=data,
                variables_scrollArea=self.ui.variables_scrollArea,
                element=True,
                reference_bar=True,
                tree_hierarchy=self.ui.tree_hierarchy_widget
            )
            property_instance.edited.connect(self.update_tree_item_value)
            self.ui.properties_layout.insertWidget(0, property_instance)

            if data_modif:
                for entry in reversed(data_modif):
                    prop_instance = PropertyFrame(
                        widget_list=self.modifiers_group_instance.layout,
                        value=entry,
                        variables_scrollArea=self.ui.variables_scrollArea,
                        tree_hierarchy=self.ui.tree_hierarchy_widget
                    )
                    prop_instance.edited.connect(self.update_tree_item_value)
                    self.modifiers_group_instance.layout.insertWidget(0, prop_instance)

            if data_sel_criteria:
                for entry in reversed(data_sel_criteria):
                    prop_instance = PropertyFrame(
                        widget_list=self.selection_criteria_group_instance.layout,
                        value=entry,
                        variables_scrollArea=self.ui.variables_scrollArea,
                        tree_hierarchy=self.ui.tree_hierarchy_widget
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

            # If any modifier or selection criteria is empty or None
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
            self.ui.tree_hierarchy_widget.currentItem().setText(1, str(output_value))

            # Realtime save
            if self.realtime_save:
                raw_delay = get_settings_value('SmartPropEditor', 'realtime_saving_delay', 5)
                time = int(float(raw_delay))
                self.realtime_save_timer.start(time)

    # ======================================[Event Filter]========================================
    def eventFilter(self, source, event):
        """Handle keyboard and shortcut events for various widgets."""
        if event.type() == QKeyEvent.KeyPress:
            # Handle events for tree_hierarchy_widget
            if source == self.ui.tree_hierarchy_widget:
                # Copy (Ctrl + C)
                if event.matches(QKeySequence.Copy):
                    self.copy_item(self.ui.tree_hierarchy_widget)
                    return True

                # Cut (Ctrl + X)
                if event.matches(QKeySequence.Cut):
                    self.cut_item(self.ui.tree_hierarchy_widget)
                    return True

                # Paste (Ctrl + V)
                if event.matches(QKeySequence.Paste):
                    self.paste_item(self.ui.tree_hierarchy_widget)
                    return True

                # Delete
                if event.matches(QKeySequence.Delete):
                    self.undo_stack.push(DeleteTreeItemCommand(self.ui.tree_hierarchy_widget))
                    return True

                # Paste with replacement (Ctrl + Shift + V)
                if event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_V:
                    self.new_item_with_replacement(QApplication.clipboard().text())
                    return True

                # Paste with replacement (Ctrl + G)
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_G:
                    self.undo_stack.push(GroupElementsCommand(self.ui.tree_hierarchy_widget))
                    return True

                # Move Up (Ctrl + Up)
                if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Up:
                    self.move_tree_item(self.ui.tree_hierarchy_widget, -1)
                    return True

                # Move Down (Ctrl + Down)
                if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Down:
                    self.move_tree_item(self.ui.tree_hierarchy_widget, 1)
                    return True

                # Duplicate (Ctrl + D)
                if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_D:
                    self.duplicate_hierarchy_items(self.ui.tree_hierarchy_widget)
                    return True

                if event.matches(QKeySequence.Undo):
                    self.undo_stack.undo()
                    return True
                if event.matches(QKeySequence.Redo):
                    self.undo_stack.redo()
                    return True

                # Add element (Ctrl + F)
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
                            update_value_ElementID(value_dict)
                            value_dict = update_child_ElementID_value(value_dict, force=True)

                            child_item = HierarchyItemModel(
                                _name=value_dict.get(
                                    "m_sLabel",
                                    get_label_id_from_value(value_dict)
                                ),
                                _data=str(value_dict),
                                _class=get_clean_class_name(item_class),
                                _id=get_ElementID_key(value_dict)
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
                    variables_scrollArea=self.ui.variables_scrollArea
                ).item
                if options:
                    for option in options:
                        option_item = AddOption(parent=new_choice, name=option["m_Name"]).item
                        variables_list_ = option["m_VariableValues"]
                        for variable in variables_list_:
                            AddVariable(
                                parent=option_item,
                                variables_scrollArea=self.ui.variables_scrollArea,
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
                        "m_nElementID": item.get("m_nElementID", None)
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

                    existing_variables = self.get_variables(layout=self.ui.variables_scrollArea, only_names=True)
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
        update_value_ElementID(element_value)
        new_element_item = HierarchyItemModel(
            _name=get_label_id_from_value(element_value),
            _data=element_value,
            _class=get_clean_class_name_value(element_value),
            _id=get_ElementID_key(element_value)
        )
        if self.ui.tree_hierarchy_widget.currentItem() is None:
            parent = self.ui.tree_hierarchy_widget.invisibleRootItem()
        else:
            parent = self.ui.tree_hierarchy_widget.currentItem()
        parent.addChild(new_element_item)
        if self.ui.tree_hierarchy_widget.currentItem() is not None:
            self.ui.tree_hierarchy_widget.setCurrentItem(new_element_item)
            self.ui.tree_hierarchy_widget.setFocus()

    # ======================================[Properties operator]========================================
    def new_operator(self, element_class, element_value):
        operator_instance = PropertyFrame(
            widget_list=self.modifiers_group_instance.layout,
            value=element_value,
            variables_scrollArea=self.ui.variables_scrollArea,
            tree_hierarchy=self.ui.tree_hierarchy_widget
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

        # Combine operator and filter dictionaries from existing lists
        operators_and_filters = operators_list + filters_list

        # Elements we will display in the popup menu
        elements_in_popupmenu = []

        # Operator classes that already exist in the layout
        exists_classes = []

        # These item names should be forced into the final list even if they already exist
        force_items_names = ["SetVariable", "SaveState", 'Comment']

        # Gather the dictionaries for forced items
        force_items = []
        for item in operators_and_filters:
            for key in item.keys():
                if key in force_items_names:
                    force_items.append(item)

        # Collect the classes currently in the layout
        for i in range(self.modifiers_group_instance.layout.count()):
            widget = self.modifiers_group_instance.layout.itemAt(i).widget()
            if isinstance(widget, PropertyFrame):
                exists_classes.append(widget.name)

        # Remove forced items from the exists_classes list
        # so they can appear again in the popup
        for class_name in force_items_names:
            if class_name in exists_classes:
                exists_classes.remove(class_name)

        # For every item in operators_and_filters, add it if its key isn't in exists_classes
        for item in operators_and_filters:
            for key in item.keys():
                if key not in exists_classes:
                    # Avoid duplicates in the final list
                    if item not in elements_in_popupmenu:
                        elements_in_popupmenu.append(item)

        # Ensure force items appear in the final list
        for item in force_items:
            if item not in elements_in_popupmenu:
                elements_in_popupmenu.append(item)

        # Create and display the popup menu
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
            operator_instance = PropertyFrame(
                widget_list=self.modifiers_group_instance.layout,
                value=ast.literal_eval(clipboard_data[2]),
                variables_scrollArea=self.ui.variables_scrollArea,
                tree_hierarchy=self.ui.tree_hierarchy_widget
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
            variables_scrollArea=self.ui.variables_scrollArea,
            tree_hierarchy=self.ui.tree_hierarchy_widget
        )
        operator_instance.edited.connect(self.update_tree_item_value)
        self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()

    def paste_selection_criteria(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(";;")

        if clipboard_data[0] == "hammer5tools:smartprop_editor_property":
            operator_instance = PropertyFrame(
                widget_list=self.selection_criteria_group_instance.layout,
                value=ast.literal_eval(clipboard_data[2]),
                variables_scrollArea=self.ui.variables_scrollArea,
                tree_hierarchy=self.ui.tree_hierarchy_widget
            )
            operator_instance.edited.connect(self.update_tree_item_value)
            self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        else:
            print("Clipboard data format is not valid.")
        self.update_tree_item_value()

    # ======================================[Explorer]========================================
    def explorer_status(self):
        if self.opened_file == "":
            self.ui.dockWidget_10.setWindowTitle("Explorer")
        else:
            self.ui.dockWidget_10.setWindowTitle(f"Explorer: ({os.path.basename(self.opened_file)})")

    def realtime_save_action(self):
        self.realtime_save = self.ui.realtime_save_checkbox.isChecked()
        if get_settings_bool('SmartPropEditor', 'enable_transparency_window', True):
            if self.realtime_save:
                transparency = float(get_settings_value('SmartPropEditor', 'transparency_window', 70))/100
                self.parent.setWindowOpacity(transparency)
            else:
                self.parent.setWindowOpacity(1)

    def create_new_file(self):
        from src.smartprop_editor.blank_vsmart import blank_vsmart
        extension = "vsmart"
        try:
            index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
            filename = self.mini_explorer.model.filePath(index)
            if os.path.splitext(filename)[1] == "":
                current_folder = filename
            else:
                current_folder = os.path.dirname(filename)
        except:
            current_folder = self.tree_directory

        counter = 0
        new_file_name = f"new_smartprop_{counter:02}.{extension}"
        while os.path.exists(os.path.join(current_folder, new_file_name)):
            counter += 1
            new_file_name = f"new_smartprop_{counter:02}.{extension}"
        filepath = os.path.join(current_folder, new_file_name)
        with open(filepath, "w") as file:
            file.write(blank_vsmart)
        self.mini_explorer.select_tree_item(filepath)

    # ======================================[Open File]========================================
    def open_file(self, external=False):
        if external:
            filename, _ = QFileDialog.getOpenFileName(
                None,
                "Open File",
                os.path.join(cs2_path, "content", "csgo_addons", get_addon_name()),
                "VSmart Files (*.vsmart);;All Files (*)"
            )
        else:
            index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
            filename = self.mini_explorer.model.filePath(index)

        self.opened_file = filename
        vsmart_instance = VsmartOpen(
            filename=filename,
            tree=self.ui.tree_hierarchy_widget,
            choices_tree=self.ui.choices_tree_widget,
            variables_scrollArea=self.ui.variables_scrollArea
        )
        variables = vsmart_instance.variables

        # Clear existing variables in the scroll area
        index = 0
        while index < self.ui.variables_scrollArea.count() - 1:
            item = self.ui.variables_scrollArea.takeAt(index)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                index += 1

        # Rebuild variables from the file
        if isinstance(variables, list):
            for item in variables:
                var_class = (item["_class"]).replace(variable_prefix, "")
                var_name = item.get("m_VariableName", None)
                var_display_name = item.get("m_ParameterName", None)
                if var_display_name is None:
                    var_display_name = item.get("m_DisplayName", None)
                var_visible_in_editor = bool(item.get("m_bExposeAsParameter", None))

                var_value = {
                    "default": item.get("m_DefaultValue", None),
                    "model": item.get("m_sModelName", None),
                    "m_nElementID": item.get("m_nElementID", None)
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

                self.add_variable(
                    name=var_name,
                    var_value=var_value,
                    var_visible_in_editor=var_visible_in_editor,
                    var_class=var_class,
                    var_display_name=var_display_name
                )

        if not self.realtime_save and self.update_title:
            self.update_title("opened", filename)
        self.explorer_status()

    # ======================================[Save File]========================================
    def save_file(self, external=False):
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
            filename, _ = QFileDialog.getSaveFileName(
                None,
                "Save File",
                os.path.join(cs2_path, "content", "csgo_addons", get_addon_name()),
                "VSmart Files (*.vsmart);;All Files (*)"
            )
        self.get_variables(self.ui.variables_scrollArea)
        if filename:
            VsmartSaveInstance = VsmartSave(
                filename=filename,
                tree=self.ui.tree_hierarchy_widget,
                choices_tree=self.ui.choices_tree_widget,
                variables_layout=self.ui.variables_scrollArea
            )
            self.opened_file = VsmartSaveInstance.filename
            if self.update_title:
                self.update_title("saved", filename)

    # ======================================[Choices Context Menu]========================================
    def open_MenuChoices(self, position):
        """
        Replacing QActions with push buttons keeps the same logic and comments,
        but we place them inside a QWidget for the menu.
        """
        menu = QMenu()
        container_widget = QWidget()
        vlayout = QVBoxLayout(container_widget)
        item = self.ui.choices_tree_widget.itemAt(position)

        # Add Choice
        add_choice_btn = QPushButton("Add Choice")
        add_choice_btn.clicked.connect(
            lambda: AddChoice(tree=self.ui.choices_tree_widget, variables_scrollArea=self.ui.variables_scrollArea)
        )
        vlayout.addWidget(add_choice_btn)

        # If item:
        if item:
            if item.text(2) == "choice":
                add_option_btn = QPushButton("Add Option")
                add_option_btn.clicked.connect(lambda: AddOption(parent=item, name="Option"))
                vlayout.addWidget(add_option_btn)
            elif item.text(2) == "option":
                add_variable_btn = QPushButton("Add Variable")
                add_variable_btn.clicked.connect(
                    lambda: AddVariable(
                        parent=item,
                        variables_scrollArea=self.ui.variables_scrollArea,
                        name="default",
                        value="",
                        type=""
                    )
                )
                vlayout.addWidget(add_variable_btn)

        # Sections and Move Up / Move Down
        move_up_btn = QPushButton("Move Up")
        move_up_btn.clicked.connect(lambda: self.move_tree_item(self.ui.choices_tree_widget, -1))
        vlayout.addWidget(move_up_btn)

        move_down_btn = QPushButton("Move Down")
        move_down_btn.clicked.connect(lambda: self.move_tree_item(self.ui.choices_tree_widget, 1))
        vlayout.addWidget(move_down_btn)

        # Remove
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.remove_tree_item(self.ui.choices_tree_widget))
        vlayout.addWidget(remove_btn)

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(container_widget)
        menu.addAction(widget_action)

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
        __data[2] = update_value_ElementID(__data[2], force=True)
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
        """
        Since we are inside the main window, we can show a menu with a QWidgetAction
        containing push buttons instead of QActions.
        """
        if self.ui.variables_QscrollArea is QApplication.focusWidget():
            context_menu = QMenu(self)
            container_widget = QWidget()
            layout = QVBoxLayout(container_widget)

            paste_variable_btn = QPushButton("Paste Variable")
            paste_variable_btn.clicked.connect(self.paste_variable)
            layout.addWidget(paste_variable_btn)

            widget_action = QWidgetAction(context_menu)
            widget_action.setDefaultWidget(container_widget)
            context_menu.addAction(widget_action)

            context_menu.exec_(event.globalPos())

    def paste_variable(self):
        """
        Deserializes variable data from clipboard and creates new variables.
        Handles the complete variable data structure including optional parameters.
        """
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
                # Extract required fields
                _class = variable.get('_class', '')
                if not _class.startswith('CSmartPropVariable_'):
                    continue

                var_class = _class.replace('CSmartPropVariable_', '')
                var_name = variable.get('m_VariableName', '')
                var_visible = variable.get('m_bExposeAsParameter', False)

                # Create value dictionary with optional parameters
                var_value = {
                    'default': variable.get('m_DefaultValue'),
                    'min': variable.get('m_flParamaterMinValue'),
                    'max': variable.get('m_flParamaterMaxValue'),
                    'model': variable.get('m_sModelName')
                }

                # Update ElementID for the new variable
                update_value_ElementID(var_value, force=True)

                # Create new variable with extracted data
                self.add_variable(
                    name=var_name,
                    var_class=var_class,
                    var_value=var_value,
                    var_visible_in_editor=var_visible,
                    var_display_name=variable.get('m_ParameterName')
                )

        except Exception as e:
            ErrorInfo(text="Failed to paste variable data.", details=str(e)).exec()

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

    # ======================================[Tree widget hierarchy context menu]========================================
    def open_hierarchy_menu(self, position):
        """
        Replace old QActions with push buttons inside a QWidgetAction, preserving the logic and comments.
        """
        menu = QMenu()
        container_widget = QWidget()
        layout = QVBoxLayout(container_widget)

        # "New element"
        new_element_btn = QPushButton("New element")
        new_element_btn.clicked.connect(self.add_an_element)
        layout.addWidget(new_element_btn)

        # "New using preset"
        add_preset_btn = QPushButton("New using preset")
        add_preset_btn.clicked.connect(self.add_preset)
        layout.addWidget(add_preset_btn)

        # Move Up
        move_up_btn = QPushButton("Move Up")
        move_up_btn.clicked.connect(lambda: self.move_tree_item(self.ui.tree_hierarchy_widget, -1))
        layout.addWidget(move_up_btn)

        # Move Down
        move_down_btn = QPushButton("Move Down")
        move_down_btn.clicked.connect(lambda: self.move_tree_item(self.ui.tree_hierarchy_widget, 1))
        layout.addWidget(move_down_btn)

        # Remove
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.undo_stack.push(DeleteTreeItemCommand(self.ui.tree_hierarchy_widget)))
        layout.addWidget(remove_btn)

        # Duplicate
        duplicate_btn = QPushButton("Duplicate")
        duplicate_btn.clicked.connect(lambda: self.duplicate_hierarchy_items(self.ui.tree_hierarchy_widget))
        layout.addWidget(duplicate_btn)

        # Group selected
        group_btn = QPushButton("Group selected")
        group_btn.clicked.connect(lambda: self.undo_stack.push(GroupElementsCommand(self.ui.tree_hierarchy_widget)))
        layout.addWidget(group_btn)

        # Copy
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: self.copy_item(self.ui.tree_hierarchy_widget))
        layout.addWidget(copy_btn)

        # Cut
        cut_btn = QPushButton("Cut")
        cut_btn.clicked.connect(lambda: self.cut_item(self.ui.tree_hierarchy_widget))
        layout.addWidget(cut_btn)

        # Paste
        paste_btn = QPushButton("Paste")
        paste_btn.clicked.connect(lambda: self.paste_item(self.ui.tree_hierarchy_widget))
        layout.addWidget(paste_btn)

        # Paste with replacement
        paste_replace_btn = QPushButton("Paste with replacement")
        paste_replace_btn.clicked.connect(lambda: self.new_item_with_replacement(QApplication.clipboard().text()))
        layout.addWidget(paste_replace_btn)

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(container_widget)
        menu.addAction(widget_action)

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
        self.undo_stack.push(DeleteTreeItemCommand(tree))

    def paste_item(self, tree, data_input=None, paste_to_parent=False):
        """
        Improved paste functionality:
         - If paste_to_parent is True, paste the first element of the serialized data
           as a sibling (same level) of the currently selected item, preserving its hierarchy.
         - Otherwise, paste as a child of the current item.
        """
        if data_input is None:
            data_input = QApplication.clipboard().text()
        try:
            obj = Kv3ToJson(self.fix_format(data_input))
            if paste_to_parent:
                # Determine the target parent for pasting as a sibling of the selected item.
                if tree.currentItem() and tree.currentItem().parent() is not None:
                    parent_item = tree.currentItem().parent()
                else:
                    parent_item = tree.invisibleRootItem()
                if "m_Children" in obj and obj["m_Children"]:
                    # Paste the first element in the serialized structure preserving its children.
                    new_item = deserialize_hierarchy_item(obj["m_Children"][0])
                    parent_item.addChild(new_item)
                    try:
                        new_item.setText(0, unique_counter_name(new_item, tree))
                    except Exception:
                        pass
                else:
                    new_item = deserialize_hierarchy_item(obj)
                    parent_item.addChild(new_item)
                    try:
                        new_item.setText(0, unique_counter_name(new_item, tree))
                    except Exception:
                        pass
            else:
                if "m_Children" in obj:
                    self.file_deserialization(obj, to_parent=False)
                else:
                    tree_item = deserialize_hierarchy_item(obj)
                    if tree.currentItem():
                        tree.currentItem().addChild(tree_item)
                    else:
                        tree.invisibleRootItem().addChild(tree_item)
                    try:
                        tree_item.setText(0, unique_counter_name(tree_item, tree))
                    except Exception:
                        pass
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

    def duplicate_hierarchy_items(self, tree):
        """Duplicate all selected items in the hierarchy tree."""
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]
        selected_items = list(set(selected_items))

        if not selected_items:
            return

        parent_to_items = {}
        for item in selected_items:
            parent = item.parent() or tree.invisibleRootItem()
            if parent not in parent_to_items:
                parent_to_items[parent] = []
            parent_to_items[parent].append(item)

        tree.clearSelection()

        for parent, items in parent_to_items.items():
            for item in items:
                item_data = serialization_hierarchy_items(item=item)

                if item_data and "m_Children" in item_data and item_data["m_Children"]:
                    new_item = deserialize_hierarchy_item(item_data["m_Children"][0])
                    parent.addChild(new_item)

                    try:
                        new_item.setText(0, unique_counter_name(new_item, tree))
                    except Exception:
                        pass

                    new_item.setSelected(True)

        if tree.selectedItems():
            tree.scrollToItem(tree.selectedItems()[0])

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
            self.ui.add_new_variable_combobox.setCurrentIndex(int(saved_index))

    def _save_user_prefs(self):
        current_index = self.ui.add_new_variable_combobox.currentIndex()
        self.settings.setValue("SmartPropEditorMainWindow/currentComboBoxIndex", current_index)
        self.settings.setValue("SmartPropEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SmartPropEditorMainWindow/windowState", self.saveState())

    def closeEvent(self, event):
        self._save_user_prefs()

    # ======================================[Other]========================================
    def fix_format(self, file_content):
        """Fixing format from Source2Viewr or from null elements, in Valve's or exported smartprops."""
        pattern = re.compile(r"= resource_name:")
        modified_content = re.sub(pattern, "= ", file_content)
        modified_content = modified_content.replace("null,", "")
        return modified_content
    def open_filebrowser(self):
        self.file_browser = FileBrowser(root=self.tree_directory, editor='SmartPropEditor', extension='vsmart')
        self.file_browser.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    import qtvscodestyle as qtvsc

    stylesheet = qtvsc.load_stylesheet(qtvsc.Theme.DARK_VS)
    app.setStyleSheet(stylesheet)
    window.show()
    sys.exit(app.exec())