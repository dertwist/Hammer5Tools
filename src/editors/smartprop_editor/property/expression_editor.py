from PySide6.QtWidgets import QToolButton, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from src.widgets.completer.main import CompletingPlainTextEdit
from src.editors.smartprop_editor.completion_utils import CompletionUtils

class ExpressionEditor(QToolButton):
    def __init__(self, target_text_field, variables_scrollArea):
        super().__init__()
        self.setIcon(QIcon(":/icons/edit_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg"))
        self.setToolTip("Open expression editor")
        self.setFixedSize(QSize(24, 24))
        self.clicked.connect(lambda: self.open_expression_editor(target_text_field))
        self.variables_scrollArea = variables_scrollArea

    def open_expression_editor(self, target_text_edit):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Expression")
        dialog.setMinimumSize(500, 300)

        layout = QVBoxLayout(dialog)

        label = QLabel("Edit expression:")
        layout.addWidget(label)

        editor = CompletingPlainTextEdit()
        editor.setStyleSheet("""QPlainTextEdit {

            font: 580 8pt "Segoe UI";
            border: 2px solid black;
            border-radius: 0px;
            border-color: rgba(80, 80, 80, 255);
            height:18px;
            padding: 2px;
            padding-left: 0px;
            padding-right: 0px;
            color: #E3E3E3;
            background-color: #1C1C1C;
        }

        QPlainTextEdit:pressed {
        }""")
        CompletionUtils.setup_completer_for_widget(
            editor,
            self.variables_scrollArea,
        )
        editor.setPlainText(target_text_edit.toPlainText())
        layout.addWidget(editor)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save", dialog)
        cancel_btn = QPushButton("Cancel", dialog)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def save():
            target_text_edit.setPlainText(editor.toPlainText())
            dialog.accept()

        def cancel():
            dialog.reject()

        save_btn.clicked.connect(save)
        cancel_btn.clicked.connect(cancel)

        dialog.exec()