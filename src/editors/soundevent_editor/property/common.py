from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QTreeWidget, QSpacerItem, QSizePolicy
from PySide6.QtWidgets import QFrame, QLineEdit
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Signal
from src.widgets.popup_menu.main import PopupMenu
from src.settings.main import get_addon_dir
from src.common import convert_snake_case
try:
    from src.editors.soundevent_editor.property.curve.ui_main import Ui_CurveWidget
except:
    pass
from src.widgets import FloatWidget, LegacyWidget, BoolWidget, DeleteButton, Button, ComboboxDynamicItems, Spacer
from src.editors.soundevent_editor.common import vsnd_filepath_convert

import re, os

#===============================================================<  Properties >============================================================

class SoundEventEditorPropertyBase(QWidget):
    edited = Signal()
    def __init__(self, parent=None, label_text: str = None, value: dict = None):
        """Base property class. There is only a label widget and a frame. New widget can be replaced or added"""
        super().__init__(parent)

        # Value variable
        self.value = value
        self.value_class = label_text

        # Init
        self.set_widget_size()
        self.init_root_layout()
        self.init_label(label_text)
        # self.on_property_update()

        self.setStyleSheet(""".QFrame {
    font: 580 10pt "Segoe UI";
    border: 2px solid black;
    border-radius: 0px;
    border-left: 0px;
    border-right: 0px;
	border-top: 0px;
    border-color: rgba(50, 50, 50, 255);
    color: #E3E3E3;
    background-color: #1C1C1C;
}

.QFrame::hover {
}
.QFrame::selected {
    background-color: #414956;
}""")

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
        self.setMaximumHeight(44)
        self.setMinimumHeight(44)
class SoundEventEditorPropertyFloat(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: dict = None, slider_range: list = [0, 0],only_positive: bool = False):
        """
        Float property. Accepts inputs:

        slider_range: list = [-10.0,10.0]
        only_positive: bool = False

        """
        super().__init__(parent, label_text, value)
        float_value = 0.0
        if isinstance(value, float):
            float_value = value
        elif isinstance(value,int):
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
        return "#73d1bf"

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
        return "#4ca0ad"
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
        return "#d9b34c"
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
        return "#d1494a"

class SoundEventEditorPropertyVector3(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: list = None, slider_range: list = None):
        """
        Vector3 Property. Have a button to paste the value form hammer editor.
        """
        super().__init__(parent, label_text, value)

        self.value_class = label_text
        self.slider_range = slider_range if slider_range is not None else [-10, 10]

        # Init Vertical layout
        self.init_vertical_layout()

        # Init values
        self.float_widget_instances = []
        for float_value in value:
            self.add_float_widget(float_value)

        # init button
        self.paste_button = Button()
        self.paste_button.set_text("Paste from clipboard")
        self.paste_button.set_icon_paste()
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        self.vertical_layout.addWidget(self.paste_button)
        # Updating value
        self.value_update()
    def add_float_widget(self, value):
        """Adding float widget instance using given name"""
        float_value = 0
        if isinstance(value, (float, int)):
            float_value = value
        float_widget_instance = FloatWidget(value=float_value, slider_range=self.slider_range, spacer_enable=False)
        float_widget_instance.edited.connect(self.on_property_update)
        float_widget_instance.setMaximumHeight(30)
        float_widget_instance.setMinimumHeight(30)
        self.vertical_layout.addWidget(float_widget_instance)
        self.float_widget_instances.append(float_widget_instance)  # Append to the list

    def init_vertical_layout(self):
        """Init paste button. The paste button suppose to be used take position form transforms when you copy transforms to the clipboard from hammer editor"""
        # Create a QFrame to hold the vertical layout
        self.frame = QFrame(self)
        self.frame.setObjectName("frame")
        self.frame.setStyleSheet("""QFrame#frame {border: None;}""")
        self.frame.setContentsMargins(0,0,0,0)
        self.frame.setFrameShape(QFrame.StyledPanel)  # Optional: Set the frame shape
        self.frame.setFrameShadow(QFrame.Raised)      # Optional: Set the frame shadow


        # Initialize the vertical layout
        self.vertical_layout = QVBoxLayout(self.frame)

        # Add the frame to the root layout
        self.root_layout.addWidget(self.frame)

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

    def paste_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        clipboard_text = clipboard.text()
        if clipboard_text.endswith('}'):
            origin_list = re.search(r'origin = "(.*?)"', clipboard_text).group(1)
            origin_list = origin_list.split()
            for index in range(len(self.float_widget_instances)):
                widget_instance: FloatWidget = self.float_widget_instances[index]
                __single_axis = float(origin_list[index])
                widget_instance.set_value(__single_axis)
        if "setpos" in clipboard_text:
            setpos_match = re.search(r'setpos\s+([\d\.\-]+)\s+([\d\.\-]+)\s+([\d\.\-]+)', clipboard_text)
            if setpos_match:
                setpos_values = [float(setpos_match.group(1)), float(setpos_match.group(2)),
                                 float(setpos_match.group(3))]
                for index, value in enumerate(setpos_values):
                    if index < len(self.float_widget_instances):
                        widget_instance: FloatWidget = self.float_widget_instances[index]
                        widget_instance.set_value(value)

    def on_property_update(self):
        """Send signal that user changed the property"""
        self.value_update()
        self.edited.emit()

    def value_update(self):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        _value = []
        for widget_instance in self.float_widget_instances:
            __single_axis = widget_instance.value
            _value.append(__single_axis)
        self.value = {self.value_class: _value}

    def init_label_color(self):
        return "#7DDA58"
    def set_widget_size(self):
        """Set maximum height"""
        # height = 44 * 3 + 40
        # self.setMaximumHeight(height)
        # self.setMinimumHeight(height)

