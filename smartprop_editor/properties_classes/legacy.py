import ast

from smartprop_editor.properties_classes.ui_legacy import Ui_Widget
from PySide6.QtWidgets import QWidget, QCompleter
from PySide6.QtCore import Signal


class PropertyLegacy(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.value_class = value_class
        self.value = value

        self.ui.value.setText(str(self.value))
        self.ui.value_label.setText(str(self.value_class))
        self.ui.value.textChanged.connect(self.on_changed)

        self.variables_scrollArea = variables_scrollArea
        variables = self.get_variables()
        print(variables)
        completer = QCompleter(variables)
        self.ui.value.setCompleter(completer)

        self.change_value()



    def on_changed(self):
        self.change_value()
        self.edited.emit()
    def change_value(self):
        value = self.ui.value.text()
        try:
            value = ast.literal_eval(value)
        except:
            pass
        self.value = {self.value_class: value}

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out