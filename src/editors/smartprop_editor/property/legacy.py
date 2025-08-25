import ast

from src.editors.smartprop_editor.property.ui_legacy import Ui_Widget
from src.widgets.completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from src.editors.smartprop_editor.completion_utils import CompletionUtils


class PropertyLegacy(QWidget):
    edited = Signal()

    def __init__(self, value_class, value, variables_scrollArea):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.value_class = value_class
        self.value = value
        self.variables_scrollArea = variables_scrollArea

        self.text_line = CompletingPlainTextEdit()
        self.text_line.completion_tail = ''
        self.ui.layout.insertWidget(1, self.text_line)

        self.text_line.setPlainText(str(self.value))
        self.ui.value_label.setText(str(self.value_class))

        self.text_line.textChanged.connect(self.on_changed)

        self.change_value()

    def on_changed(self):
        # Setup type-aware completer without filters
        CompletionUtils.setup_completer_for_widget(
            self.text_line,
            self.variables_scrollArea,
            filter_types=None,  # No filtering - show all variable types
            context='general'
        )
        
        self.change_value()
        self.edited.emit()

    def change_value(self):
        value = self.text_line.toPlainText()
        try:
            value = ast.literal_eval(value)
        except:
            pass
        self.value = {self.value_class: value}

    def get_variables(self, search_term=None):
        return CompletionUtils.get_available_variable_names(self.variables_scrollArea)