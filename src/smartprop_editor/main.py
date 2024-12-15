import ast, sys
import os.path, re

from distutils.util import strtobool

from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QFileDialog
from PySide6.QtWidgets import QMenu, QApplication, QHeaderView
from PySide6.QtGui import QAction, QKeyEvent, QUndoStack
from PySide6.QtCore import Qt
from src.smartprop_editor.ui_main import Ui_MainWindow
from src.preferences import get_addon_name, get_cs2_path

from src.smartprop_editor.variable_frame import VariableFrame
from src.smartprop_editor.objects import variables_list, variable_prefix, elements_list, operators_list, selection_criteria_list, filters_list
from src.smartprop_editor.vsmart import VsmartOpen, VsmartSave
from src.smartprop_editor.property_frame import PropertyFrame
from src.smartprop_editor.properties_group_frame import PropertiesGroupFrame
from src.smartprop_editor.choices import AddChoice, AddVariable, AddOption
from src.popup_menu.popup_menu_main import PopupMenu
from src.smartprop_editor.commands import DeleteTreeItemCommand

from src.find_and_replace.main import FindAndReplaceDialog

from PySide6.QtGui import QKeySequence

from src.explorer.main import Explorer
from src.preferences import settings
from src.common import Kv3ToJson, JsonToKv3
from src.widgets import ErrorInfo, on_three_hierarchyitem_clicked, HierarchyItemModel
from src.smartprop_editor.element_id import *
from src.smartprop_editor._common import *
from src.common import *

# Get cs2_path
cs2_path = get_cs2_path()

