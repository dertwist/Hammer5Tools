import sys
import re  # For regex search functionality
from PySide6.QtWidgets import QDialog, QApplication, QMessageBox
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import QRegularExpression as QRegExp, Qt
from find_and_replace.ui_main import Ui_Dialog  # Assuming the UI file is called ui_main.py

class FindAndReplaceDialog(QDialog):
    def __init__(self, parent=None, data='Test text, 123, regex, find next'):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # Set initial data in the text box
        self.data = data
        self.ui.viewport_QplainText.setPlainText(self.data)
        self.ui.match_case_checkBox.setChecked(True)

        # Connect buttons to functions
        self.ui.buttonBox.accepted.connect(self.on_accepted)
        self.ui.buttonBox.rejected.connect(self.reject)

        self.ui.find_text_lineEdit.textChanged.connect(self.on_text_changed)

    def on_accepted(self):
        # Fetch user inputs from the dialog
        text_to_find = self.ui.find_text_lineEdit.text()
        replace_with = self.ui.replace_with_lineEdit.text()
        use_regex = self.ui.regex_checkBox.isChecked()
        match_case = self.ui.match_case_checkBox.isChecked()
        whole_words = self.ui.whole_words_checkBox.isChecked()

        # Get the content from the text editor
        text_content = self.ui.viewport_QplainText.toPlainText()

        # Perform search and replace
        if use_regex:
            # Regex search and replace
            flags = 0
            if not match_case:
                flags |= re.IGNORECASE

            # Handle whole word search using word boundaries (\b)
            if whole_words:
                text_to_find = r'\b' + text_to_find + r'\b'

            try:
                # Compile the regex pattern
                pattern = re.compile(text_to_find, flags)

                # Replace globally or selectively based on user's input
                new_content, count = pattern.subn(replace_with, text_content)
                if count > 0:
                    self.ui.viewport_QplainText.setPlainText(new_content)
                    QMessageBox.information(self, "Find and Replace", f"{count} occurrences replaced.")
                else:
                    QMessageBox.information(self, "Find and Replace", "No matches found.")
            except re.error:
                QMessageBox.critical(self, "Find and Replace", "Invalid regular expression")
        else:
            # Plain text search and replace
            if not match_case:
                text_content_lower = text_content.lower()
                text_to_find = text_to_find.lower()
            else:
                text_content_lower = text_content

            count = text_content_lower.count(text_to_find)
            if count > 0:
                new_content = text_content.replace(text_to_find, replace_with) if match_case else text_content_lower.replace(text_to_find, replace_with)
                self.ui.viewport_QplainText.setPlainText(new_content)
                QMessageBox.information(self, "Find and Replace", f"{count} occurrences replaced.\n{new_content}")
            else:
                QMessageBox.information(self, "Find and Replace", "No matches found.")

        self.accept()

    def on_text_changed(self):
        # Fetch user inputs from the dialog
        text_to_find = self.ui.find_text_lineEdit.text()
        use_regex = self.ui.regex_checkBox.isChecked()
        match_case = self.ui.match_case_checkBox.isChecked()
        whole_words = self.ui.whole_words_checkBox.isChecked()

        # Get the content from the text editor
        text_content = self.ui.viewport_QplainText.toPlainText()

        # Highlight the found text based on the search criteria
        highlighted_text = self.highlight_text(text_content, text_to_find, use_regex, match_case, whole_words)

        # Update the text editor with the highlighted text
        # self.ui.viewport_QplainText.setPlainText(highlighted_text)

    def highlight_text(self, text_content, text_to_find, use_regex, match_case, whole_words):
        # Assuming self.ui.viewport_QplainText is the QTextEdit widget where you want to clear the character format
        cursor = self.ui.viewport_QplainText.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())  # Reset character format to default
        highlighted_text = text_content
        if text_to_find:
            if use_regex:
                # Implement regex search and highlight
                pattern = QRegExp(text_to_find)
                pattern.setCaseSensitivity(Qt.CaseInsensitive if not match_case else Qt.CaseSensitive)
                pattern.setPatternSyntax(QRegExp.RegExp2)  # Adjust pattern syntax as needed

                cursor = self.ui.viewport_QplainText.textCursor()
                format = QTextCharFormat()
                format.setBackground(QColor("yellow"))

                pos = 0
                index = pattern.indexIn(text_content, pos)
                while index != -1:
                    cursor.setPosition(index)
                    cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
                    cursor.mergeCharFormat(format)
                    pos = index + pattern.matchedLength()
                    index = pattern.indexIn(text_content, pos)

                highlighted_text = self.ui.viewport_QplainText.toPlainText()
            else:
                # Perform plain text search and highlight
                cursor = self.ui.viewport_QplainText.textCursor()
                format = QTextCharFormat()
                format.setBackground(QColor("yellow"))

                pos = 0
                while pos >= 0:
                    pos = text_content.find(text_to_find, pos)
                    if pos < 0:
                        break

                    cursor.setPosition(pos)
                    cursor.movePosition(QTextCursor.EndOfWord, QTextCursor.KeepAnchor)
                    cursor.mergeCharFormat(format)
                    pos += len(text_to_find)

                highlighted_text = self.ui.viewport_QplainText.toPlainText()
        return highlighted_text

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = FindAndReplaceDialog()
    dialog.exec()
    sys.exit(app.exec())