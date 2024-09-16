import ast
import re
from smartprop_editor.properties_classes.ui_float import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter
from PySide6.QtCore import Signal


class PropertyFloat(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea, int_bool=False):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.int_bool = int_bool
        self.variables_scrollArea = variables_scrollArea

        if self.int_bool:
            self.ui.logic_switch.setItemText(1, 'Int')

        output = re.sub(r'm_fl|m_n|m_b|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        # EditLine
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.OnlyFloat = True
        self.text_line.setPlaceholderText('Variable name, float or expression')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        if isinstance(value, dict):
            if value['m_Expression']:
                self.ui.logic_switch.setCurrentIndex(1)
                self.var_value = value['m_Expression']
                self.text_line.setPlainText(self.var_value)
            elif value['m_SourceName']:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.text_line.setPlainText(self.var_value)
            else:
                print('Could not parse given input data')
                self.value = {'m_Components': {'m_Expression': '0'}}
        if isinstance(value, float) or isinstance(value, int):
            self.ui.logic_switch.setCurrentIndex(1)
            self.text_line.setPlainText(str(value))
        else:
            self.ui.logic_switch.setCurrentIndex(0)
            self.text_line.setPlainText('0')



        self.on_changed()




    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.OnlyFloat = False
            self.text_line.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.OnlyFloat = True
            self.text_line.show()
        else:
            self.text_line.OnlyFloat = False
            self.text_line.show()

    def on_changed(self):
        self.logic_switch()
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables)
        self.change_value()
        self.edited.emit()
    def change_value(self):
        # Default
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = {self.value_class: None}
            self.value = None
        #Float or int
        elif self.ui.logic_switch.currentIndex() == 1:
            value = self.text_line.toPlainText()
            if self.int_bool:
                self.value = {self.value_class: round(float(value))}
            else:
                self.value = {self.value_class: value}
        # Variable
        elif self.ui.logic_switch.currentIndex() == 2:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_SourceName': value}}
        # Expression
        elif self.ui.logic_switch.currentIndex() == 3:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_Expression': str(value)}}

    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out
