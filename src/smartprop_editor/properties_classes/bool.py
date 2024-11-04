import ast
import re
from smartprop_editor.properties_classes.ui_bool import Ui_Widget
from src.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal


class PropertyBool(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea


        output = re.sub(r'm_fl|m_n|m_b|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        # EditLine
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.OnlyFloat = True
        self.text_line.setPlaceholderText('Variable name, float or expression')
        self.ui.layout.insertWidget(3, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        self.ui.value.stateChanged.connect(self.on_changed)

        self.ui.logic_switch.setCurrentIndex(0)
        self.text_line.setPlainText('')

        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.var_value = value['m_Expression']
                self.text_line.setPlainText(self.var_value)
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.text_line.setPlainText(self.var_value)
        elif isinstance(value, bool):
            self.ui.logic_switch.setCurrentIndex(1)
            self.ui.value.setChecked(value)
        else:
            pass


        self.on_changed()




    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.hide()
            self.ui.value.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.ui.value.show()
        else:
            self.text_line.show()
            self.ui.value.hide()

    def on_changed(self):
        self.logic_switch()
        self.ui.value.setText(str(self.ui.value.isChecked()))
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables)
        self.change_value()
        self.edited.emit()
    def change_value(self):
        # Default
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = None
        #Float or int
        elif self.ui.logic_switch.currentIndex() == 1:
            self.value = {self.value_class: self.ui.value.isChecked()}
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