from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QFrame, QScrollArea, QSizePolicy

class SmartPropViewport(QWidget):
    """
    The main viewport for the SmartProp editor.
    This class is responsible for displaying the viewport and handling user interactions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SmartPropViewport")
        self.init_ui()

    def init_ui(self):
        """The viewport has a scrollarea with a spacer. The spacer widget will be hidden while no elements are selected; instead, we will show a placeholder label."""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Placeholder label
        self.placeholder_label = QLabel("Select element to edit")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Scroll area for editing widgets
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        # Spacer widget inside scroll area
        self.spacer_widget = QWidget()
        self.spacer_layout = QVBoxLayout(self.spacer_widget)
        self.spacer_layout.addStretch(1)
        self.spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setWidget(self.spacer_widget)

        # Add widgets to main layout
        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.scroll_area)

        # Start with placeholder visible, editor hidden
        self.show_placeholder()

    def show_placeholder(self):
        """Show the placeholder label, hide the editor area."""
        self.placeholder_label.show()
        self.scroll_area.hide()

    def show_editor(self):
        """Show the editor area, hide the placeholder label."""
        self.placeholder_label.hide()
        self.scroll_area.show()

    # Example method to add an editor widget (call show_editor() when adding)
    def set_editor_widget(self, widget: QWidget):
        # Clear previous widgets
        for i in reversed(range(self.spacer_layout.count())):
            item = self.spacer_layout.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)
            self.spacer_layout.removeItem(item)
        self.spacer_layout.addWidget(widget)
        self.show_editor()

    # Example method to clear editor and show placeholder
    def clear_editor(self):
        for i in reversed(range(self.spacer_layout.count())):
            item = self.spacer_layout.itemAt(i)
            w = item.widget()
            if w:
                w.setParent(None)
            self.spacer_layout.removeItem(item)
        self.show_placeholder()

from PySide6.QtCore import Qt

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    viewport = SmartPropViewport()
    viewport.show()
    sys.exit(app.exec())
