import re
import ast
from dataclasses import dataclass, field
from typing import Any, List, Optional

from src.editors.smartprop_editor.property.ui_float import Ui_Widget as UiFloatWidget
from src.editors.smartprop_editor.property.ui_vector3d import Ui_Widget as UiVector3DWidget
from src.editors.smartprop_editor.property.ui_comment import Ui_Widget as UiCommentWidget
from src.editors.smartprop_editor.property.ui_colormatch import Ui_Widget as UiColorMatchWidget
from src.editors.smartprop_editor.property.ui_legacy import Ui_Widget as UiLegacyWidget
from src.editors.smartprop_editor.property.ui_set_variable import Ui_Widget as UiSetVariableWidget
from src.editors.smartprop_editor.property.ui_comparison import Ui_Widget as UiComparisonWidget

from src.widgets.completer.main import CompletingPlainTextEdit
from src.widgets import FloatWidget, Spacer
from src.editors.smartprop_editor.objects import expression_completer
from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
from src.settings.main import debug
from src.styles.qt_global_stylesheet import QT_Stylesheet_global

from PySide6.QtWidgets import (
    QWidget, QSizePolicy, QSpacerItem, QHBoxLayout, QColorDialog, QToolButton, QTreeWidgetItem, QMenu
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QIcon, QColor

def prettify_class_name(name: str) -> str:
    name = re.sub(r'm_fl|m_n|m_b|m_s|m_v|m_', '', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)

@dataclass
class PropertyBase(QWidget):
    value_class: str
    value: Any
    variables_scrollArea: Any = None
    edited: Signal = field(default_factory=Signal, init=False)

    def __post_init__(self):
        super().__init__()

    def get_variables(self, search_term=None) -> List[str]:
        if not self.variables_scrollArea:
            return []
        return [
            widget.name for i in range(self.variables_scrollArea.count())
            if (widget := self.variables_scrollArea.itemAt(i).widget())
        ]

    def change_value(self):
        pass

# --- Legacy Property ---
class LegacyProperty(PropertyBase):
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__(value_class, value, variables_scrollArea)
        self.ui = UiLegacyWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self._variables_cache = []
        self._variable_count = 0
        self.text_line = CompletingPlainTextEdit()
        self.ui.layout.insertWidget(1, self.text_line)
        self.text_line.setPlainText(str(self.value))
        self.ui.value_label.setText(str(self.value_class))
        self.text_line.textChanged.connect(self.on_changed)
        self.change_value()

    def on_changed(self):
        new_count = self.variables_scrollArea.count()
        if new_count != self._variable_count:
            self._variables_cache = self.get_variables()
            self._variable_count = new_count
        self.text_line.completions.setStringList(self._variables_cache)
        self.change_value()
        self.edited.emit()

    def change_value(self):
        value = self.text_line.toPlainText()
        try:
            value = ast.literal_eval(value)
        except Exception:
            pass
        self.value = {self.value_class: value}

# --- PropertyFloat ---
class PropertyFloat(PropertyBase):
    def __init__(self, value_class, value, variables_scrollArea, int_bool=False, slider_range=[0, 0]):
        super().__init__(value_class, value, variables_scrollArea)
        self.ui = UiFloatWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.int_bool = int_bool

        self.float_widget = FloatWidget(slider_range=slider_range, int_output=int_bool)
        self.float_widget.edited.connect(self.on_changed)
        self.ui.layout.addWidget(self.float_widget)

        self.spacer = Spacer()
        self.ui.layout.addWidget(self.spacer)

        if self.int_bool:
            self.ui.logic_switch.setItemText(1, 'Int')
            self.ui.property_class.setStyleSheet("color: rgb(108, 135, 255);")
        else:
            self.ui.property_class.setStyleSheet("color: rgb(181, 255, 239);")

        self.ui.property_class.setText(prettify_class_name(self.value_class))
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        self.variable = ComboboxVariablesWidget(
            variables_layout=self.variables_scrollArea, filter_types=['Float', 'Int'], variable_name=self.value_class
        )
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

        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.OnlyFloat = True
        self.text_line.setPlaceholderText('Variable name, float or expression')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        self.ui.logic_switch.setCurrentIndex(0)
        self.text_line.setPlainText('0')

        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.text_line.setPlainText(str(value['m_Expression']))
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.variable.combobox.set_variable(str(value['m_SourceName']))
        elif isinstance(value, (float, int)):
            self.ui.logic_switch.setCurrentIndex(1)
            self.float_widget.set_value(value)

        self.on_changed()

    def logic_switch(self):
        idx = self.ui.logic_switch.currentIndex()
        self.text_line.OnlyFloat = False
        self.text_line.setVisible(idx == 3)
        self.float_widget.setVisible(idx == 1)
        self.variable_frame.setVisible(idx == 2)
        self.spacer.setVisible(idx == 0)

    def on_changed(self):
        self.logic_switch()
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables + expression_completer)
        self.change_value()
        self.edited.emit()

    def change_value(self):
        idx = self.ui.logic_switch.currentIndex()
        if idx == 0:
            self.value = None
        elif idx == 1:
            value = self.float_widget.value
            self.value = {self.value_class: round(float(value)) if self.int_bool else float(value)}
        elif idx == 2:
            value = self.variable.combobox.get_variable()
            try:
                value = ast.literal_eval(value)
            except Exception:
                pass
            self.value = {self.value_class: {'m_SourceName': str(value)}}
        elif idx == 3:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except Exception:
                pass
            self.value = {self.value_class: {'m_Expression': str(value)}}

