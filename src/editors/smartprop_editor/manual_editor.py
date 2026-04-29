"""
Manual Editor widget for SmartProp Editor.

Displays the raw KV3 text representation of the currently selected hierarchy
element, variables, or choices, and allows direct text editing with Apply.

Features:
  - Line numbers (matches ExpressionEditor / CodeEditor pattern)
  - KV3 syntax highlighting with bracket matching
  - Auto-completion for KV3 keys
  - Search & Replace bar  (Ctrl+F / Ctrl+H)
  - Live text statistics  (lines, words, keys)
"""

import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPlainTextEdit,
    QPushButton, QLabel, QFrame, QTextEdit, QLineEdit, QCheckBox,
)
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
    QPainter, QTextFormat, QTextCursor, QKeyEvent,
)
from PySide6.QtCore import Qt, Signal, QRect, QSize, QStringListModel

from src.common import JsonToKv3, fast_deepcopy
from src.settings.main import debug


# ── KV3 Syntax Highlighter ────────────────────────────────────────────────────

class Kv3SyntaxHighlighter(QSyntaxHighlighter):
    """Full KV3 syntax highlighter with bracket/brace colouring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        # ── KV3 header ──
        header_fmt = QTextCharFormat()
        header_fmt.setForeground(QColor(109, 109, 109))  # #6D6D6D
        header_fmt.setFontItalic(True)
        self.highlighting_rules.append((re.compile(r'<!--.*?-->'), header_fmt))

        # ── Class values  (e.g. "CSmartProp…") ──
        class_fmt = QTextCharFormat()
        class_fmt.setForeground(QColor(78, 201, 176))  # Teal
        class_fmt.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((re.compile(r'"CSmartProp\w*"'), class_fmt))

        # ── Keys (word followed by '=') ──
        key_fmt = QTextCharFormat()
        key_fmt.setForeground(QColor(156, 220, 254))   # #9CDCFE — light blue
        self.highlighting_rules.append((re.compile(r'\b(\w+)\s*='), key_fmt, 1))

        # ── Strings ──
        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor(206, 145, 120))  # #CE9178 — orange/brown
        self.highlighting_rules.append((re.compile(r'"[^"]*"'), string_fmt))

        # ── Numbers ──
        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor(181, 206, 168))  # #B5CEA8 — green
        self.highlighting_rules.append((re.compile(r'\b-?\d+(?:\.\d+)?\b'), number_fmt))

        # ── Booleans / null ──
        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor(86, 156, 214))  # #569CD6 — blue
        keyword_fmt.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((re.compile(r'\b(?:true|false|null)\b'), keyword_fmt))

        # ── Brackets & braces ──
        bracket_fmt = QTextCharFormat()
        bracket_fmt.setForeground(QColor(220, 220, 170))  # #DCDCAA — yellow
        self.highlighting_rules.append((re.compile(r'[\[\]{}]'), bracket_fmt))

        # ── Comments (applied last to override everything) ──
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(106, 153, 85))  # #6A9955 — green
        self.comment_format.setFontItalic(True)
        self.comment_pattern = re.compile(r'//[^\n]*')

    # noinspection PyMethodOverriding
    def highlightBlock(self, text):
        for rule in self.highlighting_rules:
            if len(rule) == 3:
                pattern, fmt, group = rule
            else:
                pattern, fmt = rule
                group = 0
            for m in pattern.finditer(text):
                start = m.start(group)
                length = m.end(group) - start
                self.setFormat(start, length, fmt)

        # Comments override everything
        for m in self.comment_pattern.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self.comment_format)


# ── Line Number Area (same pattern as ExpressionEditor) ───────────────────────

class _LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


# ── KV3 Code Editor (line numbers + highlight + completions) ──────────────────

# Common KV3 property keys used across SmartProp documents
_KV3_COMPLETIONS = sorted({
    "m_Children", "m_sLabel", "_class", "m_nElementID",
    "m_Modifiers", "m_SelectionCriteria",
    "m_Variables", "m_VariableName", "m_DefaultValue",
    "m_bExposeAsParameter", "m_ParameterName",
    "m_flParamaterMinValue", "m_flParamaterMaxValue",
    "m_nParamaterMinValue", "m_nParamaterMaxValue",
    "m_sModelName", "m_HideExpression", "m_ReadOnlyExpression",
    "m_Choices", "m_Options", "m_Name", "m_DefaultOption",
    "m_VariableValues", "m_TargetName", "m_DataType", "m_Value",
    "m_Expression", "m_Comment", "m_StateName", "m_DisplayName",
    "m_nContentVersion", "generic_data_type", "editor_info",
    "m_sReferenceObjectID", "m_nReferenceID",
    "m_vRandomPositionMax", "m_vRandomPositionMin",
    "m_flRandomScaleMax", "m_flRandomScaleMin",
    "m_vRandomRotationMax", "m_vRandomRotationMin",
    "m_flScale", "m_vRotation",
    "m_CoordinateSpace", "m_DirectionSpace",
    "m_HandleColor", "m_HandleShape", "m_HandleSize",
    "m_nPickMode", "m_bEnabled", "m_flSpacing",
    "m_ReferenceObjects",
    "CSmartPropRoot", "CSmartPropChoice",
    "CSmartPropVariable_Float", "CSmartPropVariable_Int",
    "CSmartPropVariable_Bool", "CSmartPropVariable_String",
    "CSmartPropVariable_Vector3D", "CSmartPropVariable_Color",
    "CSmartPropVariable_Model",
    "true", "false", "null",
})


class Kv3CodeEditor(QPlainTextEdit):
    """KV3 text editor with line numbers, current-line highlighting and completions."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Line number gutter
        self.line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # Syntax highlighter
        self.highlighter = Kv3SyntaxHighlighter(self.document())

        # Completer
        from PySide6.QtWidgets import QCompleter
        self._completions_model = QStringListModel(self)
        self._completions_model.setStringList(_KV3_COMPLETIONS)
        self._completer = QCompleter(self._completions_model, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.activated.connect(self._insert_completion)

        self.setTabStopDistance(28)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    # ── Completions ───────────────────────────────────────────────────────

    def _trigger_completion(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        prefix = tc.selectedText()
        if prefix and len(prefix) >= 2:
            self._completer.setCompletionPrefix(prefix)
            popup = self._completer.popup()
            popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
            cr = self.cursorRect()
            cr.setWidth(popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width() * 2)
            self._completer.complete(cr)
        else:
            self._completer.popup().hide()

    def _insert_completion(self, completion):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        tc.insertText(completion)

    def keyPressEvent(self, event: QKeyEvent):
        # Let completer handle certain keys when active
        if self._completer.popup().isVisible() and event.key() in (
            Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Tab, Qt.Key_Backtab,
        ):
            event.ignore()
            return

        old_len = self.document().characterCount()
        super().keyPressEvent(event)

        # Auto-indent on Enter
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._auto_indent()

        # Trigger completion after typing
        if event.text().strip() and self.document().characterCount() > old_len:
            self._trigger_completion()
        elif self._completer.popup().isVisible():
            self._completer.popup().hide()

    def _auto_indent(self):
        """Copy leading whitespace from the previous line."""
        tc = self.textCursor()
        block = tc.block().previous()
        if block.isValid():
            text = block.text()
            indent = ''
            for ch in text:
                if ch in (' ', '\t'):
                    indent += ch
                else:
                    break
            # If previous line ends with '{' or '[', add one more tab
            stripped = text.rstrip()
            if stripped.endswith('{') or stripped.endswith('['):
                indent += '\t'
            if indent:
                tc.insertText(indent)

    # ── Line numbers (same as ExpressionEditor) ──────────────────────────

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = max(12, 8 + self.fontMetrics().horizontalAdvance('9') * digits)
        return space

    def update_line_number_area_width(self, _=None):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(29, 29, 31))  # #1d1d1f

        # Right border
        painter.setPen(QColor(54, 54, 57))  # #363639
        painter.drawLine(
            self.line_number_area.width() - 1, event.rect().top(),
            self.line_number_area.width() - 1, event.rect().bottom(),
        )

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        current_line = self.textCursor().blockNumber()

        font = self.font()
        font.setPointSize(max(8, font.pointSize() - 1))
        painter.setFont(font)
        height = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                if block_number == current_line:
                    highlight_rect = QRect(0, int(top), self.line_number_area.width() - 1, height)
                    painter.fillRect(highlight_rect, QColor(65, 73, 86, 80))
                    painter.setPen(QColor(227, 227, 227))   # #E3E3E3
                else:
                    painter.setPen(QColor(157, 157, 157))   # #9D9D9D
                painter.drawText(0, int(top), self.line_number_area.width() - 6, height,
                                 Qt.AlignRight | Qt.AlignVCenter, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        extra = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor(64, 64, 64, 100))
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            extra.append(sel)
        self.setExtraSelections(extra)


# ── Search & Replace Bar ──────────────────────────────────────────────────────

class _SearchReplaceBar(QFrame):
    """Inline search / replace bar shown above the editor."""

    def __init__(self, editor: Kv3CodeEditor, parent=None):
        super().__init__(parent)
        self._editor = editor
        self._last_search = ""
        from src.styles.common import qt_stylesheet_button, qt_stylesheet_lineedit

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        # Search row
        search_row = QHBoxLayout()
        search_row.setSpacing(4)
        search_label = QLabel("Find:")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search…")
        self._search_input.setStyleSheet(qt_stylesheet_lineedit)
        self._search_input.returnPressed.connect(self.find_next)

        self._case_cb = QCheckBox("Aa")
        from src.styles.common import qt_stylesheet_checkbox
        self._case_cb.setStyleSheet(qt_stylesheet_checkbox)
        self._case_cb.setToolTip("Case sensitive")

        self._find_prev_btn = QPushButton("▲")
        self._find_prev_btn.setStyleSheet(qt_stylesheet_button)
        self._find_prev_btn.setFixedWidth(28)
        self._find_prev_btn.setToolTip("Find previous")
        self._find_prev_btn.clicked.connect(self.find_prev)

        self._find_next_btn = QPushButton("▼")
        self._find_next_btn.setStyleSheet(qt_stylesheet_button)
        self._find_next_btn.setFixedWidth(28)
        self._find_next_btn.setToolTip("Find next")
        self._find_next_btn.clicked.connect(self.find_next)

        self._match_label = QLabel("")

        self._close_btn = QPushButton("✕")
        self._close_btn.setStyleSheet(qt_stylesheet_button)
        self._close_btn.setFixedWidth(24)
        self._close_btn.setToolTip("Close  (Esc)")
        self._close_btn.clicked.connect(self.hide)

        for w in (search_label, self._search_input, self._case_cb,
                  self._find_prev_btn, self._find_next_btn, self._match_label, self._close_btn):
            search_row.addWidget(w)
        layout.addLayout(search_row)

        # Replace row
        replace_row = QHBoxLayout()
        replace_row.setSpacing(4)
        replace_label = QLabel("Replace:")
        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("Replace…")
        self._replace_input.setStyleSheet(qt_stylesheet_lineedit)

        self._replace_btn = QPushButton("Replace")
        self._replace_btn.setStyleSheet(qt_stylesheet_button)
        self._replace_btn.clicked.connect(self._replace_one)

        self._replace_all_btn = QPushButton("Replace All")
        self._replace_all_btn.setStyleSheet(qt_stylesheet_button)
        self._replace_all_btn.clicked.connect(self._replace_all)
        
        # Style labels
        for w in (search_label, replace_label, self._match_label):
            w.setStyleSheet("color: #E3E3E3;")

        for w in (replace_label, self._replace_input, self._replace_btn, self._replace_all_btn):
            replace_row.addWidget(w)
        replace_row.addStretch()
        layout.addLayout(replace_row)

        self.hide()

    # ── Public ────────────────────────────────────────────────────────────

    def open_find(self):
        self.show()
        self._search_input.setFocus()
        self._search_input.selectAll()

    def open_replace(self):
        self.show()
        self._replace_input.setFocus()
        self._replace_input.selectAll()

    # ── Search logic ──────────────────────────────────────────────────────

    def _flags(self, backward=False):
        flags = QTextDocument.FindFlags(0)
        if self._case_cb.isChecked():
            from PySide6.QtGui import QTextDocument
            flags |= QTextDocument.FindCaseSensitively
        if backward:
            from PySide6.QtGui import QTextDocument
            flags |= QTextDocument.FindBackward
        return flags

    def find_next(self):
        from PySide6.QtGui import QTextDocument
        text = self._search_input.text()
        if not text:
            return
        flags = QTextDocument.FindFlags(0)
        if self._case_cb.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        found = self._editor.find(text, flags)
        if not found:
            # Wrap around
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self._editor.setTextCursor(cursor)
            found = self._editor.find(text, flags)
        self._update_match_count(text)

    def find_prev(self):
        from PySide6.QtGui import QTextDocument
        text = self._search_input.text()
        if not text:
            return
        flags = QTextDocument.FindBackward
        if self._case_cb.isChecked():
            flags |= QTextDocument.FindCaseSensitively
        found = self._editor.find(text, flags)
        if not found:
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.End)
            self._editor.setTextCursor(cursor)
            found = self._editor.find(text, flags)
        self._update_match_count(text)

    def _update_match_count(self, text):
        content = self._editor.toPlainText()
        if self._case_cb.isChecked():
            count = content.count(text)
        else:
            count = content.lower().count(text.lower())
        self._match_label.setText(f"{count} matches" if count else "No matches")

    # ── Replace logic ─────────────────────────────────────────────────────

    def _replace_one(self):
        tc = self._editor.textCursor()
        if tc.hasSelection():
            tc.insertText(self._replace_input.text())
        self.find_next()

    def _replace_all(self):
        text = self._search_input.text()
        repl = self._replace_input.text()
        if not text:
            return
        content = self._editor.toPlainText()
        if self._case_cb.isChecked():
            new_content = content.replace(text, repl)
        else:
            new_content = re.sub(re.escape(text), repl, content, flags=re.IGNORECASE)
        if new_content != content:
            self._editor.setPlainText(new_content)
        self._update_match_count(text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            self._editor.setFocus()
            return
        super().keyPressEvent(event)


# ── Focus modes ───────────────────────────────────────────────────────────────

FOCUS_HIERARCHY = "Hierarchy Element"
FOCUS_VARIABLES = "Variables"
FOCUS_CHOICES   = "Choices"


# ── Main widget ──────────────────────────────────────────────────────────────

class ManualEditor(QWidget):
    """Raw KV3 text editor for the SmartProp document.

    Parameters
    ----------
    document : SmartPropDocument
        The parent document that owns the hierarchy tree, variables viewport,
        and choices tree.
    """

    # Emitted after the user applies edits so the document can mark itself dirty.
    applied = Signal()

    def __init__(self, document, parent=None):
        super().__init__(parent)
        self._document = document
        self._current_focus = FOCUS_HIERARCHY

        # ── Layout ────────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────────
        toolbar = QFrame()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(6, 3, 6, 3)
        tb_layout.setSpacing(6)

        # Focus selector
        focus_label = QLabel("Focus:")
        tb_layout.addWidget(focus_label)

        self._focus_combo = QComboBox()
        self._focus_combo.addItems([FOCUS_HIERARCHY, FOCUS_VARIABLES, FOCUS_CHOICES])
        self._focus_combo.currentTextChanged.connect(self._on_focus_changed)
        tb_layout.addWidget(self._focus_combo)

        tb_layout.addStretch()

        tb_layout.addStretch()

        # Refresh button
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self.refresh)
        tb_layout.addWidget(self._refresh_btn)

        # Apply button
        self._apply_btn = QPushButton("Apply")
        self._apply_btn.clicked.connect(self._on_apply)
        tb_layout.addWidget(self._apply_btn)

        root.addWidget(toolbar)

        # ── Status label (errors) ─────────────────────────────────────────
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #F44747; border: 0px;")
        self._status_label.setWordWrap(True)
        self._status_label.hide()
        root.addWidget(self._status_label)

        # ── Search/Replace bar ────────────────────────────────────────────
        self._editor = Kv3CodeEditor(self)
        self._search_bar = _SearchReplaceBar(self._editor, self)
        root.addWidget(self._search_bar)

        # ── Code editor ──────────────────────────────────────────────────
        root.addWidget(self._editor)

        # ── Statistics & Search Bar ───────────────────────────────────────────
        bottom_toolbar = QFrame()
        bottom_layout = QHBoxLayout(bottom_toolbar)
        bottom_layout.setContentsMargins(6, 4, 6, 4)
        bottom_layout.setSpacing(6)

        # Search toggle buttons at the bottom
        from src.styles.common import qt_stylesheet_button
        self._search_btn = QPushButton("Find")
        self._search_btn.setToolTip("Find  (Ctrl+F)")
        self._search_btn.setStyleSheet(qt_stylesheet_button)
        self._search_btn.clicked.connect(self._open_find)
        bottom_layout.addWidget(self._search_btn)

        self._replace_btn = QPushButton("Replace")
        self._replace_btn.setToolTip("Replace  (Ctrl+H)")
        self._replace_btn.setStyleSheet(qt_stylesheet_button)
        self._replace_btn.clicked.connect(self._open_replace)
        bottom_layout.addWidget(self._replace_btn)

        bottom_layout.addStretch()

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #9D9D9D; font: 9pt 'Segoe UI';")
        bottom_layout.addWidget(self._stats_label)

        root.addWidget(bottom_toolbar)

        self._editor.textChanged.connect(self._update_stats)
        self._editor.cursorPositionChanged.connect(self._update_stats)
        self._update_stats()

        # Apply the program's standard stylesheets
        from src.styles.common import apply_stylesheets
        apply_stylesheets(self)

    # ── Keyboard shortcuts ────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_F:
                self._open_find()
                return
            elif event.key() == Qt.Key_H:
                self._open_replace()
                return
        super().keyPressEvent(event)

    # ── Public API ────────────────────────────────────────────────────────

    def refresh(self):
        """Re-read the current focus source and populate the editor."""
        self._status_label.hide()
        text = self._serialise_focus()
        self._editor.setPlainText(text)

    def set_focus(self, focus: str):
        """Programmatically change the focus mode."""
        idx = self._focus_combo.findText(focus)
        if idx >= 0:
            self._focus_combo.setCurrentIndex(idx)

    # ── Serialisation helpers ─────────────────────────────────────────────

    def _serialise_focus(self) -> str:
        """Return a KV3-formatted string for the current focus."""
        try:
            if self._current_focus == FOCUS_HIERARCHY:
                return self._serialise_hierarchy()
            elif self._current_focus == FOCUS_VARIABLES:
                return self._serialise_variables()
            elif self._current_focus == FOCUS_CHOICES:
                return self._serialise_choices()
        except Exception as e:
            return f"// Error serialising: {e}"
        return ""

    def _serialise_hierarchy(self) -> str:
        item = self._document.ui.tree_hierarchy_widget.currentItem()
        if item is None:
            return "// No hierarchy element selected"
        from src.editors.smartprop_editor.vsmart import serialization_hierarchy_items
        data = serialization_hierarchy_items(item)
        return JsonToKv3(data)

    def _serialise_variables(self) -> str:
        layout = self._document.variable_viewport.ui.variables_scrollArea
        variables = []
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and hasattr(widget, 'name') and hasattr(widget, 'var_class'):
                from src.editors.smartprop_editor.objects import variable_prefix
                var_dict = {
                    "_class": variable_prefix + widget.var_class,
                    "m_VariableName": widget.name,
                    "m_bExposeAsParameter": widget.var_visible_in_editor,
                    "m_DefaultValue": widget.var_value.get('default', ''),
                }
                if widget.var_value.get('m_nElementID') is not None:
                    var_dict["m_nElementID"] = widget.var_value['m_nElementID']
                if widget.var_display_name:
                    var_dict["m_DisplayName"] = widget.var_display_name
                if widget.var_value.get('min') is not None:
                    var_dict["m_flParamaterMinValue"] = widget.var_value['min']
                if widget.var_value.get('max') is not None:
                    var_dict["m_flParamaterMaxValue"] = widget.var_value['max']
                if widget.var_value.get('model') is not None:
                    var_dict["m_sModelName"] = widget.var_value['model']
                if widget.var_value.get('m_HideExpression') is not None:
                    var_dict["m_HideExpression"] = widget.var_value['m_HideExpression']
                if widget.var_value.get('m_ReadOnlyExpression') is not None:
                    var_dict["m_ReadOnlyExpression"] = widget.var_value['m_ReadOnlyExpression']
                variables.append(var_dict)

        data = {"m_Variables": variables}
        return JsonToKv3(data)

    def _serialise_choices(self) -> str:
        state = self._document._snapshot_choices()
        if not state:
            return "// No choices defined"
        # Build full KV3-compatible structure
        from src.widgets.element_id import set_ElementID
        choices = []
        for ch in state:
            options = []
            for opt in ch.get('options', []):
                var_vals = []
                for v in opt.get('variables', []):
                    var_vals.append({
                        "m_TargetName": v['name'],
                        "m_DataType": v['type'],
                        "m_Value": v['value'],
                    })
                options.append({
                    "m_Name": opt['name'],
                    "m_VariableValues": var_vals,
                })
            choices.append({
                "_class": "CSmartPropChoice",
                "m_Name": ch['name'],
                "m_DefaultOption": ch['default'],
                "m_Options": options,
            })
        return JsonToKv3({"m_Choices": choices})

    # ── Apply (write back) ────────────────────────────────────────────────

    def _on_apply(self):
        """Parse editor text and apply changes back to the document."""
        text = self._editor.toPlainText()
        try:
            if self._current_focus == FOCUS_HIERARCHY:
                self._apply_hierarchy(text)
            elif self._current_focus == FOCUS_VARIABLES:
                self._apply_variables(text)
            elif self._current_focus == FOCUS_CHOICES:
                self._apply_choices(text)
            self._status_label.hide()
            self.applied.emit()
        except Exception as e:
            self._status_label.setText(f"Apply failed: {e}")
            self._status_label.show()

    def _apply_hierarchy_internal(self, item, text):
        from src.common import Kv3ToJson
        from src.editors.smartprop_editor.vsmart import deserialize_hierarchy_item
        from src.common import fast_deepcopy

        text = self._fix_format(text)
        obj = Kv3ToJson(text)
        children = obj.get("m_Children", [])
        if not children:
            raise ValueError("No element data found in text")

        element_data = children[0]
        child_data_list = element_data.pop("m_Children", None)

        label = element_data.get("m_sLabel", item.text(0))
        item.setText(0, label)
        element_data.pop("m_sLabel", None)

        item.setData(0, Qt.UserRole, element_data)

        if child_data_list is not None:
            while item.childCount() > 0:
                item.takeChild(0)
            for child_dict in child_data_list:
                child_item = deserialize_hierarchy_item(
                    child_dict, self._document.element_id_generator
                )
                item.addChild(child_item)

        self._document.on_tree_current_item_changed(item, None)

    def _apply_hierarchy(self, text):
        item = self._document.ui.tree_hierarchy_widget.currentItem()
        if item is None:
            raise ValueError("No hierarchy element selected")

        old_text = self._serialise_hierarchy()
        self._apply_hierarchy_internal(item, text)

        from PySide6.QtGui import QUndoCommand
        class ManualHierarchyEditCommand(QUndoCommand):
            def __init__(self, doc, tr_item, o_text, n_text):
                super().__init__("Manual Edit Hierarchy")
                self.document = doc
                self.item = tr_item
                self.old_text = o_text
                self.new_text = n_text
                self._first_redo = True

            def redo(self):
                if self._first_redo:
                    self._first_redo = False
                    return
                # Verify item still exists in tree
                if self.item.treeWidget() is not None:
                    self.document._manual_editor._apply_hierarchy_internal(self.item, self.new_text)

            def undo(self):
                if self.item.treeWidget() is not None:
                    self.document._manual_editor._apply_hierarchy_internal(self.item, self.old_text)

        cmd = ManualHierarchyEditCommand(self._document, item, old_text, text)
        self._document.undo_stack.push(cmd)

    def _apply_variables(self, text):
        from src.common import Kv3ToJson
        text = self._fix_format(text)
        obj = Kv3ToJson(text)
        variables = obj.get("m_Variables", [])

        state = []
        for v in variables:
            cls = v.get("_class", "")
            if cls.startswith("CSmartPropVariable_"):
                var_class = cls.replace("CSmartPropVariable_", "")
            else:
                var_class = cls

            var_value = {
                'default': v.get('m_DefaultValue'),
                'min': v.get('m_flParamaterMinValue'),
                'max': v.get('m_flParamaterMaxValue'),
                'model': v.get('m_sModelName'),
                'm_nElementID': v.get('m_nElementID'),
                'm_HideExpression': v.get('m_HideExpression'),
                'm_ReadOnlyExpression': v.get('m_ReadOnlyExpression'),
            }
            # Commentary can be in m_sCommentary, m_DisplayName, or m_ParameterName
            display_name = v.get('m_sCommentary')
            if display_name is None:
                display_name = v.get('m_DisplayName')
            if display_name is None:
                display_name = v.get('m_ParameterName')

            state.append({
                'name': v.get('m_VariableName', ''),
                'var_class': var_class,
                'var_value': var_value,
                'var_visible_in_editor': v.get('m_bExposeAsParameter', False),
                'var_display_name': display_name,
                'expanded': False,
            })
            
        old_state = self._document._snapshot_variables()
        self._document._restore_variables(state)
        
        from src.editors.smartprop_editor.commands import VariablesSnapshotCommand
        cmd = VariablesSnapshotCommand(self._document, old_state, state, "Manual Edit Variables")
        self._document.undo_stack.push(cmd)

    def _apply_choices(self, text):
        from src.common import Kv3ToJson
        text = self._fix_format(text)
        obj = Kv3ToJson(text)
        choices_list = obj.get("m_Choices", [])

        state = []
        for ch in choices_list:
            options = []
            for opt in ch.get("m_Options", []):
                variables = []
                for var in opt.get("m_VariableValues", []):
                    variables.append({
                        'name': var.get('m_TargetName', ''),
                        'type': var.get('m_DataType', ''),
                        'value': var.get('m_Value', ''),
                    })
                options.append({
                    'name': opt.get('m_Name', ''),
                    'expanded': False,
                    'variables': variables,
                })
            state.append({
                'name': ch.get('m_Name', ''),
                'default': ch.get('m_DefaultOption', ''),
                'expanded': False,
                'options': options,
            })
            
        old_state = self._document._snapshot_choices()
        self._document._restore_choices(state)
        
        from src.editors.smartprop_editor.commands import ChoicesSnapshotCommand
        cmd = ChoicesSnapshotCommand(self._document, old_state, state, "Manual Edit Choices")
        self._document.undo_stack.push(cmd)

    # ── Internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _fix_format(text):
        """Normalise KV3 text before parsing (mirrors VsmartOpen.fix_format)."""
        text = re.sub(r"= resource_name:", "= ", text)
        text = text.replace("null,", "")
        return text

    def _on_focus_changed(self, text):
        self._current_focus = text
        self.refresh()

    def _open_find(self):
        self._search_bar.open_find()

    def _open_replace(self):
        self._search_bar.open_replace()

    def _update_stats(self):
        """Update the statistics bar with line/word/key counts and cursor position."""
        text = self._editor.toPlainText()
        lines = text.count('\n') + (1 if text else 0)
        chars = len(text)

        # Count KV3 keys (word followed by ' = ')
        keys = len(re.findall(r'\b\w+\s*=', text))

        # Cursor position
        tc = self._editor.textCursor()
        ln = tc.blockNumber() + 1
        col = tc.columnNumber() + 1

        self._stats_label.setText(
            f"  Ln {ln}, Col {col}   |   Lines: {lines}   Characters: {chars}   Keys: {keys}"
        )
