"""
Editor widgets for the SmartProp property tree view.

Holds the inline/persistent editor widget classes used by
``PropertyItemDelegate`` (see ``delegate.py``).  Keeping them in a dedicated
module leaves the delegate focused on painting and dispatch and lets each
widget grow feature-rich (mode switch, variable picker, browse buttons …)
without bloating ``delegate.py``.

Value contract
──────────────
Every scalar SmartProp field stores one of four shapes in the element dict,
exactly as the legacy widget layer did:

    DEFAULT     → key absent (the model's ``DEFAULT`` sentinel deletes it)
    VALUE       → the literal (float / int / bool / str / [r,g,b,a] …)
    VARIABLE    → {'m_SourceName': <var name>}
    EXPRESSION  → {'m_Expression': <expr>}     (raw string for m_Expression /
                                                 m_HideExpression — see below)

``parse_value_mode`` / ``build_value_shape`` are the pure helpers every scalar
editor uses to round-trip between the stored shape and its (mode, payload)
UI state.  Keeping them centralised guarantees every editor writes the same
shape the legacy ``PropertyFrame`` produced, so saved ``.vsmart`` output is
unchanged.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.editors.smartprop_editor.property import compact
from src.editors.smartprop_editor.props.model import DEFAULT
from src.editors.smartprop_editor.props.schema import FieldDef


# ── Value-contract helpers ─────────────────────────────────────────────────

# The four value modes offered by the legacy logic_switch.
MODE_DEFAULT = "default"
MODE_VALUE = "value"
MODE_VARIABLE = "variable"
MODE_EXPRESSION = "expression"

# Field names whose expression value is stored as a *raw string* (not wrapped
# in {'m_Expression': ...}).  Matches the legacy PropertyString special-case.
_RAW_EXPRESSION_FIELDS = frozenset({"m_Expression", "m_HideExpression"})


def parse_value_mode(stored: Any, field: str | None = None) -> tuple[str, Any]:
    """Decode a stored value into ``(mode, payload)``.

    payload is:
      DEFAULT    → None
      VALUE      → the literal
      VARIABLE   → the variable name (str)
      EXPRESSION → the expression text (str)
    """
    if stored is None or stored is DEFAULT:
        return MODE_DEFAULT, None

    # Raw-expression fields store the expression as a bare string.
    if field in _RAW_EXPRESSION_FIELDS and isinstance(stored, str):
        return MODE_EXPRESSION, stored

    if isinstance(stored, dict):
        if "m_SourceName" in stored:
            return MODE_VARIABLE, stored["m_SourceName"]
        if "m_Expression" in stored:
            return MODE_EXPRESSION, stored["m_Expression"]
        # Unknown dict shape — treat as default so the editor does not clobber
        # data it cannot represent; the legacy layer behaved the same way.
        return MODE_DEFAULT, None

    return MODE_VALUE, stored


def build_value_shape(mode: str, literal: Any, var: Any = None,
                      expr: Any = None, field: str | None = None) -> Any:
    """Inverse of :func:`parse_value_mode` — build the stored shape for a mode.

    Returns the ``DEFAULT`` sentinel for default mode so the model deletes the
    key (matching the legacy "Default removes the key" behaviour).
    """
    if mode == MODE_DEFAULT:
        return DEFAULT
    if mode == MODE_VARIABLE:
        return {"m_SourceName": var}
    if mode == MODE_EXPRESSION:
        if field in _RAW_EXPRESSION_FIELDS:
            return expr
        return {"m_Expression": expr}
    return literal


# ── Shared styling constants (mirror delegate.py's palette) ────────────────

_TRACK_COL = QColor("#2E2E2E")
_FILL_COL = QColor("#4A7EBB")
_FILL_HOV = QColor("#5B9BD5")
_TEXT_COL = QColor(compact.FG)

_BASE_QSS = """
    background-color: #1C1C1C;
    color: #E3E3E3;
    border: 1px solid #3A3A3A;
    border-radius: 2px;
    font: 8pt "Segoe UI";
