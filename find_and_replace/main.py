import sys
import re  # For regex search functionality
from PySide6.QtWidgets import QDialog, QApplication, QMessageBox
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import QRegularExpression as QRegExp, Qt
import regex

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
        highlighted_text = self.text_highlighter(text_content, text_to_find, replace_with, use_regex, match_case, whole_words)

        # Update the text editor with the highlighted text
        # self.ui.viewport_QplainText.setPlainText(highlighted_text)

        # Print the highlighted text after replacement
        print("Result after replacement:")
        print(highlighted_text[1])

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
        highlighted_text = self.text_highlighter(text_content, text_to_find, '', use_regex, match_case, whole_words)
        print(highlighted_text[1])
        # Update the text editor with the highlighted text
        # self.ui.viewport_QplainText.setPlainText(highlighted_text)

    def text_highlighter(self, text_content, text_to_find, replace_with, use_regex, match_case, whole_words):
        cursor = self.ui.viewport_QplainText.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())  # Reset character format to default
        highlighted_text = text_content

        if text_to_find:
            if use_regex:
                # Implement regex search and highlight
                pattern = QRegExp(text_to_find)
                pattern.setPatternOptions(QRegExp.CaseInsensitiveOption if not match_case else QRegExp.NoPatternOption)
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
        replaced_text = text_content.replace(text_to_find, replace_with)

        return highlighted_text, replaced_text
    def text_replacer(self, text_content):
        pass
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = FindAndReplaceDialog()
    dialog.exec()
    sys.exit(app.exec())