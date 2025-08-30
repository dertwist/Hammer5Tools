from src.editors.smartprop_editor.property.ui_set_variable import Ui_Widget
from src.widgets.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QSizePolicy, QSpacerItem, QHBoxLayout, QWidget
from PySide6.QtCore import Signal
from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
from src.widgets import FloatWidget, BoolWidget
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.editors.smartprop_editor.widgets.expression_editor.main import ExpressionEditor

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

    def __init__(self, value_class, value, variables_scrollArea, element_id_generator):
        super().__init__()
        try:
            self.ui = Ui_Widget()
            self.ui.setupUi(self)
            self.setAcceptDrops(False)
            self.value_class = value_class
            self.value = None
            self.m_TargetName: str = None
            self.m_DataType: str = None
            self.m_Value = None
            self.variables_scrollArea = variables_scrollArea

            # Float widget setup
            self.float_widget = FloatWidget(slider_range=[0,0], int_output=False, spacer_enable=False)
            self.float_widget.edited.connect(self.on_changed)
            self.ui.layout_3.addWidget(self.float_widget)

            # init colors
            self.ui.property_class_4.setStyleSheet(f"color: rgb{STRING_COLOR};")
            self.ui.property_class.setStyleSheet(f"color: rgb{STRING_COLOR};")

            # Bool widget setup
            self.bool_widget = BoolWidget(spacer_enable=False)
            self.bool_widget.edited.connect(self.on_changed)
            self.bool_widget.checkbox.setStyleSheet('border:None; font: 580 9pt "Segoe UI";')
            self.ui.layout_3.addWidget(self.bool_widget)

            # EditLine setup
            self.text_line = CompletingPlainTextEdit()
            self.text_line.completion_tail = ''
            self.text_line.OnlyFloat = False
            self.expression_editor = ExpressionEditor(self.text_line, self.variables_scrollArea)
            self.text_line.setPlaceholderText('Variable name, float or expression')
            self.ui.layout_3.addWidget(self.expression_editor)
            self.ui.layout_3.addWidget(self.text_line)
            self.text_line.textChanged.connect(self.on_changed)

            # Spacer frame - Create separate spacer items for different layouts
            value_spacer_item = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.value_spacer_item = QWidget()
            value_spacer_layout = QHBoxLayout()
            value_spacer_layout.addItem(value_spacer_item)
            value_spacer_layout.setContentsMargins(0, 0, 0, 0)
            self.value_spacer_item.setLayout(value_spacer_layout)
            self.ui.layout_3.addWidget(self.value_spacer_item)

            # Create separate spacer item for main spacer
            main_spacer_item = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.spacer = QWidget()
            spacer_layout = QHBoxLayout()
            spacer_layout.addItem(main_spacer_item)
            spacer_layout.setContentsMargins(0, 0, 0, 0)
            self.spacer.setLayout(spacer_layout)
            self.spacer.setStyleSheet('border:None;')
            self.spacer.setContentsMargins(0, 0, 0, 0)
            self.ui.layout.addWidget(self.spacer)

            # Connect signals
            self.ui.logic_switch.currentTextChanged.connect(self.on_changed)
            self.ui.logic_switch_value.currentTextChanged.connect(self.on_changed)

            # Variable setup
            self.variable = ComboboxVariablesWidget(
                variables_layout=self.variables_scrollArea,
                filter_types=['Float', 'Int', 'Bool'],
                variable_name=self.value_class,
                element_id_generator=element_id_generator
            )
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.variable)
            # Create separate spacer item for variable layout
            variable_spacer_item = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
            layout.addItem(variable_spacer_item)
            self.variable_frame = QWidget()
            self.variable_frame.setLayout(layout)
            self.variable.setFixedWidth(256)
            self.variable.setMaximumHeight(24)
            self.variable.search_button.set_size(width=24, height=24)
            self.variable_frame.setMinimumHeight(32)
            self.variable.combobox.changed.connect(self.on_changed)
            self.ui.layout_2.addWidget(self.variable_frame)

            # Initialize value
            self.initialize_values(value)

            # Initial state update
            self.on_changed()

        except Exception as e:
            print(f"Error in PropertyVariableValue.__init__: {e}")
            raise

    def initialize_values(self, value):
        """Initialize widget values from the provided value dictionary"""
        try:
            if 'm_Value' in value:
                print(value)
                self.m_Value = value['m_Value']
                print(self.m_Value)
                if isinstance(self.m_Value, bool):
                    self.bool_widget.set_value(self.m_Value)
                elif isinstance(self.m_Value, (float, int)):
                    self.float_widget.set_value(self.m_Value)
                elif isinstance(self.m_Value, dict) and ('m_Expression' in self.m_Value):
                    self.text_line.setPlainText(str(self.m_Value['m_Expression']))
                    self.ui.logic_switch_value.setCurrentText('Expression')

            if 'm_DataType' in value:
                self.m_DataType = value['m_DataType']
                if self.m_DataType == 'FLOAT':
                    self.ui.logic_switch.setCurrentText('Float')
                elif self.m_DataType == 'BOOL':  # Fixed typo: 'BOOl' -> 'BOOL'
                    self.ui.logic_switch.setCurrentText('Bool')
                elif self.m_DataType == 'INT':
                    self.ui.logic_switch.setCurrentText('Int')

            if 'm_TargetName' in value:
                self.m_TargetName = value['m_TargetName']
                self.variable.combobox.set_variable(self.m_TargetName)

        except Exception as e:
            print(f"Error in initialize_values: {e}")

    def logic_switch_value(self):
        """Handle switching between Value and Expression modes"""
        try:
            if self.ui.logic_switch_value.currentText() == 'Value':
                self.text_line.hide()
                self.expression_editor.hide()
                self.value_spacer_item.show()
                # Show appropriate widget based on current data type
                current_type = self.ui.logic_switch.currentText()
                if current_type == 'Bool':
                    self.float_widget.hide()
                    self.bool_widget.show()
                else:  # Float or Int
                    self.float_widget.show()
                    self.bool_widget.hide()
            elif self.ui.logic_switch_value.currentText() == 'Expression':
                self.text_line.show()
                self.expression_editor.show()
                self.value_spacer_item.hide()
                self.float_widget.hide()
                self.bool_widget.hide()
        except Exception as e:
            print(f"Error in logic_switch_value: {e}")

    def logic_switch(self):
        """Handle switching between data types (Bool, Float, Int)"""
        try:
            current_type = self.ui.logic_switch.currentText()

            if current_type in ['Float', 'Int']:
                if self.ui.logic_switch_value.currentText() == 'Value':
                    self.float_widget.show()
                    self.bool_widget.hide()
                    self.spacer.show()
                self.ui.logic_switch_value.setStyleSheet(f"color: rgb{FLOAT_COLOR};")
                self.ui.property_class_4.setStyleSheet(f"color: rgb{FLOAT_COLOR};")
                self.variable.combobox.filter_types = ['Float', 'Int']  # Fixed capitalization

            elif current_type == 'Bool':
                if self.ui.logic_switch_value.currentText() == 'Value':
                    self.float_widget.hide()
                    self.bool_widget.show()
                self.spacer.show()
                self.ui.logic_switch_value.setStyleSheet(f"color: rgb{BOOL_COLOR};")
                self.ui.property_class_4.setStyleSheet(f"color: rgb{BOOL_COLOR};")
                self.variable.combobox.filter_types = ['Bool']

            self.m_DataType = current_type.upper()
        except Exception as e:
            print(f"Error in logic_switch: {e}")

    def on_changed(self):
        """Handle any change in the widget state"""
        try:
            self.logic_switch_value()
            self.logic_switch()
            
            # Setup type-aware completer for expression mode without filters
            if self.ui.logic_switch_value.currentText() == 'Expression':
                CompletionUtils.setup_completer_for_widget(
                    self.text_line,
                    self.variables_scrollArea,
                    filter_types=None,  # No filtering - show all variable types
                    context='general'
                )
            
            self.change_value()
            self.edited.emit()
        except Exception as e:
            print(f"Error in on_changed: {e}")

    def change_value(self):
        """Update the internal value based on current widget state"""
        try:
            current_type = self.ui.logic_switch.currentText()
            current_mode = self.ui.logic_switch_value.currentText()

            if current_type in ['Float', 'Int']:
                if current_mode == 'Value':
                    self.m_Value = self.float_widget.value
                elif current_mode == 'Expression':
                    self.m_Value = {'m_Expression': str(self.text_line.toPlainText())}
            elif current_type == 'Bool':
                if current_mode == 'Value':
                    self.m_Value = self.bool_widget.get_value()
                elif current_mode == 'Expression':
                    self.m_Value = {'m_Expression': str(self.text_line.toPlainText())}

            self.m_TargetName = self.variable.combobox.get_variable()
            self.value = {
                self.value_class: {
                    'm_TargetName': str(self.m_TargetName),
                    'm_DataType': str(self.m_DataType),
                    'm_Value': self.m_Value
                }
            }
        except Exception as e:
            print(f"Error in change_value: {e}")

    def get_variables(self, search_term=None):
        """Get list of available variable names"""
        return CompletionUtils.get_available_variable_names(self.variables_scrollArea)