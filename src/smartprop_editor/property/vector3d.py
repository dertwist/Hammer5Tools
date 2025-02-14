import re

from src.smartprop_editor.property.ui_vector3d import Ui_Widget
from src.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QSizePolicy, QSpacerItem, QHBoxLayout
from PySide6.QtCore import Signal
from src.smartprop_editor.objects import expression_completer
from src.widgets import FloatWidget, ComboboxVariablesWidget


class PropertyVector3D(QWidget):
    edited = Signal()

    # Precompile patterns for faster initialization
    _pattern_phase1 = re.compile(r'm_fl|m_n|m_v|m_')
    _pattern_phase2 = re.compile(r'([a-z0-9])([A-Z])')

    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea

        # Performance: Build output string in a single pass
        intermediate = self._pattern_phase1.sub('', self.value_class)
        output = self._pattern_phase2.sub(r'\1 \2', intermediate)
        self.ui.property_class.setText(output)

        self.ui.logic_switch.currentIndexChanged.connect(self.on_changed)
        filter_types = ['Float', 'Int']

        # Variable
        self.variable_logic_switch = ComboboxVariablesWidget(
            variables_layout=self.variables_scrollArea,
            filter_types=['Vector3D'], variable_name=f"{self.value_class}"
        )
        self.variable_logic_switch.setMinimumWidth(256)
        self.variable_logic_switch.setMaximumHeight(24)
        self.variable_logic_switch.search_button.set_size(width=24, height=24)
        self.variable_logic_switch.combobox.changed.connect(self.on_changed)
        self.ui.layout.insertWidget(2, self.variable_logic_switch)

        # Vector X Setup
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

        # Vector Y Setup
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

        # Vector Z Setup
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

        # Default states
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

        # Performance: reduce logic for dict or list by pre-determining the structure
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