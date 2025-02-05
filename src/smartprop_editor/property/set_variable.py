import ast
import re
from src.smartprop_editor.property.ui_set_variable import Ui_Widget
from src.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QSizePolicy, QSpacerItem, QHBoxLayout, QWidget
from PySide6.QtCore import Signal
from src.smartprop_editor.objects import expression_completer
from src.widgets import FloatWidget, ComboboxVariablesWidget, BoolWidget

# m_VariableValue =
# {
#       m_TargetName = "end_weight"
#       m_DataType = "FLOAT"
#       m_Value = 1.000000
# }

# The SetVariable property should output m_Variable.
# The widget must include a combobox to select the variable type,
# and a specialized widget for each variable type.
# Currently, the planned variable types are: bool, float, and string.

# There is also a conflict with legacy SetVariableBool and SetVariableFloat which have also m_VariableValue key.
# I planed to make only one universal property - SetVariable, all related properties SetVariableFloat and SetVariableBool

BOOL_COLOR = '(255, 189, 190)'
FLOAT_COLOR = '(181, 255, 239)'
STRING_COLOR = '(255, 209, 153)'

class PropertyVariableValue(QWidget):
    edited = Signal()

    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.m_TargetName: str = None
        self.m_DataType: str = None
        self.m_Value = None
        self.variables_scrollArea = variables_scrollArea

        # Float widget setup
        self.float_widget = FloatWidget(slider_range=[0,0], int_output=False)
        self.float_widget.edited.connect(self.on_changed)
        self.ui.layout_3.addWidget(self.float_widget)


        # init colors
        self.ui.property_class_4.setStyleSheet(f"color: rgb{STRING_COLOR};")
        self.ui.property_class.setStyleSheet(f"color: rgb{STRING_COLOR};")




        # Bool widget setup
        self.bool_widget = BoolWidget()
        self.bool_widget.edited.connect(self.on_changed)
        self.bool_widget.checkbox.setStyleSheet('border:None; font: 580 9pt "Segoe UI";')
        self.ui.layout_3.addWidget(self.bool_widget)

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

        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)


        # Variable setup
        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, filter_types=['Float', 'Int', 'Bool'])
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
        self.ui.layout_2.addWidget(self.variable_frame)


        # EditLine setup



        # Initialize value
        if 'm_DataType' in value:
            self.m_DataType = value['m_DataType']
            if self.m_DataType == 'FLOAT':
                self.ui.logic_switch.setCurrentText('Float')
            elif self.m_DataType == 'BOOl':
                self.ui.logic_switch.setCurrentText('Bool')
        if 'm_Value' in value:
            self.m_Value = value['m_Value']
            if isinstance(self.m_Value, bool):
                self.bool_widget.set_value(self.m_Value)
            elif isinstance(self.m_Value, float):
                self.float_widget.set_value(self.m_Value)
            elif isinstance(self.m_Value, int):
                self.float_widget.set_value(self.m_Value)
        if 'm_TargetName' in value:
            self.m_TargetName = value['m_TargetName']
            self.variable.combobox.set_variable(self.m_TargetName)

        self.on_changed()

    def logic_switch(self):
        if self.ui.logic_switch.currentText() == 'Float':
            self.float_widget.show()
            self.bool_widget.hide()
            self.spacer.show()
            self.ui.property_class_5.setStyleSheet(f"color: rgb{FLOAT_COLOR};")
            self.ui.property_class_4.setStyleSheet(f"color: rgb{FLOAT_COLOR};")
            self.variable.combobox.filter_types = ['Float', 'int']
        elif self.ui.logic_switch.currentText() == 'Bool':
            self.float_widget.hide()
            self.bool_widget.show()
            self.spacer.show()
            self.ui.property_class_5.setStyleSheet(f"color: rgb{BOOL_COLOR};")
            self.ui.property_class_4.setStyleSheet(f"color: rgb{BOOL_COLOR};")
            self.variable.combobox.filter_types = ['Bool']
        self.m_DataType = self.ui.logic_switch.currentText().upper()
    def on_changed(self):
        self.logic_switch()
        variables = self.get_variables()
        self.change_value()
        self.edited.emit()
    def change_value(self):
        if self.ui.logic_switch.currentText() == 'Float':
            self.m_Value = self.float_widget.value
        elif self.ui.logic_switch.currentText() == 'Bool':
            self.m_Value = self.bool_widget.get_value()
        self.m_TargetName = self.variable.combobox.get_variable()
        self.value = {self.value_class: {'m_TargetName': str(self.m_TargetName), 'm_DataType': str(self.m_DataType), 'm_Value': self.m_Value}}

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out