# --- PropertyString ---
class PropertyString(PropertyBase):
    def __init__(self, value_class, value, variables_scrollArea, expression_bool=False, only_string=False, placeholder=None, only_variable=False, force_variable=False, filter_types=None):
        super().__init__(value_class, value, variables_scrollArea)
        self.ui = UiFloatWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.only_string = only_string
        self.expression_bool = expression_bool

        self.ui.logic_switch.setItemText(1, 'String')
        self.spacer = Spacer()
        self.ui.layout.addWidget(self.spacer)

        if filter_types is None:
            filter_types = ['String', 'MaterialGroup', 'Model']
        self.ui.property_class.setStyleSheet(
            "color: rgb(255, 123, 125);" if expression_bool else "color: rgb(255, 209, 153);"
        )
        self.ui.property_class.setText(prettify_class_name(self.value_class))
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.setPlaceholderText(placeholder or 'Variable name, string or expression')

        self.variable = ComboboxVariablesWidget(
            variables_layout=self.variables_scrollArea, filter_types=filter_types, variable_name=self.value_class
        )
        self.variable.setFixedWidth(256)
        self.variable.setMaximumHeight(24)
        self.variable.search_button.set_size(width=24, height=24)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.variable_frame = QWidget()
        self.variable_frame.setLayout(layout)
        self.variable_frame.setMinimumHeight(32)
        self.variable.combobox.changed.connect(self.on_changed)
        self.ui.layout.insertWidget(2, self.variable_frame)
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        # Initial value logic
        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.text_line.setPlainText(str(value['m_Expression']))
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.variable.combobox.set_variable(value['m_SourceName'])
        elif isinstance(value, str):
            if force_variable:
                self.ui.logic_switch.setCurrentIndex(2)
                self.variable.combobox.set_variable(str(value))
            else:
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
        idx = self.ui.logic_switch.currentIndex()
        self.variable_frame.setVisible(idx == 2)
        self.text_line.setVisible(idx in (1, 3))
        self.spacer.setVisible(idx == 0)

    def on_changed(self):
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables + expression_completer)
        self.change_value()
        self.edited.emit()

    def change_value(self):
        idx = self.ui.logic_switch.currentIndex()
        if idx == 0:
            self.value = None
        elif idx == 1:
            self.value = {self.value_class: self.text_line.toPlainText()}
        elif idx == 2:
            self.value = {self.value_class: {'m_SourceName': self.variable.combobox.get_variable()}}
        elif idx == 3:
            self.value = {self.value_class: {'m_Expression': str(self.text_line.toPlainText())}}

