import re
from src.editors.smartprop_editor.property.ui_float import Ui_Widget
from src.widgets.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget, QSizePolicy, QSpacerItem, QHBoxLayout
from PySide6.QtCore import Signal
from src.widgets import Spacer
from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.editors.smartprop_editor.widgets.expression_editor.main import ExpressionEditor
from src.editors.smartprop_editor.property.base_pooled import PooledPropertyMixin

class PropertyString(QWidget, PooledPropertyMixin):
    edited = Signal()
    def __init__(self, element_id_generator, value_class, value, variables_scrollArea, expression_bool=False, only_string=False, placeholder=None, only_variable=False, force_variable=False, filter_types=None, parent=None):
        super().__init__(parent)
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(False)
        self.value_class = value_class
        self.element_id_generator =element_id_generator
        self.value = value
        self.only_string = only_string
        self.expression_bool = expression_bool
        self.variables_scrollArea = variables_scrollArea

        self.ui.logic_switch.setItemText(1, 'String')
        self.spacer = Spacer()
        self.ui.layout.addWidget(self.spacer)

        if filter_types is None:
            filter_types = ['String', 'MaterialGroup', 'Model']
        self._pool_filter_types = list(filter_types)
        self._pool_expression_bool = bool(expression_bool)
        self._pool_only_string = bool(only_string)
        self._pool_only_variable = bool(only_variable)
        self._pool_force_variable = bool(force_variable)
        if expression_bool:
            self.ui.property_class.setStyleSheet("""
                        border:0px;
            background-color: rgba(255, 255, 255, 0);
            font: 8pt "Segoe UI";
            padding-right: 16px;

            color: rgb(255, 123, 125);
                        """)
        else:
            self.ui.property_class.setStyleSheet("""
                        border:0px;
            background-color: rgba(255, 255, 255, 0);
            font: 8pt "Segoe UI";
            padding-right: 16px;

            color: rgb(255, 209, 153);
                        """)


        output = re.sub(r'm_fl|m_n|m_b|m_s|m_v|m_f|m_', '', self.value_class)
        output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)

        self.ui.property_class.setText(output)
        self.ui.logic_switch.currentTextChanged.connect(self.on_changed)

        # EditLine
        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.expression_editor = ExpressionEditor(self.text_line, self.variables_scrollArea)

        # Variable
        self.variable = ComboboxVariablesWidget(variables_layout=self.variables_scrollArea, filter_types=filter_types, variable_name=self.value_class, element_id_generator=element_id_generator)
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

        if placeholder:
            self.text_line.setPlaceholderText(placeholder)
        else:
            self.text_line.setPlaceholderText('Variable name, string or expression')
        self.ui.layout.insertWidget(3, self.text_line)
        self.ui.layout.insertWidget(2, self.expression_editor)
        self.text_line.textChanged.connect(self.on_changed)
        if isinstance(value, dict):
            if 'm_Expression' in value:
                self.ui.logic_switch.setCurrentIndex(3)
                self.var_value = value['m_Expression']
                self.text_line.setPlainText(str(self.var_value))
            if 'm_SourceName' in value:
                self.ui.logic_switch.setCurrentIndex(2)
                self.var_value = value['m_SourceName']
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
        self._update_display_and_value()

        # Cache pool key after finalizing derived filter_types and flags.
        self._pool_key = self._pool_key_from_kwargs(
            expression_bool=self._pool_expression_bool,
            only_string=self._pool_only_string,
            only_variable=self._pool_only_variable,
            force_variable=self._pool_force_variable,
            filter_types=self._pool_filter_types,
        )

    def logic_switch(self):
        if self.ui.logic_switch.currentIndex() == 0:
            self.variable_frame.hide()
            self.text_line.hide()
            self.spacer.show()
            self.expression_editor.hide()
        elif self.ui.logic_switch.currentIndex() == 1:
            self.variable_frame.hide()
            self.text_line.show()
            self.spacer.hide()
            self.expression_editor.hide()
        elif self.ui.logic_switch.currentIndex() == 2:
            self.variable_frame.show()
            self.text_line.hide()
            self.spacer.hide()
            self.expression_editor.hide()
        elif self.ui.logic_switch.currentIndex() == 3:
            self.variable_frame.hide()
            self.text_line.show()
            self.spacer.hide()
            self.expression_editor.show()

    def _update_display_and_value(self):
        self.logic_switch()
        CompletionUtils.setup_completer_for_widget(
            self.text_line,
            self.variables_scrollArea,
        )

        self.change_value()

    def on_changed(self):
        self._update_display_and_value()
        self.edited.emit()
        
    def change_value(self):
        # Default
        if self.ui.logic_switch.currentIndex() == 0:
            self.value = {self.value_class: None}
            self.value = None
        #Float or int
        elif self.ui.logic_switch.currentIndex() == 1:
            value = self.text_line.toPlainText()
            self.value = {self.value_class: value}
        # Variable
        elif self.ui.logic_switch.currentIndex() == 2:
            value = self.variable.combobox.get_variable()
            self.value = {self.value_class: {'m_SourceName': value}}
        # Expression
        elif self.ui.logic_switch.currentIndex() == 3:
            value = self.text_line.toPlainText()
            if not self.expression_bool:
                self.value = {self.value_class: {'m_Expression': str(value)}}
            else:
                self.value = {self.value_class: str(value)}

    def get_variables(self, search_term=None):
        return CompletionUtils.get_available_variable_names(self.variables_scrollArea)

    # ===== Pooling implementation =====
    @classmethod
    def _pool_key_from_kwargs(
        cls,
        expression_bool=False,
        only_string=False,
        only_variable=False,
        force_variable=False,
        filter_types=None,
        **kwargs,
    ):
        if filter_types is None:
            filter_types = ['String', 'MaterialGroup', 'Model']
        return (
            bool(expression_bool),
            bool(only_string),
            bool(only_variable),
            bool(force_variable),
            tuple(filter_types),
        )

    def _current_pool_key(self):
        return getattr(self, "_pool_key", self._pool_key_from_kwargs())

    def reconfigure(
        self,
        element_id_generator,
        value_class,
        value,
        variables_scrollArea,
        expression_bool=False,
        only_string=False,
        placeholder=None,
        only_variable=False,
        force_variable=False,
        filter_types=None,
        **kwargs,
    ):
        children_to_block = [
            self.ui.logic_switch,
            self.text_line,
            self.variable.combobox,
            self.ui.property_class,
        ]

        for c in children_to_block:
            c.blockSignals(True)

        try:
            # Identity attributes.
            self.value_class = value_class
            self.value = value
            self.element_id_generator = element_id_generator
            self.variables_scrollArea = variables_scrollArea

            # Derived config (must match __init behavior).
            if filter_types is None:
                filter_types_final = ['String', 'MaterialGroup', 'Model']
            else:
                filter_types_final = list(filter_types)

            self.expression_bool = expression_bool
            self.only_string = only_string
            self._pool_force_variable = bool(force_variable)
            self._pool_only_variable = bool(only_variable)
            self._pool_expression_bool = bool(expression_bool)
            self._pool_only_string = bool(only_string)
            self._pool_filter_types = list(filter_types_final)

            # Update stylesheet based on expression_bool.
            if self.expression_bool:
                self.ui.property_class.setStyleSheet("""
                    border:0px;
                    background-color: rgba(255, 255, 255, 0);
                    font: 8pt "Segoe UI";
                    padding-right: 16px;
                    color: rgb(255, 123, 125);
                """)
            else:
                self.ui.property_class.setStyleSheet("""
                    border:0px;
                    background-color: rgba(255, 255, 255, 0);
                    font: 8pt "Segoe UI";
                    padding-right: 16px;
                    color: rgb(255, 209, 153);
                """)

            # Label text (mirrors __init__ logic).
            output = re.sub(r'm_fl|m_n|m_b|m_s|m_v|m_f|m_', '', self.value_class)
            output = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', output)
            self.ui.property_class.setText(output)

            # Placeholder.
            if placeholder:
                self.text_line.setPlaceholderText(placeholder)
            else:
                self.text_line.setPlaceholderText('Variable name, string or expression')

            # Reset child components holding external references.
            self.variable.reset(
                variables_layout=variables_scrollArea,
                filter_types=filter_types_final,
                variable_name=value_class,
                element_id_generator=element_id_generator,
            )
            self.expression_editor.reset(variables_scrollArea)

            # Reset edit widgets.
            self.text_line.completion_tail = ''
            self.text_line.setPlainText('')

            # Reset base mode/value first (matches __init ordering before hide-constraints).
            self.ui.logic_switch.setCurrentIndex(0)

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

            # Apply hide constraints (mirrors __init end).
            if expression_bool:
                self.ui.logic_switch.hide()
                self.ui.logic_switch.setCurrentIndex(3)
            elif only_string:
                self.ui.logic_switch.hide()
                self.ui.logic_switch.setCurrentIndex(1)
            elif only_variable:
                self.ui.logic_switch.hide()
                self.ui.logic_switch.setCurrentIndex(2)
            else:
                self.ui.logic_switch.show()

            # signals were blocked; ensure add-button visibility is correct.
            self.variable.update_add_button_visibility(self.variable.combobox.currentText())

            # Refresh cached pool key for release routing.
            self._pool_key = self._pool_key_from_kwargs(
                expression_bool=expression_bool,
                only_string=only_string,
                only_variable=only_variable,
                force_variable=force_variable,
                filter_types=filter_types_final,
            )
        finally:
            for c in children_to_block:
                c.blockSignals(False)

        self._update_display_and_value()