class SoundEventEditorPropertyList(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: list = None, tree: QTreeWidget = None):
        """
        Vector3 Property. Have a button to paste the value form hammer editor.
        """
        super().__init__(parent, label_text, value)
        self.tree = tree

        self.value_class = label_text

        self.setAcceptDrops(True)

        # Init Vertical layout
        self.init_vertical_layout()

        # Init values
        self.float_widget_instances = []

        # init button
        self.init_button()


        # Populate items
        if isinstance(value, list):
            for item in reversed(value):
                self.add_element(item)
        else:
            self.add_element(value)
        # Updating value
        self.value_update()
    def add_element(self, value: str = None):
        """Adding float widget instance using given name"""
        widget_instance = ListElement(value=value)
        widget_instance.edited.connect(self.on_property_update)
        self.vertical_layout.addWidget(widget_instance)
        self.on_property_update()

    def init_button(self):
        self.button = Button()
        self.button.set_text("Add")
        self.button.set_icon_add()
        self.button.clicked.connect(lambda :self.add_element())
        self.vertical_layout.addWidget(self.button)

    def init_vertical_layout(self):
        """Init paste button. The paste button suppose to be used take position form transforms when you copy transforms to the clipboard from hammer editor"""
        # Create a QFrame to hold the vertical layout
        self.frame = QFrame(self)
        self.frame.setObjectName("frame")
        self.frame.setStyleSheet("""QFrame#frame {border: None;}""")
        self.frame.setContentsMargins(0,0,0,0)
        self.frame.setFrameShape(QFrame.StyledPanel)  # Optional: Set the frame shape
        self.frame.setFrameShadow(QFrame.Raised)      # Optional: Set the frame shadow


        # Initialize the vertical layout
        self.vertical_layout = QVBoxLayout(self.frame)
        self.vertical_layout.setSpacing(4)

        self.spacer = QSpacerItem(40, 2, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.vertical_layout.layout().addItem(self.spacer)
        # Add the frame to the root layout
        self.root_layout.addWidget(self.frame)

    def init_root_layout(self):
        """Adding a root layout in which should be placed all widgets that would be in this class and from encapsulation. Not recommended to overwrite this function"""
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

    def on_property_update(self):
        """Send signal that user changed the property"""
        self.value_update()
        self.edited.emit()

    def value_update(self):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        _value = []
        for index in range(self.vertical_layout.count()):
            __widget_instance = self.vertical_layout.layout().itemAt(index).widget()
            if isinstance(__widget_instance, ListElement):
                __single_axis = __widget_instance.value
                if __single_axis != "" and __single_axis is not None:
                    _value.append(__single_axis)
        if _value == []:
            _value = ""
        self.value = {self.value_class: _value}

    def init_label_color(self):
        return "#F6C273"
    def set_widget_size(self):
        """Set maximum height"""
        # height = 44 * 3 + 40
        # self.setMaximumHeight(height)
        # self.setMinimumHeight(height)

class SoundEventEditorPropertyFiles(SoundEventEditorPropertyList):
    def __init__(self, parent=None, label_text: str = None, value: list = None):
        """
        Files Property. Have a button to create an element in the list.
        """
        super().__init__(parent, label_text, value)

    def init_button(self):
        """Override parent to add both Paste and Add buttons"""
        self.button = Button()
        self.button.set_text("Add")
        self.button.set_icon_add()
        self.button.clicked.connect(lambda: self.add_element())
        self.vertical_layout.addWidget(self.button)

        self.paste_button = Button()
        self.paste_button.set_text("Paste from clipboard")
        self.paste_button.set_icon_paste()
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        self.vertical_layout.addWidget(self.paste_button)

    def paste_from_clipboard(self):
        """
        Reads clipboard text, splits by newlines, and creates
        a FileElement for each valid vsnd path.
        Supports:
          - One path per line
          - Paths with or without 'sounds/' prefix
          - .vsnd, .wav, .mp3 extensions (normalized to .vsnd)
        """
        clipboard = QGuiApplication.clipboard()
        clipboard_text = clipboard.text().strip()

        if not clipboard_text:
            return

        lines = clipboard_text.splitlines()
        for line in lines:
            line = line.strip()
            if line:
                self.add_element(line)

        self.on_property_update()
    def add_element(self, value: str = None):
        """Adding float widget instance using given name"""
        widget_instance = FileElement(value=value)
        widget_instance.edited.connect(self.on_property_update)
        self.vertical_layout.insertWidget(0, widget_instance)
        self.on_property_update()
class SoundEventEditorPropertySoundEvent(SoundEventEditorPropertyList):
    def __init__(self, parent=None, label_text: str = None, value: list = None, tree: QTreeWidget = None):
        """
        Files Property. Have a button to create an element in the list.
        """
        super().__init__(parent, label_text, value, tree)
        self.tree = tree
    def add_element(self, value: str = None):
        """Adding float widget instance using given name"""
        widget_instance = SoundEventElement(value=value, tree=self.tree)
        widget_instance.edited.connect(self.on_property_update)
        self.vertical_layout.addWidget(widget_instance)
        self.vertical_layout.insertWidget(0, widget_instance)
        self.on_property_update()
class SoundEventEditorPropertyCombobox(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value)

        self.tree: QTreeWidget = tree
        self.value_class = label_text
        self.objects = objects
        # Init combobox
        self.combobox = ComboboxDynamicItems()
        self.combobox.items = self.objects
        self.combobox.setMinimumWidth(256)
        self.combobox.updateItems()
        self.combobox.currentTextChanged.connect(self.on_property_update)
        self.layout().addWidget(self.combobox)
        self.set_value(value)
        # if value == "None":
        #     pass
        # else:
        #     self.combobox.setCurrentText(str(value))


        # Init Search button
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.setMaximumWidth(32)
        self.search_button.clicked.connect(self.call_search_popup_menu)
        self.layout().addWidget(self.search_button)
        self.on_property_update()

        # Init spacer
        spacer = Spacer()
        self.layout().addWidget(spacer)

        self.setContentsMargins(0,0,0,0)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

    def init_combobox(self):
        pass
    def set_value(self, value: str):
        if value != "None":
            if value not in self.combobox.items:
                self.combobox.items.append(value)
                self.combobox.addItem(value)
            self.combobox.setCurrentText(str(value))

    def on_property_update(self):
        """Send signal that user changed the property"""
        value = self.combobox.currentText()
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#F4A9F6"

    def call_search_popup_menu(self):
        elements = []
        for item in self.objects:
            __element = {item:item}
            elements.append(__element)
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
        self.popup_menu.show()

class SoundEventEditorPropertyBaseSoundEvent(SoundEventEditorPropertyCombobox):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value, tree, objects)
        self.combobox.clicked.connect(self.update_soundevnets)
        self.update_soundevnets()

    def update_soundevnets(self):
        self.combobox.items = self.get_soundenvets()
        self.combobox.updateItems()

    def get_soundenvets(self, elements_dict = False):
        elements = []
        tree_root = self.tree.invisibleRootItem()
        for index in range(tree_root.childCount()):
            __tree_item = tree_root.child(index)
            __name = __tree_item.text(0)
            if elements_dict:
                __element = {__name: __name}
            else:
                __element = __name
            elements.append(__element)
        return elements
    def call_search_popup_menu(self):
        if self.tree is None:
            pass
        else:
            elements = self.get_soundenvets(elements_dict=True)
            self.popup_menu = PopupMenu(elements, add_once=False)
            self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
            self.popup_menu.show()
