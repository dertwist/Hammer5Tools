import ast
import re
from src.smartprop_editor.properties.ui_combobox import Ui_Widget
from src.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QSizePolicy, QSpacerItem, QHBoxLayout, QWidget
from PySide6.QtCore import Signal
from src.widgets import ComboboxVariablesWidget


class PropertyCombobox(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea, items, filter_types):
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
        self.ui.logic_switch.setItemText(1, output)

        self.ui.value.addItems(items)
        self.ui.value.currentTextChanged.connect(self.on_changed)


        # Spacer frame
        spacer_item = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.spacer = QWidget()
        spacer_layout = QHBoxLayout()
        spacer_layout.addSpacerItem(spacer_item)
        spacer_layout.setContentsMargins(0, 0, 0, 0)
        self.spacer.setLayout(spacer_layout)
        self.spacer.setStyleSheet('border:None;')
        self.spacer.setContentsMargins(0, 0, 0, 0)
        self.ui.layout.addWidget(self.spacer)


        # Variable setup
        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, filter_types=filter_types)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.variable_frame = QWidget()
        self.variable_frame.setLayout(layout)
        self.variable.setFixedWidth(256)
        self.variable.setMaximumHeight(24)
        self.variable.search_button.set_size(width=24, height=24)
        self.variable_frame.setMinimumHeight(32)
        self.variable.combobox.changed.connect(self.on_changed)
        self.ui.layout.insertWidget(2, self.variable_frame)



        # EditLine
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.setPlaceholderText('Variable name, float or expression')
        self.ui.layout.insertWidget(3, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

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
                self.variable.combobox.set_variable(str(self.var_value))
        elif isinstance(value, str):
            self.ui.logic_switch.setCurrentIndex(1)
            self.ui.value.setCurrentText(value)

        self.on_changed()




    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.OnlyFloat = False
            self.text_line.hide()
            self.ui.value.hide()
            self.variable_frame.hide()
            self.spacer.show()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.ui.value.show()
            self.variable_frame.hide()
            self.spacer.hide()
        elif self.ui.logic_switch.currentIndex() == 2:
            self.text_line.hide()
            self.ui.value.hide()
            self.variable_frame.show()
            self.spacer.hide()
        else:
            self.text_line.OnlyFloat = False
            self.text_line.show()
            self.variable_frame.hide()
            self.ui.value.hide()
            self.spacer.hide()

    def on_changed(self):
        self.logic_switch()
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
            self.value = {self.value_class: self.ui.value.currentText()}
        # Variable
        elif self.ui.logic_switch.currentIndex() == 2:
            value = self.variable.combobox.get_variable()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_SourceName': str(value)}}
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
