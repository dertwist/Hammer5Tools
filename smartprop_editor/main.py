import ast
import os.path
import shutil
import threading
import time

from distutils.util import strtobool

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QTreeWidgetItem, QVBoxLayout, QSpacerItem, QSizePolicy, QInputDialog, QTreeWidget, QMessageBox, QProgressDialog, QCheckBox
from PySide6.QtWidgets import QMenu, QApplication
from PySide6.QtGui import QCursor, QDrag, QAction
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer, QEventLoop

from smartprop_editor.ui_main import Ui_MainWindow
from preferences import get_config_value, get_addon_name, get_cs2_path

from smartprop_editor.variable_frame import VariableFrame
from smartprop_editor.objects import variables_list, variable_prefix, element_prefix, elements_list, operators_list, operator_prefix, selection_criteria_prefix, selection_criteria_list, filters_list, filter_prefix
from smartprop_editor.vsmart import VsmartOpen, VsmartSave, VsmartCompile
from smartprop_editor.property_frame import PropertyFrame
from smartprop_editor.properties_group_frame import PropertiesGroupFrame
from smartprop_editor.new_file_options import NewFileOptions
from popup_menu.popup_menu_main import PopupMenu

from PySide6.QtGui import QKeySequence

from explorer.main import Explorer
from preferences import settings

global opened_file


# Get cs2_path
cs2_path = get_cs2_path()

class CompileAll(QObject):
    progress = Signal(int, str)
    finished = Signal()

    def run(self, total_files):
        progress = 0
        for i in total_files:
            loop = QEventLoop()

            timer = QTimer()
            timer.timeout.connect(loop.quit)
            timer.start(1)

            loop.exec()
            VsmartCompile(filename=i)
            progress += 1
            self.progress.emit(progress, os.path.basename(i))
        self.finished.emit()

class SmartPropEditorMainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.settings = settings

        # Hierarchy setup
        self.ui.tree_hierarchy_widget.hideColumn(1)
        self.ui.tree_hierarchy_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tree_hierarchy_widget.customContextMenuRequested.connect(self.open_hierarchy_menu)
        self.ui.tree_hierarchy_widget.currentItemChanged.connect(self.on_tree_current_item_changed)

        # Adding the properties_classes group
        self.properties_groups_init()


        # adding var classes to combobox
        for item in variables_list:
            self.ui.add_new_variable_combobox.addItem(item)

        # restore_prefs
        self._restore_user_prefs()

        self.tree_directory = os.path.join(cs2_path, "content", "csgo_addons", get_addon_name(), 'smartprops')
        self.mini_explorer = Explorer(tree_directory=self.tree_directory, addon=get_addon_name(), editor_name='SmartProp_editor', parent=self.ui.explorer_layout_widget)
        self.ui.explorer_layout.addWidget(self.mini_explorer.frame)

        self.buttons()


    def buttons(self):
        self.ui.add_new_variable_button.clicked.connect(self.add_new_variable)
        self.ui.open_file_button.clicked.connect(lambda: self.open_file(filename=None))
        self.ui.save_file_button.clicked.connect(self.save_file)
        self.ui.variables_scroll_area_searchbar.textChanged.connect(self.search_variables)
        self.ui.cerate_file_button.clicked.connect(self.create_new_file)
        self.ui.compile_all_button.clicked.connect(self.compile_all)
        self.ui.new_file_options_button.clicked.connect(self.new_file_options)
        self.ui.all_to_vdata_button.clicked.connect(self.convert_all_to_vdata)


    def new_file_options(self):
        new_file_dialog = NewFileOptions(self)
        new_file_dialog.show()

    def properties_groups_init(self):
        self.modifiers_group_instance = PropertiesGroupFrame(widget_list=self.ui.properties_layout, name=str('Modifiers'))
        self.ui.properties_layout.insertWidget(0, self.modifiers_group_instance)
        self.modifiers_group_instance.add_signal.connect(self.add_an_operator)
        self.modifiers_group_instance.paste_signal.connect(self.paste_operator)


        self.selection_criteria_group_instance = PropertiesGroupFrame(widget_list=self.ui.properties_layout, name=str('Section criteria'))
        self.selection_criteria_group_instance.add_signal.connect(self.add_a_selection_criteria)
        self.ui.properties_layout.insertWidget(1, self.selection_criteria_group_instance)
        self.selection_criteria_group_instance.paste_signal.connect(self.paste_selection_criteria)

    def on_tree_current_item_changed(self, item):
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
                    property_instance = PropertyFrame(widget_list=self.ui.properties_layout, value=item, variables_scrollArea=self.ui.variables_scrollArea)
                    property_instance.edited.connect(self.update_tree_item_value)
                    self.modifiers_group_instance.layout.insertWidget(0, property_instance)
            if data_sel_criteria:
                for item in reversed(data_sel_criteria):
                    property_instance = PropertyFrame(widget_list=self.ui.properties_layout, value=item, variables_scrollArea=self.ui.variables_scrollArea)
                    property_instance.edited.connect(self.update_tree_item_value)
                    self.selection_criteria_group_instance.layout.insertWidget(0, property_instance)
        except Exception as error:
            print(error)
    def update_tree_item_value(self):
        if self.ui.tree_hierarchy_widget.currentItem():
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
            output_value.update({'m_Modifiers': modifiers})
            output_value.update({'m_SelectionCriteria': selection_criteria})
            self.ui.tree_hierarchy_widget.currentItem().setText(1, str(output_value))
            print(output_value)

    # Create New elemnt
    def keyPressEvent(self, event):

        # Update focus widget at mouse position
        cursor_pos = QCursor.pos()
        widget_under_cursor = QApplication.widgetAt(cursor_pos)
        if widget_under_cursor:
            widget_under_cursor.setFocus()

        focus_widget = QApplication.focusWidget()

        if focus_widget is self.ui.tree_hierarchy_widget:
            if focus_widget.viewport().underMouse():
                if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                    self.add_an_element()

                    event.accept()
        if focus_widget is self.modifiers_group_instance.ui.property_class:
            if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                self.add_an_operator()
                event.accept()
        if focus_widget is self.selection_criteria_group_instance.ui.property_class:
            if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                self.add_a_selection_criteria()
                event.accept()
    def add_an_element(self):
        self.popup_menu = PopupMenu(elements_list, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_element(name, value))
        self.popup_menu.show()
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

    def new_element(self, element_class, element_value):
        name = element_class
        new_element = QTreeWidgetItem()
        new_element.setFlags(new_element.flags() | Qt.ItemIsEditable)
        new_element.setText(0, name)
        new_element.setText(1, str(element_value))
        if self.ui.tree_hierarchy_widget.currentItem() == None:
            parent = self.ui.tree_hierarchy_widget.invisibleRootItem()
        else:
            parent = self.ui.tree_hierarchy_widget.currentItem()
        parent.addChild(new_element)
    def new_operator(self, element_class, element_value):
        operator_instance = PropertyFrame(widget_list=self.modifiers_group_instance.layout, value=element_value, variables_scrollArea=self.ui.variables_scrollArea)
        operator_instance.edited.connect(self.update_tree_item_value)
        self.modifiers_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()

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

    def new_selection_criteria(self, element_class, element_value):
        operator_instance = PropertyFrame(widget_list=self.selection_criteria_group_instance.layout, value=element_value, variables_scrollArea=self.ui.variables_scrollArea)
        operator_instance.edited.connect(self.update_tree_item_value)
        self.selection_criteria_group_instance.layout.insertWidget(1, operator_instance)
        self.update_tree_item_value()


    # Vsmart format
    def reportProgress(self, n, progress_dialog, file):
        progress_dialog.setValue(n)
        progress_dialog.setLabelText(f'Compiling: {file}')

    def compile_all(self):
        reply = QMessageBox.question(self, 'Confirmation','Are you sure you want to compile? The current file will be closed. Proceed?',QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            total_files = []

            for root, dirs, files in os.walk(self.tree_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_files.append(file_path)


            progress = 0
            progress_dialog = QProgressDialog('Compiling...', 'Cancel', 0, len(total_files), self)
            progress_dialog.setValue(progress)
            progress += 1

            progress_dialog.show()
            self.thread = QThread( )
            self.worker = CompileAll()


            self.worker.moveToThread(self.thread)

            self.thread.started.connect(lambda: self.worker.run(total_files=total_files))
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.worker.progress.connect(lambda n, file: self.reportProgress(n, progress_dialog, file))

            self.thread.start()


    def convert_all_to_vdata(self):
        reply = QMessageBox.question(self, 'Confirmation', 'Are you sure you want to convert all vsmart files in the addon to vdata? Proceed?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            for root, dirs, files, in os.walk(self.tree_directory):
                for file in files:
                    file = os.path.join(root,file)
                    print(file)
                    filename = os.path.splitext(file)[0]
                    extension= os.path.splitext(file)[1]
                    if extension == '.vsmart':
                        dist_name = filename + '.vdata'
                        shutil.move(file, dist_name)
                        print(f'Converted: {os.path.basename(file)} to vdata')

    def create_new_file(self):
        extension = get_config_value('SmartpropEditor', 'Extension')
        if extension:
            pass
        else:
            extension = 'vdata'
        from smartprop_editor.blank_vsmart import blank_vsmart
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
    def open_file(self, filename=None):
        global opened_file
        if filename == None:
            index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
            filename = self.mini_explorer.model.filePath(index)
            print(filename)
        opened_file = filename

        if filename.endswith('.vsmart'):
            show = settings.value("SmartPropEditor/ShowCompilationMessage")
            if show == None:
                show = True
            if show:
                # Create a QMessageBox dialog
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Smartprops Format Warning")
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText(
                    """Smartprops in the vsmart format cannot be compiled using the default launch options. To compile smartprops in this format, please run the application in NCM mode. If you convert vsmart to vdata, you can compile the smartprops without NCM mode by using the small button in the explorer window. However, if you have already compiled vsmart files in NCM mode, you will need to delete all compiled vsmart files and restart the application before proceeding.""")

                # Add a checkbox for the 'Do not show again' option
                do_not_show_checkbox = QCheckBox("Do not show this message again")
                msg_box.setCheckBox(do_not_show_checkbox)

                result = msg_box.exec_()
                if result == QMessageBox.Ok:
                    settings.setValue("SmartPropEditor/ShowCompilationMessage", not do_not_show_checkbox.isChecked())

        # VsmartOpen(filename=filename, tree=self.ui.tree_hierarchy_widget)
        # variables = VsmartOpen(filename=filename, tree=self.ui.tree_hierarchy_widget).variables

        vsmart_instance = VsmartOpen(filename=filename, tree=self.ui.tree_hierarchy_widget)
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
                var_visible_in_editor = bool(item.get('m_bExposeAsParameter', None))

                var_value = {
                    'default': item.get('m_DefaultValue', None),
                    'model': item.get('m_sModelName', None)
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
    def save_file(self):
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
                print('var min', type(var_min), var_min)

                # Basic
                var_dict = {
                    '_class': variable_prefix+var_class,
                    'm_VariableName': var_key_value[0],
                    'm_bExposeAsParameter':  var_key_value[3],
                    'm_DefaultValue': var_default
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
        # index = self.mini_explorer.tree.selectionModel().selectedIndexes()[0]
        filename = opened_file
        var_data = save_variables()
        print(var_data)
        print(filename)
        VsmartSave(filename=filename, tree=self.ui.tree_hierarchy_widget, var_data=var_data)
        VsmartCompile(filename=filename)

    # variables

    def search_variables(self, search_term=None):
        for i in range(self.ui.variables_scrollArea.layout().count()):
            widget = self.ui.variables_scrollArea.layout().itemAt(i).widget()
            if widget:
                if search_term.lower() in widget.name.lower():  # Adjust the search logic as needed
                    widget.show()
                else:
                    widget.hide()

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

    def add_variable(self, name, var_class, var_value, var_visible_in_editor, var_display_name):
        variable = VariableFrame(name=name, widget_list=self.ui.variables_scrollArea, var_value=var_value, var_class=var_class, var_visible_in_editor=var_visible_in_editor, var_display_name=var_display_name)
        index = (self.ui.variables_scrollArea.count()) - 1
        self.ui.variables_scrollArea.insertWidget(index, variable)

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

    # ContextMenu
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
            self.add_variable(clipboard_data[1], clipboard_data[2], ast.literal_eval(clipboard_data[3]), visible_in_editor, clipboard_data[4])
        else:
            print("Clipboard data format is not valid.")


    def open_hierarchy_menu(self, position):
        menu = QMenu()
        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")
        remove_action = menu.addAction("Remove")

        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self.duplicate_item(self.ui.tree_hierarchy_widget.itemAt(position), self.ui.tree_hierarchy_widget))

        move_up_action.triggered.connect(lambda: self.move_item(self.ui.tree_hierarchy_widget.itemAt(position), -1))
        move_down_action.triggered.connect(lambda: self.move_item(self.ui.tree_hierarchy_widget.itemAt(position), 1))
        remove_action.triggered.connect(lambda: self.remove_item(self.ui.tree_hierarchy_widget.itemAt(position)))

        copy_action = menu.addAction("Copy")
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(lambda: self.copy_item(self.ui.tree_hierarchy_widget.itemAt(position)))

        paste_action = menu.addAction("Paste")
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(lambda: self.paste_item(self.ui.tree_hierarchy_widget.itemAt(position)))

        menu.exec(self.ui.tree_hierarchy_widget.viewport().mapToGlobal(position))

    def copy_item(self, tree_item):
        text_data = []
        text_data.append(tree_item.text(0))
        text_data.append(tree_item.text(1))

        clipboard = QApplication.clipboard()
        clipboard.setText(','.join(text_data))

    def paste_item(self, position):

        clipboard = QApplication.clipboard()
        text_data = clipboard.text().split(',')
        if text_data[1] == '':
            pass
        else:
            tree_item = QTreeWidgetItem()

            if len(text_data) >= 2:
                tree_item.setText(0, text_data[0] + '_pasted')
                tree_item.setText(1, text_data[1])

            try:
                self.ui.tree_hierarchy_widget.currentItem().addChild(tree_item)
            except:
                self.ui.tree_hierarchy_widget.invisibleRootItem().addChild(tree_item)
    def open_properties_menu(self, position):
        item = self.ui.properties_tree.itemAt(position)
        if item and item.parent():  # Check if the item has a parent (not a top-level item)
            menu = QMenu()
            remove_action = menu.addAction("Remove")
            # duplicate_action = menu.addAction("Duplicate")

            # duplicate_action.triggered.connect(lambda: self.duplicate_item(item, self.ui.properties_tree))
            remove_action.triggered.connect(lambda: self.remove_item(item))

            menu.exec(self.ui.properties_tree.viewport().mapToGlobal(position))
    def move_item(self, item, direction):
        if not item:
            return
        parent = item.parent() or self.ui.tree_hierarchy_widget.invisibleRootItem()
        index = parent.indexOfChild(item)
        new_index = index + direction

        if 0 <= new_index < parent.childCount():
            parent.takeChild(index)
            parent.insertChild(new_index, item)


    def duplicate_item(self, item: QTreeWidgetItem, tree):
        parent = item.parent() or tree.invisibleRootItem()
        existing_names = [parent.child(i).text(0) for i in range(parent.childCount())]

        base_text = item.text(0)
        counter = 0
        new_text = base_text

        # Check if the element name has digits at the end
        if base_text[-1].isdigit():
            counter = int(base_text.split('_')[-1]) + 1
            new_text = f"{base_text.rsplit('_', 1)[0]}_{counter:02}"
        else:
            while new_text in existing_names:
                counter += 1
                new_text = f"{base_text}_{counter:02}"  # Change the format to include leading zeros

        new_item = QTreeWidgetItem([new_text, item.text(1)])  # Duplicate the second column as well
        new_item.setFlags(new_item.flags() | Qt.ItemIsEditable)
        parent.addChild(new_item)

        # Recursively duplicate children
        self.duplicate_children(item, new_item)

    def duplicate_children(self, source_item, target_item):
        for i in range(source_item.childCount()):
            child = source_item.child(i)
            new_child = QTreeWidgetItem([child.text(0), child.text(1)])  # Duplicate the second column as well
            new_child.setFlags(new_child.flags() | Qt.ItemIsEditable)
            target_item.addChild(new_child)
            self.duplicate_children(child, new_child)

    def remove_item(self, item):
        if item:
            parent = item.parent() or self.ui.tree_hierarchy_widget.invisibleRootItem()
            index = parent.indexOfChild(item)
            parent.takeChild(index)

    # Prefs
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
