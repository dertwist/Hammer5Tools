from PySide6.QtWidgets import QApplication, QDialog, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtCore import QEvent, Qt, Signal
from src.popup_menu.ui_main import Ui_PoPupMenu
from src.widgets_common import Button
import webbrowser
from src.settings.main import set_config_value, get_config_value

class PopupMenu(QDialog):
    label_clicked = Signal(str)
    add_property_signal = Signal(str, str)

    def __init__(
        self,
        properties: list,
        add_once: bool = False,
        parent=None,
        help_url: str = None,
        window_name: str = None
    ):
        super().__init__(parent)
        self.help_url = help_url
        self.properties = properties
        self.window_name = window_name
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setGeometry(200, 200, 400, 400)

        # Track selection state
        self.current_selection_index = -1
        self.visible_labels = []
        self.bookmarked_items = set()
        self.add_once = add_once

        # Keep track of removed items so they won't reappear if add_once is True
        self.removed_items = set()  # Will store (key, str(value)) pairs

        self.setup_ui()
        self.init_bookmarks()
        self.populate_properties(self.add_once)

    #=============================================================<  Setup  >==========================================================

    def setup_ui(self):
        """Initialize UI components and layouts"""
        self.ui.lineEdit.textChanged.connect(self.search_text_changed)
        self.ui.lineEdit.setFocus()

        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setContentsMargins(0, 0, 2, 0)

        # Create separate sections for bookmarked and regular items
        self.bookmarked_layout = QVBoxLayout()
        self.bookmarked_layout.setContentsMargins(0, 0, 0, 0)
        self.regular_layout = QVBoxLayout()
        self.regular_layout.setContentsMargins(0, 0, 0, 0)

        # Add layouts to main scroll layout
        self.scroll_layout.addLayout(self.bookmarked_layout)

        # Add separator between bookmarked and regular items
        self.separator = QWidget()
        self.separator.setFixedHeight(2)
        self.separator.setStyleSheet("background-color: #363639;")
        self.separator.setVisible(False)
        self.scroll_layout.addWidget(self.separator)

        self.scroll_layout.addLayout(self.regular_layout)
        self.scroll_layout.addSpacerItem(
            QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        scroll_content = QWidget()
        scroll_content.setLayout(self.scroll_layout)
        self.ui.scrollArea.setWidget(scroll_content)

    #=============================================================<  Bookmarks  >==========================================================

    def init_bookmarks(self):
        """Initialize bookmarks from saved settings"""
        if self.window_name:
            saved_bookmarks = get_config_value('Bookmarks', self.window_name)
            if saved_bookmarks:
                self.bookmarked_items = set(saved_bookmarks.split(','))

    def save_bookmarks(self):
        """Save bookmarks to settings"""
        if self.window_name:
            bookmarks_str = ','.join(self.bookmarked_items)
            set_config_value('Bookmarks', self.window_name, bookmarks_str)

    def add_bookmark(self, key):
        """Add an item to bookmarks"""
        if self.window_name:
            self.bookmarked_items.add(key)
            self.save_bookmarks()
            self.repopulate_items()

    def remove_bookmark(self, key):
        """Remove an item from bookmarks"""
        if self.window_name:
            self.bookmarked_items.discard(key)
            self.save_bookmarks()
            self.repopulate_items()

    def repopulate_items(self):
        """Repopulate all items after bookmark changes"""
        # Clear existing layouts
        self.clear_layout(self.bookmarked_layout)
        self.clear_layout(self.regular_layout)

        # Repopulate items using self.add_once to preserve removed items
        self.populate_properties(self.add_once)

        # Update separator visibility
        self.separator.setVisible(bool(self.bookmarked_items))

    def clear_layout(self, layout):
        """Clear all items from a layout"""
        while layout.count():
            item = layout.takeAt(0)
            self.cleanup_layout_item(item)

    #=============================================================<  Properties  >==========================================================

    def populate_properties(self, add_once):
        """
        Populate the menu with property items.
        If add_once is True, do not re-add items that were removed.
        """
        bookmarked_items_list = []
        for item in self.properties:
            for key, value in item.items():
                # Skip if item was removed permanently
                if add_once and (key, str(value)) in self.removed_items:
                    continue

                element_layout = self.create_property_item(key, value, add_once)
                if key in self.bookmarked_items:
                    bookmarked_items_list.append((key, element_layout))
                else:
                    self.regular_layout.addLayout(element_layout)

        # Add bookmarked items in order
        for i, (key, layout) in enumerate(bookmarked_items_list):
            # Last bookmark gets special style
            if i == len(bookmarked_items_list) - 1:
                label = layout.itemAt(0).widget()
                label.setStyleSheet(self.get_last_bookmark_stylesheet())
            self.bookmarked_layout.addLayout(layout)

        # Show separator if there are bookmarked items
        self.separator.setVisible(bool(self.bookmarked_items))

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

        if self.window_name:
            bookmark_button = self.create_bookmark_button(key)
            element_layout.addWidget(bookmark_button)

        return element_layout

    def create_bookmark_button(self, key):
        """Create bookmark button for property items"""
        button = Button(size=32)
        if key in self.bookmarked_items:
            button.set_icon_bookmark_added()
            button.clicked.connect(lambda: self.remove_bookmark(key))
        else:
            button.set_icon_bookmark_add()
            button.clicked.connect(lambda: self.add_bookmark(key))
        return button

    def create_label_event(self, label, key, value, add_once):
        """
        Create event handler for label clicks.
        If add_once is True, the item is removed permanently.
        Otherwise, it signals that an item was added.
        """
        if add_once:
            return lambda event: self.remove_element(label, key, str(value))
        return lambda event: self.add_property_signal.emit(key, str(value))

    #============================================================<  Help Button  >==========================================================

    def create_help_button(self, label):
        """Create help button for property items"""
        button = Button(size=32)
        button.set_icon_question()
        button.clicked.connect(lambda: self.open_wiki_page(label=label, url=self.help_url))
        return button

    def open_wiki_page(self, label=None, url=None):
        """Open the wiki page based on label and self.help_url"""
        if url is None:
            url = ''
        base_url = "https://developer.valvesoftware.com/wiki/"
        label = self.clean_spaces(label or "Workflow")
        full_url = f"{base_url + url}#{label}"

        try:
            webbrowser.open(full_url)
        except Exception:
            pass

    def clean_spaces(self, text: str) -> str:
        """Replace spaces with underscores for URL usage"""
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

    def get_last_bookmark_stylesheet(self):
        """Get stylesheet for the last bookmarked item"""
        return """
            QLabel {
                font: 580 10pt "Segoe UI";
                border-bottom: 0px solid black;  
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
        """
        Remove an element from the menu and record it so it won't be re-added
        if add_once is True.
        """
        self.add_property_signal.emit(key, value)

        # Record the item as removed permanently if add_once is active
        if self.add_once:
            self.removed_items.add((key, value))

        # Determine if this was a bookmarked item
        target_layout = self.bookmarked_layout if key in self.bookmarked_items else self.regular_layout
        if not target_layout:
            return

        # Find and remove the item from the layout
        for i in range(target_layout.count()):
            item = target_layout.itemAt(i)
            if not item or not item.layout():
                continue

            layout = item.layout()
            label_widget = layout.itemAt(0).widget()
            if label_widget and label_widget.text() == key:
                # Remove item from layout
                item = target_layout.takeAt(i)
                if item:
                    self.cleanup_layout_item(item)

                # Update visible labels and selection
                if label in self.visible_labels:
                    idx = self.visible_labels.index(label)
                    self.visible_labels.pop(idx)
                    if self.current_selection_index >= idx:
                        self.current_selection_index = max(-1, self.current_selection_index - 1)

                # Force layout updates
                target_layout.update()
                self.scroll_layout.update()

                # Update separator visibility if this was a bookmarked item
                if target_layout == self.bookmarked_layout:
                    self.separator.setVisible(self.bookmarked_layout.count() > 0)
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
        if self.visible_labels and 0 <= self.current_selection_index < len(self.visible_labels):
            label = self.visible_labels[self.current_selection_index]
            if label.mousePressEvent:
                label.mousePressEvent(None)

    #===============================================================<  Search  >============================================================

    def search_text_changed(self):
        """Handle search text changes"""
        search_text = self.ui.lineEdit.text().lower()

        # Search in bookmarked layout
        self._search_in_layout(self.bookmarked_layout, search_text)

        # Search in regular layout
        self._search_in_layout(self.regular_layout, search_text)

        # Disable separator during search if there's any text
        if search_text == '':
            self.separator.setVisible(bool(self.bookmarked_items))
        else:
            self.separator.setVisible(False)

        # Reset selection after filtering
        self.current_selection_index = -1
        self.update_visible_labels()
        if self.visible_labels:
            self.current_selection_index = 0
            self.update_selection_highlighting()

    def _search_in_layout(self, layout, search_text):
        """Helper method to search in a specific layout"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item or not item.layout():
                continue

            element_layout = item.layout()
            label_item = element_layout.itemAt(0)
            if not label_item:
                continue

            label = label_item.widget()
            if not isinstance(label, QLabel):
                continue

            visible = search_text in label.text().lower()
            label.setVisible(visible)

            # Make associated buttons (help, bookmark) visible/invisible
            for j in range(1, element_layout.count()):
                widget_item = element_layout.itemAt(j)
                if widget_item and widget_item.widget():
                    widget_item.widget().setVisible(visible)

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
        """Handle show events with improved positioning"""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        window_geometry = self.geometry()

        # Calculate the new position
        x = min(
            max(QCursor.pos().x(), screen_geometry.left()),
            screen_geometry.right() - window_geometry.width()
        )
        y = min(
            max(QCursor.pos().y(), screen_geometry.top()),
            screen_geometry.bottom() - window_geometry.height()
        )

        self.move(x, y)
        super().showEvent(event)