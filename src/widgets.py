from src.popup_menu.popup_menu_main import PopupMenu
from src.smartprop_editor.variable_frame import VariableFrame
from PySide6.QtCore import QTimer
from src.widgets_common import *
from PySide6.QtWidgets import (
    QWidget,
    QDoubleSpinBox,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
)
from PySide6.QtGui import QPainter, QPen, QColor, QDoubleValidator, QFocusEvent
from PySide6.QtCore import Qt, QRect, QEvent, Signal
import math


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
#============================================================<  Property widgets  >=========================================================

class FloatWidget(QWidget):
    edited = Signal(float)

    def __init__(self, int_output: bool = False, slider_range: list = [0, 0], value: float = 0.0, only_positive: bool = False, lock_range: bool = False, spacer_enable: bool = True, vertical: bool = False, digits: int = 3, value_step: float = 1, slider_scale: int = 5):
        """Float widget is a widget with spin box and slider that are synchronized with each other. This widget gives float or round(float) which is int variable type."""
        super().__init__()

        # Variables
        self.int_output = int_output
        self.value = value
        self.only_positive = only_positive
        self.slider_scale = slider_scale

        # SpinBox setup
        self.SpinBox = QDoubleSpinBox()
        self.SpinBox.setDecimals(digits)
        self.SpinBox.setSingleStep(value_step)
        if self.only_positive:
            self.SpinBox.setMinimum(0)
        else:
            self.SpinBox.setMinimum(-99999999)
        self.SpinBox.setMaximum(99999999)
        self.SpinBox.setValue(value)

        # Slider setup
        self.Slider = QSlider()
        self.Slider.setOrientation(Qt.Vertical if vertical else Qt.Horizontal)
        # Range
        if slider_range[0] == 0 and slider_range[1] == 0:
            value = self.SpinBox.value()
            self.Slider.setMaximum(abs(value) * self.slider_scale * 100 + 1000)
            if only_positive:
                self.Slider.setMinimum(0)
            else:
                self.Slider.setMinimum(-abs(value) * self.slider_scale * 100 - 1000)
        else:
            if only_positive:
                self.Slider.setMinimum(0)
            else:
                self.Slider.setMinimum(slider_range[0] * 100)
            self.Slider.setMaximum(slider_range[1] * 100)
        self.Slider.valueChanged.connect(self.on_Slider_updated)

        # Layout setup
        layout = QVBoxLayout() if vertical else QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        if vertical:
            layout.addWidget(self.Slider, alignment=Qt.AlignCenter)
            layout.addWidget(self.SpinBox, alignment=Qt.AlignCenter)
        else:
            layout.addWidget(self.SpinBox)
            layout.addWidget(self.Slider)
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        if spacer_enable:
            layout.addItem(spacer)
        self.setLayout(layout)
        if vertical:
            self.setFixedWidth(96)
        self.on_SpinBox_updated()
        self.SpinBox.valueChanged.connect(self.on_SpinBox_updated)

    # Colors
    def set_color(self, color):
        self.SpinBox.setStyleSheet(f"color: {color};")

    # Updating
    def on_SpinBox_updated(self):
        value = self.SpinBox.value()
        if self.int_output:
            value = round(value)
        if value > self.Slider.maximum() / 100 or value < self.Slider.minimum() / 100:
            if self.only_positive:
                self.Slider.setMinimum(0)
            else:
                self.Slider.setMinimum(-abs(value) * self.slider_scale * 100 - 1000)
            self.Slider.setMaximum(abs(value) * self.slider_scale * 100 + 1000)
        self.Slider.setValue(value * 100)
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


