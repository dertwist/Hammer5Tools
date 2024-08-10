# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'legacy_property.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QSizePolicy, QWidget)

class Ui_LegacyPropertyWidet(object):
    def setupUi(self, LegacyPropertyWidet):
        if not LegacyPropertyWidet.objectName():
            LegacyPropertyWidet.setObjectName(u"LegacyPropertyWidet")
        LegacyPropertyWidet.resize(683, 48)
        LegacyPropertyWidet.setMinimumSize(QSize(0, 48))
        LegacyPropertyWidet.setMaximumSize(QSize(16777215, 48))
        LegacyPropertyWidet.setStyleSheet(u"")
        self.horizontalLayout = QHBoxLayout(LegacyPropertyWidet)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(LegacyPropertyWidet)
        self.frame.setObjectName(u"frame")
        self.frame.setStyleSheet(u".QFrame {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"	border-top: 0px;\n"
"    border-color: rgba(50, 50, 50, 255);\n"
"    padding: 8px;\n"
"    padding-left: 6px;\n"
"    padding-right: 6px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
".QFrame::hover {\n"
"    background-color: #414956;\n"
"}\n"
".QFrame::selected {\n"
"    background-color: #414956;\n"
"}")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.frame.setLineWidth(0)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);")

        self.horizontalLayout_2.addWidget(self.label)

        self.lineEdit = QLineEdit(self.frame)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout_2.addWidget(self.lineEdit)


        self.horizontalLayout.addWidget(self.frame)


        self.retranslateUi(LegacyPropertyWidet)

        QMetaObject.connectSlotsByName(LegacyPropertyWidet)
    # setupUi

    def retranslateUi(self, LegacyPropertyWidet):
        LegacyPropertyWidet.setWindowTitle(QCoreApplication.translate("LegacyPropertyWidet", u"Form", None))
        self.label.setText(QCoreApplication.translate("LegacyPropertyWidet", u"Property (legacy):", None))
    # retranslateUi