#==========================================================<  Properties Widgets  >=======================================================

class SoundEventEditorPropertyEditLine(SoundEventEditorPropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value)

        self.tree: QTreeWidget = tree
        self.value_class = label_text
        self.objects = objects
        # Init combobox
        self.combobox = QLineEdit()
        self.combobox.setMinimumWidth(256)
        self.combobox.textChanged.connect(self.on_property_update)
        self.layout().addWidget(self.combobox)
        self.set_value(value)
        # if value == "None":
        #     pass
        # else:
        #     self.combobox.setCurrentText(str(value))


        # Init Search button
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.setMaximumWidth(32)
        self.search_button.clicked.connect(self.call_search_popup_menu)
        self.layout().addWidget(self.search_button)
        self.on_property_update()

        # Init spacer
        spacer = Spacer()
        self.layout().addWidget(spacer)

        self.setContentsMargins(0,0,0,0)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

    def init_combobox(self):
        pass
    def set_value(self, value: str):
        self.combobox.setText(str(value))

    def on_property_update(self):
        """Send signal that user changed the property"""
        value = self.combobox.text()
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#F4A9F6"

    def call_search_popup_menu(self):
        elements = []
        for item in self.objects:
            __element = {item:item}
            elements.append(__element)
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
        self.popup_menu.show()
