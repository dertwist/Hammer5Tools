from PySide6.QtWidgets import QApplication, QDialog, QWidget, QVBoxLayout, QScrollArea, QLabel, QToolButton, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtGui import QCursor, QIcon, QKeyEvent
from PySide6.QtCore import QEvent, Qt, Signal, QSize
from src.popup_menu.ui_main import Ui_PoPupMenu
import webbrowser

class PopupMenu(QDialog):
    label_clicked = Signal(str)
    add_property_signal = Signal(str, str)

    def __init__(self, properties: list, add_once: bool = False, parent=None, help_url: str = None):
        super().__init__(parent)
        self.help_url = help_url
        self.properties = properties
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setGeometry(200, 200, 400, 400)

        # Track selection state
        self.current_selection_index = -1
        self.visible_labels = []

        self.setup_ui()
        self.populate_properties(add_once)

    def setup_ui(self):
        """Initialize UI components and layouts"""
        self.ui.lineEdit.textChanged.connect(self.search_text_changed)
        self.ui.lineEdit.setFocus()

        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setContentsMargins(0, 0, 2, 0)
        self.scroll_layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))

        scroll_content = QWidget()
        scroll_content.setLayout(self.scroll_layout)
        self.ui.scrollArea.setWidget(scroll_content)

    #=============================================================<  Properties  >==========================================================

    def populate_properties(self, add_once):
        """Populate the menu with property items"""
        for item in self.properties:
            for key, value in item.items():
                element_layout = self.create_property_item(key, value, add_once)
                self.scroll_layout.insertLayout(self.scroll_layout.count() - 1, element_layout)

    def create_property_item(self, key, value, add_once):
        """Create a single property item layout"""
        label = QLabel(key)
        label.mousePressEvent = self.create_label_event(label, key, value, add_once)
        label.setStyleSheet(self.get_label_stylesheet())

        element_layout = QHBoxLayout()
        element_layout.setContentsMargins(0, 0, 0, 0)
        element_layout.addWidget(label)

        if self.help_url:
            element_layout.addWidget(self.create_help_button(key))

        return element_layout

    def create_label_event(self, label, key, value, add_once):
        """Create event handler for label clicks"""
        if add_once:
            return lambda event: self.remove_element(label, key, str(value))
        return lambda event: self.add_property_signal.emit(key, str(value))

    #============================================================<  Help Button  >==========================================================

    def create_help_button(self, label):
        """Create help button for property items"""
        button = QToolButton()
        button.setIcon(QIcon(":/icons/help_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg"))
        button.clicked.connect(lambda: self.open_wiki_page(label=label, url=self.help_url))
        return button
    def open_wiki_page(self, label=None, url=None):
        if url is None:
            url = ''
        base_url = "https://developer.valvesoftware.com/wiki/"
        label = self.clean_spaces(label or "Workflow")
        full_url = f"{base_url + url}#{label}"

        try:
            webbrowser.open(full_url)
        except Exception as e:
            pass
    def clean_spaces(self, text: str) -> str:
        return text.replace(" ", "_")

    def get_label_stylesheet(self):
        """Get stylesheet for labels with proper selection states"""
        return """
            QLabel {
                font: 580 10pt "Segoe UI";
                border-bottom: 0.5px solid black;  
                border-radius: 0px; 
                border-color: rgba(40, 40, 40, 255);
                padding-top: 8px;
                padding-bottom: 8px;
            }
            QLabel:hover {
                background-color: #414956;
            }
            QLabel[selected="true"] {
                background-color: #2A2E38;
            }
        """

    #=========================================================<  Layout  >=======================================================

    def remove_element(self, label, key, value):
        """Remove an element from the menu"""
        self.add_property_signal.emit(key, value)
        scroll_content = self.ui.scrollArea.widget()

        # Update selection indices after removal
        label_index = self.visible_labels.index(label) if label in self.visible_labels else -1

        for i in range(scroll_content.layout().count()):
            element_layout_item = scroll_content.layout().itemAt(i)
            if not element_layout_item:
                continue

            element_layout = element_layout_item.layout()
            if not element_layout:
                continue

            current_label = element_layout.itemAt(0).widget()
            if current_label.text() == key:
                # Remove the item
                item = scroll_content.layout().takeAt(i)
                if item:
                    self.cleanup_layout_item(item)

                # Update selection if needed
                if label_index != -1:
                    self.visible_labels.pop(label_index)
                    if self.current_selection_index >= label_index:
                        self.current_selection_index = max(-1, self.current_selection_index - 1)
                    self.update_selection_highlighting()
                break

    def cleanup_layout_item(self, item):
        """Clean up layout items and their widgets"""
        if item.layout():
            while item.layout().count():
                child = item.layout().takeAt(0)
                self.cleanup_layout_item(child)
        elif item.widget():
            item.widget().deleteLater()

    def update_visible_labels(self):
        """Update the list of visible labels"""
        self.visible_labels.clear()
        scroll_content = self.ui.scrollArea.widget()
        if not scroll_content or not scroll_content.layout():
            return

        for i in range(scroll_content.layout().count()):
            element_layout_item = scroll_content.layout().itemAt(i)
            if not element_layout_item:
                continue

            element_layout = element_layout_item.layout()
            if not element_layout:
                continue

            widget_item = element_layout.itemAt(0)
            if widget_item:
                widget = widget_item.widget()
                if widget and widget.isVisible():
                    self.visible_labels.append(widget)

    #=============================================================<  Navigation  >==========================================================

    def update_selection_highlighting(self):
        """Update the highlighting of selected items"""
        for i, label in enumerate(self.visible_labels):
            label.setProperty("selected", i == self.current_selection_index)
            label.style().unpolish(label)
            label.style().polish(label)

    def navigate_selection(self, direction):
        """Navigate through visible items"""
        self.update_visible_labels()
        if not self.visible_labels:
            return

        self.current_selection_index = (self.current_selection_index + direction) % len(self.visible_labels)
        self.update_selection_highlighting()

        # Ensure selected item is visible
        selected_label = self.visible_labels[self.current_selection_index]
        self.ui.scrollArea.ensureWidgetVisible(selected_label)

    def activate_selection(self):
        """Activate the currently selected item"""
        self.update_visible_labels()
        if (self.visible_labels and
            0 <= self.current_selection_index < len(self.visible_labels)):
            label = self.visible_labels[self.current_selection_index]
            if label.mousePressEvent:
                label.mousePressEvent(None)

    #===============================================================<  Search  >============================================================

    def search_text_changed(self):
        """Handle search text changes"""
        search_text = self.ui.lineEdit.text().lower()
        scroll_content = self.ui.scrollArea.widget()

        for i in range(scroll_content.layout().count()):
            element_layout_item = scroll_content.layout().itemAt(i)
            if not element_layout_item:
                continue

            element_layout = element_layout_item.layout()
            if not element_layout:
                continue

            label = element_layout.itemAt(0).widget()
            visible = search_text in label.text().lower()
            label.setVisible(visible)

            if element_layout.count() > 1:
                element_layout.itemAt(1).widget().setVisible(visible)

        # Reset selection after filtering
        self.current_selection_index = -1
        self.update_visible_labels()
        if self.visible_labels:
            self.current_selection_index = 0
            self.update_selection_highlighting()

    #===============================================================<  Events  >============================================================

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation"""
        key_handlers = {
            Qt.Key_Down: lambda: self.navigate_selection(1),
            Qt.Key_Up: lambda: self.navigate_selection(-1),
            Qt.Key_Return: self.activate_selection,
            Qt.Key_Enter: self.activate_selection,
            Qt.Key_Space: self.activate_selection
        }

        if handler := key_handlers.get(event.key()):
            handler()
            event.accept()
        else:
            super().keyPressEvent(event)

    def event(self, event):
        """Handle window events"""
        if event.type() == QEvent.WindowDeactivate:
            self.close()
            return True
        return super().event(event)

    def showEvent(self, event):
        """Handle show events"""
        self.move(QCursor.pos())
        super().showEvent(event)