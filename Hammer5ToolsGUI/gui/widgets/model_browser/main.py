"""
Source 2 style model browser.

Layout mirrors Hammer's asset picker: a filter row, a view/scale row carrying
the facet chips, a clickable sort header, the asset area (icon grid or detail
list), and a status footer with the accept button.

Mod is the only facet with real values — the content mount a model comes from.
Hammer's Tags facet has no analogue in the Hammer5Tools index, and Asset Types
is fixed at .vmdl, so neither gets a working chip.
"""
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QSlider, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QStackedWidget, QCheckBox, QButtonGroup, QFrame,
    QAbstractItemView, QMenu, QApplication
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QAction, QPen, QImage, QIcon

from gui.styles.common import apply_stylesheets
from gui.editors.smartprop_editor.property import compact
from gui.widgets.model_browser.index import (
    ModelEntry, ScanWorker, ScanSignals, active_mounts, SOURCE_ADDON, SOURCE_CORE,
    GAME_MOUNTS, get_game_entries,
)
from gui.widgets.model_browser.thumbnails import ThumbnailService, THUMB_SIZE

try:
    from gui.other.cs2_netcon import CS2Netcon
except Exception:
    CS2Netcon = None

# Resource path carried on each item, used to marry thumbnails back to rows.
_PATH_ROLE = Qt.UserRole + 1

COLUMNS = ["Name", "Source", "Mod", "Size"]
COL_NAME, COL_SOURCE, COL_MOD, COL_SIZE = range(4)

_SOURCE_COLOR = {
    SOURCE_ADDON: "#b3d096",
    SOURCE_CORE: "#a2a8b1",
}


def get_saved_mod_selection(active_addon: Optional[str] = None) -> Optional[set]:
    """Retrieve saved mod selection from settings. Returns None if not configured."""
    from gui.settings.common import get_settings_value
    val = get_settings_value("AssetBrowser", "selected_mods", default=None)
    if val is None:
        return None
    raw_list = [x.strip() for x in str(val).split(",") if x.strip()]
    resolved = set()
    for item in raw_list:
        if item in ("addon", "csgo_addons") or item.startswith("csgo_addons/"):
            if active_addon:
                resolved.add(f"csgo_addons/{active_addon}")
            else:
                resolved.add("addon")
        else:
            resolved.add(item)
    return resolved


def save_saved_mod_selection(checked_mods: set, active_addon: Optional[str] = None) -> None:
    """Save selected mods to settings."""
    from gui.settings.common import set_settings_value
    to_save = []
    addon_prefix = f"csgo_addons/{active_addon}" if active_addon else "csgo_addons/"
    for mod in checked_mods:
        if mod == "addon" or mod == addon_prefix or mod.startswith("csgo_addons/"):
            to_save.append("addon")
        else:
            to_save.append(mod)
    set_settings_value("AssetBrowser", "selected_mods", ",".join(sorted(to_save)))


class _FacetPopup(QFrame):
    """The drop-down behind a facet chip: name filter, bulk actions, value rows."""

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
        self.setStyleSheet("QFrame { background-color: #272727; border: 1px solid #464649; }")
        apply_stylesheets(self)

    def set_values(self, values: List[str], checked: Optional[set] = None):
        self._values = list(values)
        if checked is not None:
            self._checked = set(checked) & set(values)
        else:
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
            checkbox.setChecked(value in self._checked)
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

        apply_stylesheets(self)
        self.changed.emit()

    def checked_values(self) -> set:
        return set(self._checked)

    def _apply_name_filter(self, text: str):
        tokens = text.strip().lower().split()
        for value, _checkbox, row in self._rows:
            if not tokens:
                row.setVisible(True)
            else:
                v_lower = value.lower()
                row.setVisible(all(token in v_lower for token in tokens))

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

    def set_values(self, values: List[str], checked: Optional[set] = None):
        self.popup.set_values(values, checked=checked)
        self._refresh_text()

    def checked_values(self) -> set:
        return self.popup.checked_values()

    def _on_popup_changed(self):
        self._refresh_text()
        self.changed.emit()

    def _show_popup(self):
        self.popup.adjustSize()
        corner = self.mapToGlobal(self.rect().bottomRight())
        self.popup.move(corner.x() - self.popup.width(), corner.y() + 2)
        self.popup.show()

    def _refresh_text(self):
        checked = len(self.popup.checked_values())
        total = len(self.popup._values)
        self.setText(f"{checked}/{total} {self.noun}")


