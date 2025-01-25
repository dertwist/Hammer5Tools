import webbrowser
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QWidget,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QLineEdit
)
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtCore import QEvent, Qt, Signal
from src.popup_menu.ui_main import Ui_PoPupMenu
from src.widgets_common import Button
from src.settings.main import set_config_value, get_config_value
from src.popup_menu.common import _label_stylesheet, _bookmark_bottom_style


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
        # Store references to prevent garbage collection or unintended deletions
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
        """
        Called when the user clicks the property label.
        Signals the parent that this property was selected.
        """
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
        Add or remove the key from the bookmarks set, then refresh the parent's UI.
        """
        if self.key in self.bookmarked_items:
            self.bookmarked_items.remove(self.key)
            self.bookmark_button.set_icon_bookmark_add()
        else:
            self.bookmarked_items.add(self.key)
            self.bookmark_button.set_icon_bookmark_added()

        if self.window_name:
            set_config_value('Bookmarks', self.window_name, ','.join(self.bookmarked_items))

        if self._popup_menu:
            self._popup_menu.repopulate_items()

    def cleanup(self):
        """
        Explicit cleanup method to break circular references
        and ensure child widgets are properly deleted.
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
    searching, and helpful links. Keyboard-based selection is removed for clarity.
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

        # Set up the UI from the generated .ui file
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)

        # Mark whether properties should be added once and potential ignore list
        self.add_once = add_once
        self.ignore_items = self._convert_ignore_list(ignore_list)

        # Remove title bar and set initial geometry
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)  # Ensure full cleanup on close
        self.setGeometry(200, 200, 400, 400)

        # Track sets for bookmarked and removed items
        self.bookmarked_items = set()
        self.removed_items = set()

        # Set up the internal layouts, read stored bookmarks, and populate
        self._setup_ui()
        self._init_bookmarks()
        self._populate_properties()

        # Track if the menu is closing to avoid duplicate calls
        self._is_closing = False

    def _convert_ignore_list(self, ignore_list):
        """
        Convert ignore_list to a consistent set of (key, value) pairs if needed.
        """
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
        """
        Create separate layouts for bookmarked vs. regular items,
        plus a search bar at the top, and a separator widget.
        Also removes keyboard navigation for clarity.
        """
        self.ui.lineEdit.setFocusPolicy(Qt.StrongFocus)
        self.ui.lineEdit.textChanged.connect(self._search_text_changed)
        self.ui.lineEdit.setFocus()

        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setContentsMargins(0, 0, 2, 0)

        # Layout for bookmarked items at the top
        self.bookmarked_layout = QVBoxLayout()
        self.bookmarked_layout.setContentsMargins(0, 0, 0, 0)

        # Layout for regular (non-bookmarked) items below
        self.regular_layout = QVBoxLayout()
        self.regular_layout.setContentsMargins(0, 0, 0, 0)

        # Visual separator between bookmarked and regular items
        self.separator = QWidget()
        self.separator.setFixedHeight(2)
        self.separator.setStyleSheet("background-color: #363639;")
        self.separator.hide()

        # Add layouts to our scroll layout
        self.scroll_layout.addLayout(self.bookmarked_layout)
        self.scroll_layout.addWidget(self.separator)
        self.scroll_layout.addLayout(self.regular_layout)
        self.scroll_layout.addSpacerItem(
            QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # Store the scrollable content in self.container for safe cleanup later
        self.container = QWidget()
        self.container.setLayout(self.scroll_layout)
        self.ui.scrollArea.setWidget(self.container)

    def _init_bookmarks(self):
        """
        Load previously saved bookmarks for this specific window name, if any.
        """
        if self.window_name:
            saved = get_config_value('Bookmarks', self.window_name)
            if saved:
                self.bookmarked_items = set(saved.split(','))

    def repopulate_items(self):
        """
        Clears layouts and repopulates properties, ensuring
        changes (like toggling bookmarks) are applied.
        """
        self._clear_layout(self.bookmarked_layout)
        self._clear_layout(self.regular_layout)
        self._populate_properties()
        self.separator.setVisible(bool(self.bookmarked_items))

    def _clear_layout(self, layout):
        """
        Recursively remove all widgets from a layout, cleaning them up.
        """
        while layout and layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                if isinstance(widget, PropertyItemWidget):
                    widget.cleanup()
                widget.deleteLater()

    def _populate_properties(self):
        """
        Create PropertyItemWidgets for each property, separating
        bookmarked vs. regular items for distinct layouts.
        """
        bookmarked_list = []
        for mapping in self.properties:
            for key, val in mapping.items():
                # If add_once is set, skip items that have already been removed
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

                if key in self.bookmarked_items:
                    bookmarked_list.append(item_widget)
                else:
                    self.regular_layout.addWidget(item_widget)

        # Add bookmarked items after collecting them in a list
        for idx, wdg in enumerate(bookmarked_list):
            if idx == len(bookmarked_list) - 1:
                wdg.label.setStyleSheet(_bookmark_bottom_style())
            self.bookmarked_layout.addWidget(wdg)

        self.separator.setVisible(len(bookmarked_list) > 0)

    def _on_property_clicked(self, key, val, remove_item, label):
        """
        Called when a PropertyItemWidget's label is clicked.
        Emit a signal and optionally remove the item if 'add_once' requires it.
        """
        self.add_property_signal.emit(key, val)
        if remove_item:
            self.removed_items.add((key, val))
            self._remove_layout_item(label)

    def _remove_layout_item(self, label):
        """
        Traverse bookmarked and regular layouts to remove the widget with a given label.
        """
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
        """
        Safely clean up a layout item by calling its cleanup() method, then deleting it.
        """
        if not item:
            return
        widget = item.widget()
        if widget and isinstance(widget, PropertyItemWidget):
            widget.cleanup()
        if widget:
            widget.deleteLater()

    def _search_text_changed(self):
        """
        Triggered when the search text changes. Hide or show item widgets based on match.
        """
        text = self.ui.lineEdit.text().lower()
        self._search_layout_iterative(self.bookmarked_layout, text)
        self._search_layout_iterative(self.regular_layout, text)

        # Show separator only if search field is empty and there are bookmarked items
        self.separator.setVisible(len(text) == 0 and bool(self.bookmarked_items))

    def _search_layout_iterative(self, layout, search_text):
        """
        Recursively traverse a layout's items and hide/show them based on matching text.
        """
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
        """
        Overrides the main widget's keyPressEvent only to close or pass
        the event along. Keyboard-based item selection is removed.
        """
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def event(self, evt):
        """
        Close the menu when focus is lost. Avoid re-entrant calls if already closing.
        """
        if evt.type() == QEvent.WindowDeactivate and not self._is_closing:
            self._is_closing = True
            self.close()
            return True
        return super().event(evt)

    def showEvent(self, evt):
        """
        Automatically position and show the popup near the cursor.
        """
        screen_geo = QApplication.primaryScreen().availableGeometry()
        win_geo = self.geometry()

        x = min(max(QCursor.pos().x(), screen_geo.left()), screen_geo.right() - win_geo.width())
        y = min(max(QCursor.pos().y(), screen_geo.top()), screen_geo.bottom() - win_geo.height())

        self.move(x, y)
        super().showEvent(evt)

    def closeEvent(self, evt):
        """
        Ensure we don't re-enter close steps multiple times. Cleans layouts
        and breaks references for a smoother shutdown and to avoid crashes.
        """
        if self._is_closing:
            super().closeEvent(evt)
            return

        self._is_closing = True
        self._clear_layout(self.bookmarked_layout)
        self._clear_layout(self.regular_layout)

        # Clean up the scroll area contents
        if self.ui and self.ui.scrollArea:
            self.ui.scrollArea.setWidget(None)
            self.container.deleteLater()

        # Clear references for safety
        self.ui = None
        self.bookmarked_items.clear()
        self.removed_items.clear()

        super().closeEvent(evt)