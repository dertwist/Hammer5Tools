import ast

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel, QLineEdit, QCheckBox, QVBoxLayout, QToolBox, QToolButton, QGroupBox, QButtonGroup
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon, QColor, QFont
import sys, webbrowser
from src.qt_styles.common import *
from PySide6.QtWidgets import QMessageBox, QFileDialog
from PySide6.QtGui import QIcon
import webbrowser
from src.common import discord_feedback_channel
from src.popup_menu.popup_menu_main import PopupMenu
from src.preferences import get_config_bool, set_config_bool
from src.widgets_common import *
from logging import error
import traceback, ctypes
from src.common import enable_dark_title_bar
from src.smartprop_editor.variable_frame import VariableFrame
import winsound
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QHBoxLayout,
    QMessageBox
)

#============================================================<  Generic widgets  >==========================================================
class Spacer(QWidget):
    def __init__(self):
        """Spacer widget, can be hidden or shown"""
        super().__init__()

        spacer_layout = QHBoxLayout()
        spacer_layout.setContentsMargins(0,0,0,0)
        spacer_item = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        spacer_layout.addSpacerItem(spacer_item)
        self.setLayout(spacer_layout)
        self.setStyleSheet('border:None;')
        self.setContentsMargins(0,0,0,0)
class ErrorInfo(QDialog):
    def __init__(self, text="Error", details=""):
        super().__init__()
        self.setWindowTitle("Error")
        self.setWindowIcon(QIcon("appicon.ico"))
        enable_dark_title_bar(self)
        self.setMinimumSize(600, 400)
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.details = details
        winsound.MessageBeep(winsound.MB_ICONHAND)
        # Main layout
        main_layout = QVBoxLayout(self)

        # Error message label
        self.message_label = QLabel(text)
        self.message_label.setWordWrap(True)
        main_layout.addWidget(self.message_label)

        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlainText(self.details)
        self.details_text.setStyleSheet("background-color: #1C1C1C; border-color: #974533")
        main_layout.addWidget(self.details_text)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        # Save Details button
        self.save_button = QPushButton("Save Details")
        self.save_button.clicked.connect(self.save_details)
        buttons_layout.addWidget(self.save_button)

        # Report button
        self.report_button = QPushButton("Report")
        self.report_button.clicked.connect(self.report_issue)
        buttons_layout.addWidget(self.report_button)

        # Spacer to push Close button to the right
        buttons_layout.addStretch()

        # Close button
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)

        main_layout.addLayout(buttons_layout)

    def save_details(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Error Details",
            "error_details.txt",
            "Text Files (*.txt);;All Files (*)",
            options=options
        )
        if filename:
            try:
                with open(filename, 'w') as file:
                    file.write(self.details)
            except Exception as e:
                error_dialog = QMessageBox(self)
                error_dialog.setWindowTitle("Save Error")
                error_dialog.setText(f"An error occurred while saving the file:\n{e}")
                error_dialog.setIcon(QMessageBox.Critical)
                error_dialog.exec_()

    def report_issue(self):
        webbrowser.open(discord_feedback_channel)
        # Close the dialog after reporting the issue
        self.close()

def exception_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_message = f"An error occurred in `{func.__name__}`: {e}"
            error_details = traceback.format_exc()
            error(error_message)
            ErrorInfo(text=error_message, details=error_details).exec_()
    return wrapper
#============================================================<  Property widgets  >=========================================================
class FloatWidget(QWidget):
    edited = Signal(float)
    def __init__(self, int_output: bool =False, slider_range: list = [0,0], value: float=0.0, only_positive: bool = False, lock_range: bool = False, spacer_enable: bool = True):
        """Float widget is a widget with sping box and slider that are synchronized with each-other. This widget give float or round(float) which is int variable type"""
        super().__init__()

        # Variables
        self.int_output = int_output
        self.value = value
        self.only_positive = only_positive

        # SpinnBox setup
        self.SpinBox = QDoubleSpinBox()
        if self.only_positive:
            self.SpinBox.setMinimum(0)
        else:
            self.SpinBox.setMinimum(-99999999)
        self.SpinBox.setMaximum(99999999)
        self.SpinBox.setValue(value)

        # Slider setup
        self.Slider = QSlider()
        self.Slider.setOrientation(Qt.Horizontal)
        # Range
        if slider_range[0] == 0 and slider_range[1] == 0:
            value = self.SpinBox.value()
            self.Slider.setMaximum(abs(value) * 10 * 100 +1000)
            if only_positive:
                self.Slider.setMinimum(0)
            else:
                self.Slider.setMinimum(-abs(value) * 10 * 100 -1000)
        else:
            if only_positive:
                self.Slider.setMinimum(0)
            else:
                self.Slider.setMinimum(slider_range[0]*100)
            self.Slider.setMaximum(slider_range[1]*100)
        self.Slider.valueChanged.connect(self.on_Slider_updated)

        # Layout setup
        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.SpinBox)
        layout.addWidget(self.Slider)
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        if spacer_enable:
            layout.addItem(spacer)
        self.setLayout(layout)
        self.on_SpinBox_updated()
        self.SpinBox.valueChanged.connect(self.on_SpinBox_updated)
        # Widget class
    # Colors
    def set_color(self, color):
        self.SpinBox.setStyleSheet(f"color: {color};")

    # Updating
    def on_SpinBox_updated(self):
        value = self.SpinBox.value()
        if self.int_output:
            value = round(value)
        if value > self.Slider.maximum()/100 or value < self.Slider.minimum()/100:
            if self.only_positive:
                self.Slider.setMinimum(0)
            else:
                self.Slider.setMinimum(-abs(value) * 10 * 100 - 1000)
            self.Slider.setMaximum(abs(value) * 10 * 100 + 1000)
        self.Slider.setValue(value*100)
        self.value = value
        self.edited.emit(value)
    def on_Slider_updated(self):
        value = self.Slider.value() / 100
        if self.int_output:
            value = round(value)
        self.SpinBox.setValue(value)
        self.value = value
        self.edited.emit(value)
    def set_value(self, value):
        self.SpinBox.setValue(value)
        self.on_SpinBox_updated()