ASSET_LG_ICONS = {
    "vmdl": "model_lg.png",
    "vmat": "material_lg.png",
    "vsmart": "smart_prop_lg.png",
    "vsndevts": "vmix_lg.png",
    "vsnd": "vmix_lg.png",
    "vdata": "vdata_lg.png",
    "vpcf": "particles_lg.png",
    "vpost": "postprocessing_lg.png",
    "vmap": "map_lg.png",
    "vtex": "texture_lg.png",
}

ASSET_SM_ICONS = {
    "vmdl": "://icons/tools/assettypes/model_sm.png",
    "vmat": "://icons/tools/assettypes/material_sm.png",
    "vsmart": "://icons/tools/assettypes/vsmart_sm.png",
    "vsndevts": "://icons/tools/assettypes/vmix_sm.png",
    "vsnd": "://icons/tools/assettypes/vmix_sm.png",
    "vdata": "://icons/tools/assettypes/vdata_sm.png",
    "vpcf": "://icons/tools/assettypes/generic_sm.png",
    "vpost": "://icons/tools/assettypes/generic_sm.png",
    "vmap": "://icons/tools/assettypes/map_sm.png",
    "vtex": "://icons/tools/assettypes/texture_sm.png",
}

_SM_QICON_CACHE = {}


def _get_sm_icon(asset_type: str) -> QIcon:
    clean = (asset_type or "generic").lower()
    if clean not in _SM_QICON_CACHE:
        icon_path = ASSET_SM_ICONS.get(clean, "://icons/tools/assettypes/generic_sm.png")
        _SM_QICON_CACHE[clean] = QIcon(icon_path)
    return _SM_QICON_CACHE[clean]


_SOURCE_QCOLOR = {
    SOURCE_ADDON: QColor("#b3d096"),
    SOURCE_CORE: QColor("#a2a8b1"),
}


def _get_asset_icon(asset_type: str = "vmdl", grayscaled: bool = False) -> Optional[QPixmap]:
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    icon_name = ASSET_LG_ICONS.get(asset_type.lower(), "model_lg.png")
    icon_path = os.path.join(base_dir, "icons", "tools", "assettypes", icon_name)
    pixmap = QPixmap(icon_path)
    if pixmap.isNull():
        # Fallback to model_lg.png
        icon_path = os.path.join(base_dir, "icons", "tools", "assettypes", "model_lg.png")
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


def _asset_icon_pixmap(asset_type: str, size: int, grayscaled: bool = False) -> QPixmap:
    """Tile with the asset type icon."""
    from gui.styles import theme
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(theme.color(compact.BG)))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    # Outer border
    painter.setPen(theme.qcolor("#252528" if grayscaled else "#3e3e41"))
    inset = size // 5
    painter.drawRect(inset, inset, size - 2 * inset, size - 2 * inset)

    icon_pixmap = _get_asset_icon(asset_type, grayscaled=grayscaled)
    if icon_pixmap and not icon_pixmap.isNull():
        target_dim = max(16, size - 24)
        scaled_icon = icon_pixmap.scaled(target_dim, target_dim, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        target_x = (size - scaled_icon.width()) // 2
        target_y = (size - scaled_icon.height()) // 2
        painter.drawPixmap(target_x, target_y, scaled_icon)

    painter.end()
    return pixmap


_PLACEHOLDER_CACHE = {}


def _placeholder_pixmap(size: int, asset_type: str = "vmdl") -> QPixmap:
    key = (size, asset_type)
    if key not in _PLACEHOLDER_CACHE:
        _PLACEHOLDER_CACHE[key] = _asset_icon_pixmap(asset_type, size, grayscaled=False)
    return _PLACEHOLDER_CACHE[key]


def _loading_pixmap(size: int, angle: int = 0) -> QPixmap:
    pixmap = _asset_icon_pixmap("vmdl", size, grayscaled=True)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    center_x = size // 2
    center_y = size // 2 - 4
    radius = max(10, min(size // 5, 22))

    painter.setBrush(QColor(15, 15, 18, 160))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(center_x - radius - 3, center_y - radius - 3, (radius + 3) * 2, (radius + 3) * 2)

    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(60, 60, 68, 200), 2.0))
    painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)

    # Rotating accent arc
    pen = QPen(QColor("#b3d096"), 2.5)
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


