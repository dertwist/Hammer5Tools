import ast
import re
from src.editors.smartprop_editor.property.ui_float import Ui_Widget
from src.widgets.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QSizePolicy, QSpacerItem, QHBoxLayout, QWidget
from PySide6.QtCore import Signal
from src.editors.smartprop_editor.objects import expression_completer
from src.widgets import FloatWidget
from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget

class PropertyFloat(QWidget):
    edited = Signal()

    def __init__(self, element_id_generator, value_class, value, variables_scrollArea, int_bool=False, slider_range=[0, 0]):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.int_bool = int_bool
        self.variables_scrollArea = variables_scrollArea

        self.ui.logic_switch.wheelEvent = lambda event: None

        # Float widget setup
        self.float_widget = FloatWidget(slider_range=slider_range, int_output=int_bool)
        self.float_widget.edited.connect(self.on_changed)
        self.ui.layout.addWidget(self.float_widget)

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

        # Set styles based on int_bool
        if self.int_bool:
            self.ui.logic_switch.setItemText(1, 'Int')
            self.ui.property_class.setStyleSheet("""
                border:0px;
                background-color: rgba(255, 255, 255, 0);
                font: 8pt "Segoe UI";
                padding-right: 16px;
                color: rgb(108, 135, 255);
            """)
        else:
            self.ui.property_class.setStyleSheet("""
                border:0px;
                background-color: rgba(255, 255, 255, 0);
                font: 8pt "Segoe UI";
                padding-right: 16px;
                color: rgb(181, 255, 239);
            """)

        # Process value_class
        output = re.sub(r'm_fl|m_n|m_b|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)
        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)


        # Variable setup
        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, filter_types=['Float', 'Int'], variable_name=self.value_class, element_id_generator=element_id_generator)
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


        # EditLine setup
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.OnlyFloat = True
        self.text_line.setPlaceholderText('Variable name, float or expression')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        self.ui.logic_switch.setCurrentIndex(0)
        self.text_line.setPlainText('0')


        # Initialize value
        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.var_value = value['m_Expression']
                self.text_line.setPlainText(str(self.var_value))
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.variable.combobox.set_variable(str(self.var_value))
        elif isinstance(value, float) or isinstance(value, int):
            self.ui.logic_switch.setCurrentIndex(1)
            self.float_widget.set_value(value)

        self.on_changed()

    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.OnlyFloat = False
            self.text_line.hide()
            self.float_widget.hide()
            self.variable_frame.hide()
            self.spacer.show()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.float_widget.show()
            self.variable_frame.hide()
            self.spacer.hide()
        elif self.ui.logic_switch.currentIndex() == 2:
            self.text_line.hide()
            self.float_widget.hide()
            self.variable_frame.show()
            self.spacer.hide()
        else:
            self.text_line.OnlyFloat = False
            self.text_line.show()
            self.variable_frame.hide()
            self.float_widget.hide()
            self.spacer.hide()

    def on_changed(self):
        self.logic_switch()
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
            value = self.float_widget.value
            if self.int_bool:
                self.value = {self.value_class: round(float(value))}
            else:
                self.value = {self.value_class: float(value)}
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
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out
