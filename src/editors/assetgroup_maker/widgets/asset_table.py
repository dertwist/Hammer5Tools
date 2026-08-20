import os
from typing import List, Optional, Dict, Set, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMenu, QMessageBox, QApplication, QFrame, QStyledItemDelegate, QStyle
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QColor, QBrush, QPen, QAction, QDropEvent, QIcon, QPainter, QFont

from src.editors.assetgroup_maker.matcher import AssetGroupItem
from src.styles.common import (
    qt_stylesheet_lineedit, qt_stylesheet_combobox, qt_stylesheet_table, apply_stylesheets
)

try:
    from src.other.cs2_netcon import CS2Netcon
except Exception:
    CS2Netcon = None


class StatusBadgeDelegate(QStyledItemDelegate):
    """Paints a crisp, centered status badge with zero layout margins or widget clipping."""

    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Selection background
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor("#515965"))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(option.rect, QColor("#38383B"))

        text = index.data(Qt.DisplayRole) or ""
        lower = text.lower()

        if text:
            rect = option.rect
            badge_w = 58
            badge_h = 17
            badge_x = rect.x() + (rect.width() - badge_w) // 2
            badge_y = rect.y() + (rect.height() - badge_h) // 2
            badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)

            if lower == "ready":
                bg = QColor("#233827")
                border = QColor("#2E7D32")
                fg = QColor("#81C784")
            elif lower == "warning":
                bg = QColor("#3E341B")
                border = QColor("#F57F17")
                fg = QColor("#FFD54F")
            else:
                bg = QColor("#3E2020")
                border = QColor("#C62828")
                fg = QColor("#E57373")

            painter.setBrush(QBrush(bg))
            painter.setPen(QPen(border, 1))
            painter.drawRect(badge_rect)

            painter.setPen(fg)
            font = painter.font()
            font.setFamily("Segoe UI")
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(badge_rect, Qt.AlignCenter, text)

        painter.restore()


from src.editors.assetgroup_maker.matcher import AssetGroupItem, _evaluate_item_status
from src.editors.assetgroup_maker.widgets.slot_editor import SlotAssignmentDialog


