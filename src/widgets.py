from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon, QColor, QFont
import sys, webbrowser
from qt_styles.common import *

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
class ErrorInfo(QMessageBox):
    def __init__(self, text="Test", details=""):
        super().__init__()


        self.setWindowTitle("Error")
        self.setText(text)
        self.setMinimumSize(400, 200)
        self.setIcon(QMessageBox.Critical)
        self.setWindowIcon(QIcon("appicon.ico"))


        self.setDetailedText(details)

        report_button = self.addButton("Report", QMessageBox.ActionRole)
        close_button = self.addButton(QMessageBox.Close)


        report_button.clicked.connect(self.report_issue)

    def report_issue(self):
        webbrowser.open("https://discord.gg/mMaub4jCBa")

def ExpetionErrorDialog(function, id):
    try:
        function()
    except (Exception, ValueError, EOFError, InterruptedError, TypeError) as e:
        error_details = str(e)
        ErrorInfo(text=f"{id} Error: {e}", details=error_details).exec_()
#============================================================<  Property widgets  >=========================================================
class FloatWidget(QWidget):
    edited = Signal(float)
    def __init__(self, int_output: bool =False, slider_range: list = [0,0], value: float=0.0, only_positive: bool = False, lock_range: bool = False):
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
        layout.addItem(spacer)
        self.setLayout(layout)
        self.on_SpinBox_updated()
        self.SpinBox.valueChanged.connect(self.on_SpinBox_updated)
        # Widget class

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
#================================================================<  Combobox  >=============================================================
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
        self.currentTextChanged.connect(self.changed_var)
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
        if self.currentIndex() == 0:
            return ''
        else:
            return self.currentText()
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
