import ast
import re
from smartprop_editor.properties_classes.ui_float import Ui_Widget
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QCompleter, QSizePolicy, QSpacerItem, QHBoxLayout
from PySide6.QtCore import Signal
from smartprop_editor.objects import expression_completer
from widgets import ComboboxVariables, Spacer
from preferences import debug


class PropertyVariableOutput(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea

        self.spacer = Spacer()
        self.ui.layout.addWidget(self.spacer)

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
        self.ui.logic_switch.deleteLater()


        # Variable
        self.variable = ComboboxVariables(layout=self.variables_scrollArea)
        self.variable.setFixedWidth(128)  # Set a fixed width if needed
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.variable_frame = QWidget()
        self.variable_frame.setLayout(layout)
        self.variable.changed.connect(self.on_changed)
        self.ui.layout.insertWidget(2, self.variable_frame)

        if isinstance(value, dict):
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.variable.set_variable(value['m_SourceName'])
                debug(f'Loaded value in variable widget: dict {value['m_SourceName']}')

        elif isinstance(value, str):
            self.variable.set_variable(value)
            debug(f'Loaded value in variable widget: str {value}')
        else:
            self.variable.set_variable(value)
            debug(f'Loaded value in variable widget: None {value}')
        self.on_changed()
    def on_changed(self):
        self.change_value()
        self.edited.emit()
    def change_value(self):
        self.value = {self.value_class: self.variable.get_variable()}
        debug(f'Changed value in variable widget {self.value}')