"""
_COMBO_QSS = """
QComboBox {
    background-color: #1C1C1C; color: #E3E3E3;
    border: 1px solid #3A3A3A; border-radius: 2px;
    padding: 0 4px; font: 8pt "Segoe UI";
    min-height: 22px;
}
QComboBox:hover { border-color: #5588DD; }
QComboBox::drop-down { border: none; width: 16px; }
QComboBox QAbstractItemView {
    background-color: #1C1C1C; color: #E3E3E3;
    border: 1px solid #4A4A4A;
    selection-background-color: #414956;
}
"""

# Thin inline value-mode switch (Default/Value/Variable/Expression).  A compact
# restatement of compact.LOGIC_SWITCH_QSS that does not depend on the generated
# ``ui`` attributes the legacy pooled widgets exposed.
_LOGIC_SWITCH_QSS = """
QComboBox {
    font: 600 7pt "Segoe UI";
    border: 1px solid #3A3A3A; border-radius: 2px;
    color: %s; background-color: #1C1C1C;
    padding: 0 4px; margin: 0px;
    min-height: 20px; max-height: 20px;
}
QComboBox:hover { border-color: #5588DD; color: white; }
QComboBox::drop-down { border: none; width: 14px; }
QComboBox QAbstractItemView {
    border: 1px solid #4A4A4A; background-color: #1C1C1C; color: #E3E3E3;
    selection-background-color: #414956; outline: 0px;
}
""" % compact.FG_DIM


# ── Editor context ─────────────────────────────────────────────────────────

class EditorContext:
    """Handles a widget needs from the document, threaded through the delegate.

    Kept deliberately lightweight (a plain holder, not a dataclass) so it can
    be constructed cheaply once per delegate and shared by every editor.  Any
    attribute may be ``None`` (e.g. in tests) — editors must tolerate that and
    degrade gracefully (hide the variable picker / browse button).
    """

    __slots__ = ("document", "variables_layout", "element_id_generator",
                 "tree_hierarchy")

    def __init__(self, document=None, variables_layout=None,
                 element_id_generator=None, tree_hierarchy=None):
        self.document = document
        self.variables_layout = variables_layout
        self.element_id_generator = element_id_generator
        self.tree_hierarchy = tree_hierarchy

    @classmethod
    def from_document(cls, document) -> "EditorContext":
        """Build a context by pulling the standard handles off a document."""
        if document is None:
            return cls()
        variables_layout = None
        viewport = getattr(document, "variable_viewport", None)
        if viewport is not None and getattr(viewport, "ui", None) is not None:
            variables_layout = getattr(viewport.ui, "variables_scrollArea", None)
        element_id_generator = getattr(document, "element_id_generator", None)
        ui = getattr(document, "ui", None)
        tree_hierarchy = getattr(ui, "tree_hierarchy_widget", None) if ui is not None else None
        return cls(document=document, variables_layout=variables_layout,
                   element_id_generator=element_id_generator,
                   tree_hierarchy=tree_hierarchy)


# ── Scalar editor base (Default / Value / Variable / Expression) ────────────

class _ScalarEditorBase(QWidget):
    """Base for single-value editors offering the four legacy value modes.

    Subclasses provide:
      * ``_build_value_widget()`` → the literal-editing widget (spinbox, slider,
        checkbox, color swatch, line-edit, combobox …) wired so that editing it
        calls ``self._emit()``.
      * ``_literal_value()``      → read the literal from that widget.
      * ``_set_literal(v)``       → push a literal back into the widget.

    The base owns the thin mode switch and the lazily-built variable picker /
    expression text field / expression-editor button, and emits the full stored
    shape (DEFAULT sentinel included) via ``commitValue``.

    Constraint flags mirror the legacy PropertyString knobs and hide modes that
    don't apply: ``only_value`` hides the switch and forces Value mode;
    ``only_variable`` forces Variable; ``expression_bool`` forces Expression.
    """

    commitValue = Signal(object)        # full stored shape (DEFAULT sentinel ok)
    sliderPressed = Signal()           # slider drag start (undo grouping)
    sliderCommitted = Signal()         # slider drag end   (undo grouping)

    # mode-switch item order (index matters — see _MODE_INDEX)
    _SWITCH_ITEMS = ("Default", "Value", "Variable", "Expression")

    def __init__(self, field: str, ctx: EditorContext | None = None,
                 filter_types: list | None = None, only_value: bool = False,
                 only_variable: bool = False, expression_bool: bool = False,
                 parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self._filter_types = list(filter_types) if filter_types else None
        self._only_value = only_value
        self._only_variable = only_variable
        self._expression_bool = expression_bool
        self._mode = MODE_VALUE
        self._variable_picker = None    # built lazily
        self._expr_edit = None          # built lazily
        self._expr_button = None        # built lazily

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        self._root = QHBoxLayout(self)
        self._root.setContentsMargins(4, 1, 4, 1)
        self._root.setSpacing(4)

        # Mode switch (hidden when a constraint forces a single mode).
        self._switch = QComboBox(self)
        self._switch.addItems(self._SWITCH_ITEMS)
        self._switch.setStyleSheet(_LOGIC_SWITCH_QSS)
        self._switch.setFixedWidth(78)
        self._switch.wheelEvent = lambda e: None   # legacy: no wheel-scroll
        self._switch.currentIndexChanged.connect(self._on_mode_changed)
        self._root.addWidget(self._switch)

        # Stacked area: the active mode's widget set is swapped in here.
        self._value_widget = self._build_value_widget()
        self._root.addWidget(self._value_widget, 1)

        self._apply_constraints()

    # ── Subclass hooks ───────────────────────────────────────────────────────

    def _build_value_widget(self) -> QWidget:
        raise NotImplementedError

    def _literal_value(self):
        raise NotImplementedError

    def _set_literal(self, v):
        raise NotImplementedError

    # ── Constraints ──────────────────────────────────────────────────────────

    def _apply_constraints(self):
        """Hide the switch / force a mode based on the constraint flags."""
        if self._expression_bool:
            self._switch.setVisible(False)
            self._set_mode(MODE_EXPRESSION)
        elif self._only_variable:
            self._switch.setVisible(False)
            self._set_mode(MODE_VARIABLE)
        elif self._only_value:
            self._switch.setVisible(False)
            self._set_mode(MODE_VALUE)

    # ── Mode handling ────────────────────────────────────────────────────────

    _MODE_INDEX = {MODE_DEFAULT: 0, MODE_VALUE: 1, MODE_VARIABLE: 2, MODE_EXPRESSION: 3}

    def _set_mode(self, mode: str):
        """Programmatically switch mode without emitting (used on load/constraint)."""
        self._mode = mode
        idx = self._MODE_INDEX.get(mode, 1)
        self._switch.blockSignals(True)
        self._switch.setCurrentIndex(idx)
        self._switch.blockSignals(False)
        self._refresh_mode_widgets()

    def _on_mode_changed(self, _index: int):
        self._mode = self._SWITCH_ITEMS[self._switch.currentIndex()].lower()
        self._refresh_mode_widgets()
        self._emit()

    def _refresh_mode_widgets(self):
        """Swap the stacked widget set to match the current mode."""
        # Remove everything except the switch (index 0) so we can re-add.
        while self._root.count() > 1:
            item = self._root.takeAt(1)
            w = item.widget()
            if w is not None:
                w.hide()

        if self._mode == MODE_VALUE:
            self._value_widget.show()
            self._root.addWidget(self._value_widget, 1)
        elif self._mode == MODE_VARIABLE:
            self._root.addWidget(self._ensure_variable_picker(), 1)
        elif self._mode == MODE_EXPRESSION:
            self._root.addWidget(self._ensure_expression_widget(), 1)
        # MODE_DEFAULT: nothing else shown.

    # ── Lazy-built mode widgets ──────────────────────────────────────────────

    def _ensure_variable_picker(self) -> QWidget:
        if self._variable_picker is None:
            from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
            # Degrade gracefully when there is no variables source (tests).
            if self.ctx.variables_layout is None or self.ctx.element_id_generator is None:
                self._variable_picker = QLineEdit(self)
                self._variable_picker.setStyleSheet(_BASE_QSS + "min-height:22px;")
                self._variable_picker.setPlaceholderText("Variable name")
                self._variable_picker.editingFinished.connect(self._emit)
                return self._variable_picker
            self._variable_picker = ComboboxVariablesWidget(
                self.ctx.element_id_generator, parent=self,
                variables_layout=self.ctx.variables_layout,
                filter_types=self._filter_types,
                variable_name=self.field,
            )
            try:
                self._variable_picker.combobox.changed.connect(lambda _d: self._emit())
            except Exception:
                pass
        self._variable_picker.show()
        return self._variable_picker

    def _ensure_expression_widget(self) -> QWidget:
        if self._expr_edit is None:
            self._expr_edit = QLineEdit(self)
            self._expr_edit.setStyleSheet(_BASE_QSS + "min-height:22px;")
            self._expr_edit.setPlaceholderText("Expression")
            self._expr_edit.editingFinished.connect(self._emit)
            # Expression-editor button (degrades to no-op without a variables source).
            try:
                from src.editors.smartprop_editor.widgets.expression_editor.main import (
                    ExpressionEditor,
                )
                if self.ctx.variables_layout is not None:
                    self._expr_button = ExpressionEditor(self._expr_edit, self.ctx.variables_layout)
                    self._expr_button.setFixedSize(22, 22)
            except Exception:
                self._expr_button = None
        # Rebuild the expression row fresh each time so the layout is clean.
        wrap = QWidget(self)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self._expr_edit, 1)
        if self._expr_button is not None:
            lay.addWidget(self._expr_button)
        wrap.show()
        return wrap

    # ── Value read / write ───────────────────────────────────────────────────

    def set_value(self, stored):
        mode, payload = parse_value_mode(stored, self.field)
        self._set_mode(mode)
        if mode == MODE_VALUE:
            self._set_literal(payload)
        elif mode == MODE_VARIABLE:
            self._set_variable_payload(payload)
        elif mode == MODE_EXPRESSION:
            self._set_expression_payload(payload)

    def value(self):
        return self._current_shape()

    def _current_shape(self):
        if self._mode == MODE_DEFAULT:
            return DEFAULT
        if self._mode == MODE_VARIABLE:
            return build_value_shape(MODE_VARIABLE, None, var=self._read_variable(), field=self.field)
        if self._mode == MODE_EXPRESSION:
            return build_value_shape(MODE_EXPRESSION, None, expr=self._read_expression(), field=self.field)
        return self._literal_value()

    def _read_variable(self):
        if self._variable_picker is None:
            return ""
        get = getattr(self._variable_picker, "get_variable", None)
        if get is not None:
            return get() or ""
        cb = getattr(self._variable_picker, "combobox", None)
        if cb is not None:
            return cb.get_variable() or ""
        return self._variable_picker.text() if hasattr(self._variable_picker, "text") else ""

    def _read_expression(self):
        return self._expr_edit.text() if self._expr_edit is not None else ""

    def _set_variable_payload(self, payload):
        self._ensure_variable_picker()
        payload = payload or ""
        cb = getattr(self._variable_picker, "combobox", None)
        if cb is not None and hasattr(cb, "set_variable"):
            cb.set_variable(payload)
        elif hasattr(self._variable_picker, "set_variable"):
            self._variable_picker.set_variable(payload)
        elif hasattr(self._variable_picker, "setText"):
            self._variable_picker.setText(payload)

    def _set_expression_payload(self, payload):
        self._ensure_expression_widget()
        if self._expr_edit is not None:
            self._expr_edit.setText(str(payload or ""))

    def _emit(self):
        self.commitValue.emit(self._current_shape())


# ── Inline editor widgets ──────────────────────────────────────────────────

class SliderEditor(QWidget):
    """
    Inline float/int editor: a painted horizontal drag-slider track with an
    overlaid QLineEdit for direct keyboard entry.

    The slider occupies the left portion of the cell; the spinbox text is
    drawn on the right.  Dragging anywhere in the widget scrubs the value.
    """

    commitValue = Signal(object)   # emits (int | float) on every change
    # Drag grouping — the owning field editor forwards these to the document
    # so a single slider drag collapses to one undo entry.
    sliderPressed = Signal()
    sliderCommitted = Signal()

    _TRACK_H = 4
    _NUM_W = 48

    def __init__(self, fd: FieldDef, value=0.0, parent=None):
        super().__init__(parent)
        self.fd = fd
        self._is_int = bool(fd.kwargs.get("int_bool")) or fd.control == "number"
        self._min, self._max = self._extract_range()
        self._value = self._clamp(self._coerce(value))
        self._dragging = False
        self._drag_x = 0
        self._drag_v0 = self._value

        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        # Overlaid line-edit (shown only when user double-clicks or presses Enter)
        self._edit = QLineEdit(self)
        self._edit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._edit.setStyleSheet(
            "background:#1C1C1C; color:#E3E3E3; border:1px solid #5588DD;"
            " border-radius:2px; font:8pt 'Segoe UI'; padding:0 2px;"
        )
        self._edit.hide()
        self._edit.editingFinished.connect(self._on_edit_finished)

    # ── Public ──────────────────────────────────────────────────────────────

    def value(self):
        return self._value

    def set_value(self, v):
        self._value = self._clamp(self._coerce(v))
        self.update()

    # ── Painting ────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()

        # Track background
        has_range = self._max > self._min
        num_w = self._NUM_W
        if has_range:
            track_x = 4
            track_w = r.width() - num_w - track_x - 4
            track_y = r.height() // 2 - self._TRACK_H // 2
            track_r = QRect(track_x, track_y, track_w, self._TRACK_H)

            p.fillRect(track_r, _TRACK_COL)

            pct = max(0.0, min(1.0, (self._value - self._min) / (self._max - self._min)))
            fill_w = int(track_r.width() * pct)
            if fill_w > 0:
                p.fillRect(QRect(track_r.left(), track_r.top(), fill_w, self._TRACK_H),
                           _FILL_HOV if self._dragging else _FILL_COL)

            # Thumb circle
            thumb_x = track_r.left() + fill_w
            thumb_r = 5
            p.setBrush(QColor("#88AADD"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(thumb_x - thumb_r, track_y + self._TRACK_H // 2 - thumb_r,
                          thumb_r * 2, thumb_r * 2)

        # Numeric text
        text = f"{int(self._value)}" if self._is_int else f"{self._value:.4g}"
        text_rect = QRect(r.width() - num_w, 0, num_w - 2, r.height())
        p.setPen(QPen(_TEXT_COL))
        font = QFont()
        font.setPixelSize(11)
        p.setFont(font)
        p.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, text)
        p.end()

    def resizeEvent(self, event):
        self._edit.setGeometry(self.rect())

    # ── Mouse ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_x = event.pos().x()
            self._drag_v0 = self._value
            self.sliderPressed.emit()
            self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging and (event.buttons() & Qt.LeftButton):
            self._update_from_drag(event.pos().x())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._update_from_drag(event.pos().x())
            self.sliderCommitted.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self._show_edit()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_F2):
            self._show_edit()
        else:
            super().keyPressEvent(event)

    # ── Private ─────────────────────────────────────────────────────────────

    def _extract_range(self):
        sr = self.fd.kwargs.get("slider_range", [])
        if len(sr) >= 2:
            return float(sr[0]), float(sr[1])
        return 0.0, 1.0

    def _coerce(self, v):
        try:
            return int(v) if self._is_int else float(v)
        except (TypeError, ValueError):
            return 0 if self._is_int else 0.0

    def _clamp(self, v):
        if self._max > self._min:
            return max(self._min, min(self._max, v))
        return v

    def _update_from_drag(self, x: int):
        if not (self._max > self._min):
            return
        track_x = 4
        track_w = max(1, self.width() - self._NUM_W - track_x - 4)
        pct = max(0.0, min(1.0, (x - track_x) / float(track_w)))
        raw = self._min + pct * (self._max - self._min)
        self._value = self._clamp(self._coerce(raw))
        self.update()
        self.commitValue.emit(self._value)

    def _show_edit(self):
        self._edit.setText(str(int(self._value)) if self._is_int else str(self._value))
        self._edit.show()
        self._edit.setFocus()
        self._edit.selectAll()

    def _on_edit_finished(self):
        txt = self._edit.text().strip()
        self._edit.hide()
        if txt:
            try:
                v = int(txt) if self._is_int else float(txt)
                self._value = self._clamp(v)
                self.commitValue.emit(self._value)
                self.update()
            except ValueError:
                pass


class BoolEditor(QWidget):
    """Checkbox + label for bool fields."""

    commitValue = Signal(bool)

    def __init__(self, value: bool = False, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(6)

        self.cb = QCheckBox(self)
        self.cb.setStyleSheet("""
            QCheckBox::indicator { width: 14px; height: 14px; }
            QCheckBox::indicator:unchecked { background:#2A2A2A; border:1px solid #555; border-radius:2px; }
            QCheckBox::indicator:checked   { background:#4A7EBB; border:1px solid #5B9BD5; border-radius:2px; }
        """)
        self.cb.setChecked(bool(value))
        self.cb.toggled.connect(self.commitValue)
        layout.addWidget(self.cb)

        self.lbl = QLabel(str(bool(value)), self)
        self.lbl.setStyleSheet(f"color: {compact.FG}; font: 8pt 'Segoe UI';")
        layout.addWidget(self.lbl)
        layout.addStretch()

        self.cb.toggled.connect(lambda v: self.lbl.setText(str(v)))

    def value(self) -> bool:
        return self.cb.isChecked()

    def set_value(self, v: bool):
        self.cb.setChecked(bool(v))


class ComboEditor(QComboBox):
    """Styled QComboBox for enum/combobox fields."""

    commitValue = Signal(object)

    def __init__(self, items: list[str], current: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(_COMBO_QSS)
        self.addItems(items)
        if current in items:
            self.setCurrentText(current)
        # Connect via a slot so the custom Signal is reliably emitted.
        self.currentTextChanged.connect(lambda v: self.commitValue.emit(v))

    def value(self) -> str:
        return self.currentText()

    def set_value(self, v: str):
        self.setCurrentText(str(v))


class ColorEditor(QWidget):
    """Colour swatch + hex line-edit.  Clicking swatch opens QColorDialog."""

    commitValue = Signal(object)    # emits [R, G, B, A] list

    def __init__(self, value=None, parent=None):
        super().__init__(parent)
        self._color = self._parse(value)
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self._swatch = QLabel(self)
        self._swatch.setFixedSize(18, 18)
        self._swatch.setCursor(Qt.PointingHandCursor)
        self._swatch.mousePressEvent = lambda _: self._open_picker()
        layout.addWidget(self._swatch)

        self._edit = QLineEdit(self)
        self._edit.setStyleSheet(_BASE_QSS + "min-height:20px; max-height:20px;")
        self._edit.editingFinished.connect(self._on_text_edited)
        layout.addWidget(self._edit, 1)

        self._refresh_ui()

    def value(self):
        return list(self._color)

    def set_value(self, v):
        self._color = self._parse(v)
        self._refresh_ui()

    def _parse(self, v):
        if isinstance(v, (list, tuple)) and len(v) >= 3:
            return [int(x) for x in v[:4]] if len(v) >= 4 else [int(x) for x in v[:3]] + [255]
        return [255, 255, 255, 255]

    def _refresh_ui(self):
        r, g, b = self._color[:3]
        self._swatch.setStyleSheet(
            f"background: rgb({r},{g},{b}); border: 1px solid #555; border-radius: 2px;"
        )
        self._edit.setText(f"#{r:02X}{g:02X}{b:02X}")

    def _open_picker(self):
        r, g, b = self._color[:3]
        col = QColorDialog.getColor(QColor(r, g, b), self, "Pick Colour")
        if col.isValid():
            self._color = [col.red(), col.green(), col.blue(), 255]
            self._refresh_ui()
            self.commitValue.emit(self.value())

    def _on_text_edited(self):
        txt = self._edit.text().strip()
        try:
            col = QColor(txt)
            if col.isValid():
                self._color = [col.red(), col.green(), col.blue(), 255]
                self._refresh_ui()
                self.commitValue.emit(self.value())
        except Exception:
            pass


class Vector3DEditor(QWidget):
    """Three spinboxes (X / Y / Z) for vector3d fields."""

    commitValue = Signal(object)   # emits [x, y, z]

    _TAGS = [("X", "#ECA4A0"), ("Y", "#B6EFA2"), ("Z", "#A4B6EF")]

    def __init__(self, value=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(3)

        self._spins: list[QDoubleSpinBox] = []
        vals = self._parse(value)

        for i, (tag, col) in enumerate(self._TAGS):
            lbl = QLabel(tag, self)
            lbl.setFixedWidth(12)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                f"color:{col}; font:bold 8pt 'Segoe UI';"
                "background:transparent; border:none;"
            )
            layout.addWidget(lbl)

            spin = QDoubleSpinBox(self)
            spin.setDecimals(4)
            spin.setRange(-999999, 999999)
            spin.setSingleStep(0.1)
            spin.setValue(vals[i])
            spin.setStyleSheet(
                "QDoubleSpinBox { background:#1C1C1C; color:#E3E3E3;"
                " border:1px solid #3A3A3A; border-radius:2px; font:8pt 'Segoe UI';"
                " padding:0 2px; }"
                "QDoubleSpinBox:focus { border-color:#5588DD; }"
                "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width:0; border:none; }"
            )
            spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
            spin.valueChanged.connect(self._on_changed)
            layout.addWidget(spin, 1)
            self._spins.append(spin)

    def value(self) -> list:
        return [s.value() for s in self._spins]

    def set_value(self, v):
        vals = self._parse(v)
        for spin, val in zip(self._spins, vals):
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)

    def _parse(self, v) -> list:
        if isinstance(v, (list, tuple)) and len(v) >= 3:
            return [float(x) for x in v[:3]]
        return [0.0, 0.0, 0.0]

    def _on_changed(self):
        self.commitValue.emit(self.value())


class StringEditor(QLineEdit):
    """Simple styled line edit for string/variable/reference/comment fields."""

    commitValue = Signal(str)

    def __init__(self, value: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(_BASE_QSS + "min-height:22px; padding: 0 4px;")
        self.setText(str(value) if value not in (DEFAULT, None) else "")
        self.editingFinished.connect(lambda: self.commitValue.emit(self.text()))

    def value(self) -> str:
        return self.text()

    def set_value(self, v):
        self.setText(str(v) if v not in (DEFAULT, None) else "")


# ── Rich scalar field editors (Default/Value/Variable/Expression) ──────────
#
# These subclass ``_ScalarEditorBase`` and provide the literal-editing widget
# plus its read/write hooks.  They are what the delegate builds for scalar
# control kinds.  ``SliderEditor``/``BoolEditor``/…  above remain the compact
# literal-only building blocks reused by these field editors in Value mode.

class FloatFieldEditor(_ScalarEditorBase):
    """Float/int field with optional slider range + the four value modes."""

    def __init__(self, field: str, ctx: EditorContext | None = None,
                 slider_range=None, int_bool: bool = False,
                 filter_types: list | None = None, parent=None):
        self._slider_range = list(slider_range) if slider_range else None
        self._int_bool = int_bool
        ft = filter_types or (["Int", "Float"] if int_bool else ["Float", "Int"])
        super().__init__(field, ctx, filter_types=ft, parent=parent)
        # Relabel Value mode to "Int" when the field is integer-typed.
        if int_bool:
            self._switch.setItemText(1, "Int")

    def _build_value_widget(self) -> QWidget:
        # Reuse the painted drag-slider when a range is given; otherwise a
        # plain QDoubleSpinBox so the user can type arbitrary values.
        if self._slider_range:
            fd = FieldDef(field=self.field, control="number" if self._int_bool else "float",
                          kwargs={"slider_range": self._slider_range,
                                  "int_bool": self._int_bool},
                          label=self.field, icon="float")
            w = SliderEditor(fd, value=0.0, parent=self)
            w.commitValue.connect(self._emit)
            # Forward drag start/end up so the document groups the undo entry.
            try:
                w.sliderPressed.connect(self.sliderPressed)
                w.sliderCommitted.connect(self.sliderCommitted)
            except Exception:
                pass
            self._spin = None
            return w
        spin = QDoubleSpinBox(self)
        spin.setRange(-999999, 999999)
        spin.setDecimals(0 if self._int_bool else 4)
        spin.setSingleStep(1 if self._int_bool else 0.1)
        spin.setStyleSheet(
            "QDoubleSpinBox { background:#1C1C1C; color:#E3E3E3;"
            " border:1px solid #3A3A3A; border-radius:2px; font:8pt 'Segoe UI';"
            " padding:0 2px; min-height:22px; }"
            "QDoubleSpinBox:focus { border-color:#5588DD; }"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width:12px; }"
        )
        spin.valueChanged.connect(lambda _v: self._emit())
        self._spin = spin
        return spin

    def _literal_value(self):
        if self._spin is not None:
            return int(self._spin.value()) if self._int_bool else float(self._spin.value())
        return self._value_widget.value()

    def _set_literal(self, v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0.0
        if self._spin is not None:
            self._spin.blockSignals(True)
            self._spin.setValue(int(v) if self._int_bool else v)
            self._spin.blockSignals(False)
        else:
            self._value_widget.set_value(v)


class BoolFieldEditor(_ScalarEditorBase):
    """Bool field (checkbox) with the four value modes."""

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(field, ctx, filter_types=["Bool"], parent=parent)

    def _build_value_widget(self) -> QWidget:
        w = BoolEditor(value=False, parent=self)
        w.commitValue.connect(self._emit)
        return w

    def _literal_value(self):
        return bool(self._value_widget.value())

    def _set_literal(self, v):
        self._value_widget.set_value(bool(v))


class ComboFieldEditor(_ScalarEditorBase):
    """Enum/combobox field with the four value modes."""

    def __init__(self, field: str, items: list, ctx: EditorContext | None = None,
                 filter_types: list | None = None, parent=None):
        self._items = list(items)
        ft = filter_types or ["String"]
        super().__init__(field, ctx, filter_types=ft, parent=parent)

    def _build_value_widget(self) -> QWidget:
        w = ComboEditor(self._items, current=(self._items[0] if self._items else ""),
                        parent=self)
        w.commitValue.connect(self._emit)
        return w

    def _literal_value(self):
        return self._value_widget.value()

    def _set_literal(self, v):
        self._value_widget.set_value(v)


class ColorFieldEditor(_ScalarEditorBase):
    """Color field (swatch + QColorDialog, alpha-aware) with the four modes."""

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(field, ctx, filter_types=["Color"], parent=parent)

    def _build_value_widget(self) -> QWidget:
        w = ColorEditor(value=None, parent=self)
        w.commitValue.connect(self._emit)
        return w

    def _literal_value(self):
        return self._value_widget.value()

    def _set_literal(self, v):
        self._value_widget.set_value(v)


class StringFieldEditor(_ScalarEditorBase):
    """String field honouring placeholder / model_browser / expression_bool."""

    def __init__(self, field: str, ctx: EditorContext | None = None,
                 placeholder: str | None = None, model_browser: bool = False,
                 expression_bool: bool = False, only_string: bool = False,
                 only_variable: bool = False, filter_types: list | None = None,
                 parent=None):
        self._placeholder = placeholder
        self._model_browser = model_browser
        ft = filter_types or ["String", "MaterialGroup", "Model"]
        super().__init__(field, ctx, filter_types=ft, only_variable=only_variable,
                         expression_bool=expression_bool, parent=parent)
        # only_string forces Value mode (must run after base __init__).
        if only_string and not (expression_bool or only_variable):
            self._only_value = True
            self._set_mode(MODE_VALUE)
        if self._placeholder and self._line is not None:
            self._line.setPlaceholderText(self._placeholder)

    def _build_value_widget(self) -> QWidget:
        wrap = QWidget(self)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self._line = QLineEdit(wrap)
        self._line.setStyleSheet(_BASE_QSS + "min-height:22px; padding:0 4px;")
        if self._placeholder:
            self._line.setPlaceholderText(self._placeholder)
        self._line.editingFinished.connect(self._emit)
        lay.addWidget(self._line, 1)
        if self._model_browser:
            from PySide6.QtWidgets import QPushButton
            btn = QPushButton("…", wrap)
            btn.setFixedSize(22, 22)
            btn.setToolTip("Browse models")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(self._open_model_browser)
            lay.addWidget(btn)
        return wrap

    def _open_model_browser(self):
        try:
            from src.widgets.model_browser import pick_model
        except Exception:
            return
        current = self._line.text().strip()
        try:
            path = pick_model(self, current_path=current)
        except Exception:
            path = None
        if path:
            self._line.setText(path)
            self._emit()

    def _literal_value(self):
        return self._line.text()

    def _set_literal(self, v):
        self._line.setText(str(v) if v not in (DEFAULT, None) else "")


class VariableOutputEditor(QWidget):
    """Pure variable picker for ``variable`` control kind (writes bare name)."""

    commitValue = Signal(object)

    def __init__(self, field: str, ctx: EditorContext | None = None,
                 filter_types: list | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self._filter_types = filter_types
        self._fallback: QLineEdit | None = None
        self._picker = None
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 1, 4, 1)
        lay.setSpacing(4)
        lay.addWidget(self._build(), 1)

    def _build(self) -> QWidget:
        if self.ctx.variables_layout is None or self.ctx.element_id_generator is None:
            self._fallback = QLineEdit(self)
            self._fallback.setStyleSheet(_BASE_QSS + "min-height:22px;")
            self._fallback.setPlaceholderText("Variable name")
            self._fallback.editingFinished.connect(self._emit)
            return self._fallback
        from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
        self._picker = ComboboxVariablesWidget(
            self.ctx.element_id_generator, parent=self,
            variables_layout=self.ctx.variables_layout,
            filter_types=self._filter_types, variable_name=self.field,
        )
        try:
            self._picker.combobox.changed.connect(lambda _d: self._emit())
        except Exception:
            pass
        return self._picker

    def _read(self) -> str:
        if self._picker is not None:
            cb = getattr(self._picker, "combobox", None)
            if cb is not None and hasattr(cb, "get_variable"):
                return cb.get_variable() or ""
        if self._fallback is not None:
            return self._fallback.text()
        return ""

    def _emit(self):
        self.commitValue.emit(self._read())

    def value(self):
        return self._read()

    def set_value(self, stored):
        name = ""
        if isinstance(stored, dict):
            name = stored.get("m_SourceName") or ""
        elif isinstance(stored, str):
            name = stored
        if self._picker is not None:
            cb = getattr(self._picker, "combobox", None)
            if cb is not None and hasattr(cb, "set_variable"):
                cb.set_variable(name)
        elif self._fallback is not None:
            self._fallback.setText(name)


class CommentEditor(QWidget):
    """Multi-line comment editor that grows to fit its content."""

    commitValue = Signal(object)
    heightChanged = Signal()

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(0)
        from PySide6.QtWidgets import QPlainTextEdit
        self._edit = QPlainTextEdit(self)
        self._edit.setStyleSheet(
            "QPlainTextEdit { background:#1C1C1C; color:#E3E3E3;"
            " border:1px solid #3A3A3A; border-radius:2px; font:8pt 'Segoe UI';"
            " padding:2px; }"
        )
        self._edit.setPlaceholderText("Comment…")
        self._edit.textChanged.connect(self._on_text_changed)
        lay.addWidget(self._edit, 1)
        self._resize_timer = None

    def _on_text_changed(self):
        self.commitValue.emit(self._edit.toPlainText())
        # Debounced auto-resize so the tree row grows with the comment.
        from PySide6.QtCore import QTimer
        if self._resize_timer is None:
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._do_resize)
        self._resize_timer.start(120)

    def _do_resize(self):
        h = int(self._edit.document().size().height()) + 14
        h = max(64, min(h, 400))
        self._edit.setFixedHeight(h)
        self.heightChanged.emit()

    def value(self):
        return self._edit.toPlainText()

    def set_value(self, stored):
        txt = "" if stored in (DEFAULT, None) else str(stored)
        self._edit.blockSignals(True)
        self._edit.setPlainText(txt)
        self._edit.blockSignals(False)
        self._do_resize()


class WarningEditor(QWidget):
    """Static orange banner; never emits (matches legacy PropertyWarning)."""

    def __init__(self, field: str = "", ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lbl = QLabel("This property might not work in CS2.", self)
        lbl.setStyleSheet(
            "color:#ffaa00; font-weight:bold; background: rgba(255,170,0,10);"
            " border:1px solid rgba(255,170,0,30); border-radius:2px; padding:4px;"
        )
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

    def value(self):
        return None

    def set_value(self, stored):
        pass


class LegacyEditor(QWidget):
    """Fallback editor for unknown keys: text field with literal_eval round-trip."""

    commitValue = Signal(object)

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 1, 4, 1)
        lay.setSpacing(0)
        self._line = QLineEdit(self)
        self._line.setStyleSheet(_BASE_QSS + "min-height:22px; padding:0 4px;")
        self._line.editingFinished.connect(self._emit)
        lay.addWidget(self._line, 1)

    def _emit(self):
        import ast
        txt = self._line.text().strip()
        try:
            self.commitValue.emit(ast.literal_eval(txt))
        except Exception:
            self.commitValue.emit(txt)

    def value(self):
        import ast
        txt = self._line.text().strip()
        try:
            return ast.literal_eval(txt)
        except Exception:
            return txt

    def set_value(self, stored):
        self._line.setText("" if stored in (DEFAULT, None) else repr(stored))


class ReferenceEditor(QWidget):
    """Reference field: line edit + search/show-in-hierarchy buttons."""

    commitValue = Signal(object)

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 1, 4, 1)
        lay.setSpacing(2)
        self._line = QLineEdit(self)
        self._line.setStyleSheet(_BASE_QSS + "min-height:22px; padding:0 4px;")
        self._line.setPlaceholderText("Reference ID")
        self._line.editingFinished.connect(self._emit)
        lay.addWidget(self._line, 1)
        from PySide6.QtWidgets import QPushButton
        self._btn_show = QPushButton("→", self)
        self._btn_show.setFixedSize(22, 22)
        self._btn_show.setToolTip("Show in hierarchy")
        self._btn_show.setCursor(Qt.PointingHandCursor)
        self._btn_show.clicked.connect(self._show_in_hierarchy)
        lay.addWidget(self._btn_show)

    def _emit(self):
        txt = self._line.text().strip()
        if txt:
            try:
                import uuid
                self.commitValue.emit({"m_nReferenceID": int(txt),
                                       "m_sReferenceObjectID": str(uuid.uuid4())})
            except ValueError:
                self.commitValue.emit(DEFAULT)
        else:
            self.commitValue.emit(DEFAULT)

    def _show_in_hierarchy(self):
        doc = self.ctx.document
        if doc is None:
            return
        txt = self._line.text().strip()
        try:
            element_id = int(txt)
        except ValueError:
            return
        select = getattr(doc, "select_element_by_id", None)
        if select is not None:
            select(element_id)

    def value(self):
        return self._current_value()

    def _current_value(self):
        txt = self._line.text().strip()
        if not txt:
            return DEFAULT
        try:
            import uuid
            return {"m_nReferenceID": int(txt),
                    "m_sReferenceObjectID": str(uuid.uuid4())}
        except ValueError:
            return DEFAULT

    def set_value(self, stored):
        ref_id = ""
        if isinstance(stored, dict):
            ref_id = "" if stored.get("m_nReferenceID") in (None, DEFAULT) else str(stored["m_nReferenceID"])
        elif isinstance(stored, int):
            ref_id = str(stored)
        self._line.setText(ref_id)


# ── Multi-row / list field editors ─────────────────────────────────────────

class _ListEditorBase(QWidget):
    """Base for editors that own a vertical list of rows and grow with them.

    Subclasses build rows via ``_make_row(value)`` (returning a widget that
    exposes ``set_value``/``value``) and emit ``commitValue`` whenever a row
    changes or the list grows/shrinks.  ``heightChanged`` is emitted so the
    delegate can resize the tree row.
    """

    commitValue = Signal(object)
    heightChanged = Signal()

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self.setStyleSheet("background: transparent;")
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(4, 2, 4, 2)
        self._root.setSpacing(2)
        self._rows: list[QWidget] = []

    # ── Subclass hooks ───────────────────────────────────────────────────────

    def _make_row(self, value) -> QWidget:
        raise NotImplementedError

    def _default_row_value(self):
        raise NotImplementedError

    def _row_widget_value(self, row: QWidget):
        if hasattr(row, "value"):
            return row.value()
        return None

    def _set_row_widget_value(self, row: QWidget, value):
        if hasattr(row, "set_value"):
            row.set_value(value)

    def _aggregate(self) -> list:
        return [self._row_widget_value(r) for r in self._rows]

    # ── Row management ───────────────────────────────────────────────────────

    def _add_row(self, value, index: int | None = None):
        from PySide6.QtWidgets import QHBoxLayout, QPushButton
        row = self._make_row(value)
        # Push the value into the freshly-built row widget.
        self._set_row_widget_value(row, value)
        # Wire row change → re-emit aggregate.
        commit = getattr(row, "commitValue", None)
        if commit is not None:
            commit.connect(lambda _v: self._emit())
        hc = getattr(row, "heightChanged", None)
        if hc is not None:
            hc.connect(self._relayout)
        wrap = QWidget(self)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(row, 1)
        del_btn = QPushButton("✕", wrap)
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            "QPushButton { background:#2A2A2A; color:#E3E3E3; border:1px solid #3A3A3A;"
            " border-radius:2px; font:8pt 'Segoe UI'; }"
            "QPushButton:hover { background:#5A2A2A; border-color:#FF8888; }"
        )
        del_btn.clicked.connect(lambda _c=False, w=wrap: self._delete_row(w))
        lay.addWidget(del_btn)
        if index is None:
            self._root.addWidget(wrap)
            self._rows.append(row)
        else:
            self._root.insertWidget(index, wrap)
            self._rows.insert(index, row)
        wrap._row_ref = row
        return wrap

    def _delete_row(self, wrap: QWidget):
        row = getattr(wrap, "_row_ref", None)
        if row in self._rows:
            self._rows.remove(row)
        self._root.removeWidget(wrap)
        wrap.setParent(None)
        wrap.deleteLater()
        self._emit()
        self._relayout()

    def _clear_rows(self):
        while self._root.count():
            item = self._root.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._rows = []

    def _add_button(self, label: str, callback):
        from PySide6.QtWidgets import QPushButton
        btn = QPushButton(label, self)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { background:#232323; color:#C8C8C8; border:1px solid #3A3A3A;"
            " border-radius:2px; padding:3px 8px; font:8pt 'Segoe UI'; text-align:left; }"
            "QPushButton:hover { background:#2E3744; border-color:#5588DD; }"
        )
        btn.clicked.connect(callback)
        self._root.addWidget(btn)
        return btn

    def _relayout(self):
        self.updateGeometry()
        self.heightChanged.emit()

    def _emit(self):
        self.commitValue.emit(self._aggregate())

    # ── Public API ───────────────────────────────────────────────────────────

    def value(self):
        return self._aggregate()

    def set_value(self, stored):
        self._clear_rows()
        for v in (stored or []):
            self._add_row(v)
        if not self._rows:
            self._add_row(self._default_row_value())
        self._relayout()


class Vector3DFieldEditor(QWidget):
    """Vector3D field: whole-vector variable binding or 3 per-component floats.

    Stored shapes (matching the legacy PropertyVector3D):
      DEFAULT                     → key absent
      {'m_SourceName': v}         → whole-vector variable
      {'m_Components': [c0,c1,c2]}→ each ci is itself a shape (literal float,
                                     {'m_SourceName': v} or {'m_Expression': e})
    """

    commitValue = Signal(object)
    heightChanged = Signal()
    sliderPressed = Signal()
    sliderCommitted = Signal()

    _TAGS = (("X", "#ECA4A0"), ("Y", "#B6EFA2"), ("Z", "#A4B6EF"),
             ("P", "#ECA4A0"), ("Y", "#B6EFA2"), ("R", "#A4B6EF"))

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self.setStyleSheet("background: transparent;")
        self._mode = MODE_VALUE
        # Header row: whole-vector mode switch + variable picker (lazy).
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(4, 1, 4, 1)
        self._root.setSpacing(1)

        header = QWidget(self)
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(0, 0, 0, 0)
        hlay.setSpacing(4)
        self._header_switch = QComboBox(header)
        self._header_switch.addItems(("Default", "Components", "Variable"))
        self._header_switch.setStyleSheet(_LOGIC_SWITCH_QSS)
        self._header_switch.setFixedWidth(90)
        self._header_switch.wheelEvent = lambda e: None
        self._header_switch.currentIndexChanged.connect(self._on_header_mode)
        hlay.addWidget(self._header_switch)
        self._header_var: QLineEdit | None = None
        self._header_picker = None
        hlay.addStretch(1)
        self._root.addWidget(header)

        self._components: list[FloatFieldEditor] = []
        self._component_holder = QWidget(self)
        self._component_layout = QVBoxLayout(self._component_holder)
        self._component_layout.setContentsMargins(0, 0, 0, 0)
        self._component_layout.setSpacing(1)
        self._root.addWidget(self._component_holder)
        self._build_components()
        self._refresh_mode()

    def _is_angle(self) -> bool:
        vc = (self.field or "").lower()
        return "angle" in vc or "rotation" in vc or "rotator" in vc

    def _build_components(self):
        tags = self._TAGS[3:] if self._is_angle() else self._TAGS[:3]
        for i, (tag, col) in enumerate(tags):
            row = QWidget(self._component_holder)
            rlay = QHBoxLayout(row)
            rlay.setContentsMargins(12, 0, 0, 0)
            rlay.setSpacing(4)
            lbl = QLabel(tag, row)
            lbl.setFixedWidth(14)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color:{col}; font:bold 8pt 'Segoe UI'; background:transparent; border:none;")
            rlay.addWidget(lbl)
            sub = FloatFieldEditor(f"{self.field}_{tag.lower()}", self.ctx)
            sub.commitValue.connect(lambda _v: self._emit())
            sub.sliderPressed.connect(self.sliderPressed)
            sub.sliderCommitted.connect(self.sliderCommitted)
            rlay.addWidget(sub, 1)
            self._component_layout.addWidget(row)
            self._components.append(sub)

    def _on_header_mode(self, _idx: int):
        names = ("default", "value", "variable")
        self._mode = names[self._header_switch.currentIndex()]
        self._refresh_mode()
        self._emit()

    def _refresh_mode(self):
        # Show components for value mode; variable picker for variable mode.
        self._component_holder.setVisible(self._mode == MODE_VALUE)
        if self._mode == MODE_VARIABLE:
            self._ensure_header_variable()
        if self._header_var is not None:
            self._header_var.setVisible(self._mode == MODE_VARIABLE)
        if self._header_picker is not None:
            self._header_picker.setVisible(self._mode == MODE_VARIABLE)
        self.heightChanged.emit()

    def _ensure_header_variable(self):
        if self._header_var is None and self._header_picker is None:
            if self.ctx.variables_layout is None or self.ctx.element_id_generator is None:
                self._header_var = QLineEdit(self)
                self._header_var.setStyleSheet(_BASE_QSS + "min-height:22px;")
                self._header_var.setPlaceholderText("Variable name")
                self._header_var.editingFinished.connect(self._emit)
                # Insert into the header layout (index after the switch).
                header = self._root.itemAt(0).widget()
                header.layout().insertWidget(1, self._header_var)
            else:
                from src.editors.smartprop_editor.widgets.main import ComboboxVariablesWidget
                self._header_picker = ComboboxVariablesWidget(
                    self.ctx.element_id_generator, parent=self,
                    variables_layout=self.ctx.variables_layout,
                    filter_types=["Vector3D"], variable_name=self.field,
                )
                try:
                    self._header_picker.combobox.changed.connect(lambda _d: self._emit())
                except Exception:
                    pass
                header = self._root.itemAt(0).widget()
                header.layout().insertWidget(1, self._header_picker)

    def _read_header_variable(self) -> str:
        if self._header_picker is not None:
            cb = getattr(self._header_picker, "combobox", None)
            if cb is not None and hasattr(cb, "get_variable"):
                return cb.get_variable() or ""
        if self._header_var is not None:
            return self._header_var.text()
        return ""

    def _set_header_variable(self, name: str):
        self._ensure_header_variable()
        if self._header_picker is not None:
            cb = getattr(self._header_picker, "combobox", None)
            if cb is not None and hasattr(cb, "set_variable"):
                cb.set_variable(name or "")
        elif self._header_var is not None:
            self._header_var.setText(name or "")

    # ── Public API ───────────────────────────────────────────────────────────

    def value(self):
        if self._mode == MODE_DEFAULT:
            return DEFAULT
        if self._mode == MODE_VARIABLE:
            return {"m_SourceName": self._read_header_variable()}
        return {"m_Components": [c.value() for c in self._components]}

    def set_value(self, stored):
        if stored in (DEFAULT, None):
            self._mode = MODE_DEFAULT
            self._header_switch.blockSignals(True)
            self._header_switch.setCurrentIndex(0)
            self._header_switch.blockSignals(False)
            for c in self._components:
                c.set_value(DEFAULT)
            self._refresh_mode()
            return
        if isinstance(stored, dict):
            if "m_SourceName" in stored:
                self._mode = MODE_VARIABLE
                self._header_switch.blockSignals(True)
                self._header_switch.setCurrentIndex(2)
                self._header_switch.blockSignals(False)
                self._set_header_variable(stored["m_SourceName"])
                self._refresh_mode()
                return
            comps = stored.get("m_Components")
            if isinstance(comps, (list, tuple)) and len(comps) == 3:
                self._mode = MODE_VALUE
                self._header_switch.blockSignals(True)
                self._header_switch.setCurrentIndex(1)
                self._header_switch.blockSignals(False)
                for c, v in zip(self._components, comps):
                    c.set_value(v)
                self._refresh_mode()
                return
        # Bare list [x,y,z] → components value mode.
        if isinstance(stored, (list, tuple)) and len(stored) == 3:
            self._mode = MODE_VALUE
            self._header_switch.blockSignals(True)
            self._header_switch.setCurrentIndex(1)
            self._header_switch.blockSignals(False)
            for c, v in zip(self._components, stored):
                c.set_value(float(v))
            self._refresh_mode()
            return

    def _emit(self):
        self.commitValue.emit(self.value())


class ComparisonEditor(QWidget):
    """m_VariableComparison: variable name + operator + value."""

    commitValue = Signal(object)

    _OPS = ("==", "!=", "<", "<=", ">", ">=")

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 1, 4, 1)
        lay.setSpacing(4)
        self._var_line = QLineEdit(self)
        self._var_line.setStyleSheet(_BASE_QSS + "min-height:22px;")
        self._var_line.setPlaceholderText("Variable name")
        self._var_line.editingFinished.connect(self._emit)
        lay.addWidget(self._var_line, 2)
        self._op = QComboBox(self)
        self._op.addItems(self._OPS)
        self._op.setStyleSheet(_COMBO_QSS)
        self._op.currentTextChanged.connect(lambda _v: self._emit())
        lay.addWidget(self._op)
        self._val_line = QLineEdit(self)
        self._val_line.setStyleSheet(_BASE_QSS + "min-height:22px;")
        self._val_line.setPlaceholderText("Value")
        self._val_line.editingFinished.connect(self._emit)
        lay.addWidget(self._val_line, 2)

    def _emit(self):
        name = self._var_line.text().strip()
        if not name:
            self.commitValue.emit(DEFAULT)
            return
        import ast
        raw = self._val_line.text().strip()
        try:
            value = ast.literal_eval(raw)
        except Exception:
            value = raw
        self.commitValue.emit({"m_Name": name, "m_Value": value,
                               "m_Comparison": self._op.currentText()})

    def value(self):
        name = self._var_line.text().strip()
        if not name:
            return DEFAULT
        import ast
        raw = self._val_line.text().strip()
        try:
            value = ast.literal_eval(raw)
        except Exception:
            value = raw
        return {"m_Name": name, "m_Value": value,
                "m_Comparison": self._op.currentText()}

    def set_value(self, stored):
        if isinstance(stored, dict):
            self._var_line.setText(str(stored.get("m_Name", "")))
            self._val_line.setText("" if stored.get("m_Value") in (None, DEFAULT) else repr(stored.get("m_Value")))
            op = stored.get("m_Comparison", "==")
            if op in self._OPS:
                self._op.setCurrentText(op)
        else:
            self._var_line.setText("")
            self._val_line.setText("")


class ColorMatchEditor(_ListEditorBase):
    """m_ColorChoices: dynamic list of colors."""

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(field, ctx, parent)
        self._add_button("＋ Add color", lambda: self._add_color())
        # set_value called by delegate; seed one default row if empty.

    def _make_row(self, value) -> QWidget:
        return ColorFieldEditor(f"{self.field}_item", self.ctx)

    def _default_row_value(self):
        return [255, 255, 255, 255]

    def _add_color(self):
        self._add_row(self._default_row_value())
        self._emit()
        self._relayout()

    def set_value(self, stored):
        self._clear_rows()
        items = stored if isinstance(stored, list) else []
        for v in items:
            self._add_row(v)
        if not self._rows:
            self._add_row(self._default_row_value())
        # Re-add the button at the bottom.
        self._add_button("＋ Add color", lambda: self._add_color())
        self._relayout()


class SurfaceEditor(QWidget):
    """m_Allowed/DisallowedSurfaceProperties: list of surface names with add popup."""

    commitValue = Signal(object)
    heightChanged = Signal()

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(2)
        from PySide6.QtWidgets import QListWidget, QPushButton
        self._list = QListWidget(self)
        self._list.setStyleSheet(
            "QListWidget { background:#1C1C1C; color:#E3E3E3; border:1px solid #3A3A3A;"
            " border-radius:2px; font:8pt 'Segoe UI'; }"
            "QListWidget::item { padding:1px 4px; }"
            "QListWidget::item:selected { background:#414956; }"
        )
        self._list.setMinimumHeight(60)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        lay.addWidget(self._list)
        btn = QPushButton("＋ Add surface", self)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { background:#232323; color:#C8C8C8; border:1px solid #3A3A3A;"
            " border-radius:2px; padding:3px 8px; font:8pt 'Segoe UI'; text-align:left; }"
            "QPushButton:hover { background:#2E3744; border-color:#5588DD; }"
        )
        btn.clicked.connect(self._open_add_popup)
        lay.addWidget(btn)

    def _open_add_popup(self):
        try:
            from src.editors.smartprop_editor.objects import surfaces_list
            from src.widgets.popup_menu.main import PopupMenu
        except Exception:
            return
        existing = {self._list.item(i).text() for i in range(self._list.count())}
        props = [{k: k} for d in surfaces_list for k in d.keys() if k not in existing]
        if not props:
            return
        popup = PopupMenu(props, add_once=True, parent=self,
                          window_name="SPE_Property_surface")
        popup.add_property_signal.connect(lambda _name, value: self._add_surface(value))
        popup.show()

    def _add_surface(self, name: str):
        if name and any(self._list.item(i).text() == name for i in range(self._list.count())):
            return
        self._list.addItem(name)
        self._emit()
        self.heightChanged.emit()

    def _on_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        item = self._list.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        act = menu.addAction("Delete item")
        chosen = menu.exec(self._list.viewport().mapToGlobal(pos))
        if chosen is act:
            self._list.takeItem(self._list.row(item))
            self._emit()
            self.heightChanged.emit()

    def _emit(self):
        names = [self._list.item(i).text() for i in range(self._list.count())]
        self.commitValue.emit(names if names else DEFAULT)

    def value(self):
        names = [self._list.item(i).text() for i in range(self._list.count())]
        return names if names else DEFAULT

    def set_value(self, stored):
        self._list.clear()
        for name in (stored if isinstance(stored, list) else []):
            self._list.addItem(str(name))
        self.heightChanged.emit()


class MaterialReplacementsEditor(_ListEditorBase):
    """m_MaterialReplacements: list of {m_OriginalMaterial, m_ReplacementMaterial}."""

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(field, ctx, parent)
        self._add_button("＋ Add replacement", lambda: self._add_replacement())

    def _make_row(self, value) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        origin = StringFieldEditor(f"{self.field}_origin", self.ctx,
                                    filter_types=["Material", "String"])
        target = StringFieldEditor(f"{self.field}_target", self.ctx,
                                    filter_types=["Material", "String"])
        lay.addWidget(origin, 1)
        arrow = QLabel("→", row)
        arrow.setStyleSheet("color:#9AA0AA; background:transparent; border:none;")
        lay.addWidget(arrow)
        lay.addWidget(target, 1)
        row._origin = origin
        row._target = target
        origin.commitValue.connect(lambda _v: self._emit())
        target.commitValue.connect(lambda _v: self._emit())
        return row

    def _row_widget_value(self, row: QWidget):
        return {"m_OriginalMaterial": row._origin.value(),
                "m_ReplacementMaterial": row._target.value()}

    def _set_row_widget_value(self, row: QWidget, value):
        if isinstance(value, dict):
            row._origin.set_value(value.get("m_OriginalMaterial", DEFAULT))
            row._target.set_value(value.get("m_ReplacementMaterial", DEFAULT))

    def _default_row_value(self):
        return {"m_OriginalMaterial": DEFAULT, "m_ReplacementMaterial": DEFAULT}

    def _aggregate(self) -> list:
        return [self._row_widget_value(r) for r in self._rows]

    def _add_replacement(self):
        self._add_row(self._default_row_value())
        self._emit()
        self._relayout()

    def set_value(self, stored):
        self._clear_rows()
        items = stored if isinstance(stored, list) else []
        for v in items:
            self._add_row(v)
        if not self._rows:
            self._add_row(self._default_row_value())
        self._add_button("＋ Add replacement", lambda: self._add_replacement())
        self._relayout()


class MaterialGroupChoicesEditor(_ListEditorBase):
    """m_MaterialGroupChoices: list of {m_MaterialGroupName, m_flWeight}."""

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(field, ctx, parent)
        self._add_button("＋ Add choice", lambda: self._add_choice())

    def _make_row(self, value) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        name = StringFieldEditor(f"{self.field}_name", self.ctx, filter_types=["String"])
        weight = FloatFieldEditor(f"{self.field}_weight", self.ctx, slider_range=[0, 1])
        lay.addWidget(name, 2)
        wlbl = QLabel("W:", row)
        wlbl.setStyleSheet("color:#9AA0AA; background:transparent; border:none;")
        lay.addWidget(wlbl)
        lay.addWidget(weight, 1)
        row._name = name
        row._weight = weight
        name.commitValue.connect(lambda _v: self._emit())
        weight.commitValue.connect(lambda _v: self._emit())
        return row

    def _row_widget_value(self, row: QWidget):
        return {"m_MaterialGroupName": row._name.value(), "m_flWeight": row._weight.value()}

    def _set_row_widget_value(self, row: QWidget, value):
        if isinstance(value, dict):
            row._name.set_value(value.get("m_MaterialGroupName", DEFAULT))
            row._weight.set_value(value.get("m_flWeight", 1.0))

    def _default_row_value(self):
        return {"m_MaterialGroupName": DEFAULT, "m_flWeight": 1.0}

    def _aggregate(self) -> list:
        return [self._row_widget_value(r) for r in self._rows]

    def _add_choice(self):
        self._add_row(self._default_row_value())
        self._emit()
        self._relayout()

    def set_value(self, stored):
        self._clear_rows()
        items = stored if isinstance(stored, list) else []
        for v in items:
            self._add_row(v)
        if not self._rows:
            self._add_row(self._default_row_value())
        self._add_button("＋ Add choice", lambda: self._add_choice())
        self._relayout()


class SetVariableEditor(QWidget):
    """m_VariableValue for SetVariable: data type + value/expression.

    Stored shape:
      {'m_TargetName': str, 'm_DataType': 'FLOAT'|'INT'|'BOOL'|'VECTOR3D',
       'm_Value': <value>}
    where m_Value is the float/bool/[x,y,z] literal or {'m_Expression': str}.
    """

    commitValue = Signal(object)
    heightChanged = Signal()
    sliderPressed = Signal()
    sliderCommitted = Signal()

    _TYPES = ("Float", "Int", "Bool", "Vector3D")

    def __init__(self, field: str, ctx: EditorContext | None = None, parent=None):
        super().__init__(parent)
        self.field = field
        self.ctx = ctx or EditorContext()
        self.setStyleSheet("background: transparent;")
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(4, 1, 4, 1)
        self._root.setSpacing(1)

        # Target variable name + data type + value/expression switch.
        top = QWidget(self)
        tlay = QHBoxLayout(top)
        tlay.setContentsMargins(0, 0, 0, 0)
        tlay.setSpacing(4)
        self._target = QLineEdit(top)
        self._target.setStyleSheet(_BASE_QSS + "min-height:22px;")
        self._target.setPlaceholderText("Target variable")
        self._target.editingFinished.connect(self._emit)
        tlay.addWidget(self._target, 2)
        self._type = QComboBox(top)
        self._type.addItems(self._TYPES)
        self._type.setStyleSheet(_COMBO_QSS)
        self._type.currentTextChanged.connect(lambda _v: self._on_type_changed())
        tlay.addWidget(self._type)
        self._value_mode = QComboBox(top)
        self._value_mode.addItems(("Value", "Expression"))
        self._value_mode.setStyleSheet(_COMBO_QSS)
        self._value_mode.currentTextChanged.connect(lambda _v: self._on_value_mode_changed())
        tlay.addWidget(self._value_mode)
        self._root.addWidget(top)

        # Holder for the type-specific value editor.
        self._value_holder = QWidget(self)
        self._value_layout = QVBoxLayout(self._value_holder)
        self._value_layout.setContentsMargins(0, 0, 0, 0)
        self._value_layout.setSpacing(1)
        self._root.addWidget(self._value_holder)
        self._value_editor: QWidget | None = None
        self._on_type_changed()

    def _on_type_changed(self):
        dtype = self._type.currentText()
        self._clear_value_holder()
        if dtype == "Bool":
            self._value_editor = BoolFieldEditor(f"{self.field}_val", self.ctx)
        elif dtype == "Vector3D":
            self._value_editor = Vector3DFieldEditor(f"{self.field}_val", self.ctx)
            self._value_editor.heightChanged.connect(self.heightChanged)
        else:
            int_bool = (dtype == "Int")
            self._value_editor = FloatFieldEditor(f"{self.field}_val", self.ctx, int_bool=int_bool)
        self._value_editor.commitValue.connect(lambda _v: self._emit())
        sp = getattr(self._value_editor, "sliderPressed", None)
        sc = getattr(self._value_editor, "sliderCommitted", None)
        if sp is not None:
            sp.connect(self.sliderPressed)
        if sc is not None:
            sc.connect(self.sliderCommitted)
        self._value_layout.addWidget(self._value_editor)
        self._on_value_mode_changed()
        self.heightChanged.emit()

    def _on_value_mode_changed(self):
        # Only the Float/Int/Bool field editors have a mode switch; for them,
        # "Expression" means expression mode (the editor's own switch handles it).
        if not isinstance(self._value_editor, _ScalarEditorBase):
            return
        if self._value_mode.currentText() == "Expression":
            self._value_editor._set_mode(MODE_EXPRESSION)
        else:
            self._value_editor._set_mode(MODE_VALUE)

    def _clear_value_holder(self):
        while self._value_layout.count():
            item = self._value_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._value_editor = None

    def _emit(self):
        self.commitValue.emit(self.value())

    def value(self):
        target = self._target.text().strip()
        if not target:
            return DEFAULT
        dtype = self._type.currentText().upper()
        if self._value_mode.currentText() == "Expression" and isinstance(self._value_editor, _ScalarEditorBase):
            raw = self._value_editor._read_expression()
            m_value: Any = {"m_Expression": raw}
        else:
            m_value = self._value_editor.value() if self._value_editor is not None else 0.0
            if m_value is DEFAULT:
                m_value = 0.0
        return {"m_TargetName": target, "m_DataType": dtype, "m_Value": m_value}

    def set_value(self, stored):
        if not isinstance(stored, dict):
            self._target.setText("")
            return
        self._target.setText(str(stored.get("m_TargetName", "")))
        dtype = str(stored.get("m_DataType", "FLOAT")).upper()
        type_label = dtype.capitalize() if dtype.lower() in ("float", "int", "bool") else "Vector3D"
        if type_label not in self._TYPES:
            type_label = "Float"
        self._type.blockSignals(True)
        self._type.setCurrentText(type_label)
        self._type.blockSignals(False)
        self._on_type_changed()
        m_value = stored.get("m_Value", 0.0)
        if isinstance(m_value, dict) and "m_Expression" in m_value:
            self._value_mode.blockSignals(True)
            self._value_mode.setCurrentText("Expression")
            self._value_mode.blockSignals(False)
            self._on_value_mode_changed()
            if isinstance(self._value_editor, _ScalarEditorBase):
                self._value_editor._set_expression_payload(m_value["m_Expression"])
        else:
            self._value_mode.blockSignals(True)
            self._value_mode.setCurrentText("Value")
            self._value_mode.blockSignals(False)
            self._on_value_mode_changed()
            if self._value_editor is not None:
                self._value_editor.set_value(m_value)


