"""
PropertyItemDelegate — item delegate for the SmartProp property editor.

Paints value cells and supplies on-demand + persistent editor widgets.

Control kinds
─────────────
  float / number   → SliderEditor  (drag-slider track + overlaid line-edit)
  bool             → BoolEditor    (checkbox widget)
  combobox         → ComboEditor   (styled dark QComboBox)
  color            → ColorEditor   (swatch + "#RRGGBB" QLineEdit, click opens picker)
  string / comment
    / warning
    / legacy
    / variable
    / reference    → QLineEdit

Persistent (opened via openPersistentEditor in PropertyPanel):
  vector3d / colormatch / material_replacements / material_group_choices /
  set_variable / comparison / surface / path_editor
  → Vector3DEditor for vector3d; stub QLabel for the rest (future work)
"""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import (
    QEvent, QModelIndex, QPoint, QRect, QSize, Qt, Signal, QTimer,
)
from PySide6.QtGui import (
    QColor, QFont, QIcon, QMouseEvent, QPainter, QPalette, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from src.editors.smartprop_editor.property import compact
from src.editors.smartprop_editor.props.model import (
    COL_NAME,
    COL_VALUE,
    DEFAULT,
    MIXED,
    FieldDefRole,
    MixedRole,
    PropertyTreeModel,
    RefRole,
)
from src.editors.smartprop_editor.props.schema import FieldDef
from src.editors.smartprop_editor.props.widgets import (
    BoolEditor,
    BoolFieldEditor,
    ColorEditor,
    ColorFieldEditor,
    ColorMatchEditor,
    ComboEditor,
    ComboFieldEditor,
    CommentEditor,
    ComparisonEditor,
    EditorContext,
    FloatFieldEditor,
    LegacyEditor,
    MaterialGroupChoicesEditor,
    MaterialReplacementsEditor,
    ReferenceEditor,
    SetVariableEditor,
    SliderEditor,
    StringEditor,
    StringFieldEditor,
    SurfaceEditor,
    Vector3DEditor,
    Vector3DFieldEditor,
    VariableOutputEditor,
    WarningEditor,
)
from src.styles.property_icons import IconCache


# ── Constants ──────────────────────────────────────────────────────────────

PERSISTENT_CONTROLS = {
    "vector3d",
    "colormatch",
    "material_replacements",
    "material_group_choices",
    "set_variable",
    "comparison",
    "surface",
    "path_editor",
}

_TRACK_COL   = QColor("#2E2E2E")
_FILL_COL    = QColor("#4A7EBB")
_FILL_HOV    = QColor("#5B9BD5")
_TEXT_COL    = QColor(compact.FG)
_DIM_COL     = QColor(compact.FG_DIM)
_BG_SEL      = QColor(compact.HOVER)
_BG_HOV      = QColor("#2A2D34")


def is_persistent_control(control_kind: str) -> bool:
    return control_kind in PERSISTENT_CONTROLS


# ── Inline editor widgets ──────────────────────────────────────────────────
# All editor widget classes live in props/widgets.py and are imported above.
# This keeps the delegate focused on painting + dispatch while letting each
# widget grow feature-rich (mode switch, variable picker, browse buttons).

# Anchor for the removed inline-editor block — the real classes follow below.

# ── Delegate ───────────────────────────────────────────────────────────────

class PropertyItemDelegate(QStyledItemDelegate):
    """Custom item delegate for 2-column property tree view."""

    # Slider scrub grouping — forwarded up to the document (one undo per drag).
    sliderStarted = Signal(QModelIndex)
    sliderCommitted = Signal(QModelIndex)

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self._document = document
        self._ctx = EditorContext.from_document(document)
        self._dragging_index: QModelIndex | None = None
        self._drag_start_x: int = 0
        self._drag_start_val: float = 0.0
        # Cache of (row -> editor height) so multi-row editors (comment, lists)
        # report a stable height between sizeHint calls.
        self._height_cache: dict[int, int] = {}

    def set_context(self, document):
        """Re-bind the document context (used after the panel is re-parented)."""
        self._document = document
        self._ctx = EditorContext.from_document(document)

    # ── Size ────────────────────────────────────────────────────────────────

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        fd: FieldDef = index.data(FieldDefRole)
        cached = self._height_cache.get(index.row())
        if cached is not None:
            return QSize(option.rect.width(), cached)
        return QSize(option.rect.width(), compact.ROW_H)

    def update_height(self, row: int, height: int):
        """Record an editor-driven row height and nudge the view to relayout."""
        self._height_cache[row] = max(compact.ROW_H, int(height))
        idx = self._view_index(row)
        if idx is not None:
            self.sizeHintChanged.emit(idx)

    def _view_index(self, row: int) -> QModelIndex | None:
        """Find the view's COL_VALUE index for a source row (best-effort)."""
        view = self.parent()
        model = getattr(view, "model", None)
        if model is None:
            return None
        # The view's model may be a proxy; map the source row back to it.
        proxy = None
        try:
            from src.editors.smartprop_editor.props.model import PropertyTreeModel
            src = model.sourceModel() if hasattr(model, "sourceModel") else model
            if isinstance(src, PropertyTreeModel):
                src_idx = src.index(row, COL_VALUE)
                proxy = model if hasattr(model, "mapFromSource") else None
                if proxy is not None:
                    return proxy.mapFromSource(src_idx)
                return src_idx
        except Exception:
            return None
        return None

    # ── Paint ────────────────────────────────────────────────────────────────

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        rect = option.rect
        fd: FieldDef = index.data(FieldDefRole)
        is_mixed = index.data(MixedRole)
        val = index.data(Qt.EditRole)

        # Background
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hover    = bool(option.state & QStyle.State_MouseOver)

        if is_selected:
            bg_color = _BG_SEL
        elif is_hover:
            bg_color = _BG_HOV
        elif index.row() % 2 == 0:
            bg_color = QColor(compact.ROW_BG_EVEN)
        else:
            bg_color = QColor(compact.ROW_BG_ODD)

        painter.fillRect(rect, bg_color)

        # Separator
        painter.setPen(QPen(QColor("#282828"), 1))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        # ── Column 0: Name ──────────────────────────────────────────────────
        if index.column() == COL_NAME:
            icon_key = (fd.icon if fd else None) or "float"
            icon = IconCache.get_property_icon(icon_key)
            icon_size = 16
            icon_rect = QRect(
                rect.left() + 6,
                rect.top() + (rect.height() - icon_size) // 2,
                icon_size, icon_size,
            )
            painter.drawPixmap(icon_rect, icon.pixmap(icon_size, icon_size))

            label_rect = QRect(
                icon_rect.right() + 8, rect.top(),
                rect.width() - icon_size - 14, rect.height(),
            )
            painter.setPen(QPen(_TEXT_COL, 1))
            font = QFont("Segoe UI")
            font.setPixelSize(11)
            painter.setFont(font)
            display_name = index.data(Qt.DisplayRole) or (fd.label if fd else "")
            painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter, str(display_name))

        # ── Column 1: Value ─────────────────────────────────────────────────
        elif index.column() == COL_VALUE:
            val_rect = QRect(rect.left() + 4, rect.top(), rect.width() - 8, rect.height())
            font = QFont("Segoe UI")
            font.setPixelSize(11)
            painter.setFont(font)

            if is_mixed:
                painter.setPen(QPen(_DIM_COL, 1))
                painter.drawText(val_rect, Qt.AlignLeft | Qt.AlignVCenter, "—")

            elif val is DEFAULT or val is None:
                painter.setPen(QPen(QColor("#666666"), 1))
                painter.drawText(val_rect, Qt.AlignLeft | Qt.AlignVCenter, "Default")

            elif fd and fd.control in ("float", "number") and fd.kwargs and "slider_range" in fd.kwargs:
                self._paint_slider(painter, val_rect, fd, val)

            elif fd and fd.control == "bool":
                self._paint_bool(painter, val_rect, val)

            elif fd and fd.control == "color" and isinstance(val, (list, tuple)) and len(val) >= 3:
                self._paint_color(painter, val_rect, val)

            elif fd and fd.control == "combobox":
                painter.setPen(QPen(_TEXT_COL, 1))
                painter.drawText(val_rect, Qt.AlignLeft | Qt.AlignVCenter, str(val))
                # Small dropdown arrow hint
                arrow_rect = QRect(rect.right() - 14, rect.top() + 6, 8, rect.height() - 12)
                painter.setPen(QPen(_DIM_COL, 1))
                mid_x = arrow_rect.center().x()
                mid_y = arrow_rect.center().y()
                painter.drawLine(mid_x - 3, mid_y - 1, mid_x, mid_y + 2)
                painter.drawLine(mid_x, mid_y + 2, mid_x + 3, mid_y - 1)

            elif fd and fd.control == "vector3d":
                # Painted fallback when no persistent editor yet
                vals = val if isinstance(val, (list, tuple)) else [0, 0, 0]
                tags = [("X", "#ECA4A0"), ("Y", "#B6EFA2"), ("Z", "#A4B6EF")]
                seg_w = val_rect.width() // 3
                for i, (tag, col) in enumerate(tags):
                    seg = QRect(val_rect.left() + i * seg_w, val_rect.top(), seg_w, val_rect.height())
                    painter.setPen(QPen(QColor(col), 1))
                    painter.drawText(seg, Qt.AlignLeft | Qt.AlignVCenter, f"{tag}:{vals[i]:.3g}" if i < len(vals) else f"{tag}:0")

            else:
                painter.setPen(QPen(_TEXT_COL, 1))
                val_str = str(val) if val is not None else ""
                painter.drawText(val_rect, Qt.AlignLeft | Qt.AlignVCenter, val_str)

        painter.restore()

    def _paint_slider(self, p: QPainter, rect: QRect, fd: FieldDef, val):
        """Paint an inline slider track + numeric value in the value cell."""
        sr = fd.kwargs["slider_range"]
        if len(sr) < 2 or sr[1] <= sr[0]:
            p.setPen(QPen(_TEXT_COL, 1))
            p.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, str(val))
            return

        min_v, max_v = float(sr[0]), float(sr[1])
        try:
            curr_v = float(val)
        except (TypeError, ValueError):
            curr_v = min_v

        pct = max(0.0, min(1.0, (curr_v - min_v) / (max_v - min_v)))

        num_w   = 48
        track_x = rect.left() + 2
        track_w = rect.width() - num_w - 6
        track_h = 4
        track_y = rect.top() + (rect.height() - track_h) // 2

        track_r = QRect(track_x, track_y, track_w, track_h)
        p.fillRect(track_r, _TRACK_COL)

        fill_w = int(track_w * pct)
        if fill_w > 0:
            p.fillRect(QRect(track_x, track_y, fill_w, track_h), _FILL_COL)

        # Thumb
        thumb_x = track_x + fill_w
        thumb_r = 4
        p.setBrush(QColor("#7BAAD8"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(thumb_x - thumb_r, track_y + track_h // 2 - thumb_r,
                      thumb_r * 2, thumb_r * 2)

        # Number
        is_int = fd.kwargs.get("int_bool", False)
        text   = str(int(curr_v)) if is_int else f"{curr_v:.4g}"
        num_r  = QRect(rect.right() - num_w, rect.top(), num_w - 2, rect.height())
        p.setPen(QPen(_TEXT_COL, 1))
        p.setBrush(Qt.NoBrush)
        p.drawText(num_r, Qt.AlignRight | Qt.AlignVCenter, text)

    def _paint_bool(self, p: QPainter, rect: QRect, val):
        """Paint a checkbox indicator + True/False label."""
        chk_size = 14
        chk_x = rect.left()
        chk_y = rect.top() + (rect.height() - chk_size) // 2

        # Box
        chk_r = QRect(chk_x, chk_y, chk_size, chk_size)
        checked = bool(val)
        p.fillRect(chk_r, QColor("#4A7EBB" if checked else "#2A2A2A"))
        p.setPen(QPen(QColor("#5B9BD5" if checked else "#555555"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(chk_r)

        if checked:
            # Checkmark
            p.setPen(QPen(QColor("#FFFFFF"), 1.5))
            p.drawLine(chk_x + 3, chk_y + 7, chk_x + 6, chk_y + 10)
            p.drawLine(chk_x + 6, chk_y + 10, chk_x + 11, chk_y + 4)

        txt_r = QRect(chk_x + chk_size + 6, rect.top(), rect.width() - chk_size - 6, rect.height())
        p.setPen(QPen(_TEXT_COL, 1))
        p.setBrush(Qt.NoBrush)
        p.drawText(txt_r, Qt.AlignLeft | Qt.AlignVCenter, str(checked))

    def _paint_color(self, p: QPainter, rect: QRect, val):
        """Paint a colour swatch + hex text."""
        r, g, b = int(val[0]), int(val[1]), int(val[2])
        swatch_size = 16
        swatch_r = QRect(
            rect.left(), rect.top() + (rect.height() - swatch_size) // 2,
            swatch_size, swatch_size,
        )
        p.fillRect(swatch_r, QColor(r, g, b))
        p.setPen(QPen(QColor("#555555"), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(swatch_r)

        txt_r = QRect(swatch_r.right() + 6, rect.top(),
                      rect.width() - swatch_size - 6, rect.height())
        p.setPen(QPen(_TEXT_COL, 1))
        p.drawText(txt_r, Qt.AlignLeft | Qt.AlignVCenter,
                   f"#{r:02X}{g:02X}{b:02X}  ({r}, {g}, {b})")

    # ── Editor creation ─────────────────────────────────────────────────────

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget | None:
        if index.column() != COL_VALUE:
            return None

        fd: FieldDef = index.data(FieldDefRole)
        if not fd:
            return StringEditor(parent=parent)

        val = index.data(Qt.EditRole)
        if val is MIXED:
            val = None       # show empty editor for mixed selections

        editor = self._build_editor(fd, val, parent)
        if editor is None:
            return None
        self._wire_editor(editor, index)
        return editor

    def _build_editor(self, fd: FieldDef, val, parent: QWidget) -> QWidget | None:
        """Construct the feature-rich editor for a control kind.

        Returns None only for the path_editor stub (no backing widget yet); all
        other control kinds — including the persistent ones — get a real editor
        here so they can be opened as persistent editors by the view.
        """
        ctrl = fd.control
        kw = fd.kwargs or {}

        if ctrl == "path_editor":
            return None     # 3D path editor not implemented yet

        if ctrl in ("float", "number"):
            return FloatFieldEditor(
                fd.field, self._ctx,
                slider_range=kw.get("slider_range"), int_bool=kw.get("int_bool", False) or ctrl == "number",
                parent=parent)

        if ctrl == "bool":
            return BoolFieldEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "combobox":
            return ComboFieldEditor(fd.field, kw.get("items", []), self._ctx,
                                     filter_types=kw.get("filter_types"), parent=parent)

        if ctrl == "color":
            return ColorFieldEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "string":
            return StringFieldEditor(
                fd.field, self._ctx, placeholder=kw.get("placeholder"),
                model_browser=kw.get("model_browser", False),
                expression_bool=kw.get("expression_bool", False),
                only_string=kw.get("only_string", False),
                only_variable=kw.get("only_variable", False),
                filter_types=kw.get("filter_types"), parent=parent)

        if ctrl == "variable":
            return VariableOutputEditor(fd.field, self._ctx,
                                         filter_types=kw.get("filter_types"), parent=parent)

        if ctrl == "comment":
            return CommentEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "reference":
            return ReferenceEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "warning":
            return WarningEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "vector3d":
            return Vector3DFieldEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "comparison":
            return ComparisonEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "colormatch":
            return ColorMatchEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "surface":
            return SurfaceEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "material_replacements":
            return MaterialReplacementsEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "material_group_choices":
            return MaterialGroupChoicesEditor(fd.field, self._ctx, parent=parent)

        if ctrl == "set_variable":
            return SetVariableEditor(fd.field, self._ctx, parent=parent)

        # legacy / unknown
        return LegacyEditor(fd.field, self._ctx, parent=parent)

    def _wire_editor(self, editor: QWidget, index: QModelIndex):
        """Connect an editor's signals to the model + slider grouping."""
        commit = getattr(editor, "commitValue", None)
        if commit is not None:
            commit.connect(lambda v, idx=index: self._commit(idx, v))
        # Slider drag grouping (undo coalescing).
        sp = getattr(editor, "sliderPressed", None)
        sc = getattr(editor, "sliderCommitted", None)
        if sp is not None:
            sp.connect(lambda idx=index: self.sliderStarted.emit(idx))
        if sc is not None:
            sc.connect(lambda idx=index: self.sliderCommitted.emit(idx))
        # Multi-row editors can grow the row.
        hc = getattr(editor, "heightChanged", None)
        if hc is not None:
            editor._delegate_row = index.row()
            hc.connect(lambda r=index.row(), e=editor: self._on_editor_height_changed(r, e))

    def _on_editor_height_changed(self, row: int, editor: QWidget):
        h = editor.sizeHint().height()
        self.update_height(row, h)

    def _commit(self, index: QModelIndex, value):
        """Write a value directly to the model (called by editor signals)."""
        model = index.model()
        if model is not None:
            model.setData(index, value, Qt.EditRole)

    # ── setEditorData / setModelData ────────────────────────────────────────
    #
    # All rich editors share the same ``set_value(stored)`` / ``value()`` API,
    # so a single generic path handles them.  The minimal legacy classes
    # (SliderEditor/BoolEditor/…  kept for the painted Value-mode widgets) also
    # expose set_value/value and work through the same path.

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        val = index.data(Qt.EditRole)
        if val is MIXED:
            val = None
        if hasattr(editor, "set_value"):
            editor.set_value(val)

    def setModelData(self, editor: QWidget, model, index: QModelIndex):
        fd: FieldDef = index.data(FieldDefRole)
        if not fd:
            return
        if hasattr(editor, "value"):
            model.setData(index, editor.value(), Qt.EditRole)
        elif hasattr(editor, "text"):
            model.setData(index, editor.text(), Qt.EditRole)

    def updateEditorGeometry(self, editor: QWidget,
                             option: QStyleOptionViewItem, index: QModelIndex):
        editor.setGeometry(option.rect)
