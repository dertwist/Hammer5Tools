from PySide6.QtWidgets import QComboBox, QWidget, QHBoxLayout, QSpacerItem, QSizePolicy, QDialog, QVBoxLayout, QLineEdit, QPushButton, QCheckBox, QMessageBox
from PySide6.QtCore import Signal, Qt
import re

from src.widgets.popup_menu.main import PopupMenu
from src.widgets.common import Button, apply_stylesheets
from src.widgets import ComboboxDynamicItems


class ComboboxVariables(ComboboxDynamicItems):
    changed = Signal(dict)
    def __init__(self, parent=None, layout=None,filter_types=None):
        """Getting variables and put them into combobox"""
        super().__init__(parent)
        self.variables_scrollArea = layout
        self.items = None
        self.filter_types = filter_types
        self.currentTextChanged.connect(self.changed_var)

    def updateItems(self):
        """Updating widget items on click. Filter items depends on their type if you need"""
        self.currentTextChanged.disconnect(self.changed_var)
        self.items = []
        self.items.append('None')
        variables = self.get_variables()
        for item in variables:
            if self.filter_types is not None:
                if item['class'] in self.filter_types:
                    self.items.append(item['name'])
            else:
                self.items.append(item['name'])
        current = self.currentText()
        self.clear()
        self.addItems(self.items)
        if current in self.items:
            self.setCurrentText(current)
        self.currentTextChanged.connect(self.changed_var),
    def changed_var(self):
        if self.currentIndex() == 0:
            self.changed.emit({'name': None, 'class': None, 'm_default': None})
        else:
            for item in self.get_variables():
                if item['name'] == self.currentText():
                    self.changed.emit({'name': item['name'], 'class': item['class'], 'm_default': item['m_default']})
                    break
    def get_variables(self):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                var = {'name': widget.name, 'class': widget.var_class, 'm_default': widget.var_value['default']}
                data_out.append(var)
        return data_out
    def set_variable(self, value):
        self.updateItems()
        if value == "" or value is None:
            self.setCurrentIndex(0)
        else:
            self.addItem(value)
            self.setCurrentText(value)
    def get_variable(self):
        if self.currentText() == "None":
            return ''
        else:
            return self.currentText()