class LegacyWidget(QWidget):
    edited = Signal(str)

    def __init__(self, value: str = None, spacer_enable: bool = True):
        """Initialize the LegacyWidget with a given value."""
        super().__init__()
        self.isdict = False

        # Edit line initialization
        self.edit_line = QLineEdit()
        self.edit_line.textChanged.connect(self.on_editline_updated)

        # Layout initialization
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.edit_line)
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        if spacer_enable:
            layout.addItem(spacer)
        self.setLayout(layout)

        # Set initial value
        self.set_value(value)

    def on_editline_updated(self):
        """Handle updates to the edit line."""
        value = self.edit_line.text()
        try:
            value = ast.literal_eval(value)
        except:
            pass
        self.edited.emit(value)

    def set_value(self, value):
        """Set the value of the edit line."""
        if isinstance(value, dict):
            self.isdict = True
            self.edit_line.setText(str(value))
        elif isinstance(value, str):
            self.isdict = False
            self.edit_line.setText(value)
        else:
            # raise ValueError("Value must be a string or a dictionary.")
            self.isdict = False
            self.edit_line.setText(str(value))

class BoolWidget(QWidget):
    edited = Signal(bool)

    def __init__(self, value: bool = None, spacer_enable: bool = True):
        """Initialize the LegacyWidget with a given value."""
        super().__init__()

        # Init checkbox
        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self.on_updated)
        self.checkbox.setStyleSheet(qt_stylesheet_checkbox)
        self.checkbox.setMinimumWidth(72)
        # Layout initialization
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.checkbox)
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        if spacer_enable:
            layout.addItem(spacer)
        self.setLayout(layout)

        # Set initial value
        self.set_value(value)

    def on_updated(self):
        """Handle updates to the edit line."""
        value = self.checkbox.isChecked()
        # Updating text in the checkbox
        self.set_value(value)
        self.edited.emit(value)

    def set_value(self, value):
        """Set value as text for checkbox"""
        self.checkbox.setChecked(value)
        self.checkbox.setText(str(value))
