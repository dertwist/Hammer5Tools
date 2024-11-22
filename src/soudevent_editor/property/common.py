from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from src.widgets import FloatWidget, LegacyWidget, BoolWidget
from PySide6.QtCore import Signal
from src.common import convert_snake_case

class SoundEventEditorPropertyBase(QWidget):
    edited = Signal()
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """Base property class. There is only a label widget and a frame. New widget can be replaced or added"""
        super().__init__(parent)

        # Value variable
        self.value = value
        self.value_class = label_text

        # Init
        self.init_root_layout()
        self.init_label(label_text)
        self.set_widget_size()
        # self.on_property_update()

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)
    def init_label(self, label_text):
        """Adding received text to the label widget"""
        if label_text is None:
            label_text = "Label"
        label_instance = QLabel()
        label_instance.setText(convert_snake_case(label_text))
        label_instance.setStyleSheet(f"""
        color: {self.init_label_color()}""")
        self.root_layout.addWidget(label_instance)
    def init_label_color(self):
        return "#C7C7BB"
    def add_property_widget(self, widget):
        """Adding property widget to the root"""
        self.root_layout.addWidget(widget)
    def set_widget_size(self):
        """Set maximum height"""
        self.setMaximumHeight(48)
        self.setMinimumHeight(48)
    # def on_property_update(self):
    #     """Send signal that user changed the property"""
    #     self.value_update()
    #     self.edited.emit()
    # def value_update(self):
    #     """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
    #     self.value = {}
class SoundEventEditorPropertyFloat(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: dict = None, slider_range: list = [0, 0],only_positive: bool = False):
        """
        Float property. Accepts inputs:

        slider_range: list = [-10.0,10.0]
        only_positive: bool = False

        """
        super().__init__(parent, label_text, value)
        float_value  = 0
        if isinstance(value, float):
            float_value = value
        self.float_widget_instance = FloatWidget(slider_range=slider_range, only_positive=only_positive, value=float_value, spacer_enable=False)
        self.float_widget_instance.edited.connect(self.on_property_update)
        self.add_property_widget(self.float_widget_instance)
        self.value_class = label_text
        self.init_float_widget()

        # Updating value
        self.value_update()

    def init_widget(self):
        """Initialize float widget instance"""
        # self.float_widget_instance = FloatWidget(slider_range=self.slider_range, only_positive=self.only_positive)
        pass
        # self.add_property_widget(self.float_widget_instance)

    def init_float_widget(self):
        """Adding parameter init for float widget instance"""

    def on_property_update(self):
        """Send signal that user changed the property"""
        self.value_update()
        self.edited.emit()

    def value_update(self):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        _value = self.float_widget_instance.value
        self.value = {self.value_class: _value}
    def init_label_color(self):
        return "#4CE4C7"

class SoundEventEditorPropertyInt(SoundEventEditorPropertyFloat):
    def __init__(self, parent=None, label_text: str = None, value: dict = None, slider_range: list = [0, 0], only_positive: bool = False):
        """
        Int property. Accepts inputs:

        slider_range: list = [-10,10]
        only_positive: bool = False

        """
        # Call the parent constructor to ensure float_widget_instance is initialized
        super().__init__(parent, label_text, value, slider_range, only_positive)
        # self.float_widget_instance.int_output = True

    def init_float_widget(self):
        """Adding parameter init for float widget instance"""
        # Ensure float_widget_instance is initialized before accessing it
        # if hasattr(self, 'float_widget_instance'):
        self.float_widget_instance.int_output = True
    def init_label_color(self):
        return "#25A7BC"
class SoundEventEditorPropertyLegacy(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """
        Legacy property (placeholder)
        """
        super().__init__(parent, label_text, value)
        self.legacy_widget_instance = LegacyWidget(value=value, spacer_enable=False)
        self.legacy_widget_instance.edited.connect(self.on_property_update)
        self.add_property_widget(self.legacy_widget_instance)
        self.value_class = label_text

        # Updating value
        self.value_update(value)

    def on_property_update(self, value):
        """Send signal that user changed the property"""
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#BCB925"
class SoundEventEditorPropertyBool(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """
        Bool property

        value : dict
        """
        super().__init__(parent, label_text, value)
        self.bool_widget_instance = BoolWidget(value=value, spacer_enable=True)
        self.bool_widget_instance.edited.connect(self.on_property_update)
        self.add_property_widget(self.bool_widget_instance)
        self.value_class = label_text

        # Updating value
        self.value_update(value)

    def on_property_update(self, value):
        """Send signal that user changed the property"""
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#D20103"