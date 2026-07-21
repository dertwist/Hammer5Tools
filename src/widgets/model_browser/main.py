"""
Source 2 style model browser.

Layout mirrors Hammer's asset picker: a filter row, a view/scale row carrying
the facet chips, a clickable sort header, the asset area (icon grid or detail
list), and a status footer with the accept button.

Mod is the only facet with real values — the content mount a model comes from.
Hammer's Tags facet has no analogue in the Hammer5Tools index, and Asset Types
is fixed at .vmdl, so neither gets a working chip.
"""
from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QSlider, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QStackedWidget, QCheckBox, QButtonGroup, QFrame,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor

from src.styles.common import apply_stylesheets
from src.editors.smartprop_editor.property import compact
from src.widgets.model_browser.index import (
    ModelEntry, ScanWorker, ScanSignals, active_mounts, SOURCE_ADDON, SOURCE_CORE,
)
from src.widgets.model_browser.thumbnails import ThumbnailService, THUMB_SIZE

# Resource path carried on each item, used to marry thumbnails back to rows.
_PATH_ROLE = Qt.UserRole + 1

# List-view columns. The index into this list is also the sort key, and the
# tree's own QHeaderView provides the clickable sort buttons — which is why grid
# mode shows no header at all: there is no separate bar to hide.
COLUMNS = ["Name", "Source", "Mod", "Size"]
COL_NAME, COL_SOURCE, COL_MOD, COL_SIZE = range(4)

_SOURCE_COLOR = {
    SOURCE_ADDON: "#accc8d",
    SOURCE_CORE: "#9AA0AA",
}

class _FacetPopup(QFrame):
    """The drop-down behind a facet chip: name filter, bulk actions, value rows.

    Each row carries an "(Only)" button because isolating one mount is the common
    case and doing it by hand means unchecking every other box.

    A QFrame rather than a plain QWidget so the panel border and background come
    from the application style — a bare QWidget with Qt.Popup paints nothing and
    would show through to whatever is behind it.
    """

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        self._values: List[str] = []
        self._checked: set = set()
        self._rows: List[tuple] = []       # (value, QCheckBox, QWidget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)

        self.name_filter = QLineEdit()
        self.name_filter.setPlaceholderText("(Name Filter)")
        self.name_filter.textChanged.connect(self._apply_name_filter)
        layout.addWidget(self.name_filter)

        buttons = QHBoxLayout()
        buttons.setSpacing(3)
        reset = QPushButton("Reset Filter")
        reset.clicked.connect(self._reset)
        uncheck = QPushButton("Uncheck All")
        uncheck.clicked.connect(lambda: self._set_all(False))
        buttons.addWidget(reset)
        buttons.addWidget(uncheck)
        layout.addLayout(buttons)

        self.rows_host = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_host)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        layout.addWidget(self.rows_host)

    def set_values(self, values: List[str]):
        self._values = list(values)
        self._checked = set(values)

        while self.rows_layout.count():
            child = self.rows_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._rows = []

        for value in values:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(2, 0, 2, 0)
            row_layout.setSpacing(4)

            checkbox = QCheckBox(value)
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda on, v=value: self._on_toggled(v, on))
            row_layout.addWidget(checkbox, 1)

            only = QPushButton("(Only)")
            only.setFlat(True)
            only.setCursor(Qt.PointingHandCursor)
            only.setObjectName("onlyButton")
            only.clicked.connect(lambda _=False, v=value: self._only(v))
            row_layout.addWidget(only)

            self.rows_layout.addWidget(row)
            self._rows.append((value, checkbox, row))

        self.changed.emit()

    def checked_values(self) -> set:
        return set(self._checked)

    def _apply_name_filter(self, text: str):
        """Hides rows only — a hidden mount keeps its checked state, so filtering
        the list never silently changes what the grid is showing."""
        needle = text.strip().lower()
        for value, _checkbox, row in self._rows:
            row.setVisible(needle in value.lower())

    def _on_toggled(self, value: str, on: bool):
        if on:
            self._checked.add(value)
        else:
            self._checked.discard(value)
        self.changed.emit()

    def _set_all(self, on: bool):
        for _value, checkbox, _row in self._rows:
            checkbox.blockSignals(True)
            checkbox.setChecked(on)
            checkbox.blockSignals(False)
        self._checked = set(self._values) if on else set()
        self.changed.emit()

    def _only(self, value: str):
        for row_value, checkbox, _row in self._rows:
            checkbox.blockSignals(True)
            checkbox.setChecked(row_value == value)
            checkbox.blockSignals(False)
        self._checked = {value}
        self.changed.emit()

    def _reset(self):
        self.name_filter.clear()
        self._set_all(True)