class SoundEventEditorPropertyBaseLegacy(SoundEventEditorPropertyEditLine):
    def __init__(self, parent=None, label_text: str = None, value: str = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value, tree, objects)

    def get_soundenvets(self, elements_dict = False):
        elements = []
        tree_root = self.tree.invisibleRootItem()
        for index in range(tree_root.childCount()):
            __tree_item = tree_root.child(index)
            __name = __tree_item.text(0)
            if elements_dict:
                __element = {__name: __name}
            else:
                __element = __name
            elements.append(__element)
        return elements
    def call_search_popup_menu(self):
        if self.tree is None:
            pass
        else:
            elements = self.get_soundenvets(elements_dict=True)
            self.popup_menu = PopupMenu(elements, add_once=False)
            self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
            self.popup_menu.show()
    def init_label_color(self):
        return "#8684b8"

class ListElement(QWidget):
    edited = Signal()
    def __init__(self, value: str = None):
        """A line of six float widgets (last 4 hidden by default)"""
        super().__init__()
        # Variables
        self.value: list = []
        if value is None:
            value: str = "None"
        # Init layout
        self.layout_horizontal = QHBoxLayout()
        self.setLayout(self.layout_horizontal)

        # Init editline
        self.editline = QLineEdit()
        self.editline.setPlaceholderText("Type...")
        if value == "None":
            pass
        else:
            self.editline.setText(str(value))
        self.editline.textChanged.connect(self.on_update)
        self.layout().addWidget(self.editline)


        # Init Search button
        self.search_button = Button()
        self.search_button.set_icon_search()
        self.search_button.clicked.connect(self.call_search_popup_menu)
        self.layout().addWidget(self.search_button)

        # Init delete button
        self.delete_button = DeleteButton(self)
        self.layout().addWidget(self.delete_button)
        self.on_update()

        self.setContentsMargins(0,0,0,0)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

    def set_value(self, value: str = None):
        """Sets editline value"""
        self.editline.setText(str(value))

    def call_search_popup_menu(self):
        elements = []
        self.popup_menu = PopupMenu(elements, add_once=True)
        self.popup_menu.exec()

    def on_update(self):
        self.value = self.get_value()
        self.edited.emit()
    def get_value(self):
        return self.editline.text()
    def closeEvent(self, event):
        self.value = None
        self.edited.emit()
        self.deleteLater()
class FileElement(ListElement):
    def __init__(self, value: str = None):
        super().__init__(value)
    
    def call_search_popup_menu(self):
        elements = []
        __sounds_path = os.path.join(get_addon_dir(), 'sounds')
        __addon_path = get_addon_dir()
        for dirpath, dirnames, filenames in os.walk(__sounds_path):
            for filename in filenames:
                __filepath = os.path.join(dirpath, filename)
                __filepath = vsnd_filepath_convert(__filepath)

                __element = {filename: __filepath}
                elements.append(__element)
        self.popup_menu = PopupMenu(elements, add_once=False)
        self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
        self.popup_menu.show()
class SoundEventElement(ListElement):
    def __init__(self, value: str = None, tree: QTreeWidget = None):
        super().__init__(value)
        self.tree = tree

    def call_search_popup_menu(self):
        if self.tree is None:
            pass
        else:
            elements = []
            tree_root = self.tree.invisibleRootItem()
            for index in range(tree_root.childCount()):
                __tree_item = tree_root.child(index)
                __name = __tree_item.text(0)
                __element = {__name:__name}
                elements.append(__element)
            self.popup_menu = PopupMenu(elements, add_once=False)
            self.popup_menu.add_property_signal.connect(lambda name, value: self.set_value(value))
            self.popup_menu.show()