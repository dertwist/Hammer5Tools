import sys
import re  # For regex search functionality
from PySide6.QtWidgets import QDialog, QApplication, QMessageBox, QInputDialog
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor


from find_and_replace.ui_main import Ui_Dialog


class FindAndReplaceDialog(QDialog):
    def __init__(self, parent=None, data='Test text, 12 - 23, regex, find next'):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.data = data
        self.ui.viewport_QplainText.setPlainText(self.data)
        self.ui.match_case_checkBox.setChecked(True)

        self.ui.buttonBox.accepted.connect(self.on_accepted)
        self.ui.buttonBox.rejected.connect(self.reject)

        self.ui.find_text_lineEdit.textChanged.connect(self.on_text_changed)


        # Checkboxes
        self.ui.match_case_checkBox.stateChanged.connect(self.on_match_case_changed)
        self.ui.whole_words_checkBox.stateChanged.connect(self.on_whole_words_changed)



    def on_match_case_changed(self, state):
        self.update_highlight()



    def on_whole_words_changed(self, state):
        self.update_highlight()

    def on_text_changed(self):
        self.update_highlight()

    def update_highlight(self):
        text_to_find = self.ui.find_text_lineEdit.text()
        match_case = self.ui.match_case_checkBox.isChecked()
        whole_words = self.ui.whole_words_checkBox.isChecked()
        text_content = self.ui.viewport_QplainText.toPlainText()

        # Clear previous highlights
        cursor = self.ui.viewport_QplainText.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())  # Reset character format

        # Apply new highlights
        if text_to_find:
            self.text_highlighter(text_content, text_to_find, match_case, whole_words)

    def text_highlighter(self, text_content, text_to_find, match_case, whole_words):
        cursor = self.ui.viewport_QplainText.textCursor()
        format = QTextCharFormat()
        format.setBackground(QColor("#414956"))

        # Determine regex flags
        flags = 0
        if not match_case:
            flags |= re.IGNORECASE

        # Adjust pattern for whole word matching
        if whole_words:
            text_to_find = r'\b' + re.escape(text_to_find) + r'\b'
        else:
            text_to_find = re.escape(text_to_find)

        # Compile regex pattern
        pattern = re.compile(text_to_find, flags)

        # Find all matches and apply highlight
        for match in pattern.finditer(text_content):
            start, end = match.span()
            word = match.group()

            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(format)

    def on_accepted(self):
        text_to_find = self.ui.find_text_lineEdit.text()
        replace_with = self.ui.replace_with_lineEdit.text()
        match_case = self.ui.match_case_checkBox.isChecked()
        whole_words = self.ui.whole_words_checkBox.isChecked()

        text_content = self.ui.viewport_QplainText.toPlainText()
        replaced_text = self.text_replacer(text_content, text_to_find, replace_with, match_case, whole_words)
        self.ui.viewport_QplainText.setPlainText(replaced_text)  # Display updated text
        print("Result after replacement:", replaced_text)

    def text_replacer(self, text_content, text_to_find, replace_with, match_case, whole_words):
        flags = 0
        if not match_case:
            flags |= re.IGNORECASE

        if whole_words:
            text_to_find = r'\b' + re.escape(text_to_find) + r'\b'
        else:
            text_to_find = re.escape(text_to_find)

        pattern = re.compile(text_to_find, flags)
        replaced_text = pattern.sub(lambda m: replace_with, text_content)

        return replaced_text


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = FindAndReplaceDialog()
    import qtvscodestyle as qtvsc

    stylesheet = qtvsc.load_stylesheet(qtvsc.Theme.DARK_VS)
    app.setStyleSheet(stylesheet)
    # app.setStyle('fusion')
    dialog.exec()
    sys.exit(app.exec())