# --- PropertyVector3D ---
class PropertyVector3D(PropertyBase):
    edited = Signal()
    _pattern_phase1 = re.compile(r'm_fl|m_n|m_v|m_')
    _pattern_phase2 = re.compile(r'([a-z0-9])([A-Z])')

    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__(value_class, value, variables_scrollArea)
        self.ui = UiVector3DWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)

        intermediate = self._pattern_phase1.sub('', self.value_class)
        output = self._pattern_phase2.sub(r'\1 \2', intermediate)
        self.ui.property_class.setText(output)

        self.ui.logic_switch.currentIndexChanged.connect(self.on_changed)
        filter_types = ['Float', 'Int']

        self.variable_logic_switch = ComboboxVariablesWidget(
            variables_layout=self.variables_scrollArea,
            filter_types=['Vector3D'], variable_name=f"{self.value_class}"
        )
        self.variable_logic_switch.setMinimumWidth(256)
        self.variable_logic_switch.setMaximumHeight(24)
        self.variable_logic_switch.search_button.set_size(width=24, height=24)
        self.variable_logic_switch.combobox.changed.connect(self.on_changed)
        self.ui.layout.insertWidget(2, self.variable_logic_switch)

        self.float_widget_x = FloatWidget()
        self.float_widget_x.edited.connect(self.on_changed)
        self.ui.layout_x.insertWidget(2, self.float_widget_x)

        self.variable_x = ComboboxVariablesWidget(
            variables_layout=self.variables_scrollArea,
            filter_types=filter_types, variable_name=f"{self.value_class}_x"
        )
        self.variable_x.setMinimumWidth(256)
        self.variable_x.setMaximumHeight(24)
        self.variable_x.search_button.set_size(width=24, height=24)
        layout = QHBoxLayout()
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable_x)
        layout.addSpacerItem(spacer)
        self.variable_x_frame = QWidget()
        self.variable_x_frame.setLayout(layout)
        self.variable_x_frame.setMinimumHeight(32)
        self.variable_x.combobox.changed.connect(self.on_changed)
        self.ui.layout_x.insertWidget(3, self.variable_x_frame)

        self.text_line_x = CompletingPlainTextEdit()
        self.ui.layout_x.insertWidget(4, self.text_line_x)
        self.text_line_x.textChanged.connect(self.on_changed)
        self.ui.comboBox_x.currentIndexChanged.connect(self.on_changed)

        self.float_widget_y = FloatWidget()
        self.float_widget_y.edited.connect(self.on_changed)
        self.ui.layout_y.insertWidget(2, self.float_widget_y)

        self.variable_y = ComboboxVariablesWidget(
            variables_layout=self.variables_scrollArea,
            filter_types=filter_types, variable_name=f"{self.value_class}_y"
        )
        self.variable_y.setMinimumWidth(256)
        self.variable_y.setMaximumHeight(24)
        self.variable_y.search_button.set_size(width=24, height=24)
        layout = QHBoxLayout()
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable_y)
        layout.addSpacerItem(spacer)
        self.variable_y_frame = QWidget()
        self.variable_y_frame.setMinimumHeight(32)
        self.variable_y_frame.setLayout(layout)
        self.variable_y.combobox.changed.connect(self.on_changed)
        self.ui.layout_y.insertWidget(3, self.variable_y_frame)

        self.text_line_y = CompletingPlainTextEdit()
        self.ui.layout_y.insertWidget(4, self.text_line_y)
        self.text_line_y.textChanged.connect(self.on_changed)
        self.ui.comboBox_y.currentIndexChanged.connect(self.on_changed)

        self.float_widget_z = FloatWidget()
        self.float_widget_z.edited.connect(self.on_changed)
        self.ui.layout_z.insertWidget(2, self.float_widget_z)

        self.variable_z = ComboboxVariablesWidget(
            variables_layout=self.variables_scrollArea,
            filter_types=filter_types, variable_name=f"{self.value_class}_z"
        )
        self.variable_z.setMinimumWidth(196)
        self.variable_z.setMaximumHeight(24)
        self.variable_z.search_button.set_size(width=24, height=24)
        layout = QHBoxLayout()
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable_z)
        layout.addSpacerItem(spacer)
        self.variable_z_frame = QWidget()
        self.variable_z_frame.setMinimumHeight(32)
        self.variable_z_frame.setLayout(layout)
        self.variable_z.combobox.changed.connect(self.on_changed)
        self.ui.layout_z.insertWidget(3, self.variable_z_frame)

        self.text_line_z = CompletingPlainTextEdit()
        self.ui.layout_z.insertWidget(4, self.text_line_z)
        self.text_line_z.textChanged.connect(self.on_changed)
        self.ui.comboBox_z.currentIndexChanged.connect(self.on_changed)

        self.value = None
        self.ui.logic_switch.setCurrentIndex(0)

        def add_value(layout_widget, in_value, combo, variable, float_widget):
            if isinstance(in_value, dict):
                if 'm_Expression' in in_value:
                    layout_widget.setPlainText(str(in_value['m_Expression']))
                    combo.setCurrentIndex(2)
                if 'm_SourceName' in in_value:
                    variable.combobox.updateItems()
                    variable.combobox.addItem(in_value['m_SourceName'])
                    variable.combobox.setCurrentText(in_value['m_SourceName'])
                    combo.setCurrentIndex(1)
            elif isinstance(in_value, int) or isinstance(in_value, float):
                float_widget.SpinBox.setValue(in_value)
                float_widget.on_SpinBox_updated()
                combo.setCurrentIndex(0)
            else:
                layout_widget.setPlainText(str(in_value))
                combo.setCurrentIndex(0)

        if isinstance(value, dict):
            if 'm_Components' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                add_value(self.text_line_x, value['m_Components'][0], self.ui.comboBox_x,
                          self.variable_x, self.float_widget_x)
                add_value(self.text_line_y, value['m_Components'][1], self.ui.comboBox_y,
                          self.variable_y, self.float_widget_y)
                add_value(self.text_line_z, value['m_Components'][2], self.ui.comboBox_z,
                          self.variable_z, self.float_widget_z)
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(1)
                self.var_value = value['m_SourceName']
                self.variable_logic_switch.combobox.addItem(value['m_SourceName'])
                self.variable_logic_switch.combobox.setCurrentText(value['m_SourceName'])
        elif isinstance(value, list):
            self.ui.logic_switch.setCurrentIndex(2)
            add_value(self.text_line_x, value[0], self.ui.comboBox_x,
                      self.variable_x, self.float_widget_x)
            add_value(self.text_line_y, value[1], self.ui.comboBox_y,
                      self.variable_y, self.float_widget_y)
            add_value(self.text_line_z, value[2], self.ui.comboBox_z,
                      self.variable_z, self.float_widget_z)

        self.on_changed()

    def logic_switch_line(self):
        if self.ui.comboBox_x.currentIndex() == 0:
            self.text_line_x.hide()
            self.float_widget_x.show()
            self.variable_x_frame.hide()
        elif self.ui.comboBox_x.currentIndex() == 1:
            self.text_line_x.hide()
            self.float_widget_x.hide()
            self.variable_x_frame.show()
        else:
            self.text_line_x.show()
            self.float_widget_x.hide()
            self.variable_x_frame.hide()

        if self.ui.comboBox_y.currentIndex() == 0:
            self.text_line_y.hide()
            self.float_widget_y.show()
            self.variable_y_frame.hide()
        elif self.ui.comboBox_y.currentIndex() == 1:
            self.text_line_y.hide()
            self.float_widget_y.hide()
            self.variable_y_frame.show()
        else:
            self.text_line_y.show()
            self.float_widget_y.hide()
            self.variable_y_frame.hide()

        if self.ui.comboBox_z.currentIndex() == 0:
            self.text_line_z.hide()
            self.float_widget_z.show()
            self.variable_z_frame.hide()
        elif self.ui.comboBox_z.currentIndex() == 1:
            self.text_line_z.hide()
            self.float_widget_z.hide()
            self.variable_z_frame.show()
        else:
            self.text_line_z.show()
            self.float_widget_z.hide()
            self.variable_z_frame.hide()

    def logic_switch(self):
        widget = self.ui.layout.itemAt(2).widget()
        if self.ui.logic_switch.currentIndex() == 0:
            self.ui.frame_4.setMaximumHeight(0)
            widget.hide()
            self.variable_logic_switch.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.ui.frame_4.setMaximumHeight(0)
            widget.show()
            self.variable_logic_switch.show()
        else:
            self.ui.frame_4.setMaximumHeight(1600)
            if isinstance(widget, CompletingPlainTextEdit):
                widget.hide()
            self.variable_logic_switch.hide()

    def on_changed(self):
        variables = self.get_variables()
        self.text_line_x.completions.setStringList(variables + expression_completer)
        self.text_line_y.completions.setStringList(variables + expression_completer)
        self.text_line_z.completions.setStringList(variables + expression_completer)
        self.logic_switch_line()
        self.logic_switch()
        self.change_value()
        self.edited.emit()

    def change_value(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = None
        elif self.ui.logic_switch.currentIndex() == 1:
            value = self.variable_logic_switch.combobox.get_variable()
            self.value = {self.value_class: {'m_SourceName': value}}
        elif self.ui.logic_switch.currentIndex() == 2:
            def handle_value(line, combo_box, variable, float_widget):
                index = combo_box.currentIndex()
                if index == 0:
                    return float_widget.value
                elif index == 1:
                    return {'m_SourceName': variable.combobox.get_variable()}
                return {'m_Expression': line.toPlainText()}

            value_x = handle_value(self.text_line_x, self.ui.comboBox_x,
                                   self.variable_x, self.float_widget_x)
            value_y = handle_value(self.text_line_y, self.ui.comboBox_y,
                                   self.variable_y, self.float_widget_y)
            value_z = handle_value(self.text_line_z, self.ui.comboBox_z,
                                   self.variable_z, self.float_widget_z)
            self.value = {self.value_class: {'m_Components': [value_x, value_y, value_z]}}

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

# --- PropertyVariableOutput ---
class PropertyVariableOutput(PropertyBase):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__(value_class, value, variables_scrollArea)
        self.ui = UiFloatWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)

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

        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, variable_type='Float', filter_types=['Float', 'Int'], variable_name=self.value_class)
        self.variable.setMaximumHeight(24)
        self.variable.search_button.set_size(width=24, height=24)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.variable_frame = QWidget()
        self.variable_frame.setMinimumHeight(32)
        self.variable_frame.setLayout(layout)
        self.variable.combobox.changed.connect(self.on_changed)
        self.ui.layout.insertWidget(2, self.variable_frame)

        if isinstance(value, dict):
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
                self.variable.combobox.set_variable(value['m_SourceName'])
                debug(f'Loaded value in variable widget: dict {value["m_SourceName"]}')
        elif isinstance(value, str):
            self.variable.combobox.set_variable(value)
            debug(f'Loaded value in variable widget: str {value}')
        else:
            self.variable.combobox.set_variable(str(value))
            debug(f'Loaded value in variable widget: None {value}')
        self.on_changed()
    def on_changed(self):
        self.change_value()
        self.edited.emit()
    def change_value(self):
        self.value = {self.value_class: self.variable.combobox.get_variable()}
        debug(f'Changed value in variable widget {self.value}')