class _FacetChip(QPushButton):
    """A 'N/N Mods'-style chip that opens a :class:`_FacetPopup` beneath itself."""

    changed = Signal()

    def __init__(self, noun: str, parent=None):
        super().__init__(parent)
        self.noun = noun
        self.setCursor(Qt.PointingHandCursor)
        self.popup = _FacetPopup(self)
        self.popup.changed.connect(self._on_popup_changed)
        self.clicked.connect(self._show_popup)
        self._refresh_text()

    def set_values(self, values: List[str]):
        self.popup.set_values(values)

    def checked_values(self) -> set:
        return self.popup.checked_values()

    def _on_popup_changed(self):
        self._refresh_text()
        self.changed.emit()

    def _show_popup(self):
        self.popup.adjustSize()
        # Right-align the popup with the chip so it opens inward, not off-screen
        # for chips that sit near the dialog's right edge.
        corner = self.mapToGlobal(self.rect().bottomRight())
        self.popup.move(corner.x() - self.popup.width(), corner.y() + 2)
        self.popup.show()

    def _refresh_text(self):
        checked = len(self.popup.checked_values())
        total = len(self.popup._values)
        self.setText(f"{checked}/{total} {self.noun}")


def _get_model_icon(grayscaled: bool = False) -> Optional[QPixmap]:
    import os
    from PySide6.QtGui import QImage
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icon_path = os.path.join(base_dir, "icons", "tools", "assettypes", "model_lg.png")
    if not os.path.isfile(icon_path):
        icon_path = "src/icons/tools/assettypes/model_lg.png"

    pixmap = QPixmap(icon_path)
    if pixmap.isNull():
        return None

    if grayscaled:
        img = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        for y in range(img.height()):
            for x in range(img.width()):
                c = img.pixelColor(x, y)
                g = int(0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
                c.setRed(g)
                c.setGreen(g)
                c.setBlue(g)
                c.setAlpha(int(c.alpha() * 0.4))
                img.setPixelColor(x, y, c)
        pixmap = QPixmap.fromImage(img)

    return pixmap


def _vmdl_icon_pixmap(size: int, grayscaled: bool = False) -> QPixmap:
    """Tile with the model_lg.png icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(compact.BG))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    # Outer border
    painter.setPen(QColor("#252528" if grayscaled else "#2D2D30"))
    inset = size // 5
    painter.drawRect(inset, inset, size - 2 * inset, size - 2 * inset)

    # Draw model_lg.png icon
    icon_pixmap = _get_model_icon(grayscaled=grayscaled)
    if icon_pixmap and not icon_pixmap.isNull():
        target_dim = max(16, size - 24)
        scaled_icon = icon_pixmap.scaled(target_dim, target_dim, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        target_x = (size - scaled_icon.width()) // 2
        target_y = (size - scaled_icon.height()) // 2
        painter.drawPixmap(target_x, target_y, scaled_icon)

    painter.end()
    return pixmap


def _placeholder_pixmap(size: int) -> QPixmap:
    """Fallback tile with a 3D model (.vmdl) icon shown when no thumbnail is available."""
    return _vmdl_icon_pixmap(size, grayscaled=False)


def _loading_pixmap(size: int, angle: int = 0) -> QPixmap:
    """Grayscaled .vmdl icon tile overlaid with a smooth rotating loading spinner."""
    from PySide6.QtGui import QPen

    pixmap = _vmdl_icon_pixmap(size, grayscaled=True)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    center_x = size // 2
    center_y = size // 2 - 4
    radius = max(10, min(size // 5, 22))

    # Track ring (semi-transparent background disk + track)
    painter.setBrush(QColor(15, 15, 18, 160))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(center_x - radius - 3, center_y - radius - 3, (radius + 3) * 2, (radius + 3) * 2)

    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(60, 60, 68, 200), 2.0))
    painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

    # Rotating accent arc
    pen = QPen(QColor("#accc8d"), 2.5)
    painter.setPen(pen)
    start_angle = int(-angle * 16)
    span_angle = int(100 * 16)
    painter.drawArc(center_x - radius, center_y - radius, radius * 2, radius * 2, start_angle, span_angle)

    painter.end()
    return pixmap


def _human_size(num_bytes: int) -> str:
    if not num_bytes:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} GB"


class ModelBrowserDialog(QDialog):
    """Pick a .vmdl by resource path."""

    # Tiles never render above THUMB_SIZE; the slider only scales them down, so
    # its ceiling is that resolution rather than an arbitrary larger one.
    MIN_THUMB, MAX_THUMB = 64, THUMB_SIZE

    def __init__(self, parent=None, current_path: str = "", addon: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Select Model")
        self.resize(940, 720)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self._entries: List[ModelEntry] = []
        self._visible: List[ModelEntry] = []
        self._selected_path = current_path or ""
        self._thumb_size = THUMB_SIZE
        # Resolve the addon up front. scan_all() falls back to get_addon_name()
        # on its own, so leaving this None would index the addon's models but
        # then omit its mount from the chip — filtering every one of them out.
        if not addon:
            from src.settings.common import get_addon_name
            addon = get_addon_name()
        self._addon = addon

        self.thumbnails = ThumbnailService(size=THUMB_SIZE, parent=self)
        self.thumbnails.ready.connect(self._on_thumbnail_ready)
        self.thumbnails.failed.connect(self._on_thumbnail_failed)

        self._spinner_angle = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(50)
        self._anim_timer.timeout.connect(self._update_loading_spinners)

        self._build_ui()
        self._start_scan()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(3)

        root.addLayout(self._build_filter_row())
        root.addLayout(self._build_view_row())

        self.grid = QListWidget()
        self.grid.setViewMode(QListWidget.IconMode)
        self.grid.setResizeMode(QListWidget.Adjust)
        self.grid.setMovement(QListWidget.Static)
        self.grid.setUniformItemSizes(True)
        self.grid.setWordWrap(True)
        self.grid.setSpacing(3)
        self.grid.setSelectionMode(QAbstractItemView.SingleSelection)
        self.grid.itemSelectionChanged.connect(self._on_grid_selection)
        self.grid.itemDoubleClicked.connect(lambda _: self.accept())
        self.grid.verticalScrollBar().valueChanged.connect(self._schedule_thumbnails)

        self.list = QTreeWidget()
        self.list.setRootIsDecorated(False)
        self.list.setUniformRowHeights(True)
        self.list.setAlternatingRowColors(False)
        self.list.setColumnCount(len(COLUMNS))
        self.list.setHeaderLabels(COLUMNS)
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.itemSelectionChanged.connect(self._on_list_selection)
        self.list.itemDoubleClicked.connect(lambda *_: self.accept())

        # Sorting is driven from the header indicator but applied in
        # _apply_filter(), not by Qt: the views are rebuilt from self._visible on
        # every change, and letting the tree sort itself as well would leave the
        # grid ordered differently from the list.
        header = self.list.header()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(COL_NAME, Qt.AscendingOrder)
        header.sortIndicatorChanged.connect(lambda *_: self._apply_filter())

        self.stack = QStackedWidget()
        self.stack.addWidget(self.grid)
        self.stack.addWidget(self.list)
        root.addWidget(self.stack, 1)

        root.addLayout(self._build_footer())

        # Thumbnail requests are coalesced so a flung scrollbar queues one batch
        # for where it lands, not one per intermediate frame.
        self._thumb_timer = QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self._thumb_timer.setInterval(90)
        self._thumb_timer.timeout.connect(self._request_visible_thumbnails)

    def _build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(3)

        title = QLabel("Filter")
        row.addWidget(title)

        clear = QPushButton("✕")
        clear.setFixedWidth(22)
        clear.setToolTip("Clear filter")
        clear.clicked.connect(lambda: self.filter_edit.clear())
        row.addWidget(clear)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by name or folder…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_filter)
        row.addWidget(self.filter_edit, 1)

        self.refresh_button = QPushButton("Rescan")
        self.refresh_button.setToolTip("Rebuild the model index from disk")
        self.refresh_button.clicked.connect(lambda: self._start_scan(use_cache=False))
        row.addWidget(self.refresh_button)

        return row

    def _build_view_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(5)

        self.list_radio = QRadioButton("List")
        self.grid_radio = QRadioButton("Grid")
        self.grid_radio.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.list_radio)
        group.addButton(self.grid_radio)
        self.grid_radio.toggled.connect(self._on_view_mode_changed)
        row.addWidget(self.list_radio)
        row.addWidget(self.grid_radio)

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setFixedWidth(110)
        self.size_slider.setRange(self.MIN_THUMB, self.MAX_THUMB)
        self.size_slider.setValue(self._thumb_size)
        self.size_slider.setToolTip("Thumbnail size")
        self.size_slider.valueChanged.connect(self._on_thumb_size_changed)
        row.addWidget(self.size_slider)

        row.addStretch(1)

        self.mod_chip = _FacetChip("Mods")
        self.mod_chip.changed.connect(self._apply_filter)
        row.addWidget(self.mod_chip)

        type_chip = QPushButton("1/1 Asset Types")
        type_chip.setEnabled(False)
        type_chip.setToolTip("This browser lists .vmdl models only")
        row.addWidget(type_chip)

        return row

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(5)

        self.status_label = QLabel("Scanning…")
        row.addWidget(self.status_label)

        row.addStretch(1)

        self.path_label = QLabel(self._selected_path or "")
        row.addWidget(self.path_label)

        self.accept_button = QPushButton("Accept")
        self.accept_button.setEnabled(bool(self._selected_path))
        self.accept_button.setDefault(True)
        self.accept_button.clicked.connect(self.accept)
        row.addWidget(self.accept_button)

        return row

    # -------------------------------------------------------------- scanning

    def _start_scan(self, use_cache: bool = True):
        from PySide6.QtCore import QThreadPool

        self.status_label.setText("Scanning…")
        self.refresh_button.setEnabled(False)

        # Owned by the dialog so the worker cannot outlive its signal target.
        self._scan_signals = ScanSignals()
        self._scan_signals.finished.connect(self._on_scan_finished, Qt.QueuedConnection)
        QThreadPool.globalInstance().start(
            ScanWorker(self._addon, self._scan_signals, use_cache=use_cache))

    def _on_scan_finished(self, entries: list):
        self._entries = entries
        self.refresh_button.setEnabled(True)

        # Every mount on the search path, in precedence order rather than
        # alphabetically, so the addon sits at the top where Hammer puts it.
        # Mounts that contributed nothing are still listed: csgo_imported and
        # csgo_core carry no models at all, and quietly dropping them would make
        # the chip's contents look different between installs.
        self.mod_chip.set_values(active_mounts(self._addon))

        self._apply_filter()

    # ------------------------------------------------------------- filtering

    def _apply_filter(self, *_):
        needle = self.filter_edit.text().strip().lower()
        allowed_mods = self.mod_chip.checked_values()

        matches = []
        for entry in self._entries:
            if entry.mod not in allowed_mods:
                continue
            # Match against the full resource path so "props/urban" narrows by
            # folder just as well as a bare model name does.
            if needle and needle not in entry.path.lower():
                continue
            matches.append(entry)

        header = self.list.header()
        column = header.sortIndicatorSection()
        descending = header.sortIndicatorOrder() == Qt.DescendingOrder
        # Path is the tiebreaker everywhere so equal sizes/mods keep a stable,
        # readable order rather than whatever the filter loop happened to yield.
        sort_keys = {
            COL_NAME: lambda e: e.path.lower(),
            COL_SOURCE: lambda e: (e.source, e.path.lower()),
            COL_MOD: lambda e: (e.mod.lower(), e.path.lower()),
            COL_SIZE: lambda e: (e.size, e.path.lower()),
        }
        matches.sort(key=sort_keys.get(column, sort_keys[COL_NAME]), reverse=descending)

        self._visible = matches
        self._populate()

    def _populate(self):
        self._anim_timer.stop()
        self.thumbnails.cancel_pending()
        placeholder = _placeholder_pixmap(self._thumb_size)

        self.grid.setUpdatesEnabled(False)
        self.list.setUpdatesEnabled(False)
        self.grid.clear()
        self.list.clear()

        self.grid.setIconSize(QSize(self._thumb_size, self._thumb_size))
        # Room for the icon plus the two-line elided name beneath it.
        self.grid.setGridSize(QSize(self._thumb_size + 16, self._thumb_size + 38))

        selected_grid_item = None
        selected_list_item = None

        for entry in self._visible:
            item = QListWidgetItem(entry.name)
            item.setIcon(placeholder)
            item.setData(_PATH_ROLE, entry.path)
            item.setToolTip(f"{entry.path}\n{entry.mod} · {entry.source}")
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            item.setSizeHint(QSize(self._thumb_size + 16, self._thumb_size + 38))
            self.grid.addItem(item)
            if entry.path == self._selected_path:
                selected_grid_item = item

            row = QTreeWidgetItem([
                entry.path, entry.source, entry.mod, _human_size(entry.size)])
            row.setData(0, _PATH_ROLE, entry.path)
            row.setForeground(1, QColor(_SOURCE_COLOR.get(entry.source, "#E3E3E3")))
            self.list.addTopLevelItem(row)
            if entry.path == self._selected_path:
                selected_list_item = row

        for column, width in enumerate((0, 90, 150, 90)):
            if width:
                self.list.setColumnWidth(column, width)
        self.list.setColumnWidth(0, max(320, self.list.viewport().width() - 330))

        if selected_grid_item is not None:
            self.grid.setCurrentItem(selected_grid_item)
            self.grid.scrollToItem(selected_grid_item, QAbstractItemView.PositionAtCenter)
        if selected_list_item is not None:
            self.list.setCurrentItem(selected_list_item)
            self.list.scrollToItem(selected_list_item, QAbstractItemView.PositionAtCenter)

        self.grid.setUpdatesEnabled(True)
        self.list.setUpdatesEnabled(True)

        self.status_label.setText(
            f"{len(self._visible)} of {len(self._entries)} Assets Visible")
        self._schedule_thumbnails()

    # ------------------------------------------------------------ thumbnails

    def _schedule_thumbnails(self, *_):
        self._thumb_timer.start()

    def _request_visible_thumbnails(self):
        """Queue thumbnails for exactly the tiles the user can see right now.

        A full index runs to thousands of models; baking all of them would spend
        minutes of GPU and disk on tiles nobody looks at. Anything queued for a
        previous scroll position is dropped first, so a fast scroll does not make
        the tiles now on screen wait behind a backlog of ones already passed.
        """
        if self.stack.currentWidget() is not self.grid:
            self._anim_timer.stop()
            return

        by_path = {e.path: e for e in self._visible}
        viewport_rect = self.grid.viewport().rect()

        visible_items = []
        visible_paths = set()

        for index in range(self.grid.count()):
            item = self.grid.item(index)
            rect = self.grid.visualItemRect(item)
            if not rect.intersects(viewport_rect):
                if rect.isValid() and rect.top() > viewport_rect.bottom():
                    break
                continue
            path = item.data(_PATH_ROLE)
            if path in by_path:
                visible_items.append((item, by_path[path]))
                visible_paths.add(path)

        self.thumbnails.set_visible_paths(visible_paths)

        has_pending = False
        loading_icon = _loading_pixmap(self._thumb_size, self._spinner_angle)

        for item, entry in visible_items:
            pixmap = self.thumbnails.request(entry)
            if pixmap is not None:
                item.setIcon(self._scaled(pixmap))
            else:
                item.setIcon(loading_icon)
                has_pending = True

        if has_pending:
            if not self._anim_timer.isActive():
                self._anim_timer.start()
        else:
            self._anim_timer.stop()

    def _update_loading_spinners(self):
        if not self.thumbnails.has_pending() or self.stack.currentWidget() is not self.grid:
            self._anim_timer.stop()
            return

        self._spinner_angle = (self._spinner_angle + 25) % 360
        loading_icon = _loading_pixmap(self._thumb_size, self._spinner_angle)

        viewport_rect = self.grid.viewport().rect()
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            rect = self.grid.visualItemRect(item)
            if not rect.intersects(viewport_rect):
                if rect.isValid() and rect.top() > viewport_rect.bottom():
                    break
                continue
            path = item.data(_PATH_ROLE)
            if path and self.thumbnails.is_pending(path):
                item.setIcon(loading_icon)

    def _scaled(self, pixmap: QPixmap) -> QPixmap:
        if pixmap.width() == self._thumb_size:
            return pixmap
        return pixmap.scaled(self._thumb_size, self._thumb_size,
                             Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _on_thumbnail_ready(self, resource_path: str, pixmap: QPixmap):
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            if item.data(_PATH_ROLE) == resource_path:
                item.setIcon(self._scaled(pixmap))
                break
        if not self.thumbnails.has_pending():
            self._anim_timer.stop()

    def _on_thumbnail_failed(self, resource_path: str):
        placeholder = _placeholder_pixmap(self._thumb_size)
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            if item.data(_PATH_ROLE) == resource_path:
                item.setIcon(placeholder)
                break
        if not self.thumbnails.has_pending():
            self._anim_timer.stop()

    def _on_thumb_size_changed(self, value: int):
        self._thumb_size = value
        # The service renders at a fixed resolution and the grid scales down, so
        # dragging the slider never invalidates the cache.
        self._populate()

    # -------------------------------------------------------------- selection

    def _on_view_mode_changed(self, grid_checked: bool):
        # Grid mode has no column header of its own — switching the stack is all
        # it takes for the Name/Source/Mod/Size buttons to go away.
        self.stack.setCurrentWidget(self.grid if grid_checked else self.list)
        self._schedule_thumbnails()

    def resizeEvent(self, event):
        # The grid rewraps on resize, bringing different tiles into view.
        super().resizeEvent(event)
        self._schedule_thumbnails()

    def _set_selected(self, resource_path: str):
        self._selected_path = resource_path or ""
        self.path_label.setText(self._selected_path)
        self.accept_button.setEnabled(bool(self._selected_path))

    def _on_grid_selection(self):
        item = self.grid.currentItem()
        self._set_selected(item.data(_PATH_ROLE) if item else "")

    def _on_list_selection(self):
        item = self.list.currentItem()
        self._set_selected(item.data(0, _PATH_ROLE) if item else "")

    # ------------------------------------------------------------------- API

    def selected_path(self) -> str:
        return self._selected_path

    def keyPressEvent(self, event):
        # Enter in the filter box should not fall through to Accept while the
        # user is still narrowing the list.
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.filter_edit.hasFocus():
            return
        super().keyPressEvent(event)


def pick_model(parent=None, current_path: str = "", addon: Optional[str] = None) -> Optional[str]:
    """Open the browser and return the chosen resource path, or None if cancelled."""
    dialog = ModelBrowserDialog(parent, current_path=current_path, addon=addon)
    apply_stylesheets(dialog)
    if dialog.exec() == QDialog.Accepted:
        return dialog.selected_path() or None
    return None
