###############################################################################
# script.py (excerpt with bookmark toggle fix for immediate UI feedback)
###############################################################################

import webbrowser
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy
)
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtCore import QEvent, Qt, Signal
from src.widgets.popup_menu.ui_main import Ui_PoPupMenu
from src.widgets.common import Button
from src.settings.main import set_settings_value, get_settings_value
from src.widgets.popup_menu.common import _label_stylesheet, _bookmark_bottom_style


class PropertyItemWidget(QWidget):
    """
    Represents an individual property entry in the popup menu.
    Allows toggling bookmarks, showing help, and emitting item-click signals.
    """
    property_clicked = Signal(str, str, bool, object)

    def __init__(
        self,
        key,
        value,
        help_url=None,
        window_name=None,
        add_once=False,
        ignore_items=None,
        bookmarked_items=None,
        popup_menu=None,
        parent=None
    ):
        super().__init__(parent)
        self._parent = parent
        self._popup_menu = popup_menu

        self.key = key
        self.value = value
        self.help_url = help_url
        self.window_name = window_name
        self.add_once = add_once
        self.ignore_items = ignore_items or set()
        self.bookmarked_items = bookmarked_items or set()

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        # Main layout for this property widget
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Label that displays the property name/key
        self.label = QLabel(self.key, self)
        self.label.mousePressEvent = self._on_label_clicked
        self._layout.addWidget(self.label)

        # Optional help button
        if self.help_url:
            self.help_button = Button(size=32)
            self.help_button.set_icon_question()
            self.help_button.clicked.connect(self._on_help_clicked)
            self._layout.addWidget(self.help_button)

        # Optional bookmark button
        if self.window_name:
            self.bookmark_button = Button(size=32)
            if self.key in self.bookmarked_items:
                self.bookmark_button.set_icon_bookmark_added()
            else:
                self.bookmark_button.set_icon_bookmark_add()
            self.bookmark_button.clicked.connect(self._toggle_bookmark)
            self._layout.addWidget(self.bookmark_button)

    def _apply_styles(self):
        # Apply a global stylesheet to the label
        self.label.setStyleSheet(_label_stylesheet())

    def _on_label_clicked(self, event):
        """Called when the user clicks the property label."""
        if self.add_once and (self.key, str(self.value)) in self.ignore_items:
            return
        remove_item = self.add_once and (self.key, str(self.value)) not in self.ignore_items
        self.property_clicked.emit(self.key, str(self.value), remove_item, self.label)

    def _on_help_clicked(self):
        """
        Open the help URL in a web browser. The label name is appended
        to the URL's fragment identifier.
        """
        base_url = "https://developer.valvesoftware.com/wiki/"
        cleaned_label = self.key.replace(" ", "_") or "Workflow"
        url = f"{base_url}{self.help_url or ''}#{cleaned_label}"
        webbrowser.open(url)

    def _toggle_bookmark(self):
        """
        Add or remove the key from the bookmarks set, then refresh the parent's UI
        so that the change is immediately visible.
        """
        if self.key in self.bookmarked_items:
            self.bookmarked_items.remove(self.key)
            self.bookmark_button.set_icon_bookmark_add()
        else:
            self.bookmarked_items.add(self.key)
            self.bookmark_button.set_icon_bookmark_added()

        # Persist the updated bookmarks
        if self.window_name:
            set_settings_value('Bookmarks', self.window_name, ','.join(self.bookmarked_items))

        # Immediately refresh the popup menu's layout to reflect the new bookmark status
        if self._popup_menu:
            self._popup_menu.bookmarked_items = self.bookmarked_items
            self._popup_menu.repopulate_items()

    def cleanup(self):
        """
        Cleanup method to break circular references and ensure child widgets
        are properly deleted.
        """
        if hasattr(self, 'help_button'):
            self.help_button.deleteLater()
        if hasattr(self, 'bookmark_button'):
            self.bookmark_button.deleteLater()
        self.label.deleteLater()
        self._popup_menu = None
        self._parent = None


