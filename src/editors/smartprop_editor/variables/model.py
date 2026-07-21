from src.editors.smartprop_editor.variables.ui_legacy import Ui_Widget

from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtCore import Signal


class Var_class_model(QWidget):
    """Variable widget for CSmartPropVariable_Model — a .vmdl asset path."""
    edited = Signal(str, str, str, str)

    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.min = None
        self.max = None
        self.model = None
        self.default = '' if default is None else str(default)

        self.ui.value.setText(self.default)
        self.ui.value.setPlaceholderText("Model path (e.g. models/props/crate01.vmdl)")
        self.ui.value.textChanged.connect(self.on_changed)

        self.browse_button = QPushButton('…')
        self.browse_button.setFixedSize(22, 22)
        self.browse_button.setToolTip('Browse models')
        self.browse_button.clicked.connect(self._open_model_browser)
        self.ui.horizontalLayout_2.addWidget(self.browse_button)

    def _open_model_browser(self):
        from src.widgets.model_browser import pick_model
        path = pick_model(self, current_path=self.ui.value.text().strip())
        if path:
            self.ui.value.setText(path)

    def on_changed(self):
        self.default = self.ui.value.text()
        self.edited.emit(self.default, self.min, self.max, str(self.model))
