"""
PropertyTreeView & PropertyPanel — Section 2 property panel view for SmartProp editor (Phase P4).

Features:
- Filter bar (QLineEdit + clear filter action + settings button)
- QSortFilterProxyModel filtering COL_NAME
- QTreeView styled matching Source 2 Hammer Object Properties:
  - 2 columns: Name | Value
  - setUniformRowHeights(True)
  - Fixed name column width (~150px)
  - Single-click edit triggers
  - Custom branch icons
  - PropertyItemDelegate for painting and editing
"""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QModelIndex, QSize, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from src.editors.smartprop_editor.property import compact
from src.editors.smartprop_editor.props.delegate import PropertyItemDelegate
from src.editors.smartprop_editor.props.model import (
    COL_NAME,
    COL_VALUE,
    FieldDefRole,
    PropertyTreeModel,
    RefRole,
)
from src.editors.smartprop_editor.props.property_list_base import AbstractPropertyList
from src.editors.smartprop_editor.props.schema import FieldDef


def is_field_visible_for_layout2dgrid(field_name: str, target_dict: dict) -> bool:
    mode = target_dict.get("m_GridArrangement") or target_dict.get("m_GridPlacementMode", "SEGMENT")
    alt = bool(target_dict.get("m_bAlternateShift", False))
    if mode == "SEGMENT":
        if field_name in ("m_flSpacingWidth", "m_flSpacingLength"):
            return False
        if field_name in ("m_flAlternateShiftWidth", "m_flAlternateShiftLength") and not alt:
            return False
    elif mode == "FILL":
        if field_name in ("m_nCountW", "m_nCountL", "m_bAlternateShift", "m_flAlternateShiftWidth", "m_flAlternateShiftLength"):
            return False
    return True