class PopupMenu(QDialog):
    """
    A popup menu that displays a list of property items, supports bookmarking,
    searching, and helpful links.
    """
    label_clicked = Signal(str)
    add_property_signal = Signal(str, str)

    def __init__(
        self,
        properties,
        add_once=False,
        ignore_list=None,
        parent=None,
        help_url=None,
        window_name=None
    ):
        super().__init__(parent)
        # Store configuration parameters
        self.properties = properties
        self.help_url = help_url
        self.window_name = window_name

        # Set up the UI from generated .ui file
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)

        self.add_once = add_once
        self.ignore_items = self._convert_ignore_list(ignore_list)

        # Remove title bar and set initial geometry
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setGeometry(200, 200, 400, 400)

        self.bookmarked_items = set()
        self.removed_items = set()

        # Create internal layouts, read stored bookmarks, and populate
        self._setup_ui()
        self._init_bookmarks()
        self._populate_properties()

        self._is_closing = False

    def _convert_ignore_list(self, ignore_list):
        """Convert ignore_list to a consistent set of (key, value) pairs if needed."""
        ignore = set()
        if ignore_list:
            for item in ignore_list:
                if isinstance(item, str):
                    ignore.add((item, item))
                else:
                    k, v = item
                    ignore.add((k, str(v)))
        return ignore

    def _setup_ui(self):
        """Create layouts for bookmarked vs. regular items, handle search bar."""
        self.ui.lineEdit.setFocusPolicy(Qt.StrongFocus)
        self.ui.lineEdit.textChanged.connect(self._search_text_changed)
        self.ui.lineEdit.setFocus()

        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setContentsMargins(0, 0, 2, 0)

        # Layout for bookmarked items
        self.bookmarked_layout = QVBoxLayout()
        self.bookmarked_layout.setContentsMargins(0, 0, 0, 0)

        # Layout for regular items
        self.regular_layout = QVBoxLayout()
        self.regular_layout.setContentsMargins(0, 0, 0, 0)

        # Separator between bookmarked and regular items
        self.separator = QWidget()
        self.separator.setFixedHeight(2)
        self.separator.setStyleSheet("background-color: #363639;")
        self.separator.hide()

        # Combine everything
        self.scroll_layout.addLayout(self.bookmarked_layout)
        self.scroll_layout.addWidget(self.separator)
        self.scroll_layout.addLayout(self.regular_layout)
        self.scroll_layout.addSpacerItem(
            QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        self.container = QWidget()
        self.container.setLayout(self.scroll_layout)
        self.ui.scrollArea.setWidget(self.container)

    def _init_bookmarks(self):
        """Load saved bookmarks from config."""
        if self.window_name:
            saved = get_settings_value('Bookmarks', self.window_name)
            if saved:
                self.bookmarked_items = set(saved.split(','))

    def repopulate_items(self):
        """Clears layouts and repopulates items so any bookmark changes are visible."""
        self._clear_layout(self.bookmarked_layout)
        self._clear_layout(self.regular_layout)
        self._populate_properties()
        self.separator.setVisible(bool(self.bookmarked_items))

    def _clear_layout(self, layout):
        """Remove all widgets in a layout."""
        while layout and layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                if isinstance(widget, PropertyItemWidget):
                    widget.cleanup()
                widget.deleteLater()

    def _populate_properties(self):
        """Populate the menu with bookmarked items on top, regular items below."""
        bookmarked_list = []
        for mapping in self.properties:
            for key, val in mapping.items():
                if self.add_once and (key, str(val)) in self.removed_items:
                    continue

                item_widget = PropertyItemWidget(
                    key=key,
                    value=val,
                    help_url=self.help_url,
                    window_name=self.window_name,
                    add_once=self.add_once,
                    ignore_items=self.ignore_items,
                    bookmarked_items=self.bookmarked_items,
                    popup_menu=self,
                    parent=self
                )
                item_widget.property_clicked.connect(self._on_property_clicked)

                # Decide if it goes in bookmarked or regular layout
                if key in self.bookmarked_items:
                    bookmarked_list.append(item_widget)
                else:
                    self.regular_layout.addWidget(item_widget)

        # If bookmarked_list isn't empty, style the last item differently
        for idx, wdg in enumerate(bookmarked_list):
            if idx == len(bookmarked_list) - 1:
                wdg.label.setStyleSheet(_bookmark_bottom_style())
            self.bookmarked_layout.addWidget(wdg)

        self.separator.setVisible(len(bookmarked_list) > 0)

    def _on_property_clicked(self, key, val, remove_item, label):
        """User clicked a property label."""
        self.add_property_signal.emit(key, val)
        if remove_item:
            self.removed_items.add((key, val))
            self._remove_layout_item(label)

    def _remove_layout_item(self, label):
        """Remove a widget with the given label from either layout."""
        for layout in (self.bookmarked_layout, self.regular_layout):
            for i in range(layout.count()):
                it = layout.itemAt(i)
                if not it:
                    continue
                wdg = it.widget()
                if wdg and isinstance(wdg, PropertyItemWidget) and wdg.label == label:
                    layout.takeAt(i)
                    self._cleanup_layout_item(it)
                    self.separator.setVisible(self.bookmarked_layout.count() > 0)
                    return

    def _cleanup_layout_item(self, item):
        """Clean up a layout item properly."""
        if not item:
            return
        widget = item.widget()
        if widget and isinstance(widget, PropertyItemWidget):
            widget.cleanup()
        if widget:
            widget.deleteLater()

    def _search_text_changed(self):
        """When the search bar changes, show only matching items."""
        text = self.ui.lineEdit.text().lower()
        self._search_layout_iterative(self.bookmarked_layout, text)
        self._search_layout_iterative(self.regular_layout, text)
        self.separator.setVisible(len(text) == 0 and bool(self.bookmarked_items))

    def _search_layout_iterative(self, layout, search_text):
        queue = [layout]
        while queue:
            current_layout = queue.pop(0)
            for i in range(current_layout.count()):
                it = current_layout.itemAt(i)
                if not it:
                    continue
                child_wdg = it.widget()
                child_lay = it.layout()

                if child_lay:
                    queue.append(child_lay)
                elif child_wdg and isinstance(child_wdg, PropertyItemWidget):
                    is_match = search_text in child_wdg.label.text().lower()
                    child_wdg.setVisible(is_match)

    def keyPressEvent(self, event: QKeyEvent):
        """Allow closing with escape; no keyboard-based item selection."""
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def event(self, evt):
        """Close the menu when focus is lost, if not already closing."""
        if evt.type() == QEvent.WindowDeactivate and not self._is_closing:
            self._is_closing = True
            self.close()
            return True
        return super().event(evt)

    def showEvent(self, evt):
        """Position the popup near the mouse cursor when it shows."""
        screen_geo = QApplication.primaryScreen().availableGeometry()
        win_geo = self.geometry()

        x = min(max(QCursor.pos().x(), screen_geo.left()), screen_geo.right() - win_geo.width())
        y = min(max(QCursor.pos().y(), screen_geo.top()), screen_geo.bottom() - win_geo.height())

        self.move(x, y)
        super().showEvent(evt)

    def closeEvent(self, evt):
        """Clean up layouts and references on close."""
        if self._is_closing:
            super().closeEvent(evt)
            return

        self._is_closing = True
        self._clear_layout(self.bookmarked_layout)
        self._clear_layout(self.regular_layout)

        if self.ui and self.ui.scrollArea:
            self.ui.scrollArea.setWidget(None)
            self.container.deleteLater()

        self.ui = None
        self.bookmarked_items.clear()
        self.removed_items.clear()
        super().closeEvent(evt)