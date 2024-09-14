import sys
from completer.main import CompletingPlainTextEdit
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QDockWidget
from PySide6.QtCore import QCommandLineParser, QCommandLineOption, Qt


def main():
    app = QApplication(sys.argv)

    # Create a main window
    main_window = QMainWindow()


    te = CompletingPlainTextEdit()
    te.completions.setStringList(['test', 'print', 'group', 'small', 'new_fd'])

    ted = CompletingPlainTextEdit()
    ted.completions.setStringList(['test', 'print', 'group', 'small', 'new_fd' '|', ''])



    # Set the label as the central widget of the main window
    main_window.setCentralWidget(te)
    # Create a QDockWidget instance
    dock_widget = QDockWidget()
    dock_widget.setWidget(ted)

    dock_widgetd = QDockWidget()
    dock_widgetd.setWidget(te)

    # Add the QDockWidget to the main window
    main_window.addDockWidget(Qt.RightDockWidgetArea, dock_widget)
    main_window.addDockWidget(Qt.LeftDockWidgetArea, dock_widgetd)

    # Show the main window
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()