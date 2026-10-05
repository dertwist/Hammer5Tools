from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from gui.editors.smartprop_editor.property.base_pooled import PooledPropertyMixin

class PropertyWarning(QWidget, PooledPropertyMixin):
    edited = Signal()
    def __init__(self, value=None, value_class=None, parent=None, **kwargs):
        super().__init__(parent)
        self.value_class = value_class
        self.raw_value = value
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        
        self.label = QLabel("This property might not work in CS2.")
        self.label.setProperty("h5Component", "smartpropPropertyWarning")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)
        
        # Identity for consistency, though we don't emit 'edited'
        self.value = {self.value_class: self.raw_value} if self.value_class else None

    def reconfigure(self, value=None, value_class=None, **kwargs):
        # Nothing to change for a static warning, but we must implement it for pooling
        if value_class is not None:
            self.value_class = value_class
        if value is not None:
            self.raw_value = value
        self.value = {self.value_class: self.raw_value} if self.value_class else None

    @classmethod
    def _pool_key_from_kwargs(cls, **kwargs):
        return ("Warning",)

    def _current_pool_key(self):
        return ("Warning",)
