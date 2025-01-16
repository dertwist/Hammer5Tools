import ast

from src.smartprop_editor.properties.ui_legacy import Ui_Widget
from src.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget
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
        self.variables_scrollArea = variables_scrollArea

        self.text_line = CompletingPlainTextEdit()
        self.ui.layout.insertWidget(1, self.text_line)

        self.text_line.setPlainText(str(self.value))
        self.ui.value_label.setText(str(self.value_class))
        self.text_line.textChanged.connect(self.on_changed)


        self.change_value()



    def on_changed(self):
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables)
        self.change_value()
        self.edited.emit()
    def change_value(self):
        value = self.text_line.toPlainText()
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