# --- PropertyVariableValue ---
class PropertyVariableValue(PropertyBase):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__(value_class, value, variables_scrollArea)
        self.ui = UiSetVariableWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.m_TargetName: str = None
        self.m_DataType: str = None
        self.m_Value = None
        self.variables_scrollArea = variables_scrollArea

        self.float_widget = FloatWidget(slider_range=[0,0], int_output=False)
        self.float_widget.edited.connect(self.on_changed)
        self.ui.layout_3.addWidget(self.float_widget)

        BOOL_COLOR = '(255, 189, 190)'
        FLOAT_COLOR = '(181, 255, 239)'
        STRING_COLOR = '(255, 209, 153)'

        self.ui.property_class_4.setStyleSheet(f"color: rgb{STRING_COLOR};")
        self.ui.property_class.setStyleSheet(f"color: rgb{STRING_COLOR};")

        from src.widgets import BoolWidget
        self.bool_widget = BoolWidget()
        self.bool_widget.edited.connect(self.on_changed)
        self.bool_widget.checkbox.setStyleSheet('border:None; font: 580 9pt "Segoe UI";')
        self.ui.layout_3.addWidget(self.bool_widget)

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

        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, filter_types=['Float', 'Int', 'Bool'], variable_name=self.value_class)
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
        BOOL_COLOR = '(255, 189, 190)'
        FLOAT_COLOR = '(181, 255, 239)'
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

