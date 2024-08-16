from PySide6.QtWidgets import QWidget, QComboBox, QCompleter
from PySide6.QtCore import Qt
from soudevent_editor.properties.ui_combobox_property import Ui_PropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions
from soudevent_editor.parse_soundevents_from_the_game.items import soundevents
import ast



class ComboboxProperty(QWidget):
    def __init__(self, name, display_name, value, widget_list):
        super().__init__()
        self.ui = Ui_PropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.lineEdit.setAcceptDrops(False)  # Change comboBox to lineEdit
        self.widget_list = widget_list
        self.display_name = display_name
        self.name = name
        self.value = value

        self.init_ui()

    def init_ui(self):
        self.ui.label.setText(self.display_name)

        # self.ui.lineEdit.addItems(soundevents)  # Update comboBox method to lineEdit

        self.ui.lineEdit.setText(str(self.value))  # Update comboBox method to lineEdit
        self.ui.lineEdit.setCompleter(QCompleter(soundevents, self))  # Update comboBox method to lineEdit
        self.ui.lineEdit.textChanged.connect(self.update_value_from_lineedit)  # Update comboBox signal to lineEdit

        # Enable search functionality in the lineEdit
        self.ui.lineEdit.setReadOnly(False)  # Update comboBox method to lineEdit
        self.ui.lineEdit.setClearButtonEnabled(True)  # Add a clear button to the line edit

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_value_from_lineedit(self):  # Update method name
        self.value = self.ui.lineEdit.text()  # Update comboBox method to lineEdit

    mousePressEvent = PropertyActions.mousePressEvent
    mouseMoveEvent = PropertyActions.mouseMoveEvent
    dragEnterEvent = PropertyActions.dragEnterEvent
    dropEvent = PropertyActions.dropEvent
    def show_context_menu(self):
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