class ModelBrowserWidget(QWidget):
    """Reusable Source 2 Asset & Model Browser widget."""

    model_selected = Signal(str)
    model_double_clicked = Signal(str)
    use_as_template = Signal(str)

    MIN_THUMB, MAX_THUMB = 64, THUMB_SIZE

    def __init__(
        self, parent=None, current_path: str = "", addon: Optional[str] = None,
        show_accept: bool = False, auto_scan: bool = True,
        addon_only: bool = False, asset_types: Optional[List[str]] = None
    ):
        super().__init__(parent)
        self._entries: List[ModelEntry] = []
        self._visible: List[ModelEntry] = []
        self._selected_path = current_path or ""
        self._thumb_size = THUMB_SIZE
        self.show_accept = show_accept
        self._has_scanned = False
        self._addon_only = addon_only
        self._asset_types = asset_types
        self._game_scanned = False

        if not addon:
            from gui.settings.common import get_addon_name
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
        if auto_scan:
            self._start_scan()

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
        self.grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self._show_context_menu)
        self.grid.itemSelectionChanged.connect(self._on_grid_selection)
        self.grid.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.grid.verticalScrollBar().valueChanged.connect(self._schedule_thumbnails)

        self.list = QTreeWidget()
        self.list.setRootIsDecorated(False)
        self.list.setUniformRowHeights(True)
        self.list.setAlternatingRowColors(False)
        self.list.setColumnCount(len(COLUMNS))
        self.list.setHeaderLabels(COLUMNS)
        self.list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._show_context_menu)
        self.list.itemSelectionChanged.connect(self._on_list_selection)
        self.list.itemDoubleClicked.connect(self._on_item_double_clicked)

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

        self._thumb_timer = QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self._thumb_timer.setInterval(90)
        self._thumb_timer.timeout.connect(self._request_visible_thumbnails)

    def _build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(3)

        title = QLabel("Filter")
        row.addWidget(title)



        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter by name or folder…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_filter)
        row.addWidget(self.filter_edit, 1)

        self.refresh_button = QPushButton("Rescan")
        self.refresh_button.setToolTip("Rebuild the asset index from disk")
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
        self.mod_chip.changed.connect(self._on_mod_chip_changed)
        row.addWidget(self.mod_chip)

        self.type_chip = _FacetChip("Asset Types")
        self.type_chip.changed.connect(self._apply_filter)
        row.addWidget(self.type_chip)

        return row

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(5)

        self.status_label = QLabel("Ready")
        row.addWidget(self.status_label)

        row.addStretch(1)

        self.path_label = QLabel(self._selected_path or "")
        row.addWidget(self.path_label)

        if self.show_accept:
            self.accept_button = QPushButton("Accept")
            self.accept_button.setEnabled(bool(self._selected_path))
            self.accept_button.setDefault(True)
            row.addWidget(self.accept_button)

        return row

    def _show_context_menu(self, position):
        sender = self.sender()
        if not sender:
            return

        path = self._selected_path
        if not path:
            return

        menu = QMenu(self)

        use_template_action = QAction("Use as Reference Template in AssetGroup Maker", self)
        use_template_action.triggered.connect(lambda: self.use_as_template.emit(path))
        menu.addAction(use_template_action)

        menu.addSeparator()

        copy_action = QAction("Copy Resource Path", self)
        copy_action.triggered.connect(lambda: QApplication.clipboard().setText(path))
        menu.addAction(copy_action)

        open_cs2_action = QAction("Open in CS2 Tools", self)
        open_cs2_action.triggered.connect(lambda: self._open_in_cs2(path))
        menu.addAction(open_cs2_action)

        menu.exec_(sender.mapToGlobal(position))

    def _open_in_cs2(self, path: str):
        if CS2Netcon:
            clean_path = path.replace('\\', '/').strip('/')
            CS2Netcon.send(f"open_asset {clean_path}")

    def _start_scan(self, use_cache: bool = True):
        self._has_scanned = True
        self.status_label.setText("Scanning…")
        self.refresh_button.setEnabled(False)

        # Check if saved mod selection only selects addon (no game mounts)
        scan_addon_only = self._addon_only
        if not scan_addon_only:
            saved = get_saved_mod_selection(self._addon)
            if saved is not None:
                has_game = any(m in saved for m in GAME_MOUNTS)
                if not has_game:
                    scan_addon_only = True

        self._game_scanned = not scan_addon_only

        # Fast path: if index is already in memory cache and use_cache is True,
        # load synchronously to avoid thread dispatch latency.
        from gui.widgets.model_browser.index import is_index_cached, scan_all
        if use_cache and is_index_cached(self._addon, addon_only=scan_addon_only):
            entries = scan_all(
                self._addon,
                addon_only=scan_addon_only,
                asset_types=self._asset_types,
                use_game_cache=True,
                use_addon_cache=True
            )
            self._on_scan_finished(entries)
            return

        from PySide6.QtCore import QThreadPool
        self._scan_signals = ScanSignals()
        self._scan_signals.finished.connect(self._on_scan_finished, Qt.QueuedConnection)
        QThreadPool.globalInstance().start(
            ScanWorker(
                self._addon,
                self._scan_signals,
                use_cache=use_cache,
                addon_only=scan_addon_only,
                asset_types=self._asset_types
            )
        )

    def _on_scan_finished(self, entries: list):
        self._entries = entries
        self.refresh_button.setEnabled(True)

        saved_mods = None
        if not self._addon_only:
            saved_mods = get_saved_mod_selection(self._addon)

        self.mod_chip.set_values(
            active_mounts(self._addon, addon_only=self._addon_only),
            checked=saved_mods
        )

        discovered_types = sorted(list({f".{e.asset_type}" for e in self._entries if e.asset_type}))
        if discovered_types:
            self.type_chip.set_values(discovered_types)
            if len(discovered_types) > 1:
                self.type_chip.show()
            else:
                self.type_chip.hide()
        else:
            self.type_chip.hide()

        self._apply_filter()

    def _on_mod_chip_changed(self):
        checked_mods = self.mod_chip.checked_values()
        if not self._addon_only:
            save_saved_mod_selection(checked_mods, self._addon)

            # If user checked any game mount, but game entries weren't loaded yet
            if not self._game_scanned and any(m in checked_mods for m in GAME_MOUNTS):
                self._load_game_entries()

        self._apply_filter()

    def _load_game_entries(self):
        """Dynamically load and merge game mount entries into self._entries."""
        from gui.settings.main import get_cs2_path
        from gui.widgets.model_browser.index import get_game_entries
        cs2_path = get_cs2_path()
        if not cs2_path:
            return
        game_entries = get_game_entries(cs2_path, use_cache=True)
        if self._asset_types:
            clean_types = {t.lstrip('.').lower() for t in self._asset_types}
            game_entries = [e for e in game_entries if e.asset_type.lower() in clean_types]

        seen = {e.path.lower() for e in self._entries}
        new_entries = list(self._entries)
        for e in game_entries:
            key = e.path.lower()
            if key not in seen:
                seen.add(key)
                new_entries.append(e)

        self._entries = new_entries
        self._game_scanned = True

        discovered_types = sorted(list({f".{e.asset_type}" for e in self._entries if e.asset_type}))
        if discovered_types:
            self.type_chip.set_values(discovered_types)
            if len(discovered_types) > 1:
                self.type_chip.show()
            else:
                self.type_chip.hide()

    def _apply_filter(self, *_):
        raw = self.filter_edit.text().strip().lower().replace("\\", "/")
        tokens = raw.split()
        allowed_mods = self.mod_chip.checked_values()
        allowed_types = {t.lstrip('.').lower() for t in self.type_chip.checked_values()}

        matches = []
        for entry in self._entries:
            if entry.mod not in allowed_mods:
                continue
            if allowed_types and entry.asset_type.lower() not in allowed_types:
                continue
            if tokens:
                path_lower = entry.path.lower()
                if not all(token in path_lower for token in tokens):
                    continue
            matches.append(entry)

        header = self.list.header()
        column = header.sortIndicatorSection()
        descending = header.sortIndicatorOrder() == Qt.DescendingOrder

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

        self.grid.setUpdatesEnabled(False)
        self.list.setUpdatesEnabled(False)
        self.grid.clear()
        self.list.clear()

        item_size = QSize(self._thumb_size + 16, self._thumb_size + 38)
        self.grid.setIconSize(QSize(self._thumb_size, self._thumb_size))
        self.grid.setGridSize(item_size)

        selected_grid_item = None
        selected_list_item = None
        tree_rows = []
        default_color = QColor("#e5e5e5")

        for entry in self._visible:
            placeholder = _placeholder_pixmap(self._thumb_size, entry.asset_type)
            item = QListWidgetItem(entry.name)
            item.setIcon(placeholder)
            item.setData(_PATH_ROLE, entry.path)
            item.setToolTip(f"{entry.path}\n{entry.mod} · {entry.source}")
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            item.setSizeHint(item_size)
            self.grid.addItem(item)
            if entry.path == self._selected_path:
                selected_grid_item = item

            row = QTreeWidgetItem([
                entry.path, entry.source, entry.mod, _human_size(entry.size)
            ])
            row.setData(0, _PATH_ROLE, entry.path)
            row.setIcon(0, _get_sm_icon(entry.asset_type))
            row.setForeground(1, _SOURCE_QCOLOR.get(entry.source, default_color))
            tree_rows.append(row)
            if entry.path == self._selected_path:
                selected_list_item = row

        if tree_rows:
            self.list.addTopLevelItems(tree_rows)

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

    def _schedule_thumbnails(self, *_):
        self._thumb_timer.start()

    def _request_visible_thumbnails(self):
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
                entry = by_path[path]
                if entry.asset_type.lower() == 'vmdl':
                    visible_items.append((item, entry))
                    visible_paths.add(path)
                else:
                    item.setIcon(_placeholder_pixmap(self._thumb_size, entry.asset_type))

        self.thumbnails.set_visible_paths(visible_paths)

        has_pending = False
        loading_icon = _loading_pixmap(self._thumb_size, self._spinner_angle)

        for item, entry in visible_items:
            placeholder = _placeholder_pixmap(self._thumb_size, entry.asset_type)
            pixmap = self.thumbnails.request(entry)
            if pixmap is not None:
                item.setIcon(self._scaled(pixmap))
            elif self.thumbnails.is_failed(entry.path):
                item.setIcon(placeholder)
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

        self._spinner_angle = (self._spinner_angle + 10) % 360
        loading_icon = _loading_pixmap(self._thumb_size, self._spinner_angle)

        for index in range(self.grid.count()):
            item = self.grid.item(index)
            path = item.data(_PATH_ROLE)
            if self.thumbnails.is_pending(path):
                item.setIcon(loading_icon)

    def _scaled(self, pixmap: QPixmap) -> QPixmap:
        if pixmap.width() == self._thumb_size and pixmap.height() == self._thumb_size:
            return pixmap
        return pixmap.scaled(
            self._thumb_size, self._thumb_size,
            Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _on_thumbnail_ready(self, path: str, pixmap: QPixmap):
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            if item.data(_PATH_ROLE) == path:
                item.setIcon(self._scaled(pixmap))
                break
        if not self.thumbnails.has_pending():
            self._anim_timer.stop()

    def _on_thumbnail_failed(self, path: str):
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            if item.data(_PATH_ROLE) == path:
                item.setIcon(_placeholder_pixmap(self._thumb_size, "vmdl"))
                break
        if not self.thumbnails.has_pending():
            self._anim_timer.stop()

    def _on_thumb_size_changed(self, value: int):
        self._thumb_size = value
        self._populate()

    def _on_view_mode_changed(self, grid_checked: bool):
        self.stack.setCurrentWidget(self.grid if grid_checked else self.list)
        self._schedule_thumbnails()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_thumbnails()

    def _set_selected(self, resource_path: str):
        self._selected_path = resource_path or ""
        self.path_label.setText(self._selected_path)
        if hasattr(self, 'accept_button'):
            self.accept_button.setEnabled(bool(self._selected_path))
        self.model_selected.emit(self._selected_path)

    def _on_grid_selection(self):
        item = self.grid.currentItem()
        self._set_selected(item.data(_PATH_ROLE) if item else "")

    def _on_list_selection(self):
        item = self.list.currentItem()
        self._set_selected(item.data(0, _PATH_ROLE) if item else "")

    def _on_item_double_clicked(self, *_):
        if self._selected_path:
            self.model_double_clicked.emit(self._selected_path)

    def selected_path(self) -> str:
        return self._selected_path

    def set_current_path(self, current_path: str):
        self._set_selected(current_path)

        # Scroll to selected item in grid and list
        selected_grid_item = None
        for index in range(self.grid.count()):
            item = self.grid.item(index)
            if item.data(_PATH_ROLE) == self._selected_path:
                selected_grid_item = item
                break

        selected_list_item = None
        for index in range(self.list.topLevelItemCount()):
            item = self.list.topLevelItem(index)
            if item.data(0, _PATH_ROLE) == self._selected_path:
                selected_list_item = item
                break

        if selected_grid_item is not None:
            self.grid.setCurrentItem(selected_grid_item)
            self.grid.scrollToItem(selected_grid_item, QAbstractItemView.PositionAtCenter)
        else:
            self.grid.clearSelection()

        if selected_list_item is not None:
            self.list.setCurrentItem(selected_list_item)
            self.list.scrollToItem(selected_list_item, QAbstractItemView.PositionAtCenter)
        else:
            self.list.clearSelection()

        self._schedule_thumbnails()


class AssetBrowserDialog(QDialog):
    """Dialog wrapper around ModelBrowserWidget supporting multi-asset types and addon filtering."""

    def __init__(
        self,
        parent=None,
        current_path: str = "",
        addon: Optional[str] = None,
        addon_only: bool = True,
        asset_types: Optional[List[str]] = None,
        title: str = "Select Reference Template Asset"
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(960, 720)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.browser = ModelBrowserWidget(
            self,
            current_path=current_path,
            addon=addon,
            show_accept=True,
            auto_scan=True,
            addon_only=addon_only,
            asset_types=asset_types
        )
        self.browser.accept_button.clicked.connect(self.accept)
        self.browser.model_double_clicked.connect(lambda _: self.accept())
        layout.addWidget(self.browser)

        # Apply the SmartProp editor's iconic per-widget stylesheets automatically
        # so every caller gets consistent styling without needing to remember.
        apply_stylesheets(self)

    def selected_path(self) -> str:
        return self.browser.selected_path()


_DIALOG_CACHE: Dict[tuple, AssetBrowserDialog] = {}


def clear_dialog_cache():
    """Clear all pre-cached dialog instances."""
    global _DIALOG_CACHE
    _DIALOG_CACHE.clear()


def _get_cached_dialog(
    parent=None,
    current_path: str = "",
    addon: Optional[str] = None,
    addon_only: bool = False,
    asset_types: Optional[List[str]] = None,
    title: str = "Select Asset"
) -> AssetBrowserDialog:
    """Get or create a pre-cached AssetBrowserDialog for instant reopening."""
    global _DIALOG_CACHE
    try:
        from shiboken6 import isValid
    except Exception:
        isValid = lambda obj: True

    if not addon:
        from gui.settings.common import get_addon_name
        addon = get_addon_name()

    types_key = tuple(sorted(asset_types)) if asset_types else ()
    cache_key = (addon or "", addon_only, types_key)

    dialog = _DIALOG_CACHE.get(cache_key)
    if dialog is not None and isValid(dialog):
        dialog.setWindowTitle(title)
        if parent is not None:
            dialog.setParent(parent, dialog.windowFlags())
        dialog.browser.set_current_path(current_path)
        return dialog

    dialog = AssetBrowserDialog(
        parent=parent,
        current_path=current_path,
        addon=addon,
        addon_only=addon_only,
        asset_types=asset_types,
        title=title
    )
    _DIALOG_CACHE[cache_key] = dialog
    return dialog


def pick_model(parent=None, current_path: str = "", addon: str = None) -> Optional[str]:
    """Open the browser and return the chosen resource path, or None if cancelled."""
    dialog = _get_cached_dialog(
        parent=parent,
        current_path=current_path,
        addon=addon,
        addon_only=False,
        asset_types=[".vmdl"],
        title="Select Model"
    )
    if dialog.exec() == QDialog.Accepted:
        return dialog.selected_path() or None
    return None


def pick_smartprop(parent=None, current_path: str = "", addon: str = None) -> Optional[str]:
    """Open the smartprop browser and return the chosen resource path, or None if cancelled."""
    dialog = _get_cached_dialog(
        parent=parent,
        current_path=current_path,
        addon=addon,
        addon_only=False,
        asset_types=[".vsmart"],
        title="Select SmartProp"
    )
    if dialog.exec() == QDialog.Accepted:
        return dialog.selected_path() or None
    return None


def pick_asset(
    parent=None,
    current_path: str = "",
    addon: Optional[str] = None,
    addon_only: bool = True,
    asset_types: Optional[List[str]] = None,
    title: str = "Select Asset"
) -> Optional[str]:
    """Open the asset browser dialog and return chosen resource path, or None if cancelled."""
    dialog = _get_cached_dialog(
        parent=parent,
        current_path=current_path,
        addon=addon,
        addon_only=addon_only,
        asset_types=asset_types,
        title=title
    )
    if dialog.exec() == QDialog.Accepted:
        return dialog.selected_path() or None
    return None

