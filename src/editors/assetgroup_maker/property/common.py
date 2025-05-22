from PySide6.QtWidgets import QTreeWidget
from PySide6.QtGui import QTextOption
from PySide6.QtCore import Qt, Signal
from src.common import convert_snake_case
from src.editors.assetgroup_maker.context_menu import ReplacementsContextMenu
from src.editors.assetgroup_maker.highlighter import CustomHighlighter
from src.styles.common import *
try:
    from src.editors.soundevent_editor.property.curve.ui_main import Ui_CurveWidget
except:
    pass
from src.widgets import Button


#===============================================================<  Properties >============================================================

class PropertyBase(QWidget):
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
        # self.init_label(label_text)
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

class PropertyReplacement(PropertyBase):
    def __init__(self, parent=None, label_text: str = None, value: list = None, tree: QTreeWidget = None, objects: list = None):
        """
        Combox property

        value : str
        """
        super().__init__(parent, label_text, value)

        self.tree: QTreeWidget = tree
        self.value_class = label_text
        self.objects = objects

        # Init source line
        self.source_line = QPlainTextEdit()
        self.source_line.setMinimumWidth(64)
        self.layout().addWidget(self.source_line)
        self.set_value(value[0], self.source_line)
        self.source_line.setPlaceholderText('Source')

        self.source_line.setWordWrapMode(QTextOption.NoWrap)
        self.source_line.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.source_line.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


        # Init arrow button
        self.search_button = Button()
        self.search_button.set_icon(":/icons/arrow_forward_ios_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg")
        self.search_button.set_size(24,24)
        self.search_button.setEnabled(False)
        self.layout().addWidget(self.search_button)

        # Init dist line
        self.destination_line = QPlainTextEdit()
        self.destination_line.setMinimumWidth(64)
        self.layout().addWidget(self.destination_line)
        self.set_value(value[1], self.destination_line)
        self.destination_line.setPlaceholderText('Destination')

        self.destination_line.setWordWrapMode(QTextOption.NoWrap)
        self.destination_line.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.destination_line.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setContentsMargins(0,0,0,0)
        self.setMinimumHeight(48)
        self.setMaximumHeight(48)

        # Context menu

        self.context_menu = ReplacementsContextMenu(self, self.destination_line)

        self.destination_line.setContextMenuPolicy(Qt.CustomContextMenu)
        self.destination_line.customContextMenuRequested.connect(self.context_menu.show)

        # Highlighting
        self.highlighter_source = CustomHighlighter(self.source_line.document())
        self.highlighter_destination = CustomHighlighter(self.destination_line.document())
        self.source_line.setStyleSheet(qt_stylesheet_plain_text_batch_inline)
        self.destination_line.setStyleSheet(qt_stylesheet_plain_text_batch_inline)

        # connections for updating on changes
        self.source_line.textChanged.connect(self.on_property_update)
        self.destination_line.textChanged.connect(self.on_property_update)

        self.on_property_update()
    def set_value(self, value: str, widget):
        widget.setPlainText(str(value))

    def on_property_update(self):
        """Send signal that user changed the property"""
        value = [self.source_line.toPlainText(), self.destination_line.toPlainText()]
        self.value_update(value)
        self.edited.emit()

    def value_update(self, value):
        """Gathering values and put them into dict value. Very specific, should be overwritten for each individual cause"""
        self.value = {self.value_class: value}
    def init_label_color(self):
        return "#F4A9F6"