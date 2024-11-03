import re
from smartprop_editor.properties_classes.ui_float import Ui_Widget
from src.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QSizePolicy, QSpacerItem, QHBoxLayout
from PySide6.QtCore import Signal
from smartprop_editor.objects import expression_completer
from widgets import ComboboxVariables, Spacer


class PropertyString(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea, expression_bool=False, only_string=False, placeholder=None, only_variable=False):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.only_string = only_string
        self.expression_bool = expression_bool
        self.variables_scrollArea = variables_scrollArea

        self.ui.logic_switch.setItemText(1, 'String')
        self.spacer = Spacer()
        self.ui.layout.addWidget(self.spacer)

        if expression_bool:
            self.ui.property_class.setStyleSheet("""
                        border:0px;
            background-color: rgba(255, 255, 255, 0);
            font: 8pt "Segoe UI";
            padding-right: 16px;

            color: rgb(255, 123, 125);
                        """)
        else:
            self.ui.property_class.setStyleSheet("""
                        border:0px;
            background-color: rgba(255, 255, 255, 0);
            font: 8pt "Segoe UI";
            padding-right: 16px;

            color: rgb(255, 209, 153);
                        """)


        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        # EditLine
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''

        # Variable
        self.variable = ComboboxVariables(layout=self.variables_scrollArea)
        self.variable.setFixedWidth(128)  # Set a fixed width if needed
        self.variable.filter_types = ['String','MaterialGroup', 'Model']
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.variable_frame = QWidget()
        self.variable_frame.setLayout(layout)
        self.variable.changed.connect(self.on_changed)
        self.ui.layout.insertWidget(2, self.variable_frame)

        if placeholder:
            self.text_line.setPlaceholderText(placeholder)
        else:
            self.text_line.setPlaceholderText('Variable name, string or expression')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)
        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.var_value = value['m_Expression']
                self.text_line.setPlainText(str(self.var_value))
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.variable.set_variable(value['m_SourceName'])
        elif isinstance(value, str):
            self.ui.logic_switch.setCurrentIndex(1)
            self.text_line.setPlainText(value)
        else:
            self.ui.logic_switch.setCurrentIndex(0)
            self.text_line.setPlainText('')


        if self.expression_bool:
            self.ui.logic_switch.hide()
            self.ui.logic_switch.setCurrentIndex(3)
        elif self.only_string:
            self.ui.logic_switch.hide()
            self.ui.logic_switch.setCurrentIndex(1)
        elif only_variable:
            self.ui.logic_switch.hide()
            self.ui.logic_switch.setCurrentIndex(2)
        self.ui.logic_switch.currentIndexChanged.connect(self.logic_switch)
        self.logic_switch()

    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.variable_frame.hide()
            self.text_line.hide()
            self.spacer.show()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.variable_frame.hide()
            self.text_line.show()
            self.spacer.hide()
        elif self.ui.logic_switch.currentIndex() == 2:
            self.variable_frame.show()
            self.text_line.hide()
            self.spacer.hide()
        elif self.ui.logic_switch.currentIndex() == 3:
            self.variable_frame.hide()
            self.text_line.show()
            self.spacer.hide()
        self.on_changed()


    def on_changed(self):
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables + expression_completer)
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
            self.value = {self.value_class: value}
        # Variable
        elif self.ui.logic_switch.currentIndex() == 2:
            value = self.variable.get_variable()
            self.value = {self.value_class: {'m_SourceName': value}}
        # Expression
        elif self.ui.logic_switch.currentIndex() == 3:
            value = self.text_line.toPlainText()
            self.value = {self.value_class: {'m_Expression': str(value)}}

    def get_variables(self, search_term=None):
        self.variables_scrollArea
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out
