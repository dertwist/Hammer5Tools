# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QFrame, QHBoxLayout, QLineEdit,
    QPlainTextEdit, QSizePolicy, QVBoxLayout, QWidget)
import src.resources_rc as resources_rc

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(931, 755)
        icon = QIcon()
        icon.addFile(u":/icons/appicon.ico", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        Dialog.setWindowIcon(icon)
        self.verticalLayout_2 = QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.viewport_QplainText = QPlainTextEdit(Dialog)
        self.viewport_QplainText.setObjectName(u"viewport_QplainText")

        self.verticalLayout.addWidget(self.viewport_QplainText)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")

        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.frame = QFrame(Dialog)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(320, 0))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.match_case_checkBox = QCheckBox(self.frame)
        self.match_case_checkBox.setObjectName(u"match_case_checkBox")

        self.horizontalLayout_4.addWidget(self.match_case_checkBox)

        self.whole_words_checkBox = QCheckBox(self.frame)
        self.whole_words_checkBox.setObjectName(u"whole_words_checkBox")

        self.horizontalLayout_4.addWidget(self.whole_words_checkBox)


        self.horizontalLayout_3.addWidget(self.frame)

        self.find_text_lineEdit = QLineEdit(Dialog)
        self.find_text_lineEdit.setObjectName(u"find_text_lineEdit")

        self.horizontalLayout_3.addWidget(self.find_text_lineEdit)

        self.replace_with_lineEdit = QLineEdit(Dialog)
        self.replace_with_lineEdit.setObjectName(u"replace_with_lineEdit")

        self.horizontalLayout_3.addWidget(self.replace_with_lineEdit)


        self.verticalLayout.addLayout(self.horizontalLayout_3)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout_2.addWidget(self.buttonBox)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Find and replace", None))
        self.match_case_checkBox.setText(QCoreApplication.translate("Dialog", u"Match Case", None))
        self.whole_words_checkBox.setText(QCoreApplication.translate("Dialog", u"Whole words", None))
        self.find_text_lineEdit.setText("")
        self.find_text_lineEdit.setPlaceholderText(QCoreApplication.translate("Dialog", u"Find", None))
        self.replace_with_lineEdit.setPlaceholderText(QCoreApplication.translate("Dialog", u"Replace", None))
    # retranslateUi

