# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'popup_menu.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLineEdit, QScrollArea,
    QSizePolicy, QToolButton, QVBoxLayout, QWidget)
import rc_resources

class Ui_PoPupMenu(object):
    def setupUi(self, PoPupMenu):
        if not PoPupMenu.objectName():
            PoPupMenu.setObjectName(u"PoPupMenu")
        PoPupMenu.resize(486, 803)
        PoPupMenu.setStyleSheet(u"")
        self.verticalLayout = QVBoxLayout(PoPupMenu)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalWidget = QWidget(PoPupMenu)
        self.horizontalWidget.setObjectName(u"horizontalWidget")
        self.horizontalWidget.setMaximumSize(QSize(16777215, 30))
        self.horizontalWidget.setStyleSheet(u"QWidget  {\n"
"    background-color: #151515;\n"
"    outline: none;\n"
"	border:2px solid black;\n"
"	border-bottom:0px solid black;\n"
"	border-radius: 0px;\n"
"	border-color: rgba(80, 80, 80, 255);\n"
"}")
        self.horizontalLayout = QHBoxLayout(self.horizontalWidget)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(2, 0, 2, 0)
        self.toolButton_2 = QToolButton(self.horizontalWidget)
        self.toolButton_2.setObjectName(u"toolButton_2")
        self.toolButton_2.setEnabled(False)
        self.toolButton_2.setStyleSheet(u"QToolButton {\n"
"    font: 700 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"	border-bottom: 0px solid black;\n"
"	border-left: 0px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:16px;\n"
"	width:16px;\n"
"    padding: 4px;\n"
"    padding-left: 6px;\n"
"    padding-right: 6px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"QToolButton:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"QToolButton:pressed {\n"
"    background-color: #1C1C1C;\n"
"    padding: 4px;\n"
"    padding-left: 6px;\n"
"    padding-right: 6px;\n"
"    height:16px;\n"
"	width:16px;\n"
"    margin:  0px;\n"
"    margin-left: 0px;\n"
"    margin-right: 0px;\n"
"	font: 700 10pt \"Sego\";\n"
"\n"
"}\n"
"\n"
"")
        icon = QIcon()
        icon.addFile(u":/icons/search_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton_2.setIcon(icon)
        self.toolButton_2.setIconSize(QSize(20, 20))
        self.toolButton_2.setCheckable(False)
        self.toolButton_2.setChecked(False)
        self.toolButton_2.setPopupMode(QToolButton.DelayedPopup)

        self.horizontalLayout.addWidget(self.toolButton_2)

        self.lineEdit = QLineEdit(self.horizontalWidget)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setStyleSheet(u"QLineEdit {\n"
"    border: 0px solid #CCCCCC;\n"
"    border-radius: 0px;\n"
"    color: #E3E3E3;\n"
"	font: 700 10pt \"Segoe UI\";\n"
"margin: 0px;\n"
"padding: 0px;\n"
"padding-top: 0px;\n"
"padding-bottom: 0px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"height:22px;\n"
"}\n"
"QLineEdit:focus {\n"
"\n"
"}\n"
"QLineEdit::selection {\n"
"    color: white;\n"
"}")
        self.lineEdit.setClearButtonEnabled(False)

        self.horizontalLayout.addWidget(self.lineEdit)


        self.verticalLayout.addWidget(self.horizontalWidget)

        self.scrollArea = QScrollArea(PoPupMenu)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setStyleSheet(u"")
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 484, 772))
        self.scrollAreaWidgetContents.setStyleSheet(u"QWidget  {\n"
"	border:0px solid gray;\n"
"}")
        self.verticalLayout_3 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(2, 2, 2, 2)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)


        self.retranslateUi(PoPupMenu)

        QMetaObject.connectSlotsByName(PoPupMenu)
    # setupUi

    def retranslateUi(self, PoPupMenu):
        PoPupMenu.setWindowTitle(QCoreApplication.translate("PoPupMenu", u"Form", None))
#if QT_CONFIG(whatsthis)
        PoPupMenu.setWhatsThis(QCoreApplication.translate("PoPupMenu", u"<html><head/><body><pre style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:'Courier New'; background-color:#1f1f1f;\"><br/></pre></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.toolButton_2.setText(QCoreApplication.translate("PoPupMenu", u"...", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("PoPupMenu", u"Search...", None))
    # retranslateUi

