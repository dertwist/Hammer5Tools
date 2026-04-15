from src.editors.smartprop_editor.property.ui_comment import Ui_Widget
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, QTimer, Qt


class PropertyComment(QWidget):
    edited = Signal()

    def __init__(self, value_class, value):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.value_class = value_class
        self.value = value

        self.ui.text_field.setPlainText(value)
        self.ui.text_field.textChanged.connect(self.on_changed)

        # Timer for debouncing resize operations
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._do_auto_resize)
        self._resize_timer.setInterval(100)

        self.change_value()
        # Initial resize after content is set
        self._do_auto_resize()

    def on_changed(self):
        self.change_value()
        self.edited.emit()
        # Debounce the resize to avoid excessive updates during rapid typing
        self._resize_timer.start()

    def _do_auto_resize(self):
        doc = self.ui.text_field.document()
        doc_height = doc.size().height()

        padding = 16
        new_height = max(128, int(doc_height) + padding)

        self.setFixedHeight(new_height)
        self.updateGeometry()

        from src.editors.smartprop_editor.property_frame import PropertyFrame
        parent = self.parentWidget()
        while parent is not None:
            parent.updateGeometry()
            parent_layout = QWidget.layout(parent)
            if parent_layout is not None:
                parent_layout.activate()
            parent.adjustSize()
            if isinstance(parent, PropertyFrame):
                break
            parent = parent.parentWidget()

    def change_value(self):
        value = self.ui.text_field.toPlainText()
        self.value = {self.value_class: str(value)}
