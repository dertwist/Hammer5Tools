import ast

from src.soundevent_editor.ui_properties_window import Ui_MainWindow
from src.preferences import settings, debug
from src.soundevent_editor.property.frame import SoundEventEditorPropertyFrame
from src.popup_menu.popup_menu_main import PopupMenu
from src.soundevent_editor.objects import *
from src.widgets import ErrorInfo
from PySide6.QtWidgets import QMainWindow, QWidget, QListWidgetItem, QMenu, QPlainTextEdit, QApplication, QTreeWidget
from PySide6.QtGui import QKeySequence, QKeyEvent
from PySide6.QtCore import Qt, Signal

class SoundEventEditorPropertiesWindow(QMainWindow):
    edited = Signal()
    def __init__(self, parent=None, value: str = None, tree:QTreeWidget = None):
        """
        The properties window is supposed to store property frame instances in the layout.
        When any of the frames are edited, the value updates and
        sends a signal that can be used to save the file or update the tree item in the hierarchy.
        """

        super().__init__(parent)

        # Load ui file
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Init QT settings variable from preferences
        self.settings = settings

        # Init common state variables
        self.realtime_save = False

        # Init value variable:
        self.value = self.load_value(value)

        # Init variables
        self.tree = tree

        # Init context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

        self.ui.centralwidget.setFocusPolicy(Qt.StrongFocus)

        # Hide properties on start
        self.properties_groups_hide()

    #=============================================================<  Load value  >==========================================================
    def load_value(self, value):
        if isinstance(value, str):
            return ast.literal_eval(value)
        elif isinstance(value, dict):
            return value
    #===========================================================<  Comment Widget  >========================================================

    def get_comment(self):
        try:
            return self.comment_widget.toPlainText()
        except:
            return ""
    def init_comment(self, value):
        self.comment_widget = QPlainTextEdit()
        self.comment_widget.setPlainText(value)
        self.ui.groupBox_2.layout().addWidget(self.comment_widget)
        self.comment_widget.textChanged.connect(self.on_update)
    def delete_comment(self):
        try:
            self.comment_widget.deleteLater()
        except:
            pass

    # =========================================================<  Properties Actions  >======================================================

    def new_property_popup(self):
        """Call popup menu with all properties"""
        existing_items = set()
        __properties = self.get_properties_value()
        for item in __properties:
            existing_items.add(item)

        soundevent_editor_properties_filtered = []
        # Assuming soundevent_editor_properties is a list of tuples or a dictionary
        for dict_value in soundevent_editor_properties:
            for key, value in dict_value.items():
                key_value = next(iter(value.items()))[0]
                if key_value not in existing_items:
                    soundevent_editor_properties_filtered.append({key:value})
        # Use the filtered properties for the popup menu
        self.popup_menu = PopupMenu(soundevent_editor_properties_filtered, add_once=True, help_url="SoundEvent_Editor")
        self.popup_menu.add_property_signal.connect(lambda name, value: self.new_property(name, value))
        self.popup_menu.show()

    def new_property(self, name:str = None, value:dict  = None):
        """Creates new property in Properties Window"""
        if name is None:
            name = 'Name'
        if value is None:
            value = {}

        # Getting key and value from dict value (single dict value that contains only one key and value)

        # Check if value is a string and convert it to a dictionary if necessary
        if isinstance(value, str):
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError) as e:
                debug(f"Error converting string to dictionary: {e}")
                value = {}

        # Ensure value is a dictionary and has at least one item
        if isinstance(value, dict) and value:
            key, val = next(iter(value.items()))
            self.create_property(key, val)
        else:
            debug("Value is not a valid dictionary or is empty.")
        self.on_update()

    def paste_property(self):
        """Creates new property from clipboard using new_property function"""
        clipboard = QApplication.clipboard()
        clipboard_text = clipboard.text()

        try:
            data = ast.literal_eval(clipboard_text)
            key = next(iter(data))
            existing_items = set()
            __properties = self.get_properties_value()
            for item in __properties:
                existing_items.add(item)
            if key not in existing_items:
                self.create_property(key, data[key])
            else:
                ErrorInfo(
                    text='It seems a property with this name already exists in the sound event. Please remove the existing property to create a new one.').exec()
        except (ValueError, SyntaxError) as e:
            ErrorInfo("Error parsing clipboard content").exec()
    #===============================================================<  Filter  >============================================================

    def eventFilter(self, source, event):
        """Handle keyboard and shortcut events for various widgets."""

        if event.type() == QKeyEvent.KeyPress:
            # Handle events for the specific widget, e.g., tree_hierarchy_widget
            if source == self.ui.centralwidget:
                if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                    self.new_property_popup()
                    return True
                if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
                    self.paste_property()
                    return True

        return super().eventFilter(source, event)
    #=======================================================<  Properties widget  >=====================================================

    def properties_groups_hide(self):
        """Hide properties and show placeholder"""
        self.ui.properties_spacer.hide()
        self.ui.properties_placeholder.show()
        self.ui.CommetSeciton.hide()

        # Unset Filter
        self.ui.centralwidget.removeEventFilter(self)

        # Remove context menu connection
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.customContextMenuRequested.disconnect(self.open_context_menu)
    def properties_groups_show(self):
        """Show properties and hide placeholder"""
        self.ui.properties_placeholder.hide()
        self.ui.properties_spacer.show()
        self.ui.CommetSeciton.show()

        # Set Filter
        self.ui.centralwidget.installEventFilter(self)

        # Add context menu connection
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)
    def properties_clear(self):
        for i in range(self.ui.properties_layout.count()):
            widget = self.ui.properties_layout.itemAt(i).widget()
            if isinstance(widget, SoundEventEditorPropertyFrame):
                widget.deleteLater()

        self.delete_comment()
    def populate_properties(self, _data):
        """Loading properties from given data"""
        if isinstance(_data, dict):
            # Reverse input data and use insertWidget with index 0 because in that way all widgets will be upper spacer
            debug(f"populate_properties _data \n {_data}")
            # If there is no comment in data init comment widget
            if 'comment' in _data:
                pass
            else:
                self.init_comment("")

            for item, value in _data.items():
                if item == 'comment':
                    self.init_comment(value)
                elif item == 'm_sLabel':
                    pass
                else:
                    self.create_property(item,value)
        else:
            print(f"[SoundEventEditorProperties]: Wrong input data format. Given data: \n {_data} \n {type(_data)}")


    #=============================================================<  Property  >==========================================================
    def create_property(self, key, value):
        """Create frame widget instance"""
        widget_instance = SoundEventEditorPropertyFrame(_data={key: value}, widget_list=self.ui.properties_layout, tree=self.tree)
        widget_instance.edited.connect(self.on_update)
        index = self.ui.properties_layout.count() - 1
        self.ui.properties_layout.insertWidget(index, widget_instance)

    def get_property_value(self, index):
        """Getting dict value from widget instance frame"""
        widget_instance = self.ui.properties_layout.itemAt(index).widget()
        if isinstance(widget_instance, SoundEventEditorPropertyFrame):
            value = widget_instance.value
            debug(f"Getting SoundEventEditorPropertyFrame Value: \n {value}")
            return value
        else:
            return {}
    def get_properties_value(self):
        """Getting all values from frame widget which in layout"""
        _data: dict = {}
        for index in range(self.ui.properties_layout.count()):
            if index is not None:
                try:
                    _data.update(self.get_property_value(index))
                except:
                    pass
        return _data

    #==============================================================<  Updating  >===========================================================
    def on_update(self):
        """Updating dict value and send signal"""
        self.update_value()
        self.edited.emit()
    def update_value(self):
        _data = self.get_properties_value()
        comment = self.get_comment()
        if comment != "":
            _data.update({'comment': comment})
        self.value = _data
    #============================================================<  Context menu  >=========================================================
    def open_context_menu(self, position):
        """Layout context menu"""
        menu = QMenu()
        menu.addSeparator()
        # New Property action
        new_property = menu.addAction("New Property")
        new_property.triggered.connect(self.new_property_popup)
        new_property.setShortcut(QKeySequence("Ctrl+F"))
        # Paste action
        paste = menu.addAction("Paste")
        paste.triggered.connect(self.paste_property)
        paste.setShortcut(QKeySequence("Ctrl+V"))
        menu.exec(self.ui.scrollArea.viewport().mapToGlobal(position))