import ast
import re
from smartprop_editor.properties_classes.ui_comparison import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter
from PySide6.QtCore import Signal


class PropertyComparison(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea

        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.comparison.currentTextChanged.connect(self.on_changed)

        # Name
        self.m_name = CompletingPlainTextEdit()
        self.m_name.completion_tail = ''
        self.m_name.setPlaceholderText('Variable name')
        self.ui.layout_2.insertWidget(1, self.m_name)
        self.m_name.textChanged.connect(self.on_changed)



        # Name
        self.m_value = CompletingPlainTextEdit()
        self.m_value.completion_tail = ''
        self.m_value.setPlaceholderText('Value')
        self.ui.layout_2.insertWidget(4, self.m_value)
        self.m_value.textChanged.connect(self.on_changed)



        if isinstance(value, dict):
            if 'm_Name' in value:
                self.m_name.setPlainText(str(value['m_Name']))
            if 'm_Value' in value:
                self.m_value.setPlainText(str(value['m_Value']))
        else:
            self.m_value.setPlainText('')
            self.m_name.setPlainText('')


        self.on_changed()


    def on_changed(self):
        variables = self.get_variables()
        self.m_name.completions.setStringList(variables)
        self.m_value.completions.setStringList(variables)
        self.change_value()
        self.edited.emit()
    def change_value(self):
        # Default
        var_value = self.m_value.toPlainText()
        try:
            var_value = ast.literal_eval(var_value)
        except:
            pass


        try:
            var_value = float(var_value)
        except:
            pass

        self.value = {self.value_class: {'m_Name': self.m_name.toPlainText(), 'm_value': var_value,'m_Comparison': self.ui.comparison.currentText()}}

    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out
