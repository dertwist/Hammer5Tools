from gui.editors.smartprop_editor.variables.ui_material_group import Ui_Widget

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal
from gui.editors.smartprop_editor.property import compact


class MaterialGroupVariable(QWidget):
    edited = Signal(str, str, str, str)
    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        compact.style_variable_body(self, "string")
        self.setAcceptDrops(True)
        self.min = None
        self.max = None
        if default == None:
            self.default = ''
        else:
            self.default = str(default)

        if model == None:
            self.model = ''
        else:
            self.model = str(model)
        self.ui.value.setText(str(self.default))
        self.ui.model.setText(str(self.model))
        # Capped to the same column as the model row below, with the stretch
        # the picker adds to that one, so both fields start and end together.
        self.ui.value.setMaximumWidth(compact.SUB_ROW_W)
        self.ui.horizontalLayout_2.addStretch(1)
        self.ui.value.textChanged.connect(self.on_changed)
        self.ui.model.textChanged.connect(self.on_changed)

        # Only the model row is an asset path; `value` is a material-group
        # name defined inside that model, which the browser cannot pick.
        self.browse_button = compact.browse_button('model')
        self.browse_button.clicked.connect(self._open_browser)
        compact.attach_browse_button(self.ui.horizontalLayout_3, self.ui.model, self.browse_button)

    def _open_browser(self):
        path = compact.pick_asset_path('model', self, self.ui.model.text().strip())
        if path:
            self.ui.model.setText(path)

    def on_changed(self):
        self.default = self.ui.value.text()
        self.model = self.ui.model.text()
        self.edited.emit(self.default, self.min, self.max, self.model)


Var_class_material_group = MaterialGroupVariable