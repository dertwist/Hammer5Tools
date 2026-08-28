from gui.editors.smartprop_editor.variables.ui_legacy import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from gui.editors.smartprop_editor.property import compact


class MaterialVariable(QWidget):
    """Variable widget for CSmartPropVariable_Material - material asset path."""
    edited = Signal(str, str, str, str)

    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        compact.style_variable_body(self, "string")
        self.setAcceptDrops(True)
        self.min = None
        self.max = None
        self.model = None
        if default is None:
            self.default = ''
        else:
            self.default = str(default)
        self.ui.value.setText(str(self.default))
        self.ui.value.setPlaceholderText("Material path (e.g. materials/dev/reflectivity_20.vmat)")
        self.ui.value.textChanged.connect(self.on_changed)

        self.browse_button = compact.browse_button('material')
        self.browse_button.clicked.connect(self._open_browser)
        compact.attach_browse_button(self.ui.horizontalLayout_2, self.ui.value, self.browse_button)

    def _open_browser(self):
        path = compact.pick_asset_path('material', self, self.ui.value.text().strip())
        if path:
            self.ui.value.setText(path)

    def on_changed(self):
        self.default = self.ui.value.text()
        self.edited.emit(self.default, self.min, self.max, str(self.model))


Var_class_material = MaterialVariable
