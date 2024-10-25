import sys
import re  # For regex search functionality
from PySide6.QtWidgets import QDialog, QApplication, QMessageBox
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

    def on_accepted(self):
        # Fetch user inputs from the dialog
        text_to_find = self.ui.find_text_lineEdit.text()
        replace_with = self.ui.replace_with_lineEdit.text()
        use_regex = self.ui.regex_checkBox.isChecked()
        match_case = self.ui.match_case_checkBox.isChecked()
        whole_words = self.ui.whole_words_checkBox.isChecked()
        search_backwards = self.ui.serach_backward_checkBox.isChecked()
        search_from_start = self.ui.search_from_start_checkBox.isChecked()

        if not text_to_find:
            QMessageBox.warning(self, "Find and Replace", "Please enter text to find.")
            return

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
                QMessageBox.critical(self, "Find and Replace", "Invalid regular expression.")
        else:
            # Plain text search and replace
            if not match_case:
                text_content_lower = text_content.lower()
                text_to_find = text_to_find.lower()
            else:
                text_content_lower = text_content

            count = text_content_lower.count(text_to_find)
            if count > 0:
                new_content = text_content.replace(text_to_find,
                                                   replace_with) if match_case else text_content_lower.replace(
                    text_to_find, replace_with)
                self.ui.viewport_QplainText.setPlainText(new_content)
                QMessageBox.information(self, "Find and Replace", f"{count} occurrences replaced.")
            else:
                QMessageBox.information(self, "Find and Replace", "No matches found.")

        self.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = FindAndReplaceDialog()
    dialog.exec()
    sys.exit(app.exec())