# --- PropertyComment ---
class PropertyComment(Property):
    edited = Signal()
    def __init__(self, value_class, value):
        super().__init__()
        self.ui = UiCommentWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.value_class = value_class
        self.value = value

        self.ui.text_field.setPlainText(value)
        self.ui.text_field.textChanged.connect(self.on_changed)
        self.change_value()

    def on_changed(self):
        self.change_value()
        self.edited.emit()

    def change_value(self):
        value = self.ui.text_field.toPlainText()
        self.value = {self.value_class: str(value)}

# --- PropertyColorMatch ---
class PropertyColorMatch(Property):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = UiColorMatchWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value

        self.color = [255, 255, 255]

        self.variables_scrollArea = variables_scrollArea

        self.dialog = QColorDialog()
        self.dialog.setStyleSheet(QT_Stylesheet_global)

        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for key, value in item.items():
                        self.add_color_widget(key, value)

        self.ui.add_color_widget.clicked.connect(lambda: self.add_color_widget(key='m_Color', value=[255,255,255]))

        self.on_changed()

    def add_color_widget(self, key, value):
        from src.editors.smartprop_editor.property.color import PropertyColor
        ColorInstance = PropertyColor(key, value, self.variables_scrollArea)
        delete_button = QToolButton()
        delete_button.setStyleSheet("""QToolButton {
	icon: url(:/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);
    font: 700 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 0px;
    border-color: rgba(80, 80, 80, 255);
    height:18px;
    padding: 4px;
    padding-left: 6px;
    padding-right: 6px;
    color: #E3E3E3;
    background-color: #1C1C1C;
}
QToolButton:hover {
    background-color: #414956;
    color: white;
}
QToolButton:pressed {
    background-color: red;
    background-color: #1C1C1C;
    margin: 1 px;
    margin-left: 2px;
    margin-right: 2px;
    font: 580 9pt "Segoe UI";

}""")
        delete_icon_path = ":/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"
        delete_icon = QIcon(delete_icon_path)
        delete_button.setIcon(delete_icon)
        delete_button.clicked.connect(lambda: self.delete_action(ColorInstance))
        ColorInstance.ui.layout.addWidget(delete_button)
        ColorInstance.edited.connect(self.on_changed)
        self.ui.layout_color.addWidget(ColorInstance)
        self.on_changed()

    def delete_action(self, widget):
        widget.deleteLater()

    def on_changed(self):
        self.change_value()
        self.edited.emit()
    def change_value(self):
        value = []
        for i in range(self.ui.layout_color.count()):
            item = self.ui.layout_color.itemAt(i).widget()
            if hasattr(item, "value"):
                value.append(item.value)
        self.value = {self.value_class: value}

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

