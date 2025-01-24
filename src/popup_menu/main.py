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


class PropertyItemWidget(QWidget):
    """
    Represents an individual property entry in the popup menu.
    Allows toggling bookmarks, showing help, and emitting item click signals.
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
        self.key = key
        self.value = value
        self.help_url = help_url
        self.window_name = window_name
        self.add_once = add_once
        self.ignore_items = ignore_items or set()
        self.bookmarked_items = bookmarked_items or set()
        self.popup_menu = popup_menu
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(self.key, self)
        self.label.mousePressEvent = self._on_label_clicked
        layout.addWidget(self.label)

        if self.help_url:
            help_button = Button(size=32)
            help_button.set_icon_question()
            help_button.clicked.connect(self._on_help_clicked)
            layout.addWidget(help_button)

        if self.window_name:
            bookmark_button = Button(size=32)
            if self.key in self.bookmarked_items:
                bookmark_button.set_icon_bookmark_added()
            else:
                bookmark_button.set_icon_bookmark_add()
            bookmark_button.clicked.connect(self._toggle_bookmark)
            layout.addWidget(bookmark_button)

    def _apply_styles(self):
        self.label.setStyleSheet(self._label_stylesheet())

    def _on_label_clicked(self, event):
        """
        If 'add_once' is set, skip if already ignored,
        or remove it if newly added.
        """
        if self.add_once and (self.key, str(self.value)) in self.ignore_items:
            return
        remove_item = self.add_once and (self.key, str(self.value)) not in self.ignore_items
        self.property_clicked.emit(self.key, str(self.value), remove_item, self.label)

    def _on_help_clicked(self):
        base_url = "https://developer.valvesoftware.com/wiki/"
        cleaned_label = self.key.replace(" ", "_") or "Workflow"
        url = f"{base_url}{self.help_url or ''}#{cleaned_label}"
        webbrowser.open(url)

    def _toggle_bookmark(self):
        if self.key in self.bookmarked_items:
            self.bookmarked_items.remove(self.key)
        else:
            self.bookmarked_items.add(self.key)

        if self.window_name:
            set_config_value('Bookmarks', self.window_name, ','.join(self.bookmarked_items))

        if self.popup_menu:
            self.popup_menu.repopulate_items()

    @staticmethod
    def _label_stylesheet():
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


class PopupMenu(QDialog):
    """
    A popup menu that displays a list of property items, supports bookmarking,
    searching, keyboard navigation, and helpful links.
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
        self.properties = properties
        self.help_url = help_url
        self.window_name = window_name
        self.ui = Ui_PoPupMenu()
        self.ui.setupUi(self)

        self.add_once = add_once
        self.ignore_items = self._convert_ignore_list(ignore_list)

        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setGeometry(200, 200, 400, 400)

        self.current_selection_index = -1
        self.visible_labels = []
        self.bookmarked_items = set()
        self.removed_items = set()

        # Setup UI, load bookmarks, and populate items
        self._setup_ui()
        self._init_bookmarks()
        self._populate_properties()

        # Track if the menu has begun closing to avoid recursive calls
        self._is_closing = False

    def _convert_ignore_list(self, ignore_list):
        """
        Convert ignore_list to a consistent set of (key, value) pairs.
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
        Create separate layouts for bookmarked and regular items,
        plus a search bar at the top and a separator widget.
        Also installs an event filter on the lineEdit to capture arrow keys.
        """
        self.ui.lineEdit.installEventFilter(self)
        self.ui.lineEdit.textChanged.connect(self._search_text_changed)
        self.ui.lineEdit.setFocus()

        # Scroll container layout
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setContentsMargins(0, 0, 2, 0)

        self.bookmarked_layout = QVBoxLayout()
        self.bookmarked_layout.setContentsMargins(0, 0, 0, 0)

        self.regular_layout = QVBoxLayout()
        self.regular_layout.setContentsMargins(0, 0, 0, 0)

        # Separator line
        self.separator = QWidget()
        self.separator.setFixedHeight(2)
        self.separator.setStyleSheet("background-color: #363639;")
        self.separator.hide()

        self.scroll_layout.addLayout(self.bookmarked_layout)
        self.scroll_layout.addWidget(self.separator)
        self.scroll_layout.addLayout(self.regular_layout)
        self.scroll_layout.addSpacerItem(
            QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        scroll_content = QWidget()
        scroll_content.setLayout(self.scroll_layout)
        self.ui.scrollArea.setWidget(scroll_content)

    def eventFilter(self, obj, event):
        """
        Capture arrow keys from self.ui.lineEdit so that
        up/down navigates items instead of moving cursor.
        """
        if obj == self.ui.lineEdit and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self.navigate_selection(-1)
                return True
            elif event.key() == Qt.Key_Down:
                self.navigate_selection(1)
                return True
        return super().eventFilter(obj, event)

    def _init_bookmarks(self):
        """
        Load previously saved bookmarks for this specific window name,
        if any exist in settings.
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
        Iteratively remove and delete all widgets from a layout.
        """
        while layout.count():
            item = layout.takeAt(0)
            self._cleanup_layout_item(item)

    def _populate_properties(self):
        """
        Create PropertyItemWidgets for each property, separating
        bookmarked vs. regular items.
        """
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

                if key in self.bookmarked_items:
                    bookmarked_list.append(item_widget)
                else:
                    self.regular_layout.addWidget(item_widget)

        for idx, wdg in enumerate(bookmarked_list):
            if idx == len(bookmarked_list) - 1:
                wdg.label.setStyleSheet(self._bookmark_bottom_style())
            self.bookmarked_layout.addWidget(wdg)

        self.separator.setVisible(len(bookmarked_list) > 0)
        self._update_visible_labels()

    def _on_property_clicked(self, key, val, remove_item, label):
        """
        Called when a PropertyItemWidget's label is clicked.
        Emit a signal and optionally remove the item if 'add_once' requires it.
        """
        self.add_property_signal.emit(key, val)
        if remove_item:
            self.removed_items.add((key, val))
            self._remove_layout_item(label)
        self._update_visible_labels()

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
        Non-recursive BFS approach to safely delete widgets or layouts inside an item.
        """
        wdg = item.widget()
        if wdg:
            wdg.deleteLater()
        else:
            child_layout = item.layout()
            if child_layout:
                queue = [child_layout]
                while queue:
                    current_layout = queue.pop()
                    while current_layout.count():
                        cn_item = current_layout.takeAt(0)
                        cn_wdg = cn_item.widget()
                        if cn_wdg:
                            cn_wdg.deleteLater()
                        else:
                            cl = cn_item.layout()
                            if cl:
                                queue.append(cl)

    def _update_visible_labels(self):
        """
        Gathers visible labels in BFS order for keyboard navigation.
        """
        self.visible_labels.clear()
        self.current_selection_index = -1

        scroll_widget = self.ui.scrollArea.widget()
        if not scroll_widget:
            return

        queue = [scroll_widget.layout()]
        while queue:
            current_layout = queue.pop(0)
            if not current_layout:
                continue

            for i in range(current_layout.count()):
                itm = current_layout.itemAt(i)
                if itm is None:
                    continue
                child_wdg = itm.widget()
                child_lay = itm.layout()

                if child_lay:
                    queue.append(child_lay)
                elif child_wdg and isinstance(child_wdg, PropertyItemWidget):
                    if child_wdg.isVisible():
                        self.visible_labels.append(child_wdg.label)

        # Automatically select first visible label
        if self.visible_labels:
            self.current_selection_index = 0
            self._update_selection_highlighting()

    def navigate_selection(self, delta):
        """
        Moves selection up/down among visible labels.
        """
        if not self.visible_labels:
            return
        self.current_selection_index = (self.current_selection_index + delta) % len(self.visible_labels)
        self._update_selection_highlighting()
        label = self.visible_labels[self.current_selection_index]
        self.ui.scrollArea.ensureWidgetVisible(label)

    def _update_selection_highlighting(self):
        """
        Update label highlight based on current selection index.
        """
        for idx, label in enumerate(self.visible_labels):
            label.setProperty("selected", idx == self.current_selection_index)
            label.style().unpolish(label)
            label.style().polish(label)

    def activate_selection(self):
        """
        Simulate clicking the currently selected label.
        """
        if 0 <= self.current_selection_index < len(self.visible_labels):
            label = self.visible_labels[self.current_selection_index]
            if label.mousePressEvent:
                label.mousePressEvent(None)

    def _search_text_changed(self):
        """
        Triggered when the search text changes. Hide or show item widgets based on match.
        """
        text = self.ui.lineEdit.text().lower()
        self._search_layout_iterative(self.bookmarked_layout, text)
        self._search_layout_iterative(self.regular_layout, text)

        # Show the separator only if search field is empty and there are bookmarked items
        self.separator.setVisible(len(text) == 0 and bool(self.bookmarked_items))

        self._update_visible_labels()

    def _search_layout_iterative(self, layout, search_text):
        """
        Iteratively traverse a layout to show/hide items matching the search text.
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
        Keyboard handling for navigation and activation when the dialog
        (not the lineEdit) has focus.
        """
        handlers = {
            Qt.Key_Down: lambda: self.navigate_selection(1),
            Qt.Key_Up: lambda: self.navigate_selection(-1),
            Qt.Key_Return: self.activate_selection,
            Qt.Key_Enter: self.activate_selection,
            Qt.Key_Space: self.activate_selection
        }
        func = handlers.get(event.key())
        if func:
            func()
            event.accept()
        else:
            super().keyPressEvent(event)

    def event(self, evt):
        """
        Close the menu when focus is lost.
        Avoid re-entrant calls if the dialog is already closing.
        """
        if evt.type() == QEvent.WindowDeactivate and not self._is_closing:
            self._is_closing = True
            self.close()
            return True
        return super().event(evt)

    def showEvent(self, evt):
        """
        Position and show the popup near the cursor.
        """
        screen_geo = QApplication.primaryScreen().availableGeometry()
        win_geo = self.geometry()

        x = min(max(QCursor.pos().x(), screen_geo.left()), screen_geo.right() - win_geo.width())
        y = min(max(QCursor.pos().y(), screen_geo.top()), screen_geo.bottom() - win_geo.height())

        self.move(x, y)
        super().showEvent(evt)

    def closeEvent(self, evt):
        """
        Thoroughly clean up to prevent resource leaks.
        """
        if self._is_closing:
            # We are already in the closing process; skip redundant calls
            super().closeEvent(evt)
            return

        self._is_closing = True
        self._clear_layout(self.bookmarked_layout)
        self._clear_layout(self.regular_layout)
        if self.ui and self.ui.scrollArea:
            self.ui.scrollArea.setWidget(None)

        self.ui = None
        self.bookmarked_items.clear()
        self.removed_items.clear()
        self.visible_labels.clear()
        super().closeEvent(evt)

    @staticmethod
    def _bookmark_bottom_style():
        """
        Special style for the last bookmarked item.
        """
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