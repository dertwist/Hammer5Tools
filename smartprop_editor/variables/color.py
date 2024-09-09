from smartprop_editor.variables.ui_color import Ui_Widget

from PySide6.QtWidgets import QWidget, QColorDialog
from PySide6.QtCore import Signal
from qt_styles.qt_global_stylesheet import QT_Stylesheet_global

class Var_class_color(QWidget):

    edited = Signal(list, str, str, str)
    def __init__(self, default, min, max, model):
        super().__init__()
        self.dialog = QColorDialog()
        self.dialog.setStyleSheet(QT_Stylesheet_global)

        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.min = None
        self.max = None
        self.model = None
        if default == None:
            self.default = [255, 255 ,255]
        else:
            self.default = list(default)
        self.ui.color.clicked.connect(self.open_dialog)
        # self.ui.value.setText(str(self.default))
        # self.ui.value.textChanged.connect(self.on_changed)


    def on_changed(self):
        self.edited.emit(self.default, self.min, self.max, str(self.model))

    def open_dialog(self):
        color = self.dialog.getColor().getRgb()[:3]
        self.ui.color.setStyleSheet(f"""background-color: rgb{color};
            padding:4px;
            border:0px;
            border: 2px solid translucent;
            border-color: rgba(80, 80, 80, 100);
            """)
        print("RGB Color:", color)
        self.default = list(color)
        self.on_changed()