class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings
        self.realtime_save = False
        self.opened_file = None

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

        #Groups setup
        self.properties_groups_init()

        self.ui.tree_hierarchy_search_bar_widget.textChanged.connect(lambda text: self.search_hierarchy(text, self.ui.tree_hierarchy_widget.invisibleRootItem()))

        # adding var classes to combobox
        for item in variables_list:
            self.ui.add_new_variable_combobox.addItem(item)

        # restore_prefs
        self._restore_user_prefs()

        # create smartprops folder if doesn't exists
        # smartprops_folder = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name(), 'smartprops')
        # if os.path.exists(smartprops_folder):
        #     pass
        # else:
        #     os.makedirs(smartprops_folder)

        self.init_explorer()

        self.buttons()

        self.undo_stack = QUndoStack(self)


    def open_preset_manager(self):
        """Creating another instance of this window without button preset manger and another path in the explorer"""
        self.new_instance = SmartPropEditorMainWindow()
        self.new_instance.mini_explorer.deleteLater()
        self.new_instance.mini_explorer.frame.deleteLater()
        tree_directory = SmartPropEditor_Preset_Path
        self.new_instance.init_explorer(tree_directory, 'SmartPropEditorPresetManager')
        self.new_instance.ui.preset_manager_button.deleteLater()
        self.new_instance.show()
    def init_explorer(self, dir: str = None, editor_name: str = None):
        if dir is None:
            self.tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name())
        else:
            self.tree_directory = dir
        if editor_name is None:
            editor_name = "SmartPropEditor"
        else:
            pass
        self.mini_explorer = Explorer(tree_directory=self.tree_directory, addon=get_addon_name(), editor_name=editor_name, parent=self.ui.explorer_layout_widget)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)
    def buttons(self):
        self.ui.add_new_variable_button.clicked.connect(self.add_new_variable)
        self.ui.open_file_button.clicked.connect(lambda: self.open_file())
        self.ui.open_file_as_button.clicked.connect(lambda: self.open_file(external=True))
        self.ui.save_file_button.clicked.connect(self.save_file)
        self.ui.save_as_file_button.clicked.connect(lambda: self.save_file(external=True))
        self.ui.variables_scroll_area_searchbar.textChanged.connect(self.search_variables)
        self.ui.cerate_file_button.clicked.connect(self.create_new_file)
        self.ui.paste_variable_button.clicked.connect(self.paste_variable)
        self.ui.realtime_save_checkbox.clicked.connect(self.realtime_save_action)
        self.ui.preset_manager_button.clicked.connect(self.open_preset_manager)

    # ======================================[Properties groups]========================================
    def properties_groups_init(self):
        self.modifiers_group_instance = PropertiesGroupFrame(widget_list=self.ui.properties_layout, name=str('Modifiers'))
        self.ui.properties_layout.insertWidget(0, self.modifiers_group_instance)
        self.modifiers_group_instance.add_signal.connect(self.add_an_operator)
        self.modifiers_group_instance.paste_signal.connect(self.paste_operator)


        self.selection_criteria_group_instance = PropertiesGroupFrame(widget_list=self.ui.properties_layout, name=str('Section criteria'))
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
            for i in range(self.ui.properties_layout.count()):
                widget = self.ui.properties_layout.itemAt(i).widget()
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
            data_modif = data.get('m_Modifiers', {})
            data_sel_criteria = data.get('m_SelectionCriteria', {})
            data.pop('m_Modifiers', None)
            data.pop('m_SelectionCriteria', None)
            property_instance = PropertyFrame(widget_list=self.ui.properties_layout, value=data, variables_scrollArea=self.ui.variables_scrollArea, element=True)
            property_instance.edited.connect(self.update_tree_item_value)



            self.ui.properties_layout.insertWidget(0, property_instance)
            if data_modif:
                for item in reversed(data_modif):
                    property_instance = PropertyFrame(widget_list=self.modifiers_group_instance.layout, value=item, variables_scrollArea=self.ui.variables_scrollArea)
                    property_instance.edited.connect(self.update_tree_item_value)
                    self.modifiers_group_instance.layout.insertWidget(0, property_instance)
            if data_sel_criteria:
                for item in reversed(data_sel_criteria):
                    property_instance = PropertyFrame(widget_list=self.selection_criteria_group_instance.layout, value=item, variables_scrollArea=self.ui.variables_scrollArea)
                    property_instance.edited.connect(self.update_tree_item_value)
                    self.selection_criteria_group_instance.layout.insertWidget(0, property_instance)
        except Exception as error:
            print(error)
    def update_tree_item_value(self, item=None):
        if item is None:
            item = self.ui.tree_hierarchy_widget.currentItem()
        if item:
            output_value = {}
            modifiers = []
            selection_criteria = []
            for item in range(self.modifiers_group_instance.layout.count()):
                widget = self.modifiers_group_instance.layout.itemAt(item).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    modifiers.append(value)
            for item in range(self.selection_criteria_group_instance.layout.count()):
                widget = self.selection_criteria_group_instance.layout.itemAt(item).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    selection_criteria.append(value)
            for item in range(self.ui.properties_layout.count()):
                widget = self.ui.properties_layout.itemAt(item).widget()
                if isinstance(widget, PropertyFrame):
                    value = widget.value
                    output_value.update(value)
            # if any modifier, set empty list
            try:
                if modifiers[0] == None:
                    modifiers = []
            except:
                pass
            try:
                if selection_criteria[0] == None:
                    selection_criteria = []
            except:
                pass
            output_value.update({'m_Modifiers': modifiers})
            output_value.update({'m_SelectionCriteria': selection_criteria})
            self.ui.tree_hierarchy_widget.currentItem().setText(1, str(output_value))
            if settings.value("OTHER/debug_info", type=bool):
                print(output_value)
            if self.realtime_save:
                self.save_file()

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

                # Paste (Ctrl + V)
                if event.matches(QKeySequence.Paste):
                    self.paste_item(self.ui.tree_hierarchy_widget)
                    return True

                # Delete
                if event.matches(QKeySequence.Delete):
                    self.undo_stack.push(DeleteTreeItemCommand(self.ui.tree_hierarchy_widget))

                    return True
                # Paste with replacement
                if event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_V:
                    self.new_item_with_replacement(QApplication.clipboard().text())
                    return True
                # Move Up
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_Up:
                    self.move_tree_item(self.ui.tree_hierarchy_widget, -1)
                    return True
                # Move Down
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_Down:
                    self.move_tree_item(self.ui.tree_hierarchy_widget, 1)
                    return True
                # Duplicate
                if event.modifiers() == (Qt.ControlModifier) and event.key() == Qt.Key_D:
                    self.duplicate_hierarchy_items(self.ui.tree_hierarchy_widget)
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
        presets = list()
        for root, dirs, files in os.walk(SmartPropEditor_Preset_Path):
            for file in files:
                presets.append({file: os.path.join(root, file)})

        self.popup_menu = PopupMenu(presets, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.load_preset(name, value))
        self.popup_menu.show()
    def load_preset(self, name: str = None, path:str = None):
        name, extension = os.path.splitext(name)
        with open(path, 'r') as file:
            __data = file.read()
        __data = Kv3ToJson(__data)
        def populate_tree(data, parent = None):
            if parent is None:
                parent = self.ui.tree_hierarchy_widget.invisibleRootItem()
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == 'm_Children':
                        if isinstance(value, list):
                            for item in value:
                                # Get keys
                                item_class = item.get('_class')
                                value_dict = item.copy()

                                # Delete m_Children key
                                value_dict.pop('m_Children', None)

                                # Assign or get element id
                                update_value_ElementID(value_dict)
                                value_dict = update_child_ElementID_value(value_dict, force=True)

                                # Add tree item
                                child_item = HierarchyItemModel(
                                    _name=value_dict.get('m_sLabel', get_label_id_from_value(value_dict)),
                                    _data=str(value_dict), _class=get_clean_class_name(item_class),
                                    _id=get_ElementID_key(value_dict))

                                parent.addChild(child_item)
                                populate_tree(item, child_item)
            pass

        def populate_choices(data):
            if data == None:
                print('No choices')
                return False
            else:
                debug(f'Choices {data}')
                for choice in data:
                    name = choice['m_Name']
                    default = choice.get('m_DefaultOption', None)
                    options = choice.get('m_Options', None)
                    choice = AddChoice(name=name, tree=self.ui.choices_tree_widget, default=default,
                                       variables_scrollArea=self.ui.variables_scrollArea).item
                    for option in options:
                        option_item = AddOption(parent=choice, name=option['m_Name']).item
                        variables = option['m_VariableValues']
                        for variable in variables:
                            AddVariable(parent=option_item, variables_scrollArea=self.ui.variables_scrollArea,
                                        name=variable['m_TargetName'], type=variable.get('m_DataType', ''),
                                        value=variable['m_Value'])
        def populate_variables(data):
            if isinstance(data, list):
                for item in data:
                    var_class = (item['_class']).replace(variable_prefix, '')
                    var_name = item.get('m_VariableName', None)
                    var_display_name = item.get('m_DisplayName', None)
                    if var_display_name is None:
                        var_display_name = item.get('m_ParameterName', None)
                    var_visible_in_editor = bool(item.get('m_bExposeAsParameter', None))

                    var_value = {
                        'default': item.get('m_DefaultValue', None),
                        'model': item.get('m_sModelName', None),
                        'm_nElementID': item.get('m_nElementID', None)
                    }
                    if var_class == 'Float':
                        var_value.update({
                            'min': item.get('m_flParamaterMinValue', None),
                            'max': item.get('m_flParamaterMaxValue', None)
                        })
                    elif var_class == 'Int':
                        var_value.update({
                            'min': item.get('m_nParamaterMinValue', None),
                            'max': item.get('m_nParamaterMaxValue', None)
                        })
                    else:
                        var_value.update({
                            'min': None,
                            'max': None
                        })
                    existing_variables = self.get_variables(layout= self.ui.variables_scrollArea,only_names=True)
                    variable_exists = False

                    for index, variable in existing_variables.items():
                        name = variable[0]
                        if name == var_name:
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


        if self.ui.tree_hierarchy_widget.currentItem() == None:
            parent = self.ui.tree_hierarchy_widget.invisibleRootItem()
        else:
            parent = self.ui.tree_hierarchy_widget.currentItem()
        populate_tree(__data, parent)
        populate_choices(__data.get('m_Choices', None))
        populate_variables(__data.get('m_Variables'))
    def add_an_element(self):
        self.popup_menu = PopupMenu(elements_list, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_element(name, value))
        self.popup_menu.show()
    def new_element(self, element_class, element_value):
        element_value = ast.literal_eval(element_value)
        update_value_ElementID(element_value)
        new_element = HierarchyItemModel(_name=get_label_id_from_value(element_value), _data=element_value, _class=get_clean_class_name_value(element_value), _id=get_ElementID_key(element_value))
        if self.ui.tree_hierarchy_widget.currentItem() == None:
            parent = self.ui.tree_hierarchy_widget.invisibleRootItem()
        else:
            parent = self.ui.tree_hierarchy_widget.currentItem()
        parent.addChild(new_element)

    # ======================================[Properties operator]========================================
    def new_operator(self, element_class, element_value):
        operator_instance = PropertyFrame(widget_list=self.modifiers_group_instance.layout, value=element_value, variables_scrollArea=self.ui.variables_scrollArea)
        operator_instance.edited.connect(self.update_tree_item_value)
        self.modifiers_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()
    def add_an_operator(self):
        operators_and_filters = operators_list + filters_list
        elements_in_popupmenu = []
        exists_classes = []
        for i in range(self.modifiers_group_instance.layout.count()):
            widget = self.modifiers_group_instance.layout.itemAt(i).widget()
            if isinstance(widget, PropertyFrame):
                exists_classes.append(widget.name)

        for item in operators_and_filters:
            for key, value in item.items():
                if key in exists_classes:
                    pass
                else:
                    elements_in_popupmenu.append(item)

        self.popup_menu = PopupMenu(elements_in_popupmenu, add_once=True)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_operator(name, value))
        self.popup_menu.show()

    def paste_operator(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(';;')

        if clipboard_data[0] == "hammer5tools:smartprop_editor_property":
            operator_instance = PropertyFrame(widget_list=self.modifiers_group_instance.layout, value=ast.literal_eval(clipboard_data[2]),variables_scrollArea=self.ui.variables_scrollArea)
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
                if key in exists_classes:
                    pass
                else:
                    elements_in_popupmenu.append(item)
        self.popup_menu = PopupMenu(elements_in_popupmenu, add_once=True)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_selection_criteria(name, value))
        self.popup_menu.show()

    def new_selection_criteria(self, element_class, element_value):
        operator_instance = PropertyFrame(widget_list=self.selection_criteria_group_instance.layout, value=element_value, variables_scrollArea=self.ui.variables_scrollArea)
        operator_instance.edited.connect(self.update_tree_item_value)
        self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()
    def paste_selection_criteria(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(';;')

        if clipboard_data[0] == "hammer5tools:smartprop_editor_property":
            operator_instance = PropertyFrame(widget_list=self.selection_criteria_group_instance.layout, value=ast.literal_eval(clipboard_data[2]),variables_scrollArea=self.ui.variables_scrollArea)
            operator_instance.edited.connect(self.update_tree_item_value)
            self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        else:
            print("Clipboard data format is not valid.")
        self.update_tree_item_value()


    # ======================================[Explorer]========================================

    def explorer_status(self):
        if self.opened_file == '':
            self.ui.dockWidget_10.setWindowTitle('Explorer')
        else:
            self.ui.dockWidget_10.setWindowTitle(f'Explorer: ({os.path.basename(self.opened_file)})')
    def realtime_save_action(self):
        if self.ui.realtime_save_checkbox.isChecked():
            self.realtime_save = True
        else:
            self.realtime_save = False

    def create_new_file(self):
        extension = 'vsmart'
        from src.smartprop_editor.blank_vsmart import blank_vsmart
        try:
            index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
            filename = self.mini_explorer.model.filePath(index)
            if os.path.splitext(filename)[1] == '':
                current_folder = filename
            else:
                current_folder = self.tree_directory
        except:
            current_folder = self.tree_directory
        counter = 0
        new_file_name = f"new_smartprop_{counter:02}.{extension}"
        while os.path.exists(os.path.join(current_folder, new_file_name)):
            counter += 1
            new_file_name = f"new_smartprop_{counter:02}.{extension}"


        with open(os.path.join(current_folder, new_file_name), 'w') as file:
            file.write(blank_vsmart)
            pass

    # ======================================[Open File]========================================
    def open_file(self, external=False):
        if external:
            filename, _ = QFileDialog.getOpenFileName(None, "Open File", os.path.join(cs2_path, "content", "csgo_addons", get_addon_name()), "VSmart Files (*.vsmart);;All Files (*)")
        else:
            index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
            filename = self.mini_explorer.model.filePath(index)

        self.opened_file = filename

        vsmart_instance = VsmartOpen(filename=filename, tree=self.ui.tree_hierarchy_widget, choices_tree=self.ui.choices_tree_widget, variables_scrollArea=self.ui.variables_scrollArea)
        variables = vsmart_instance.variables
        index = 0
        while index < self.ui.variables_scrollArea.count() - 1:
            item = self.ui.variables_scrollArea.takeAt(index)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                index += 1
        if isinstance(variables, list):
            for item in variables:
                var_class = (item['_class']).replace(variable_prefix, '')
                var_name = item.get('m_VariableName', None)
                var_display_name = item.get('m_DisplayName', None)
                if var_display_name is None:
                    var_display_name = item.get('m_ParameterName', None)
                var_visible_in_editor = bool(item.get('m_bExposeAsParameter', None))

                var_value = {
                    'default': item.get('m_DefaultValue', None),
                    'model': item.get('m_sModelName', None),
                    'm_nElementID': item.get('m_nElementID', None)
                }
                if var_class == 'Float':
                    var_value.update({
                        'min': item.get('m_flParamaterMinValue', None),
                        'max': item.get('m_flParamaterMaxValue', None)
                    })
                elif var_class == 'Int':
                    var_value.update({
                        'min': item.get('m_nParamaterMinValue', None),
                        'max': item.get('m_nParamaterMaxValue', None)
                    })
                else:
                    var_value.update({
                        'min': None,
                        'max': None
                    })
                self.add_variable(name=var_name, var_value=var_value, var_visible_in_editor=var_visible_in_editor, var_class=var_class, var_display_name=var_display_name)
        print(f'Opened file: {filename}')
        self.explorer_status()

    # ======================================[Save File]========================================
    def save_file(self, external=False):
        if external:
            pass
        else:
            if self.opened_file:
                filename = self.opened_file
                external = False
            else:
                filename = None
                external = True
        def save_variables():
            variables = []
            raw_variables = self.get_variables(self.ui.variables_scrollArea)
            for var_key, var_key_value in raw_variables.items():
                var_default = (var_key_value[2])['default']
                if var_default == None:
                    var_default = ''
                var_min = (var_key_value[2])['min']
                var_max = (var_key_value[2])['max']
                var_model = (var_key_value[2])['model']
                var_class = var_key_value[1]
                var_id = (var_key_value[2])['m_nElementID']

                # Basic
                var_dict = {
                    '_class': variable_prefix+var_class,
                    'm_VariableName': var_key_value[0],
                    'm_bExposeAsParameter':  var_key_value[3],
                    'm_DefaultValue': var_default,
                    'm_nElementID': var_id
                }
                # If display name none set variable name as display
                if var_key_value[4] == None or var_key_value[4] == '':
                    var_dict.update({'m_ParameterName': var_key_value[0]})
                else:
                    var_dict.update({'m_ParameterName': var_key_value[4]})

                if var_min is not None:
                    if var_class == 'Float':
                        var_dict.update({'m_flParamaterMinValue': var_min})
                    elif var_class == 'Int':
                        var_dict.update({'m_nParamaterMinValue': var_min})

                if var_max is not None:
                    if var_class == 'Float':
                        var_dict.update({'m_flParamaterMaxValue': var_max})
                    elif var_class == 'Int':
                        var_dict.update({'m_nParamaterMaxValue': var_max})

                if var_model is not None:
                    var_dict.update({'m_sModelName': var_model})

                variables.append(var_dict)

            return variables
        if external:
            filename, _ = QFileDialog.getSaveFileName(None, "Save File", os.path.join(cs2_path, "content", "csgo_addons", get_addon_name()), "VSmart Files (*.vsmart);;All Files (*)")

        var_data = save_variables()
        VsmartSaveInstance = VsmartSave(filename=filename, tree=self.ui.tree_hierarchy_widget, var_data=var_data, choices_tree=self.ui.choices_tree_widget)
        self.opened_file = VsmartSaveInstance.filename

    # ======================================[Choices Context Menu]========================================
    def open_MenuChoices(self, position):
        menu = QMenu()
        item = self.ui.choices_tree_widget.itemAt(position)
        add_choice = menu.addAction("Add Choice")
        add_choice.triggered.connect(lambda: AddChoice(tree=self.ui.choices_tree_widget, variables_scrollArea=self.ui.variables_scrollArea))

        if item:
            if item.text(2) == 'choice':
                add_option = menu.addAction("Add Option")
                add_option.triggered.connect(lambda : AddOption(parent=item, name='Option'))
            elif item.text(2) == 'option':
                add_variable = menu.addAction("Add Variable")
                add_variable.triggered.connect(lambda : AddVariable(parent=item,variables_scrollArea=self.ui.variables_scrollArea, name='default', value='', type=''))

        menu.addSection('')

        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")

        move_up_action.triggered.connect(lambda: self.move_tree_item(self.ui.choices_tree_widget, -1))
        move_down_action.triggered.connect(lambda: self.move_tree_item(self.ui.choices_tree_widget, 1))
        menu.addSection('')


        # copy_action = menu.addAction("Copy")
        # copy_action.setShortcut(QKeySequence.Copy)
        # copy_action.triggered.connect(lambda: self.copy_item(item))
        #
        # paste_action = menu.addAction("Paste")
        # paste_action.setShortcut(QKeySequence.Paste)
        # paste_action.triggered.connect(lambda: self.paste_item(item))
        # menu.addSection('')
        #
        # duplicate_action = menu.addAction("Duplicate")
        # duplicate_action.triggered.connect(lambda: self.duplicate_item(item, tree=self.ui.choices_tree_widget))

        remove_action = menu.addAction("Remove")
        remove_action.triggered.connect(lambda: self.remove_tree_item(self.ui.choices_tree_widget))
        # remove_action.triggered.connect(lambda: self.undo_stack.push(DeleteTreeItemCommand(self.ui.choices_tree_widget)))


        menu.exec(self.ui.choices_tree_widget.viewport().mapToGlobal(position))

    # ======================================[Variables Actions]========================================

    def add_variable(self, name, var_class, var_value, var_visible_in_editor, var_display_name, index:int = None):
        variable = VariableFrame(name=name, widget_list=self.ui.variables_scrollArea, var_value=var_value, var_class=var_class, var_visible_in_editor=var_visible_in_editor, var_display_name=var_display_name)
        variable.duplicate.connect(self.duplicate_variable)
        if index is None:
            index = (self.ui.variables_scrollArea.count()) - 1
        else:
            index = index +1
        self.ui.variables_scrollArea.insertWidget(index, variable)

    def duplicate_variable(self, __data, __index):
        self.add_variable(__data[0], __data[1], __data[2], __data[3], __data[4], __index)

    def add_new_variable(self):
        name = 'new_var'
        existing_variables = []
        variables = self.get_variables(self.ui.variables_scrollArea)
        for key, value in variables.items():
            existing_variables.append(value[0])

        # Check if the name already exists
        if name in existing_variables:
            suffix = 1
            while f"{name}_{suffix}" in existing_variables:
                suffix += 1
            name = f"{name}_{suffix}"

        var_class = self.ui.add_new_variable_combobox.currentText()
        var_name = name
        var_display_name = None
        var_visible_in_editor = False
        var_value = {
            'default':None,
            'min': None,
            'max': None,
            'model': None
        }
        self.add_variable(name=var_name, var_value=var_value, var_visible_in_editor=var_visible_in_editor,var_class=var_class, var_display_name=var_display_name)

    # ======================================[Variables Other]========================================
    def search_variables(self, search_term=None):
        for i in range(self.ui.variables_scrollArea.layout().count()):
            widget = self.ui.variables_scrollArea.layout().itemAt(i).widget()
            if widget:
                if search_term.lower() in widget.name.lower():  # Adjust the search logic as needed
                    widget.show()
                else:
                    widget.hide()


    def get_variables(self, layout, only_names=False):
        if only_names:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    item = {i: [widget.name, widget.var_class, widget.var_display_name]}
                    data_out.update(item)
            return data_out
        else:
            data_out = {}
            for i in range(layout.count()):
                widget = layout.itemAt(i).widget()
                if widget:
                    item = {i: [widget.name, widget.var_class, widget.var_value, widget.var_visible_in_editor, widget.var_display_name]}
                    data_out.update(item)
            return data_out

    #======================================[Variables Context menu]========================================
    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        if self.ui.variables_QscrollArea is QApplication.focusWidget():
            paste_action = QAction("Paste Variable", self)
            paste_action.triggered.connect(self.paste_variable)
            context_menu.addAction(paste_action)
        else:
            pass

        context_menu.exec_(event.globalPos())

    def paste_variable(self):
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()
        clipboard_data = clipboard_text.split(';;')

        if clipboard_data[0] == "hammer5tools:smartprop_editor_var":
            visible_in_editor = bool(strtobool(clipboard_data[4]))
            display_name = clipboard_data[5]
            if display_name == 'None':
                display_name = ''
            var_value = ast.literal_eval(clipboard_data[3])
            update_value_ElementID(var_value, force=True)
            self.add_variable(clipboard_data[1], clipboard_data[2], var_value, visible_in_editor, display_name)
        else:
            ErrorInfo(text="Clipboard data format is not valid.", details=clipboard_data).exec()

    # ======================================[Tree widget hierarchy filter]========================================
    def search_hierarchy(self, filter_text, parent_item):
        # Reset the root visibility and start the filtering process
        self.filter_tree_item(parent_item, filter_text.lower(), True)

    def filter_tree_item(self, item, filter_text, is_root=False):
        if not isinstance(item, QTreeWidgetItem):
            return False

        # Check if the current item's text matches the filter
        item_text = item.text(0).lower()
        item_visible = filter_text in item_text

        # Always show the root, regardless of filter
        if is_root:
            item.setHidden(False)
        else:
            # Hide the item if it doesn't match the filter
            item.setHidden(not item_visible)

        # Track visibility of any child matching the filter
        any_child_visible = False

        # Recursively filter all children
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_visible = self.filter_tree_item(child_item, filter_text, False)

            if child_visible:
                any_child_visible = True

        # If any child is visible, make sure this item is also visible
        if any_child_visible:
            item.setHidden(False)
            item.setExpanded(True)

        # Return True if this item or any of its children is visible
        return item_visible or any_child_visible

    # ======================================[Tree widget hierarchy context menu]========================================
    def open_hierarchy_menu(self, position):
        menu = QMenu()
        item = self.ui.choices_tree_widget.itemAt(position)
        add_new_action = menu.addAction("New element")
        add_new_action.triggered.connect(self.add_an_element)
        add_new_action.setShortcut(QKeySequence(QKeySequence("Ctrl+F")))

        add_new_action = menu.addAction("New using preset")
        add_new_action.triggered.connect(self.add_preset)

        menu.addSeparator()

        move_up_action = menu.addAction("Move Up")
        move_up_action.triggered.connect(lambda: self.move_tree_item(self.ui.tree_hierarchy_widget, -1))
        move_up_action.setShortcut(QKeySequence(QKeySequence("Ctrl+Up")))

        move_down_action = menu.addAction("Move Down")
        move_down_action.triggered.connect(lambda: self.move_tree_item(self.ui.tree_hierarchy_widget, 1))
        move_down_action.setShortcut(QKeySequence(QKeySequence("Ctrl+Down")))
        menu.addSeparator()

        remove_action = menu.addAction("Remove")
        # remove_action.triggered.connect(lambda: self.remove_tree_item(self.ui.tree_hierarchy_widget))
        remove_action.triggered.connect(lambda: self.undo_stack.push(DeleteTreeItemCommand(self.ui.tree_hierarchy_widget)))
        remove_action.setShortcut(QKeySequence(QKeySequence("Delete")))

        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self.duplicate_hierarchy_items(self.ui.tree_hierarchy_widget))
        duplicate_action.setShortcut(QKeySequence(QKeySequence("Ctrl+D")))

        menu.addSeparator()

        copy_action = menu.addAction("Copy")
        copy_action.setShortcut(QKeySequence(QKeySequence.Copy))
        copy_action.triggered.connect(lambda: self.copy_item(self.ui.tree_hierarchy_widget))

        paste_action = menu.addAction("Paste")
        paste_action.setShortcut(QKeySequence(QKeySequence.Paste))
        paste_action.triggered.connect(lambda: self.paste_item(self.ui.tree_hierarchy_widget))

        paste_action = menu.addAction("Paste with replacement")
        paste_action.setShortcut(QKeySequence(QKeySequence("Ctrl+Shift+V")))
        paste_action.triggered.connect(lambda: self.new_item_with_replacement(QApplication.clipboard().text()))

        menu.exec(self.ui.tree_hierarchy_widget.viewport().mapToGlobal(position))

    # ======================================[Tree widget functions]========================================

    def new_item_with_replacement(self, data):
        instance = FindAndReplaceDialog(data=data)
        instance.accepted_output.connect(lambda text:self.paste_item(tree=self.ui.tree_hierarchy_widget, data_input=text))
        instance.exec()

    def move_tree_item(self,tree, direction):
        """Move selected tree items up or down within their parent."""
        selected_items = tree.selectedItems()
        if not selected_items:
            return  # Exit if no items are selected

        # Group items by parent and sort by current index
        parent_to_items = {}
        for item in selected_items:
            parent = item.parent() or tree.invisibleRootItem()
            if parent not in parent_to_items:
                parent_to_items[parent] = []
            parent_to_items[parent].append(item)

        # Move items for each parent separately
        for parent, items in parent_to_items.items():
            # Sort items by their index in reverse if moving down (to avoid index shifting)
            items.sort(key=lambda item: parent.indexOfChild(item), reverse=(direction > 0))

            for item in items:
                current_index = parent.indexOfChild(item)
                new_index = current_index + direction

                # Check bounds
                if 0 <= new_index < parent.childCount():
                    # Move item
                    parent.takeChild(current_index)
                    parent.insertChild(new_index, item)

        tree.clearSelection()
        for item in selected_items:
            item.setSelected(True)
        tree.scrollToItem(selected_items[-1] if direction > 0 else selected_items[0])
    def copy_item(self, tree, copy_to_clipboard=True):
        """Coping Tree item"""
        # Gathering selected items
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]

        # Remove the same items
        selected_items = list(set(selected_items))

        for tree_item in selected_items:
            item_data = self.serialization_hierarchy_items(item=tree_item)
        # Output
        if copy_to_clipboard:
            clipboard = QApplication.clipboard()
            clipboard.setText(JsonToKv3(item_data))
        else:
            return JsonToKv3(item_data)

    def paste_item(self, tree, data_input=None, paste_to_parent=False):
        """Pasting tree item"""
        if data_input is None:
            data_input = QApplication.clipboard().text()
        try:
            input = Kv3ToJson(self.fix_format(data_input))
            if 'm_Children' in input:
                for key in input['m_Children']:
                    tree_item = self.deserialize_hierarchy_item(key)
                    try:
                        tree_item.setText(0, unique_counter_name(tree_item, tree))
                    except:
                        pass
                    try:
                        if paste_to_parent:
                            tree.currentItem().parent().addChild(tree_item)
                        else:
                            tree.currentItem().addChild(tree_item)
                    except:
                        tree.invisibleRootItem().addChild(tree_item)
            else:
                tree_item = self.deserialize_hierarchy_item(input)
                try:
                    tree_item.setText(0, unique_counter_name(tree_item, tree))
                except:
                    pass
                try:
                    if paste_to_parent:
                        tree.currentItem().parent().addChild(tree_item)
                    else:
                        tree.currentItem().addChild(tree_item)
                except:
                    tree.invisibleRootItem().addChild(tree_item)
        except Exception as error:
            error_message = str(error)
            error_dialog = ErrorInfo(text="Wrong format of the pasting content", details=error_message)
            error_dialog.exec()

    def remove_tree_item(self, tree):
        """Removing Tree item"""
        selected_indexes = tree.selectedIndexes()
        selected_items = [tree.itemFromIndex(index) for index in selected_indexes]
        for item in selected_items:
            if item:
                if item == item.treeWidget().invisibleRootItem():
                    pass
                else:
                    parent = item.parent() or item.treeWidget().invisibleRootItem()
                    index = parent.indexOfChild(item)
                    parent.takeChild(index)

    def duplicate_hierarchy_items(self, tree):
        data = self.copy_item(tree=tree, copy_to_clipboard=False)
        self.paste_item(tree, data, paste_to_parent=True)

    # ======================================[Tree item serialization and deserialization]========================================

    def serialization_hierarchy_items(self, item, data=None):
        """Convert tree structure to json"""
        if data is None:
            data = {'m_Children': []}
        value_row = item.text(1)
        parent_data = ast.literal_eval(value_row)
        # Label form tree element name
        parent_data['m_sLabel'] = item.text(0)
        if item.childCount() > 0:
            parent_data['m_Children'] = []
        data['m_Children'].append(parent_data)
        if item.childCount() > 0:
            for index in range(item.childCount()):
                child = item.child(index)
                key = child.text(0)
                value_row = child.text(1)

                child_data = ast.literal_eval(value_row)
                child_data['m_sLabel'] = key

                if child.childCount() > 0:
                    child_data['m_Children'] = []
                    self.serialization_hierarchy_items(child, child_data)

                parent_data['m_Children'].append(child_data)

        return data

    def deserialize_hierarchy_item(self, m_Children=HierarchyItemModel):
        item_value = {}

        # If there is a dict with child element, copy all expect child key in a new variable, and process it.
        for key in m_Children:
            if key == 'm_Children':
                pass
            else:
                item_value.update({key:m_Children[key]})

        # Unique ID fro each element that have _class key. Without force option output will use ID that in the value
        item_value = update_child_ElementID_value(item_value, force=True)
        # Get tree item name
        name = item_value.get('m_sLabel',get_clean_class_name_value(item_value))

        # New element
        tree_item = HierarchyItemModel(_data=item_value, _name=name, _id=get_ElementID_key(item_value), _class=get_clean_class_name_value(item_value))

        # Child processing
        for child_data in m_Children.get('m_Children', []):
            child_item = self.deserialize_hierarchy_item(child_data)
            tree_item.addChild(child_item)
        return tree_item


    #======================================[Window State]========================================
    def _restore_user_prefs(self):
        """Restore window state"""
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
        """Save window state"""
        current_index = self.ui.add_new_variable_combobox.currentIndex()
        self.settings.setValue("SmartPropEditorMainWindow/currentComboBoxIndex", current_index)
        self.settings.setValue("SmartPropEditorMainWindow/geometry", self.saveGeometry())
        self.settings.setValue("SmartPropEditorMainWindow/windowState", self.saveState())
    def closeEvent(self, event):
        self._save_user_prefs()
    #===============================================================<  Other  >=============================================================

    def fix_format(self, file_content):
            """Fixing format from Source2Viewr and from null elements, usually it happens in case of Hammer5Tools export, but in valve's smartprops it also could be."""
            pattern = re.compile(r'= resource_name:')
            modified_content = re.sub(pattern, '= ', file_content)
            modified_content = modified_content.replace('null,', '')
            return modified_content

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartPropEditorMainWindow()
    import qtvscodestyle as qtvsc

    stylesheet = qtvsc.load_stylesheet(qtvsc.Theme.DARK_VS)
    app.setStyleSheet(stylesheet)
    # app.setStyle('fusion')
    window.show()
    sys.exit(app.exec())