class BoxSlider(QWidget):
    edited = Signal(float)

    STYLE = """
    QLineEdit {
        background-color: #1C1C1C;
        color: #E3E3E3;
        border: none;
        padding: 0px;
        selection-background-color: #414956;
        font: 580 10pt "Segoe UI";
    }
    """

    def __init__(self, int_output: bool = False, slider_range: list = [0, 0], value: float = 0.0,
                 only_positive: bool = False, lock_range: bool = False, digits: int = 3,
                 value_step: float = 0.1, slider_scale: int = 5):
        """
        BoxSlider is a widget with a spin box and slider that are synchronized with each other.
        This widget gives float or round(float) which is int variable type.
        """
        super().__init__()

        self.int_output = int_output
        self.min_value, self.max_value = slider_range
        self.value = value
        self.only_positive = only_positive
        self.lock_range = lock_range
        self.digits = digits
        self.value_step = value_step
        self.slider_scale = slider_scale

        # Handle infinity range case
        if slider_range[0] == 0 and slider_range[1] == 0:
            self.min_value = -math.inf
            self.max_value = math.inf

        self.in_edit_mode = False
        self.dragging = False

        self.setup_ui()
        self.set_value(self.value)

    def setup_ui(self):
        """Initialize the UI components"""
        self.edit_box = QLineEdit(self)
        self.edit_box.hide()
        self.edit_box.setValidator(QDoubleValidator(self.min_value, self.max_value, self.digits, self))
        self.edit_box.returnPressed.connect(self.finish_edit)
        self.edit_box.installEventFilter(self)

        self.slider_rect = QRect(0, 0, 100, 20)
        self.setFixedSize(self.slider_rect.width(), self.slider_rect.height())

        self.setStyleSheet(self.STYLE)
        self.installEventFilter(self)
        self.setFocusPolicy(Qt.StrongFocus)
        self.edit_box.setFocusPolicy(Qt.StrongFocus)

        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and self.in_edit_mode:
            clicked_widget = QApplication.widgetAt(event.globalPos())
            if clicked_widget not in (self, self.edit_box):
                self.finish_edit()
                return True

        if obj == self:
            if event.type() == QEvent.MouseButtonDblClick and not self.in_edit_mode:
                self.enter_edit_mode()
                return True

            if not self.in_edit_mode:
                if event.type() == QEvent.MouseButtonPress:
                    self.start_drag(event.position().x())
                    return True
                elif event.type() == QEvent.MouseMove and self.dragging:
                    self.update_value_by_drag(event.position().x())
                    return True
                elif event.type() == QEvent.MouseButtonRelease and self.dragging:
                    self.finish_drag()
                    return True

        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1C1C1C"))
        painter.drawRect(self.rect())

        # Draw border
        painter.setPen(QPen(QColor("#363639")))
        painter.drawRect(self.slider_rect)

        # Draw text
        painter.setPen(QColor("#E3E3E3"))
        value_text = f"{int(self.value) if self.int_output else self.value:.{self.digits}f}"
        painter.drawText(self.slider_rect, Qt.AlignCenter, value_text)

    def enter_edit_mode(self):
        self.in_edit_mode = True
        self.edit_box.setText(f"{self.value:.{self.digits}f}")
        self.edit_box.setGeometry(self.slider_rect)
        self.edit_box.show()
        self.edit_box.selectAll()
        self.edit_box.setFocus()
        self.update()

    def finish_edit(self):
        if self.in_edit_mode:
            try:
                new_value = float(self.edit_box.text())
                if self.int_output:
                    new_value = round(new_value)
                self.set_value(new_value)
            except ValueError:
                pass
            self.in_edit_mode = False
            self.edit_box.hide()
            self.setFocus()
            self.update()

    def start_drag(self, x):
        if not self.in_edit_mode:
            self.dragging = True
            self.last_drag_x = x

    def update_value_by_drag(self, x):
        if not self.in_edit_mode:
            delta = x - self.last_drag_x
            self.last_drag_x = x

            # Calculate sensitivity based on slider_scale
            range_width = self.max_value - self.min_value if not math.isinf(self.max_value) else 100
            sensitivity = ((range_width / self.slider_rect.width()) * self.slider_scale)/4

            new_value = self.value + delta * sensitivity
            if self.int_output:
                new_value = round(new_value)
            self.set_value(new_value)

    def finish_drag(self):
        self.dragging = False

    def set_value(self, value):
        value = float(value)
        if self.lock_range and not math.isinf(self.max_value):
            value = max(self.min_value, min(value, self.max_value))

        if self.only_positive:
            value = max(0, value)

        if self.int_output:
            value = round(value)

        self.value = value
        self.edited.emit(self.value)
        self.update()

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
            if isinstance(filter_types, list):
                self.variable_type = filter_types[0]
            else:
                self.variable_type = 'String'

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


from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import sys

class WidgetsShowcaseWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Widgets Showcase")
        self.setGeometry(100, 100, 400, 300)

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Add FloatWidget to the layout
        self.float_test = FloatWidget(vertical=True)
        main_layout.addWidget(self.float_test)


        self.float_test_2 = FloatWidget(spacer_enable=False)
        main_layout.addWidget(self.float_test_2)

        self.float_test_3 = BoxSlider()
        main_layout.addWidget(self.float_test_3)

        # Set the central widget
        self.setCentralWidget(main_widget)

def main():
    app = QApplication(sys.argv)
    window = WidgetsShowcaseWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()