# --- PropertyComparison ---
class PropertyComparison(Property):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = UiComparisonWidget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea

        self.ui.comparison.currentTextChanged.connect(self.on_changed)

        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, variable_name=self.value_class)
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
        self.ui.layout_2.insertWidget(1, self.variable_frame)

        self.m_value = CompletingPlainTextEdit()
        self.m_value.completion_tail = ''
        self.m_value.setPlaceholderText('Value')
        self.ui.layout_2.insertWidget(4, self.m_value)
        self.m_value.textChanged.connect(self.on_changed)

        if isinstance(value, dict):
            if 'm_Name' in value:
                name_value = value['m_Name']
                self.variable.combobox.set_variable(str(name_value))
            if 'm_Value' in value:
                self.m_value.setPlainText(str(value['m_Value']))

        self.on_changed()

    def on_changed(self):
        variables = self.get_variables()
        self.m_value.completions.setStringList(variables)
        self.change_value()
        self.edited.emit()
    def change_value(self):
        var_value = self.m_value.toPlainText()
        try:
            var_value = ast.literal_eval(var_value)
        except:
            pass

        self.value = {self.value_class: {'m_Name': self.variable.combobox.get_variable(), 'm_Value': var_value,'m_Comparison': self.ui.comparison.currentText()}}

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variablesScrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