class PropertyFilterProxyModel(QSortFilterProxyModel):
    """Proxy model filtering property rows by name and schema visibility rules."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterKeyColumn(COL_NAME)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source_model = self.sourceModel()
        if source_model:
            idx = source_model.index(source_row, COL_NAME)
            fd: FieldDef = idx.data(FieldDefRole)
            ref = idx.data(RefRole)
            if fd and ref:
                target = ref.target(ref.item.data(0, Qt.UserRole)) if ref.item else None
                if isinstance(target, dict) and target.get("_class") in ("CSmartPropElement_Layout2DGrid", "CSmartPropElement_Grid"):
                    if not is_field_visible_for_layout2dgrid(fd.field, target):
                        return False

        pattern = self.filterRegularExpression().pattern()
        if not pattern:
            return True
        return super().filterAcceptsRow(source_row, source_parent)


class PropertyTreeView(QTreeView):
    """QTreeView over PropertyTreeModel."""

    # Forwarded slider scrub grouping (one undo entry per drag).
    sliderStarted = Signal(QModelIndex)
    sliderCommitted = Signal(QModelIndex)

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self._document = document
        # Always-visible editors with variable row heights (comment, lists).
        self.setUniformRowHeights(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # Every value cell shows a persistent editor at rest, so no additional
        # edit triggers are needed (they would stack a second editor on top).
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAllColumnsShowFocus(True)
        self.setFrameShape(QFrame.NoFrame)

        # Style tree view and scrollbars matching Source 2 dark theme
        self.setStyleSheet("""
            QTreeView {
                background-color: #1C1C1C;
                color: #E3E3E3;
                border: 0px;
                outline: 0px;
                font: 8pt "Segoe UI";
            }
            QTreeView::item {
                height: 29px;
                border: 0px;
            }
            QTreeView::item:hover {
                background-color: #2A2D34;
            }
            QTreeView::item:selected {
                background-color: #4F5259;
                color: #FFFFFF;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                image: url(:/icons/propertyeditor/hierarchy_collapsed.png);
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                image: url(:/icons/propertyeditor/hierarchy_expanded.png);
            }
            QHeaderView::section {
                background-color: #242424;
                color: #AAAAAA;
                padding: 4px 6px;
                border: 0px;
                border_bottom: 1px solid #333333;
                font-weight: bold;
                font-size: 11px;
            }
        """)

        header = self.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(COL_NAME, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_VALUE, QHeaderView.Stretch)
        self.setColumnWidth(COL_NAME, compact.LABEL_W)

        self._delegate = PropertyItemDelegate(document=document, parent=self)
        self.setItemDelegate(self._delegate)

        # Forward slider scrub grouping up to the document (undo coalescing).
        self._delegate.sliderStarted.connect(self.sliderStarted)
        self._delegate.sliderCommitted.connect(self.sliderCommitted)

        # Mouse tracking lets hover states render on editor widgets.
        self.setMouseTracking(True)


class PropertyPanel(AbstractPropertyList):
    """Section 2 Property Panel container widget (new treeview backend)."""

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Top Filter Bar
        filter_bar = QFrame(self)
        filter_bar.setFixedHeight(28)
        filter_bar.setStyleSheet("QFrame { background-color: #242424; border-bottom: 1px solid #333333; }")

        bar_layout = QHBoxLayout(filter_bar)
        bar_layout.setContentsMargins(4, 2, 4, 2)
        bar_layout.setSpacing(4)

        self.txt_filter = QLineEdit(filter_bar)
        self.txt_filter.setPlaceholderText("Filter properties...")
        self.txt_filter.setStyleSheet("""
            QLineEdit {
                background-color: #1C1C1C;
                color: #E3E3E3;
                border: 1px solid #3A3A3A;
                border-radius: 2px;
                padding: 2px 6px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #5588DD;
            }
        """)

        # Clear filter button action
        self.act_clear = QAction(self.txt_filter)
        self.act_clear.setIcon(QIcon(":/icons/propertyeditor/clear_filter.png"))
        self.act_clear.setToolTip("Clear filter")
        self.act_clear.triggered.connect(self.txt_filter.clear)
        self.txt_filter.addAction(self.act_clear, QLineEdit.TrailingPosition)
        self.act_clear.setVisible(False)

        bar_layout.addWidget(self.txt_filter, 1)

        # Settings button (⚙)
        self.btn_settings = QToolButton(filter_bar)
        self.btn_settings.setIcon(QIcon(":/icons/propertyeditor/attr_menu.png"))
        self.btn_settings.setFixedSize(22, 22)
        self.btn_settings.setStyleSheet("""
            QToolButton { border: none; background: transparent; }
            QToolButton:hover { background-color: #333333; border-radius: 2px; }
        """)
        self.btn_settings.setToolTip("Property Panel Settings")
        bar_layout.addWidget(self.btn_settings)

        layout.addWidget(filter_bar)

        # Models & View
        self.tree_model = PropertyTreeModel(document=self.document, parent=self)
        self.proxy_model = PropertyFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.tree_model)

        self.tree_view = PropertyTreeView(document=self.document, parent=self)
        self.tree_view.setModel(self.proxy_model)
        layout.addWidget(self.tree_view, 1)

        # Persistent editor indices we have opened (so we can close them).
        self._open_editor_indices: list = []

        # Connect signals
        self.txt_filter.textChanged.connect(self._on_filter_changed)

    def set_components(self, refs: list) -> float:
        """Point the panel at selected components. Returns render time in ms."""
        t0 = time.perf_counter()
        # Close any stale persistent editors from the previous selection before
        # the model resets (avoids dangling editor references).
        self._close_persistent_editors()
        self._delegate_reset_heights()
        self.tree_model.set_components(refs)
        self.tree_view.expandAll()
        self._open_persistent_editors()
        t1 = time.perf_counter()
        render_ms = (t1 - t0) * 1000.0
        return render_ms

    def _close_persistent_editors(self):
        """Close every currently-open persistent editor."""
        for idx in list(self._open_editor_indices):
            if idx.isValid():
                try:
                    self.tree_view.closePersistentEditor(idx)
                except Exception:
                    pass
        self._open_editor_indices = []

    def _delegate_reset_heights(self):
        delegate = self.tree_view.itemDelegate()
        if hasattr(delegate, "_height_cache"):
            delegate._height_cache.clear()

    def apply_external_data(self, item, new_data, changed_keys=()):
        """Forward external updates (undo/redo) to the model."""
        if hasattr(self.tree_model, "apply_external_data"):
            self.tree_model.apply_external_data(item, new_data, changed_keys)
        else:
            self.tree_model.layoutChanged.emit()

    def _on_filter_changed(self, text: str):
        self.act_clear.setVisible(bool(text))
        self.proxy_model.setFilterFixedString(text)

    def _open_persistent_editors(self):
        """Open a persistent (always-visible) editor for every value cell.

        Every property row shows its full editor at rest — the mode switch,
        value widget, and (on demand) variable picker / expression editor —
        matching the legacy always-visible property panel.
        """
        for row in range(self.proxy_model.rowCount()):
            idx = self.proxy_model.index(row, COL_VALUE)
            fd: FieldDef = idx.data(FieldDefRole)
            if not fd:
                continue
            if fd.control == "path_editor":
                continue   # no backing editor yet
            self.tree_view.openPersistentEditor(idx)
            self._open_editor_indices.append(QModelIndex(idx))