#================================================================<  Combobox  >=============================================================
class ComboboxDynamicItems(QComboBox):
    clicked = Signal()

    def __init__(self, parent=None, items: list =None, use_search:bool = False):
        """Combobox that updates it's items when user clicked on it"""
        super().__init__(parent)
        # self.setStyleSheet('padding:2px; font: 580 9pt "Segoe UI"; padding-left:4px;')
        self.setStyleSheet(qt_stylesheet_combobox)
        self.items = items if items is not None else []

    def updateItems(self):
        current = self.currentText()
        self.clear()
        self.addItems(self.items)
        if current in self.items:
            self.setCurrentText(current)

    def showPopup(self):
        self.clicked.emit()
        self.updateItems()
        super().showPopup()


    def wheelEvent(self, event):
        event.ignore()

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
    def __init__(self, parent=None, variables_layout=None, filter_types=None, variable_type=None):
        """Combobox variables widget with search and add buttons that dynamically show or hide the add button."""
        super().__init__(parent)

        # Set up the main layout for the widget
        layout_widget = QHBoxLayout(self)
        layout_widget.setContentsMargins(0, 0, 0, 0)

        self.filter_types = filter_types
        self.variable_type = variable_type
        self.variables_layout = variables_layout

        # Initialize the combobox for variables
        self.combobox = ComboboxVariables(parent=self, layout=variables_layout, filter_types=filter_types)
        layout_widget.addWidget(self.combobox)

        # Initialize the add new variable button
        self.add_new_variable_button = Button()
        self.add_new_variable_button.set_icon_add()
        self.add_new_variable_button.set_size(width=24)
        self.add_new_variable_button.clicked.connect(self.add_new_variable_and_set)
        layout_widget.addWidget(self.add_new_variable_button)

        # Initialize the search button
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.set_size(width=24)
        self.search_button.clicked.connect(self.call_search_popup_menu)
        layout_widget.addWidget(self.search_button)


        # Set the initial visibility of the add button
        self.update_add_button_visibility(self.combobox.currentText())

        # Connect the combobox text change signal to update the add button visibility
        self.combobox.currentTextChanged.connect(self.update_add_button_visibility)

        if variable_type is None:
            self.variable_type = filter_types[0]

    def update_add_button_visibility(self, value):
        """Show the add button if value is None or empty, otherwise hide it."""
        if value == "" or value is None or value == 'None':
            self.add_new_variable_button.show()
        else:
            self.add_new_variable_button.hide()

    def add_variable(self, name, var_class, var_value, var_visible_in_editor, var_display_name, index: int = None):
        variable = VariableFrame(
            name=name,
            widget_list=self.variables_layout,
            var_value=var_value,
            var_class=var_class,
            var_visible_in_editor=var_visible_in_editor,
            var_display_name=var_display_name
        )
        variable.duplicate.connect(self.duplicate_variable)
        if index is None:
            index = self.variables_layout.count() - 1
        else:
            index += 1  # Insert after current index when duplicating
        self.variables_layout.insertWidget(index, variable)

    def duplicate_variable(self, data, index):
        self.add_variable(
            name=data[0],
            var_class=data[1],
            var_value=data[2],
            var_visible_in_editor=data[3],
            var_display_name=data[4],
            index=index
        )
    def add_new_variable_and_set(self):
        name = self.new_variable()
        self.combobox.set_variable(name)
    def new_variable(self):
        base_name = 'new_var'
        existing_variable_names = self.get_all_variables()
        print(existing_variable_names)

        # Generate a unique variable name
        name = base_name
        if name in existing_variable_names:
            suffix = 1
            while f"{base_name}_{suffix}" in existing_variable_names:
                suffix += 1
            name = f"{base_name}_{suffix}"

        var_class = self.variable_type  # Ensure 'variable_type' is defined
        var_display_name = ''
        var_visible_in_editor = False
        var_value = {
            'default': None,
            'min': None,
            'max': None,
            'model': None
        }
        self.add_variable(
            name=name,
            var_class=var_class,
            var_value=var_value,
            var_visible_in_editor=var_visible_in_editor,
            var_display_name=var_display_name
        )
        return name

    def get_all_variables(self):
        data_out = []
        for i in range(self.variables_layout.count()):
            widget = self.variables_layout.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

    def get_variables(self):
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
        elements = self.get_variables()
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.combobox.set_variable(value))
        self.popup_menu.show()
class ComboboxTreeChild(ComboboxDynamicItems):
    """Shows a tree child as items """
    def __init__(self, parent=None, layout=QTreeWidget, root=QTreeWidgetItem):
        super().__init__(parent)
        self.layout = layout
        self.root = root
        self.items = None

    def updateItems(self):
        self.items = self.get_child(self.root)
        current = self.currentText()
        self.clear()
        self.addItems(self.items)
        if current in self.items:
            self.setCurrentText(current)

    def get_child(self, parent_item):
        data_out = []
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            data_out.append(child_item.text(0))

        return data_out


#================================================================<  generic  >==============================================================






#==============================================================<  Tree widgets  >===========================================================

class HierarchyItemModel(QTreeWidgetItem):
    def __init__(self, _name="New Hierarchy Item", _data=None, _class=None, _id=None, parent=None):
        super().__init__(parent)

        # Set text for name, data, class, and id
        self.setText(0, str(_name))
        if _data is not None:
            self.setText(1, str(_data))
        if _class is not None:
            self.setText(2, str(_class))
        if _id is not None:
            self.setText(3, str(_id))

        # Initially set editable flags only on the first column
        self.setFlags(self.flags() | Qt.ItemIsEditable)

        # Set up custom colors and font for specific columns
        self.custom_colors = {
            2: QColor("#9D9D9D"),
            3: QColor("#9D9D9D"),
        }
        self.background_colors = {
            0: QColor("#f0f0f0"),  # Light grey background in column 0
        }
        self.custom_font = QFont("Segoe UI", 10, QFont.DemiBold)

    def data(self, column, role):
        if role == Qt.ForegroundRole and column in self.custom_colors:
            # Set text color for specific columns
            return self.custom_colors[column]

        if role == Qt.BackgroundRole and column in self.background_colors:
            # Set background color for specific columns
            return self.background_colors[column]

        if role == Qt.FontRole and column == 0:
            # Set custom font for column 0
            return self.custom_font

        return super().data(column, role)

    def set_editable(self, editable):
        """Set the item editable flag based on `editable` boolean."""
        if editable:
            self.setFlags(self.flags() | Qt.ItemIsEditable)
        else:
            self.setFlags(self.flags() & ~Qt.ItemIsEditable)


def on_three_hierarchyitem_clicked(item, column):
    """Set item as editable if clicked on the first column; otherwise, make it non-editable."""
    if column == 0:
        item.set_editable(True)
    else:
        item.set_editable(False)

#
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#
#     import qtvscodestyle as qtvsc
#
#     stylesheet = qtvsc.load_stylesheet(qtvsc.Theme.DARK_VS)
#     app.setStyleSheet(stylesheet)
#     ErrorInfo('Testhgkhkljhklhklj asf asf asf asf asdf asdf asf asdf ', 'dfaasd').exec()
#     sys.exit(app.exec())