# --- PropertyBool ---
class PropertyBool(Property):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        from src.editors.smartprop_editor.property.ui_bool import Ui_Widget
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
        self.text_line.setPlaceholderText('Expression')
        self.ui.layout.insertWidget(3, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        self.ui.value.stateChanged.connect(self.on_changed)

        self.ui.logic_switch.setCurrentIndex(0)
        self.text_line.setPlainText('')

        # Variable setup
        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, filter_types=['Bool'], variable_name=self.value_class)
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
            self.ui.value.hide()
            if hasattr(self, 'variable_frame'):
                self.variable_frame.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.ui.value.show()
            if hasattr(self, 'variable_frame'):
                self.variable_frame.hide()
        elif self.ui.logic_switch.currentIndex() == 2:
            self.text_line.hide()
            self.ui.value.hide()
            if hasattr(self, 'variable_frame'):
                self.variable_frame.show()
        else:
            self.text_line.show()
            if hasattr(self, 'variable_frame'):
                self.variable_frame.hide()
            self.ui.value.hide()

    def on_changed(self):
        self.logic_switch()
        self.ui.value.setText(str(self.ui.value.isChecked()))
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables)
        self.change_value()
        self.edited.emit()
    def change_value(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = None
        elif self.ui.logic_switch.currentIndex() == 1:
            self.value = {self.value_class: self.ui.value.isChecked()}
        elif self.ui.logic_switch.currentIndex() == 2:
            value = self.variable.combobox.get_variable()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_SourceName': value}}
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

# --- PropertyCombobox ---
class PropertyCombobox(Property):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea, items, filter_types):
        super().__init__()
        from src.editors.smartprop_editor.property.ui_combobox import Ui_Widget
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea

        self._variable_count = 0
        self._cached_variables = []

        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2',
                  re.sub(r'm_fl|m_n|m_b|m_', '', self.value_class))
        self.ui.property_class.setText(output)

        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)
        self.ui.logic_switch.setItemText(1, output)

        self.ui.value.addItems(items)
        self.ui.value.currentTextChanged.connect(self.on_changed)

        spacer_item = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.spacer = QWidget()
        spacer_layout = QHBoxLayout()
        spacer_layout.addSpacerItem(spacer_item)
        spacer_layout.setContentsMargins(0, 0, 0, 0)
        self.spacer.setLayout(spacer_layout)
        self.spacer.setStyleSheet('border:None;')
        self.spacer.setContentsMargins(0, 0, 0, 0)
        self.ui.layout.addWidget(self.spacer)

        self.variable = ComboboxVariablesWidget(
            variables_layout=self.variablesScrollArea,
            filter_types=filter_types, variable_name=self.value_class
        )
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
                self.text_line.setPlainText(self.var_value)
            elif 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.variable.combobox.set_variable(str(value['m_SourceName']))
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
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = None
        elif self.ui.logic_switch.currentIndex() == 1:
            self.value = {self.value_class: self.ui.value.currentText()}
        elif self.ui.logic_switch.currentIndex() == 2:
            val = self.variable.combobox.get_variable()
            try:
                val = ast.literal_eval(val)
            except:
                pass
            self.value = {self.value_class: {'m_SourceName': str(val)}}
        elif self.ui.logic_switch.currentIndex() == 3:
            val = self.text_line.toPlainText()
            try:
                val = ast.literal_eval(val)
            except:
                pass
            self.value = {self.value_class: {'m_Expression': str(val)}}

    def get_variables(self, search_term=None):
        new_count = self.variables_scrollArea.count()
        if new_count != self._variable_count:
            data_out = []
            for i in range(self.variables_scrollArea.count()):
                widget = self.variables_scrollArea.itemAt(i).widget()
                if widget:
                    data_out.append(widget.name)
            self._cached_variables = data_out
            self._variable_count = new_count
        return self._cached_variables

# --- PropertySurface ---
class PropertySurface(Property):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        from src.editors.smartprop_editor.property.ui_filtersurface import Ui_Widget
        from src.editors.smartprop_editor.objects import surfaces_list
        from src.widgets.popup_menu.main import PopupMenu
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value

        self.color = [255, 255, 255]
        self.variables_scrollArea = variables_scrollArea

        self.ui.surfaces_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.surfaces_tree.customContextMenuRequested.connect(self.open_hierarchy_menu)

        self.dialog = QColorDialog()
        self.dialog.setStyleSheet(QT_Stylesheet_global)

        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)

        if isinstance(value, list):
            for key in value:
                item = QTreeWidgetItem()
                item.setText(0, key)
                self.ui.surfaces_tree.invisibleRootItem().addChild(item)

        self.ui.add_surface.clicked.connect(self.surface_popup)

        self.on_changed()
    def add_surface(self, name, value):
        item = QTreeWidgetItem()
        item.setText(0, name)
        self.ui.surfaces_tree.invisibleRootItem().addChild(item)
        self.on_changed()

    def open_hierarchy_menu(self, position):
        menu = QMenu()
        delete_action = menu.addAction("Delete item")
        delete_action.triggered.connect(lambda: self.delete_selected_tree_items())
        menu.exec(self.ui.surfaces_tree.viewport().mapToGlobal(position))

    def delete_selected_tree_items(self):
        selected_items = self.ui.surfaces_tree.selectedItems()
        for item in selected_items:
            parent = item.parent()
            if parent is not None:
                parent.removeChild(item)
            else:
                self.ui.surfaces_tree.invisibleRootItem().removeChild(item)
        self.on_changed()

    def surface_popup(self):
        from src.editors.smartprop_editor.objects import surfaces_list
        from src.widgets.popup_menu.main import PopupMenu
        elements_in_popupmenu = []
        existing_items = []
        for i in range(self.ui.surfaces_tree.topLevelItemCount()):
            item = self.ui.surfaces_tree.topLevelItem(i)
            existing_items.append(item.text(0))
        for item in surfaces_list:
            for key, value in item.items():
                if key in existing_items:
                    pass
                else:
                    elements_in_popupmenu.append(item)

        self.popup_menu = PopupMenu(elements_in_popupmenu, add_once=True, window_name='SPE_Property_filtersurface')
        self.popup_menu.add_property_signal.connect(lambda name, value: self.add_surface(name, value))
        self.popup_menu.show()

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
        self.change_value()
        self.edited.emit()
    def change_value(self):
        value = []
        for i in range(self.ui.surfaces_tree.topLevelItemCount()):
            item = self.ui.surfaces_tree.topLevelItem(i)
            value.append(item.text(0))
        self.value = {self.value_class: value}

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variables_scrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out

