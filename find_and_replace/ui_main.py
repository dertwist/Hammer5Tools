# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
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
    QDialogButtonBox, QHBoxLayout, QLineEdit, QPlainTextEdit,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(931, 755)
        self.verticalLayout_2 = QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.viewport_QplainText = QPlainTextEdit(Dialog)
        self.viewport_QplainText.setObjectName(u"viewport_QplainText")

        self.verticalLayout.addWidget(self.viewport_QplainText)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.match_case_checkBox = QCheckBox(Dialog)
        self.match_case_checkBox.setObjectName(u"match_case_checkBox")

        self.horizontalLayout.addWidget(self.match_case_checkBox)

        self.regex_checkBox = QCheckBox(Dialog)
        self.regex_checkBox.setObjectName(u"regex_checkBox")

        self.horizontalLayout.addWidget(self.regex_checkBox)

        self.whole_words_checkBox = QCheckBox(Dialog)
        self.whole_words_checkBox.setObjectName(u"whole_words_checkBox")

        self.horizontalLayout.addWidget(self.whole_words_checkBox)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.serach_backward_checkBox = QCheckBox(Dialog)
        self.serach_backward_checkBox.setObjectName(u"serach_backward_checkBox")

        self.horizontalLayout_2.addWidget(self.serach_backward_checkBox)

        self.search_from_start_checkBox = QCheckBox(Dialog)
        self.search_from_start_checkBox.setObjectName(u"search_from_start_checkBox")

        self.horizontalLayout_2.addWidget(self.search_from_start_checkBox)

        self.serach_selection_checkBox = QCheckBox(Dialog)
        self.serach_selection_checkBox.setObjectName(u"serach_selection_checkBox")

        self.horizontalLayout_2.addWidget(self.serach_selection_checkBox)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
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
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Duplicate Element With Replace", None))
        self.match_case_checkBox.setText(QCoreApplication.translate("Dialog", u"Match Case", None))
        self.regex_checkBox.setText(QCoreApplication.translate("Dialog", u"Regex", None))
        self.whole_words_checkBox.setText(QCoreApplication.translate("Dialog", u"Whole words", None))
        self.serach_backward_checkBox.setText(QCoreApplication.translate("Dialog", u"Search backward", None))
        self.search_from_start_checkBox.setText(QCoreApplication.translate("Dialog", u"Search from start", None))
        self.serach_selection_checkBox.setText(QCoreApplication.translate("Dialog", u"Search selection", None))
        self.find_text_lineEdit.setText("")
        self.find_text_lineEdit.setPlaceholderText(QCoreApplication.translate("Dialog", u"Find text", None))
        self.replace_with_lineEdit.setPlaceholderText(QCoreApplication.translate("Dialog", u"Replace With", None))
    # retranslateUi

