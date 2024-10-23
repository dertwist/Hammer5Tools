from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem
class FloatWidget(QWidget):
    edited = Signal(float)
    def __init__(self, int_output=False, slider_range=[-99,99]):
        """Float widget is a widget with sping box and slider that are synchronized with each-other. This widget give float or round(float) which is int variable type"""
        super().__init__()
        # Variables
        self.int_output = int_output
        self.value = 0.0
        # SpinnBox setup
        self.SpinBox = QDoubleSpinBox()
        self.SpinBox.setMinimum(-99999999)
        self.SpinBox.setMaximum(99999999)
        self.SpinBox.valueChanged.connect(self.on_SpinBox_updated)
        # Slider setup
        self.Slider = QSlider()
        self.Slider.setOrientation(Qt.Horizontal)
        self.Slider.setMinimum(slider_range[0] * 100)
        self.Slider.setMaximum(slider_range[1] * 100)
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
    def __init__(self, parent=None, layout=None):
        """Getting variables and put them into combobox"""
        super().__init__(parent)
        self.variables_scrollArea = layout
        self.items = None
        self.currentTextChanged.connect(self.changed_var)

    def updateItems(self):
        self.currentTextChanged.disconnect(self.changed_var)
        self.items = []
        variables = self.get_variables()
        for item in variables:
            self.items.append(item['name'])

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