class AssetTableWidget(QWidget):
    """
    Multi-File Target Asset Mapping Table displaying detected assets,
    matched companion file slots, target output filenames, and status badges.
    """

    files_dropped = Signal(list)  # List[str] of dropped paths
    slots_modified = Signal(AssetGroupItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: List[AssetGroupItem] = []
        self._visible_items: List[AssetGroupItem] = []
        self.slots_def: Dict[str, Dict] = {}
        self._build_ui()

    def set_slots_definition(self, slots_def: Dict[str, Dict]):
        self.slots_def = slots_def or {}

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 1. Filter Bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)

        search_label = QLabel("Search:")
        search_label.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #A5A5A5;")
        filter_row.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setStyleSheet(qt_stylesheet_lineedit)
        self.search_edit.setPlaceholderText("Filter assets by name or file path...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.search_edit, 1)

        status_label = QLabel("Status:")
        status_label.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #A5A5A5;")
        filter_row.addWidget(status_label)

        self.status_combo = QComboBox()
        self.status_combo.setStyleSheet(qt_stylesheet_combobox)
        self.status_combo.addItems(["All", "Ready", "Warnings", "Errors"])
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.status_combo)

        tpl_label = QLabel("Template:")
        tpl_label.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #A5A5A5;")
        filter_row.addWidget(tpl_label)

        self.template_filter_combo = QComboBox()
        self.template_filter_combo.setStyleSheet(qt_stylesheet_combobox)
        self.template_filter_combo.addItem("All Templates")
        self.template_filter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.template_filter_combo)

        layout.addLayout(filter_row)

        # 2. Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "#", "Status", "Template", "Target Asset Name", "Matched Multi-File Slots", "Target Output File"
        ])

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.setAcceptDrops(True)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 36)
        self.table.setColumnWidth(1, 72)
        self.table.setColumnWidth(2, 125)
        self.table.setColumnWidth(3, 170)
        self.table.setColumnWidth(5, 210)

        self.table.setItemDelegateForColumn(1, StatusBadgeDelegate(self.table))
        self.table.setStyleSheet(qt_stylesheet_table)

        # Override drop event on table
        self.table.dragEnterEvent = self._table_drag_enter
        self.table.dragMoveEvent = self._table_drag_move
        self.table.dropEvent = self._table_drop

        layout.addWidget(self.table, 1)

    def _table_drag_enter(self, event: QDropEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _table_drag_move(self, event: QDropEvent):
        event.acceptProposedAction()

    def _table_drop(self, event: QDropEvent):
        mime = event.mimeData()
        paths = []
        if mime.hasUrls():
            for url in mime.urls():
                p = url.toLocalFile()
                if p:
                    paths.append(p)
        elif mime.hasText():
            for line in mime.text().splitlines():
                line = line.strip().strip('"').strip("'")
                if line:
                    paths.append(line)

        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()

    def set_items(self, items: List[AssetGroupItem]):
        self._all_items = items
        self._update_template_filter_options()
        self._apply_filter()

    def _update_template_filter_options(self):
        current = self.template_filter_combo.currentText()
        templates_present = sorted(list(set(i.template_label for i in self._all_items if i.template_label)))

        self.template_filter_combo.blockSignals(True)
        self.template_filter_combo.clear()
        self.template_filter_combo.addItem("All Templates")
        for tpl in templates_present:
            self.template_filter_combo.addItem(tpl)

        idx = self.template_filter_combo.findText(current)
        if idx >= 0:
            self.template_filter_combo.setCurrentIndex(idx)
        else:
            self.template_filter_combo.setCurrentIndex(0)
        self.template_filter_combo.blockSignals(False)

    def get_items(self) -> List[AssetGroupItem]:
        return self._all_items

    def _apply_filter(self):
        query = self.search_edit.text().strip().lower()
        status_filter = self.status_combo.currentText().lower()
        tpl_filter = self.template_filter_combo.currentText()

        filtered = []
        for item in self._all_items:
            # Status filter
            if status_filter == "ready" and item.status != "ready":
                continue
            if status_filter == "warnings" and item.status != "warning":
                continue
            if status_filter == "errors" and item.status != "error":
                continue

            # Template filter
            if tpl_filter != "All Templates" and item.template_label != tpl_filter:
                continue

            # Query filter
            if query:
                name_match = query in item.name.lower()
                slot_match = any(query in os.path.basename(p).lower() for p in item.slots.values())
                out_match = query in item.target_output.lower()
                tpl_match = query in item.template_label.lower()
                if not (name_match or slot_match or out_match or tpl_match):
                    continue

            filtered.append(item)

        self._visible_items = filtered
        self._populate_table()

    def _populate_table(self):
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(self._visible_items))

        for row_idx, item in enumerate(self._visible_items):
            # 0. Index
            idx_item = QTableWidgetItem(str(row_idx + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_idx, 0, idx_item)

            # 1. Status Badge Item (Rendered cleanly via StatusBadgeDelegate)
            status_item = QTableWidgetItem(item.status.capitalize())
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            status_item.setToolTip(item.status_message)
            self.table.setItem(row_idx, 1, status_item)

            # 2. Template
            tpl_item = QTableWidgetItem(item.template_label or item.extension)
            tpl_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_idx, 2, tpl_item)

            # 3. Asset Name
            name_item = QTableWidgetItem(item.name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_idx, 3, name_item)

            # 4. Matched Slots String
            slots_str = self._format_slots_string(item)
            slots_item = QTableWidgetItem(slots_str)
            slots_item.setToolTip("\n".join(f"{k}: {v}" for k, v in item.slots.items()))
            slots_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_idx, 4, slots_item)

            # 5. Target Output
            out_item = QTableWidgetItem(item.target_output)
            out_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_idx, 5, out_item)

            self.table.setRowHeight(row_idx, 24)

        self.table.setUpdatesEnabled(True)

    def _get_slots_for_item(self, item: AssetGroupItem) -> Dict[str, Dict]:
        if item.template_id in self.slots_def and isinstance(self.slots_def[item.template_id], dict):
            return self.slots_def[item.template_id]
        return self.slots_def

    def _format_slots_string(self, item: AssetGroupItem) -> str:
        parts = []
        for k, v in sorted(item.slots.items()):
            fname = os.path.basename(v)
            parts.append(f"{k.capitalize()}: {fname}")
        return "  |  ".join(parts) if parts else "—"

    def _on_cell_double_clicked(self, row: int, column: int):
        if 0 <= row < len(self._visible_items):
            item = self._visible_items[row]
            self._show_in_explorer(item)

    def _show_context_menu(self, position):
        row = self.table.currentRow()
        if not (0 <= row < len(self._visible_items)):
            return

        item = self._visible_items[row]
        menu = QMenu(self)

        show_folder_action = QAction("Show in Explorer", self)
        show_folder_action.setIcon(QIcon(":/valve_common/icons/tools/common/open.png"))
        show_folder_action.triggered.connect(lambda: self._show_in_explorer(item))
        menu.addAction(show_folder_action)

        if CS2Netcon:
            open_cs2_action = QAction("Open in CS2 Tools", self)
            open_cs2_action.setIcon(QIcon(":/valve_common/icons/tools/common/control_play.png"))
            open_cs2_action.triggered.connect(lambda: self._open_asset_in_cs2(item))
            menu.addAction(open_cs2_action)

        menu.addSeparator()

        copy_name_action = QAction("Copy Asset Name", self)
        copy_name_action.triggered.connect(self._copy_selected_name)
        menu.addAction(copy_name_action)

        copy_output_action = QAction("Copy Output Path", self)
        copy_output_action.triggered.connect(self._copy_selected_output)
        menu.addAction(copy_output_action)

        menu.exec(self.table.mapToGlobal(position))

    def _show_in_explorer(self, item: AssetGroupItem):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        from src.settings.main import get_addon_dir

        addon_dir = get_addon_dir()
        first_file = next(iter(item.slots.values()), None)
        if first_file and os.path.isfile(first_file):
            folder = os.path.dirname(first_file)
        elif item.relative_folder and addon_dir:
            folder = os.path.join(addon_dir, item.relative_folder)
        else:
            folder = addon_dir or os.getcwd()

        if os.path.isdir(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _open_asset_in_cs2(self, item: AssetGroupItem):
        if CS2Netcon and item.target_output:
            path = item.target_output.replace('\\', '/').strip('/')
            if item.relative_folder:
                path = f"{item.relative_folder.strip('/')}/{path}"
            CS2Netcon.send(f"open_asset {path}")

    def _copy_selected_name(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._visible_items):
            QApplication.clipboard().setText(self._visible_items[row].name)

    def _copy_selected_output(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._visible_items):
            QApplication.clipboard().setText(self._visible_items[row].target_output)
