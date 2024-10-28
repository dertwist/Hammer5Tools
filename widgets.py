from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSlider, QDoubleSpinBox, QFrame, QSpacerItem, QSizePolicy, QComboBox, QTreeWidget, QTreeWidgetItem, QDialog, QMessageBox, QPushButton, QApplication, QLabel
from PySide6.QtGui import QStandardItemModel
from PySide6.QtGui import QIcon
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
#============================================================<  Property widgets  >=========================================================
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
    def __init__(self, tree_widget, _name="New Hierarchy Item", _data=None, _class=None, _id=None):
        super().__init__(tree_widget)

        # Set text for name and data
        self.setText(0, _name)
        self.setText(1, _data)
        self.setFlags(self.flags() | Qt.ItemIsEditable)

        # If _class is provided, create QLabel and set it in the tree widget
        if _class:
            label = QLabel()
            label.setText(_class)
            tree_widget.setItemWidget(self, 2, label)

        if _id:
            label = QLabel()
            label.setText(_id)
            tree_widget.setItemWidget(self, 3, label)
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

# Example usage
# app = QApplication([])
# tree_widget = QTreeWidget()
# tree_widget.setColumnCount(4)
# tree_widget.setHeaderLabels(['Name', 'Data', 'Class', 'ID'])
#
# # Adding an example item
# item = HierarchyItemModel(tree_widget, 'Item1', 'Data1', 'Class1', 'ID1')
#
# tree_widget.show()
# app.exec_()
