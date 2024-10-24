from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem

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
class FloatWidget(QWidget):
    edited = Signal(float)
    def __init__(self, int_output=False, slider_range=[-0,0], value=0.0):
        """Float widget is a widget with sping box and slider that are synchronized with each-other. This widget give float or round(float) which is int variable type"""
        super().__init__()
        # Variables
        self.int_output = int_output
        self.value = value

        # SpinnBox setup
        self.SpinBox = QDoubleSpinBox()
        self.SpinBox.setMinimum(-99999999)
        self.SpinBox.setMaximum(99999999)
        self.SpinBox.valueChanged.connect(self.on_SpinBox_updated)
        self.SpinBox.setValue(value)

        # Slider setup
        self.Slider = QSlider()
        self.Slider.setOrientation(Qt.Horizontal)
        # Range
        if slider_range[0] == 0 and slider_range[1] == 0:
            value = self.SpinBox.value()
            self.Slider.setMaximum(abs(value) * 10 * 100 +1000)
            self.Slider.setMinimum(-abs(value) * 10 * 100 -1000)
        else:
            self.Slider.setMinimum(slider_range[0])
            self.Slider.setMaximum(slider_range[1])
        self.Slider.valueChanged.connect(self.on_Slider_updated)

        # Layout setup
        layout = QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.SpinBox)
        layout.addWidget(self.Slider)
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addItem(spacer)
        self.setLayout(layout)
        # Widget class

    # Updating
    def on_SpinBox_updated(self):
        value = self.SpinBox.value()
        if self.int_output:
            value = round(value)
        if value > self.Slider.maximum()/100 or value < self.Slider.minimum()/100:
            self.Slider.setMaximum(abs(value) * 10 * 100 + 1000)
            self.Slider.setMinimum(-abs(value) * 10 * 100 - 1000)
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

class ComboboxDynamicItems(QComboBox):
    clicked = Signal()

    def __init__(self, parent=None, items=None):
        """Combobox that updates it's items when user clicked on it"""
        super().__init__(parent)
        self.setStyleSheet('padding:2px; font: 580 9pt "Segoe UI"; padding-left:4px;')
        self.items = items

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
        variables = self.get_variables()
        for item in variables:
            if self.filter_types is not None:
                if item['class'] in self.filter_types:
                    self.items.append(item['name'])
            else:
                self.items.append(item['name'])
        self.items.append('')
        current = self.currentText()
        self.clear()
        self.addItems(self.items)
        if current in self.items:
            self.setCurrentText(current)
        self.currentTextChanged.connect(self.changed_var)
    def changed_var(self):
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
        self.addItem(value)
        self.setCurrentText(value)

class ComboboxTreeChild(ComboboxDynamicItems):
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