from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Signal
from src.common import convert_snake_case
from src.widgets import Button

class ExplorerItem(QWidget):
    """
    ExplorerItem is a custom QWidget that represents an item with a label and an optional button.
    It is designed to be a base property class with a label widget and a frame.
    """

    # Signal emitted when the item is edited
    edited = Signal()

    def __init__(self, parent: QWidget = None, label_text: str = None, value: dict = None):
        """
        Initialize the ExplorerItem widget.

        :param parent: The parent widget.
        :param label_text: The text to display on the label.
        :param value: A dictionary representing the value associated with this item.
        """
        super().__init__(parent)

        # Store the value and label text
        self.value = value
        self.value_class = label_text

        # Initialize the widget's size, layout, and label
        self.set_widget_size()
        self.init_root_layout()
        self.init_label(label_text)

        # Set the stylesheet for the widget
        self.setStyleSheet("""
        .QFrame {
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

        # Add an open button to the layout
        self.open_button = Button()
        self.root_layout.addWidget(self.open_button)

    def init_root_layout(self):
        """
        Initialize the root layout for the widget.
        This layout will contain all widgets added to this class.
        """
        self.root_layout = QHBoxLayout()
        self.setLayout(self.root_layout)

    def init_label(self, label_text: str):
        """
        Initialize the label widget with the provided text.

        :param label_text: The text to display on the label.
        """
        if label_text is None:
            label_text = "Label"
        label_instance = QLabel()
        label_instance.setText(convert_snake_case(label_text))
        label_instance.setStyleSheet(f"color: {self.init_label_color()}")
        self.root_layout.addWidget(label_instance)

    def init_label_color(self) -> str:
        """
        Get the color for the label text.

        :return: A string representing the color code.
        """
        return "#C7C7BB"

    def add_property_widget(self, widget: QWidget):
        """
        Add a property widget to the root layout.

        :param widget: The widget to add.
        """
        self.root_layout.addWidget(widget)

    def set_widget_size(self):
        """
        Set the maximum and minimum height for the widget.
        """
        self.setMaximumHeight(44)
        self.setMinimumHeight(44)