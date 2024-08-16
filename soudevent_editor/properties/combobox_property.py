from PySide6.QtWidgets import QWidget, QComboBox
from PySide6.QtCore import Qt
from soudevent_editor.properties.ui_combobox_property import Ui_PropertyWidet
from soudevent_editor.properties.property_actions import PropertyActions
import ast

class ComboboxProperty(QWidget):
    def __init__(self, name, display_name, value, widget_list):
        super().__init__()
        self.ui = Ui_PropertyWidet()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)
        self.ui.comboBox.setAcceptDrops(False)
        self.widget_list = widget_list
        self.display_name = display_name
        self.name = name
        self.value = value

        self.init_ui()

    def init_ui(self):
        self.ui.label.setText(self.display_name)

        # Set the items to the comboBox
        items = "test,test,test,te23st,t23est,Music.MatchStart.3kliksphilip_01,test,test,test,t23est,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,test,"
        items_list = items.split(',')
        self.ui.comboBox.addItems(items_list)

        self.ui.comboBox.setCurrentText(str(self.value))
        self.ui.comboBox.editTextChanged.connect(self.update_value_from_combobox)

        # Enable search functionality in the combobox
        self.ui.comboBox.setEditable(True)
        self.ui.comboBox.setInsertPolicy(QComboBox.NoInsert)  # Prevent inserting new text

        # Access the line edit widget of the combobox
        line_edit = self.ui.comboBox.lineEdit()
        line_edit.setClearButtonEnabled(True)  # Add a clear button to the line edit

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def update_value_from_combobox(self):
        self.value = self.ui.comboBox.currentText()

    def show_context_menu(self):
        PropertyActions.show_context_menu(self, event=self.event, property_class=self)
