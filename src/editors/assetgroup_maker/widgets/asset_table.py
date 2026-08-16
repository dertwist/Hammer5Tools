import os
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMenu, QMessageBox, QApplication, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QAction, QDropEvent, QIcon

from src.editors.assetgroup_maker.matcher import AssetGroupItem


class AssetTableWidget(QWidget):
    """
    Multi-File Target Asset Mapping Table displaying detected assets,
    matched companion file slots, target output filenames, and status badges.
    """

    files_dropped = Signal(list)  # List[str] of dropped paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: List[AssetGroupItem] = []
        self._visible_items: List[AssetGroupItem] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 6)
        layout.setSpacing(4)

        # 1. Filter Bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)

        search_label = QLabel("Search:")
        search_label.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #9D9D9D;")
        filter_row.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter assets by name or file path...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.search_edit, 1)

        status_label = QLabel("Filter:")
        status_label.setStyleSheet("font: 600 9pt 'Segoe UI'; color: #9D9D9D;")
        filter_row.addWidget(status_label)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Ready", "Warnings", "Errors"])
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.status_combo)

        layout.addLayout(filter_row)

        # 2. Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "#", "Status", "Target Asset Name", "Matched Multi-File Slots", "Target Output File"
        ])

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.setAcceptDrops(True)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(4, 220)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #151515;
                gridline-color: #2D2D30;
                border: 1px solid #363639;
                border-radius: 3px;
                color: #E3E3E3;
                font: 580 9pt "Segoe UI";
            }
            QHeaderView::section {
                background-color: #1C1C1C;
                color: #C7C7BB;
                padding: 4px 6px;
                border: 1px solid #363639;
                font: 600 9pt "Segoe UI";
            }
            QTableWidget::item:selected {
                background-color: #414956;
                color: #FFFFFF;
            }
        """)

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
        self._apply_filter()

    def get_items(self) -> List[AssetGroupItem]:
        return self._all_items

    def _apply_filter(self):
        query = self.search_edit.text().strip().lower()
        status_filter = self.status_combo.currentText().lower()

        filtered = []
        for item in self._all_items:
            # Status filter
            if status_filter == "ready" and item.status != "ready":
                continue
            if status_filter == "warnings" and item.status != "warning":
                continue
            if status_filter == "errors" and item.status != "error":
                continue

            # Query filter
            if query:
                name_match = query in item.name.lower()
                slot_match = any(query in os.path.basename(p).lower() for p in item.slots.values())
                out_match = query in item.target_output.lower()
                if not (name_match or slot_match or out_match):
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

            # 1. Status Badge Widget
            status_widget = self._create_status_badge(item)
            self.table.setCellWidget(row_idx, 1, status_widget)

            # 2. Asset Name
            name_item = QTableWidgetItem(item.name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_idx, 2, name_item)

            # 3. Matched Slots String
            slots_str = self._format_slots_string(item)
            slots_item = QTableWidgetItem(slots_str)
            slots_item.setToolTip("\n".join(f"{k}: {v}" for k, v in item.slots.items()))
            slots_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_idx, 3, slots_item)

            # 4. Target Output
            out_item = QTableWidgetItem(item.target_output)
            out_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_idx, 4, out_item)

            self.table.setRowHeight(row_idx, 26)

        self.table.setUpdatesEnabled(True)

    def _create_status_badge(self, item: AssetGroupItem) -> QWidget:
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(4, 2, 4, 2)
        h.setAlignment(Qt.AlignCenter)

        badge = QLabel()
        badge.setAlignment(Qt.AlignCenter)

        if item.status == "ready":
            badge.setText("Ready")
            badge.setStyleSheet("""
                background-color: #1E3A24;
                color: #68D391;
                border: 1px solid #2F855A;
                border-radius: 3px;
                padding: 1px 6px;
                font: 600 8pt 'Segoe UI';
            """)
        elif item.status == "warning":
            badge.setText("Warning")
            badge.setStyleSheet("""
                background-color: #3D321D;
                color: #ECC94B;
                border: 1px solid #D69E2E;
                border-radius: 3px;
                padding: 1px 6px;
                font: 600 8pt 'Segoe UI';
            """)
        else:
            badge.setText("Error")
            badge.setStyleSheet("""
                background-color: #3B1E1E;
                color: #FC8181;
                border: 1px solid #E53E3E;
                border-radius: 3px;
                padding: 1px 6px;
                font: 600 8pt 'Segoe UI';
            """)

        badge.setToolTip(item.status_message)
        h.addWidget(badge)
        return container

    def _format_slots_string(self, item: AssetGroupItem) -> str:
        parts = []
        for k, v in sorted(item.slots.items()):
            fname = os.path.basename(v)
            parts.append(f"{k.capitalize()}: {fname}")
        return "  |  ".join(parts) if parts else "—"

    def _show_context_menu(self, position):
        menu = QMenu(self)

        copy_name_action = QAction("Copy Asset Name", self)
        copy_name_action.triggered.connect(self._copy_selected_name)
        menu.addAction(copy_name_action)

        copy_output_action = QAction("Copy Output Path", self)
        copy_output_action.triggered.connect(self._copy_selected_output)
        menu.addAction(copy_output_action)

        menu.exec_(self.table.mapToGlobal(position))

    def _copy_selected_name(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._visible_items):
            QApplication.clipboard().setText(self._visible_items[row].name)

    def _copy_selected_output(self):
        row = self.table.currentRow()
        if 0 <= row < len(self._visible_items):
            QApplication.clipboard().setText(self._visible_items[row].target_output)