class ComboboxVariablesWidget(QWidget):
    def __init__(self, element_id_generator, parent=None, variables_layout=None, filter_types: list = None, variable_type: str = None, variable_name: str = None):
        """Combobox variables widget with search and add buttons.
           It dynamically shows or hides the add button and supports creating new variables via a non-modal dialog.
        """
        super().__init__(parent)
        layout_widget = QHBoxLayout(self)
        layout_widget.setContentsMargins(0, 0, 0, 0)
        self.element_id_generator = element_id_generator
        if variable_name is None:
            self.variable_name = "new_var"
        else:
            self.variable_name = variable_name
            self.variable_name = self.variable_name.replace('m_v', '')
            self.variable_name = self.variable_name.replace('m_fl', '')
            self.variable_name = self.variable_name.replace('m_s', '')
            self.variable_name = self.variable_name.replace('m_n', '')
            self.variable_name = self.variable_name.replace('m_b', '')
            self.variable_name = self.variable_name.replace('m_', '')
        self.variable_type = variable_type if variable_type is not None else (
            filter_types[0] if isinstance(filter_types, list) and filter_types else 'String')
        self.variables_layout = variables_layout

        self.filter_types = filter_types  # Optional filter list for variable types.
        self.variable_type = variable_type if variable_type is not None else (
            filter_types[0] if isinstance(filter_types, list) and filter_types else 'String')
        self.variables_layout = variables_layout

        # Initialize internal combobox using internal organization widget.
        self.combobox = ComboboxVariables(parent=self, layout=variables_layout, filter_types=filter_types)
        layout_widget.addWidget(self.combobox)

        # Add new variable button.
        self.add_new_variable_button = Button()
        self.add_new_variable_button.set_icon_add()
        self.add_new_variable_button.set_size(width=24)
        self.add_new_variable_button.clicked.connect(self.add_new_variable_and_set)
        layout_widget.addWidget(self.add_new_variable_button)

        # Search button.
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.set_size(width=24)
        self.search_button.clicked.connect(self.call_search_popup_menu)
        layout_widget.addWidget(self.search_button)

        # Set initial visibility of add button.
        self.update_add_button_visibility(self.combobox.currentText())
        self.combobox.currentTextChanged.connect(self.update_add_button_visibility)

    def update_add_button_visibility(self, value):
        """Show the add button if value is blank; otherwise, hide it."""
        if value in ("", None, "None"):
            self.add_new_variable_button.show()
        else:
            self.add_new_variable_button.hide()

    def add_variable(self, name, var_class, var_value, var_visible_in_editor, var_display_name, index: int = None):
        """Create a variable widget and add it to the variables layout."""
        from src.editors.smartprop_editor.variable_frame import VariableFrame
        self.element_id_generator.update_value(var_value, force=True)
        variable = VariableFrame(
            name=name,
            widget_list=self.variables_layout,
            var_value=var_value,
            var_class=var_class,
            var_visible_in_editor=var_visible_in_editor,
            var_display_name=var_display_name,
            element_id_generator=self.element_id_generator
        )
        variable.duplicate.connect(self.duplicate_variable)
        if index is None:
            index = self.variables_layout.count() - 1
        else:
            index += 1  # Insert after current index.
        self.variables_layout.insertWidget(index, variable)

    def duplicate_variable(self, data, index):
        """Duplicate the variable by reusing its properties."""
        self.element_id_generator.update_value(data, force=True)
        self.add_variable(
            name=data[0],
            var_class=data[1],
            var_value=data[2],
            var_visible_in_editor=data[3],
            var_display_name=data[4],
            index=index
        )

    def add_new_variable_and_set(self):
        """Initiate the new variable creation dialog. Use the dialog function before calling new_variable."""
        self.show_new_variable_dialog()

    def show_new_variable_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Variable")
        dialog.setModal(False)  # Non-modal dialog.
        dialog.setWindowFlags(Qt.Window)
        dialog.setFixedSize(400, 140)

        # Define local UI variables.
        name_edit = QLineEdit(dialog)
        name_edit.setPlaceholderText("Enter variable name")
        name_edit.setText(self.variable_name)

        type_combo = QComboBox(dialog)
        type_combo.setFixedHeight(28)
        # Populate the combobox using filter_types if provided, else use the full list from variables_list.
        from src.editors.smartprop_editor.objects import variables_list
        local_types = self.filter_types if self.filter_types is not None else variables_list
        type_combo.addItems(local_types)
        if self.variable_type in local_types:
            type_combo.setCurrentText(self.variable_type)

        show_all_chk = QCheckBox("Show all variable types", dialog)
        show_all_chk.setFixedHeight(28)
        def update_type_combo(state):
            type_combo.clear()
            if show_all_chk.isChecked():
                type_combo.addItems(variables_list)
            else:
                type_combo.addItems(self.filter_types if self.filter_types is not None else variables_list)
        show_all_chk.stateChanged.connect(update_type_combo)

        cancel_button = QPushButton("Cancel", dialog)
        create_button = QPushButton("Create", dialog)

        # Layout for the dialog organization.
        main_layout = QVBoxLayout(dialog)
        main_layout.addWidget(name_edit)
        type_layout = QHBoxLayout()
        type_layout.addWidget(type_combo)
        type_layout.addWidget(show_all_chk)
        main_layout.addLayout(type_layout)
        button_layout = QHBoxLayout()
        button_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(create_button)
        main_layout.addLayout(button_layout)

        cancel_button.clicked.connect(dialog.reject)

        def on_create():
            new_name_local = name_edit.text().strip()
            # Validate variable name:
            # 1. All characters must be in ASCII range (0-255).
            # 2. Must contain at least one letter or digit.
            if not all(ord(c) < 256 for c in new_name_local) or not re.search(r'[A-Za-z0-9]', new_name_local):
                QMessageBox.warning(dialog, "Invalid Variable Name",
                                    "Variable name must consist of only ASCII characters (0-255) and contain at least one letter or number.",
                                    QMessageBox.Ok)
                name_edit.setFocus()
                return

            if not new_name_local:
                name_edit.setFocus()
                return
            selected_type = type_combo.currentText()
            final_name_local = self.new_variable(new_name_local, selected_type)
            self.combobox.set_variable(final_name_local)
            dialog.accept()
        create_button.clicked.connect(on_create)
        apply_stylesheets(dialog)
        dialog.show()

    def new_variable(self, name, var_type):
        base_name = name
        existing_names = self.get_all_variables()
        final_name = base_name
        if final_name in existing_names:
            suffix = 1
            while f"{base_name}_{suffix}" in existing_names:
                suffix += 1
            final_name = f"{base_name}_{suffix}"
        var_display_name = ''
        var_visible_in_editor = False
        var_value = {
            'default': None,
            'min': None,
            'max': None,
            'model': None,
            'm_nElementID': None,
        }
        # Always assign a new unique element ID to avoid duplication
        from src.widgets.element_id import set_ElementID
        var_value['m_nElementID'] = set_ElementID(force=True)
        self.add_variable(
            name=final_name,
            var_class=var_type,
            var_value=var_value,
            var_visible_in_editor=var_visible_in_editor,
            var_display_name=var_display_name
        )
        return final_name

    def get_all_variables(self):
        """Return a list of all variable names from the variables layout."""
        names = []
        for i in range(self.variables_layout.count()):
            widget = self.variables_layout.itemAt(i).widget()
            if widget:
                names.append(widget.name)
        return names

    def get_variables(self):
        """Retrieve variable properties in a format used for the popup menu."""
        elements = []
        variables = self.combobox.get_variables()
        for item in variables:
            if self.filter_types is not None:
                if item['class'] in self.filter_types:
                    elements.append({item['name']: item['name']})
            else:
                elements.append({item['name']: item['name']})
        return elements

    def call_search_popup_menu(self):
        """Display the search popup menu to select variables."""
        elements = self.get_variables()
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.combobox.set_variable(value))
        self.popup_menu.show()