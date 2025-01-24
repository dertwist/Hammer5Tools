from src.smartprop_editor.variables.ui_color import Ui_Widget

from PySide6.QtWidgets import QWidget, QColorDialog
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from src.styles.qt_global_stylesheet import QT_Stylesheet_global
import ast

class Var_class_color(QWidget):
    edited = Signal(list, str, str, str)

    def __init__(self, default, min, max, model):
        super().__init__()
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self.setAcceptDrops(True)

        # Initialize default color
        if default is None:
            self.default = [255, 255, 255]  # Default to white
        else:
            self.default = default

        # Create a QColor object from the default RGB values
        self.color = QColor(*self.default)

        # Connect the color button to open the color picker dialog
        self.ui.color.clicked.connect(self.open_dialog)

        # Update the button style to reflect the initial color
        self.update_button_style()

        self.on_changed()

    def update_button_style(self):
        """Update the style of the color button to display the current color."""
        r, g, b = self.color.red(), self.color.green(), self.color.blue()
        self.ui.color.setStyleSheet(f"""
            background-color: rgb({r}, {g}, {b});
            padding: 4px;
            border: 0px;
            border: 2px solid rgba(80, 80, 80, 100);
        """)

    def on_changed(self):
        """Emit the edited signal with the current RGB values."""
        self.default = [self.color.red(), self.color.green(), self.color.blue()]
        self.edited.emit(self.default, '', '', '')

    def open_dialog(self):
        """Open the color picker dialog and handle the selected color."""
        # Open the color dialog with the current color as the initial selection
        selected_color = QColorDialog.getColor(
            initial=self.color,
            parent=self,
            options=QColorDialog.ColorDialogOptions(QColorDialog.ShowAlphaChannel)
        )

        # Check if the user selected a valid color
        if selected_color.isValid():
            # Update the internal color and default RGB values
            self.color = selected_color
            self.update_button_style()
            self.on_changed()
        else:
            # User canceled the color selection; do not change the color
            pass