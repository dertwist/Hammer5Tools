from PySide6.QtCore import Qt, QStringListModel, QCommandLineParser, QCommandLineOption
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QApplication, QLineEdit, QSizePolicy
from PySide6.QtGui import QKeyEvent, QTextCursor, QTextOption

# test = QLineEdit()
# test.cursorPosition()
class CompletingPlainTextEdit(QPlainTextEdit):
    completion_tail: str = " "
    ignore_return: bool = False


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.completions = QStringListModel(self)
        self.completer = QCompleter(self.completions, self)
        self.completer.setWidget(self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.activated.connect(self.insert_completion)
        self.setWordWrapMode(QTextOption.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred))

        self.setStyleSheet("""QPlainTextEdit {

            font: 580 10pt "Segoe UI";
            border: 2px solid black;
            border-radius: 0px;
            border-color: rgba(80, 80, 80, 255);
        	border:none;
            height:18px;
            padding: 0px;
            padding-left: 0px;
            padding-right: 0px;
            color: #E3E3E3;
            background-color: #1C1C1C;
        }

        QPlainTextEdit:pressed {
        }""")


    def complete(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        selected_text = tc.selectedText()
        if selected_text:
            self.completer.setCompletionPrefix(selected_text)

            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
            cr = self.cursorRect()
            cr.setWidth(popup.sizeHintForColumn(0) +
                        popup.verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

    def insert_completion(self, completion):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        tc.insertText(completion + self.completion_tail)

    def keyPressEvent(self, event: QKeyEvent) -> None:

        if event.key() == Qt.Key_Return:
            event.ignore()
            return

        if self.completer.popup().isVisible() and event.key() in [
            Qt.Key_Up,
            Qt.Key_Down,
            # Accept completion
            Qt.Key_Return,
            Qt.Key_Tab,
            Qt.Key_Backtab,
        ]:
            event.ignore()
            return

        if event.key() == Qt.Key_Tab or event.key() == Qt.Key_Backtab:
            event.ignore()
            return

        old_len = self.document().characterCount()
        super().keyPressEvent(event)
        if event.text().strip() and self.document().characterCount() > old_len:
            self.complete()
        elif self.completer.popup().isVisible():
            self.completer.popup().hide()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    parser = QCommandLineParser()
    parser.addHelpOption()
    tail = QCommandLineOption(["tail"],"Insert <str> after each completion instead of a blank space")
    tail.setValueName("str")
    tail.setDefaultValue(' ')
    parser.addOption(tail)

    parser.process(app)
    args = parser.positionalArguments()
    # if not args:
    #     print("Usage: {} <completion> ...".format(sys.argv[0]))
    #     sys.exit(0)

    te = CompletingPlainTextEdit()
    te.completions.setStringList(['args', 'fd'])
    te.completion_tail = parser.value(tail)
    te.show()
    sys.exit(app.exec())