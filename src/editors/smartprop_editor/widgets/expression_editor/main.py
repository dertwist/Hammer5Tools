from PySide6.QtWidgets import QToolButton, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel, QSplitter, QListWidget, QListWidgetItem, QFrame, QWidget
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QIcon, QFont, QPainter, QColor, QTextFormat, QSyntaxHighlighter, QTextCharFormat, QFontMetrics
from src.widgets.completer.main import CompletingPlainTextEdit
from src.editors.smartprop_editor.completion_utils import CompletionUtils
from src.editors.smartprop_editor.objects import expression_completer
from src.styles.common import *
import re


class ExpressionSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None, variables_info=None):
        super().__init__(parent)
        self.variables_info = variables_info or {}
        self.highlighting_rules = []

        # Define colors for different elements - matching project color scheme
        keyword_color = QColor(86, 156, 214)  # Blue for keywords
        operator_color = QColor(227, 227, 227)  # Light gray for operators (matching #E3E3E3)
        number_color = QColor(181, 206, 168)  # Light green for numbers
        function_color = QColor(220, 220, 170)  # Yellow for functions
        comment_color = QColor(109, 109, 109)  # Desaturated gray for comments (matching #6D6D6D)

        # Type-specific colors for variables
        bool_color = QColor(86, 156, 214)  # Blue for bool
        vector3d_color = QColor(255, 140, 0)  # Orange for vector3d
        float_color = QColor(181, 206, 168)  # Light green for float
        int_color = QColor(255, 215, 0)  # Gold for int
        default_var_color = QColor(156, 220, 254)  # Light blue for other variables

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(keyword_color)
        keyword_format.setFontWeight(QFont.Bold)
        keywords = ["true", "false"]
        for keyword in keywords:
            self.highlighting_rules.append((re.compile(f"\\b{keyword}\\b"), keyword_format))

        # Operators
        operator_format = QTextCharFormat()
        operator_format.setForeground(operator_color)
        operator_format.setFontWeight(QFont.Bold)
        operators = ["\\+", "-", "\\*", "/", "%", "==", "!=", "<=", ">=", "<", ">", "&&", "\\|\\|", "!", "\\?", ":", "\\(", "\\)", "\\[", "\\]"]
        for op in operators:
            self.highlighting_rules.append((re.compile(op), operator_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(number_color)
        self.highlighting_rules.append((re.compile(r"\b\d+\.?\d*\b"), number_format))

        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(function_color)
        self.highlighting_rules.append((re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*(?=\()"), function_format))

        # Comments (// style) - Store separately to apply last
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(comment_color)
        self.comment_format.setFontItalic(True)
        self.comment_pattern = re.compile(r"//.*$", re.MULTILINE)

        # Variables with type-specific colors
        self.variable_formats = {
            'bool': self._create_format(bool_color),
            'vector3d': self._create_format(vector3d_color),
            'float': self._create_format(float_color),
            'int': self._create_format(int_color),
            'default': self._create_format(default_var_color)
        }

    def _create_format(self, color):
        format = QTextCharFormat()
        format.setForeground(color)
        return format

    def highlightBlock(self, text):
        # Apply general highlighting rules first
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - match.start()
                self.setFormat(start, length, format)

        # Apply variable-specific highlighting
        variable_pattern = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b(?!\()")
        for match in variable_pattern.finditer(text):
            var_name = match.group()
            var_type = self.variables_info.get(var_name, 'default')
            format = self.variable_formats.get(var_type, self.variable_formats['default'])
            start = match.start()
            length = match.end() - match.start()
            self.setFormat(start, length, format)

        # Apply comment highlighting LAST to override all other formatting
        # This ensures ALL characters in comment lines are gray
        for match in self.comment_pattern.finditer(text):
            start = match.start()
            length = match.end() - match.start()
            self.setFormat(start, length, self.comment_format)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(CompletingPlainTextEdit):
    def __init__(self, variables_info=None):
        super().__init__()

        self.variables_info = variables_info or {}
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # Set up syntax highlighter with variable type information
        self.highlighter = ExpressionSyntaxHighlighter(self.document(), variables_info)

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1

        # Ensure minimum width and add padding for better appearance
        space = max(12, 8 + self.fontMetrics().horizontalAdvance('9') * digits)
        return space

    def update_line_number_area_width(self, new_block_count):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)

        # Fill background with darker color matching project theme
        painter.fillRect(event.rect(), QColor(29, 29, 31))  # #1d1d1f - project secondary background

        # Draw a subtle border on the right side
        painter.setPen(QColor(54, 54, 57))  # #363639 - project stroke color
        painter.drawLine(self.line_number_area.width() - 1, event.rect().top(),
                        self.line_number_area.width() - 1, event.rect().bottom())

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Get current line for highlighting
        current_line = self.textCursor().blockNumber()

        # Set up font for line numbers
        font = self.font()
        font.setPointSize(max(8, font.pointSize() - 1))  # Slightly smaller than editor font
        painter.setFont(font)

        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(block_number + 1)

                # Highlight current line number
                if block_number == current_line:
                    # Highlight background for current line
                    highlight_rect = QRect(0, int(top), self.line_number_area.width() - 1, height)
                    painter.fillRect(highlight_rect, QColor(65, 73, 86, 80))  # #414956 with transparency

                    # Use brighter color for current line number
                    painter.setPen(QColor(227, 227, 227))  # #E3E3E3 - project primary text
                else:
                    # Use muted color for other line numbers
                    painter.setPen(QColor(157, 157, 157))  # #9D9D9D - project neutral text

                # Draw line number with right alignment and padding
                painter.drawText(0, int(top), self.line_number_area.width() - 6, height,
                               Qt.AlignRight | Qt.AlignVCenter, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()

            line_color = QColor(64, 64, 64, 100)  # Semi-transparent gray
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)


class ExpressionEditor(QToolButton):
    def __init__(self, target_text_field, variables_scrollArea):
        super().__init__()
        self.setIcon(QIcon(":/icons/edit_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        self.setToolTip("Open expression editor")
        self.setFixedSize(QSize(24, 24))
        self.clicked.connect(lambda: self.open_expression_editor(target_text_field))
        self.variables_scrollArea = variables_scrollArea

    def _get_variables_with_types(self):
        """Extract variable names and their types from the variables scroll area."""
        variables_info = {}
        try:
            # Iterate through all widgets in the scroll area to find variable types
            scroll_widget = self.variables_scrollArea.widget()
            if scroll_widget:
                for i in range(scroll_widget.layout().count()):
                    item = scroll_widget.layout().itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        # Check if widget has a name_label and determine type
                        if hasattr(widget, 'name_label'):
                            var_name = widget.name_label.text()
                            # Determine type based on widget class name
                            widget_class = widget.__class__.__name__.lower()
                            if 'bool' in widget_class:
                                variables_info[var_name] = 'bool'
                            elif 'vector3d' in widget_class:
                                variables_info[var_name] = 'vector3d'
                            elif 'float' in widget_class:
                                variables_info[var_name] = 'float'
                            elif 'int' in widget_class:
                                variables_info[var_name] = 'int'
                            else:
                                variables_info[var_name] = 'unknown'
        except Exception:
            pass
        return variables_info

    def open_expression_editor(self, target_text_edit):
        dialog = QDialog(self)
        dialog.setWindowTitle("Expression Editor")
        dialog.setMinimumSize(750, 550)
        dialog.resize(900, 650)



        # Main layout
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Create splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #404040;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #505050;
            }
        """)
        main_layout.addWidget(splitter)

        # Left panel - Variables and functions
        left_panel = QFrame()
        left_panel.setMaximumWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        # Variables section
        variables_label = QLabel("Available Variables:")
        variables_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        variables_label.setStyleSheet("""
            QLabel {
                color: #E3E3E3;
                # padding: 4px;
                # background-color: #2D2D2D;
                # border: 1px solid #404040;
                # border-radius: 3px;
            }
        """)
        left_layout.addWidget(variables_label)

        variables_list = QListWidget()

        # Gather variable type information and populate variables list
        variables_info = {}
        try:
            available_vars = CompletionUtils.get_available_variable_names(self.variables_scrollArea)
            variables_with_types = self._get_variables_with_types()

            for var_name in available_vars:
                var_type = variables_with_types.get(var_name, 'unknown')
                variables_info[var_name] = var_type

                # Create colored item based on type
                item = QListWidgetItem(var_name)
                tooltip = f"Variable: {var_name}"
                if var_type != 'unknown':
                    tooltip += f" (Type: {var_type})"

                # Add type-specific styling hints
                if var_type == 'bool':
                    tooltip += " - Boolean value (true/false)"
                elif var_type == 'vector3d':
                    tooltip += " - 3D vector (x, y, z coordinates)"
                elif var_type == 'float':
                    tooltip += " - Floating point number"
                elif var_type == 'int':
                    tooltip += " - Integer number"

                item.setToolTip(tooltip)
                variables_list.addItem(item)
        except:
            pass

        left_layout.addWidget(variables_list)

        # Functions/operators section
        functions_label = QLabel("Functions & Operators:")
        functions_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        functions_label.setStyleSheet(variables_label.styleSheet())
        left_layout.addWidget(functions_label)

        functions_list = QListWidget()
        functions_list.setStyleSheet(variables_list.styleSheet())

        # Add common functions and operators with ternary support
        common_functions = [
            # Conditional operators
            "condition ? value_if_true : value_if_false",
            "== (equals)", "!= (not equals)", "< (less than)", "> (greater than)",
            "<= (less or equal)", ">= (greater or equal)", "&& (and)", "|| (or)",
            "! (not)",
            # Arithmetic
            "+ (add)", "- (subtract)", "* (multiply)", "/ (divide)", "% (modulo)",
            # Math functions
            "abs(x)", "min(x, y)", "max(x, y)", "clamp(x, min, max)",
            "lerp(a, b, t)", "sin(x)", "cos(x)", "tan(x)", "sqrt(x)", "pow(x, y)",
            "floor(x)", "ceil(x)", "round(x)",
            # Constants
            "true", "false"
        ]

        # Add expression_completer functions from objects.py
        for expr in expression_completer:
            common_functions.append(expr)

        for func in common_functions:
            item = QListWidgetItem(func)
            if "?" in func:
                item.setToolTip("Ternary operator: condition ? value_if_true : value_if_false")
            elif "(" in func and ")" in func:
                item.setToolTip(f"Function: {func}")
            else:
                item.setToolTip(f"Operator: {func}")
            functions_list.addItem(item)

        left_layout.addWidget(functions_list)

        # Examples section
        examples_label = QLabel("Common Patterns:")
        examples_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        examples_label.setStyleSheet(variables_label.styleSheet())
        left_layout.addWidget(examples_label)

        examples_list = QListWidget()
        examples_list.setStyleSheet(variables_list.styleSheet())

        # Add example patterns
        example_patterns = [
            "(var == 1) ? 16 : 0",
            "(var >= 2 && var <= 3) ? 23 : 0",
            "(var >= 4 && var <= 6) ? 15 : 0",
            "abs(var - 5)",
            "min(var1, var2)",
            "max(0, var - 10)",
            "clamp(var, 0, 100)",
            "var * 2 + 5"
        ]

        for pattern in example_patterns:
            item = QListWidgetItem(pattern)
            item.setToolTip(f"Example pattern: {pattern}")
            examples_list.addItem(item)

        left_layout.addWidget(examples_list)

        splitter.addWidget(left_panel)

        # Right panel - Editor
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #404040;
                border-radius: 4px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        # Create the code editor with line numbers and syntax highlighting
        editor = CodeEditor(variables_info)

        # Set up completer with expression_completer functions included
        completions = CompletionUtils.generate_type_aware_completions(
            self.variables_scrollArea,
        )
        # Ensure expression_completer items are included
        completions.extend(expression_completer)
        # Remove duplicates and sort
        completions = sorted(list(set(completions)))
        editor.completions.setStringList(completions)

        editor.setPlainText(target_text_edit.toPlainText())
        right_layout.addWidget(editor)

        # Help text with comment support and enhanced tips
        help_text = """Tips:
• Double-click items from the left panel to insert them
• Use // for comments (e.g., // This is a comment)
• Variables are color-coded by type: Bool (blue), Vector3D (orange), Float (green), Int (gold)
• Use ternary operators: (condition) ? value_if_true : value_if_false
• Example: (block_type == 1) ? 16 : ((block_type >= 2 && block_type <= 3) ? 23 : 0)
• Chain multiple conditions for complex logic
• Available functions: InstanceIndex(), InstanceCount(), LinearScale(), RandomInt(), RandomFloat(), etc."""
        
        help_label = QLabel(help_text)
        help_label.setMaximumHeight(120)
        help_label.setStyleSheet("""
            QLabel {
                color: #CCCCCC; 
                font-size: 8pt; 
                padding: 8px;
                background-color: #2D2D2D;
                border: 1px solid #404040;
                border-radius: 3px;
                line-height: 1.4;
            }
        """)
        help_label.setWordWrap(True)
        right_layout.addWidget(help_label)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([380, 920])

        # Button layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(qt_stylesheet_button)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(qt_stylesheet_button)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

        # Event handlers
        def insert_text(item):
            text = item.text()
            # Extract just the function/operator part before any description
            if " (" in text:
                text = text.split(" (")[0]
            cursor = editor.textCursor()
            cursor.insertText(text)
            editor.setFocus()

        def save():
            target_text_edit.setPlainText(editor.toPlainText())
            dialog.accept()

        def cancel():
            dialog.reject()

        # Connect signals
        variables_list.itemDoubleClicked.connect(insert_text)
        functions_list.itemDoubleClicked.connect(insert_text)
        examples_list.itemDoubleClicked.connect(insert_text)
        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(cancel)

        # Set focus to editor
        editor.setFocus()

        dialog.exec()