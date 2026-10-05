from gui.editors.smartprop_editor.property.ui_comparison import Ui_Widget
import ast
import re
from gui.widgets.completer_widget import CompletingPlainTextEdit
from PySide6.QtWidgets import QSizePolicy, QSpacerItem, QHBoxLayout, QWidget, QFrame, QLabel
from PySide6.QtCore import Signal
from gui.editors.smartprop_editor.combobox_variables import ComboboxVariablesWidget
from gui.editors.smartprop_editor.completion_utils import CompletionUtils
from gui.editors.smartprop_editor.property import compact


def _display_name(value_class):
    """`m_ComparisonValue` -> `Comparison Value`, as the other editors label."""
    text = re.sub(r'm_fl|m_n|m_b|m_s|m_v|m_', '', value_class or '')
    return re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text)


class PropertyComparison(QWidget):
    edited = Signal()
    def __init__(self, value_class, value, variables_scrollArea, element_id_generator):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea

        # Variable setup
        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, variable_name=self.value_class, element_id_generator=element_id_generator)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.variable)
        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.variable_frame = QWidget()
        self.variable_frame.setLayout(layout)
        self.variable.setFixedWidth(256)

        self.m_value = CompletingPlainTextEdit()
        self.m_value.completion_tail = ''
        self.m_value.setPlaceholderText('Value')
        compact.style_text_line(self.m_value)

        # Header row keeps the operator; name and value become indented
        # sub-rows under it, the way Vector3D lays out X/Y/Z. All three used to
        # share one line, which left each field about a third of the panel.
        self.header_label = QLabel(_display_name(value_class))
        self.ui.layout_2.insertWidget(0, self.header_label)

        self.name_frame = self._sub_row(self.ui.property_class_2, "Variable Name", self.variable_frame)
        self.value_frame = self._sub_row(self.ui.property_class_3, "Value", self.m_value)

        if isinstance(value, dict):
            if 'm_Name' in value:
                name_value = value['m_Name']
                self.variable.combobox.set_variable(str(name_value))
            if 'm_Value' in value:
                self.m_value.setPlainText(str(value['m_Value']))
            if 'm_Comparison' in value:
                self.ui.comparison.setCurrentText(str(value['m_Comparison']))

        self.ui.comparison.currentTextChanged.connect(self.on_changed)
        self.variable.combobox.changed.connect(self.on_changed)
        self.m_value.textChanged.connect(self.on_changed)

        self.on_changed()

        # Compact Source2-style rows. The .ui names its frame/label differently
        # from the other editors, and the comparison operator takes the place
        # of the value-mode switch on the header row.
        compact.apply_plain_row(self, self.ui.frame_2, self.header_label,
                                label_color="#B5FFEF", clamp_height=False)
        self._compact_frames = [self.ui.frame_2, self.name_frame, self.value_frame]
        compact.style_value_combobox(self.ui.comparison)
        compact.compact_variable_frame(self.variable_frame, self.variable)

    def _sub_row(self, label, text, editor):
        """An indented `label: editor` frame appended under the header row."""
        frame = QFrame()
        row = QHBoxLayout(frame)
        row.setContentsMargins(6, 0, 4, 0)
        row.setSpacing(4)
        label.setParent(None)
        label.setText(text)
        compact.style_label(label, color="#B5FFEF")
        compact.indent_label(label)
        row.addWidget(label)
        row.addWidget(editor)
        row.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        compact.compact_frame(frame)
        self.ui.verticalLayout.addWidget(frame)
        return frame


    def on_changed(self):
        # Setup type-aware completer without filters
        CompletionUtils.setup_completer_for_widget(
            self.m_value,
            self.variables_scrollArea,
            filter_types=None,  # No filtering - show all variable types
            context='comparison'
        )
        
        self.change_value()
        self.edited.emit()
        
    def change_value(self):
        # Default
        var_value = self.m_value.toPlainText()
        try:
            var_value = ast.literal_eval(var_value)
        except:
            pass

        self.value = {self.value_class: {'m_Name': self.variable.combobox.get_variable(), 'm_Value': var_value,'m_Comparison': self.ui.comparison.currentText()}}

    def get_variables(self, search_term=None):
        return CompletionUtils.get_available_variable_names(self.variables_scrollArea)