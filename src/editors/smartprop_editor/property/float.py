import ast
import re
from src.editors.smartprop_editor.property.ui_float import Ui_Widget
from src.widgets.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QSizePolicy, QSpacerItem, QHBoxLayout, QWidget
from PySide6.QtCore import Signal
from src.widgets import FloatWidget
from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.editors.smartprop_editor.widgets.expression_editor.main import ExpressionEditor
from src.editors.smartprop_editor.property.base_pooled import PooledPropertyMixin

class PropertyFloat(QWidget, PooledPropertyMixin):
    edited = Signal()
    slider_pressed = Signal()
    committed = Signal()

    def __init__(self, element_id_generator, value_class, value, variables_scrollArea, int_bool=False, slider_range=[0, 0]):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.value = value
        self.int_bool = int_bool
        self.variables_scrollArea = variables_scrollArea
        self._slider_range = slider_range
        self._filter_types = ['Int', 'Float'] if int_bool else ['Float', 'Int']

        self.ui.logic_switch.wheelEvent = lambda event: None

        # Float widget setup
        self.float_widget = FloatWidget(slider_range=slider_range, int_output=int_bool)
        self.float_widget.edited.connect(self.on_changed)
        self.float_widget.slider_pressed.connect(self.slider_pressed)
        self.float_widget.committed.connect(self.committed)
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
        self.variable = ComboboxVariablesWidget(
            variables_layout=self.variables_scrollArea,
            filter_types=self._filter_types,
            variable_name=self.value_class,
            element_id_generator=element_id_generator,
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


        # EditLine setup
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.text_line.OnlyFloat = True
        self.text_line.setPlaceholderText('Variable name, float or expression')
        self.expression_editor = ExpressionEditor(self.text_line, self.variables_scrollArea)
        self.ui.layout.insertWidget(2, self.text_line)
        self.ui.layout.insertWidget(2, self.expression_editor)
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
            self.expression_editor.hide()
            self.float_widget.hide()
            self.variable_frame.hide()
            self.spacer.show()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.text_line.hide()
            self.expression_editor.hide()
            self.float_widget.show()
            self.variable_frame.hide()
            self.spacer.hide()
        elif self.ui.logic_switch.currentIndex() == 2:
            self.text_line.hide()
            self.expression_editor.hide()
            self.float_widget.hide()
            self.variable_frame.show()
            self.spacer.hide()
        else:
            self.text_line.OnlyFloat = False
            self.text_line.show()
            self.expression_editor.show()
            self.variable_frame.hide()
            self.float_widget.hide()
            self.spacer.hide()

    def on_changed(self):
        self._update_display_and_value()
        self.edited.emit()

    def _update_display_and_value(self):
        self.logic_switch()

        # Setup type-aware completer for expression mode without filters
        if self.ui.logic_switch.currentIndex() == 3:  # Expression mode
            CompletionUtils.setup_completer_for_widget(
                self.text_line,
                self.variables_scrollArea,
                filter_types=None,  # No filtering - show all variable types
                context='numeric',
            )

        self.change_value()
        
    def change_value(self):
        # Default
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = {self.value_class: None}
            self.value = None
        #Float or int
        elif self.ui.logic_switch.currentIndex() == 1:
            # In Float mode the text_line is hidden; read the slider/spinbox directly.
            # The old pattern (text_line → set_value) was resetting the slider to '0'
            # (the initial placeholder text) on every change, discarding user drags.
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
        return CompletionUtils.get_available_variable_names(self.variables_scrollArea)

    # ===== Pooling implementation =====
    @classmethod
    def _pool_key_from_kwargs(cls, int_bool=False, slider_range=None, **kwargs):
        slider_range = slider_range if slider_range is not None else [0, 0]
        filter_types = ['Int', 'Float'] if int_bool else ['Float', 'Int']
        return (bool(int_bool), tuple(filter_types), tuple(slider_range))

    def _current_pool_key(self):
        return (bool(self.int_bool), tuple(getattr(self, "_filter_types", ['Float', 'Int'])), tuple(getattr(self, "_slider_range", [0, 0])))

    def reconfigure(
        self,
        element_id_generator,
        value_class,
        value,
        variables_scrollArea,
        int_bool=False,
        slider_range=None,
        **kwargs,
    ):
        """
        Reconfigure this instance for a new float/int property without reconstruction.
        """
        # Normalize slider_range to match constructor behavior.
        if slider_range is None:
            slider_range = getattr(self, "_slider_range", [0, 0])

        children_to_block = [
            self.ui.logic_switch,
            self.float_widget,
            self.text_line,
            self.variable.combobox,
            self.ui.property_class,
        ]
        for c in children_to_block:
            c.blockSignals(True)

        try:
            # STEP 2: Update identity attributes FIRST.
            self.value_class = value_class
            self.value = value
            self.int_bool = int_bool
            self.variables_scrollArea = variables_scrollArea
            self.element_id_generator = element_id_generator
            self._slider_range = slider_range
            self._filter_types = ['Int', 'Float'] if int_bool else ['Float', 'Int']

            # STEP 3: Reset child components holding external references.
            self.variable.reset(
                variables_layout=variables_scrollArea,
                filter_types=self._filter_types,
                variable_name=value_class,
                element_id_generator=element_id_generator,
            )
            self.expression_editor.reset(variables_scrollArea)

            # STEP 4: Reset CompletingPlainTextEdit state flags.
            self.text_line.completion_tail = ''
            self.text_line.setPlainText('0')

            # STEP 5: Update the label text (pure display, no signal path).
            output = re.sub(r'm_fl|m_n|m_b|m_', '', self.value_class)
            output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)
            self.ui.property_class.setText(output)

            # STEP 6: Update stylesheet if int_bool changed.
            if int_bool:
                self.ui.property_class.setStyleSheet("""
                    border:0px; background-color: rgba(255,255,255,0);
                    font: 8pt "Segoe UI"; padding-right: 16px;
                    color: rgb(108, 135, 255);
                """)
            else:
                self.ui.property_class.setStyleSheet("""
                    border:0px; background-color: rgba(255,255,255,0);
                    font: 8pt "Segoe UI"; padding-right: 16px;
                    color: rgb(181, 255, 239);
                """)

            # STEP 7: Apply the new mode/value.
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

            # signals were blocked; sync add-button visibility manually.
            self.variable.update_add_button_visibility(self.variable.combobox.currentText())
        finally:
            for c in children_to_block:
                c.blockSignals(False)

        # STEP 9: Sync display state and compute self.value without emitting edited.
        self._update_display_and_value()