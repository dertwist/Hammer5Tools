from src.editors.smartprop_editor.property.ui_bool import Ui_Widget
import ast
import re
from src.widgets.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QSizePolicy, QSpacerItem, QHBoxLayout, QWidget
from PySide6.QtCore import Signal
from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.editors.smartprop_editor.widgets.expression_editor.main import ExpressionEditor

class PropertyBool(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea, element_id_generator):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea
        self.element_id_generator = element_id_generator

        self.ui.logic_switch.wheelEvent = lambda event: None
        self.ui.value.wheelEvent = lambda event: None


        output = re.sub(r'm_fl|m_n|m_b|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        # EditLine
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.setPlaceholderText('Expression')
        self.expression_editor = ExpressionEditor(self.text_line, self.variables_scrollArea)
        self.ui.layout.insertWidget(3, self.text_line)
        self.ui.layout.insertWidget(3, self.expression_editor)
        self.text_line.textChanged.connect(self.on_changed)

        self.ui.value.stateChanged.connect(self.on_changed)

        self.ui.logic_switch.setCurrentIndex(0)
        self.text_line.setPlainText('')

        # Variable setup
        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, filter_types=['Bool'], variable_name=self.value_class, element_id_generator=self.element_id_generator)
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

        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.var_value = value['m_Expression']
                self.text_line.setPlainText(self.var_value)
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.variable.combobox.set_variable(self.var_value)
        elif isinstance(value, bool):
            self.ui.logic_switch.setCurrentIndex(1)
            self.ui.value.setChecked(value)
        else:
            pass


        self.on_changed()

    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.hide()
            self.expression_editor.hide()
            self.ui.value.hide()
            if hasattr(self, 'variable_frame'):
                self.variable_frame.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.expression_editor.hide()
            self.ui.value.show()
            if hasattr(self, 'variable_frame'):
                self.variable_frame.hide()
        elif self.ui.logic_switch.currentIndex() == 2:
            self.text_line.hide()
            self.expression_editor.hide()
            self.ui.value.hide()
            if hasattr(self, 'variable_frame'):
                self.variable_frame.show()
        else:
            self.text_line.show()
            self.expression_editor.show()
            if hasattr(self, 'variable_frame'):
                self.variable_frame.hide()
            self.ui.value.hide()

    def on_changed(self):
        self.logic_switch()
        self.ui.value.setText(str(self.ui.value.isChecked()))
        
        # Setup type-aware completer for expression mode without filters
        if self.ui.logic_switch.currentIndex() == 3:  # Expression mode
            CompletionUtils.setup_completer_for_widget(
                self.text_line,
                self.variables_scrollArea,
                filter_types=None,  # No filtering - show all variable types
                context='general'
            )
        
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
            value = self.variable.combobox.get_variable()
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
        return CompletionUtils.get_available_variable_names(self.variables_scrollArea)