# --- PropertyColor ---
class PropertyColor(Property):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        from src.editors.smartprop_editor.property.ui_color import Ui_Widget
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value

        self.color = [255, 255, 255]
        self.ui.logic_switch.setCurrentIndex(0)

        self.variables_scrollArea = variables_scrollArea

        self.dialog = QColorDialog()
        self.dialog.setStyleSheet(QT_Stylesheet_global)

        output = re.sub(r'm_fl|m_n|m_b|m_s|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, filter_types=['Color'], variable_name=self.value_class)
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

        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.setPlaceholderText('Variable name, RGB or expression')
        self.ui.layout.insertWidget(2, self.text_line)
        self.text_line.textChanged.connect(self.on_changed)

        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.text_line.setPlainText(self.var_value)
                self.color = [255, 255, 255]
            elif 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.color = [255, 255 ,255]
                self.var_value = value['m_SourceName']
                self.variable.combobox.set_variable(str(self.var_value))
            else:
                self.color = [255, 255, 255]
        elif isinstance(value, list):
            self.ui.logic_switch.setCurrentIndex(1)
            self.color = value

        self.ui.value.clicked.connect(self.open_dialog)

        self.on_changed()

    def open_dialog(self):
        color_dialog = self.dialog
        selected_color = color_dialog.getColor(QColor(*self.color))
        if selected_color.isValid():
            color = selected_color.getRgb()[:3]
            self.ui.value.setStyleSheet(f"""background-color: rgb{color};
                padding:4px;
                border:0px;
                border: 2px solid translucent;
                border-color: rgba(80, 80, 80, 100);
                """)
            self.color = list(color)
            self.on_changed()

    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.text_line.hide()
            self.ui.value.hide()
            self.variable_frame.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.ui.value.show()
            self.variable_frame.hide()
        elif self.ui.logic_switch.currentIndex() == 2:
            self.text_line.hide()
            self.ui.value.hide()
            self.variable_frame.show()
        else:
            self.text_line.show()
            self.ui.value.hide()

    def on_changed(self):
        self.logic_switch()
        variables = self.get_variables()
        self.text_line.completions.setStringList(variables)
        self.change_value()
        self.ui.value.setStyleSheet(f"""background-color: rgb{tuple(self.color)};
            padding:4px;
            border:0px;
            border: 2px solid translucent;
            border-color: rgba(80, 80, 80, 100);
            """)
        self.edited.emit()
    def change_value(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = None
        elif self.ui.logic_switch.currentIndex() == 1:
            self.value = {self.value_class: self.color}
        elif self.ui.logic_switch.currentIndex() == 2:
            value = self.variable.combobox.get_variable()
            self.value = {self.value_class: {'m_SourceName': value}}
        elif self.ui.logic_switch.currentIndex() == 3:
            value = self.text_line.toPlainText()
            try:
                value = ast.literal_eval(value)
            except:
                pass
            self.value = {self.value_class: {'m_Expression': value}}

    def get_variables(self, search_term=None):
        data_out = []
        for i in range(self.variables_scrollArea.count()):
            widget = self.variablesScrollArea.itemAt(i).widget()
            if widget:
                data_out.append(widget.name)
        return data_out