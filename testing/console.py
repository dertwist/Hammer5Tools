import sys
from PySide6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QMessageBox
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtCore import QObject, Signal

import jtextfsm as textfsm

class Stream(QObject):
    newText = Signal(str)

    def write(self, text):
        self.newText.emit(str(text))

class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        self.setGeometry(50, 50, 500, 300)
        self.setWindowTitle("PyQT tuts!")
        self.setWindowIcon(QIcon('pythonlogo.png'))
        self.home()


        sys.stdout = Stream(newText=self.onUpdateText)
        for i in range(999):
            print(i)

    def onUpdateText(self, text):
        cursor = self.process.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.process.setTextCursor(cursor)
        self.process.ensureCursorVisible()

    def __del__(self):
        sys.stdout = sys.__stdout__

    def home(self):
        w = QWidget()
        self.setCentralWidget(w)
        lay = QVBoxLayout(w)
        btn = QPushButton("Generate")
        btn.clicked.connect(self.TextFSM)

        self.process = QTextEdit()
        self.process.moveCursor(QTextCursor.Start)
        self.process.ensureCursorVisible()
        self.process.setLineWrapColumnOrWidth(500)
        self.process.setLineWrapMode(QTextEdit.FixedPixelWidth)

        lay.addWidget(btn)
        lay.addWidget(self.process)

        self.show()

    def TextFSM(self):
        nameFile = 'Switch'

        try:
            input_file = open(nameFile + '.txt', encoding='utf-8')  # show version
            raw_text_data = input_file.read()
            input_file.close()

            # Add similar file reading and processing for other templates

        except IOError:
            print("Error: The file does not appear to exist.")
            QMessageBox.question(self, 'Warning', "ERROR: Please check your '.txt' file and TextFSM File.")

def run():
    app = QApplication(sys.argv)
    GUI = Window()
    sys.exit(app.exec_())

run()