# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'legacy.ui'
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
    QLayout, QSizePolicy, QVBoxLayout, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(790, 32)
        Widget.setMinimumSize(QSize(0, 0))
        Widget.setMaximumSize(QSize(16777215, 32))
        Widget.setStyleSheet(u".QWidget {\n"
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
".QWidget::hover {\n"
"}\n"
".QWidget::selected {\n"
"    background-color: #414956;\n"
"}")
        self.verticalLayout = QVBoxLayout(Widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(Widget)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(16777215, 32))
        self.frame.setStyleSheet(u".QFrame {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"	border-top: 0px;\n"
"    border-color: rgba(50, 50, 50, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
".QFrame::hover {\n"
"}\n"
".QFrame::selected {\n"
"    background-color: #414956;\n"
"}")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.frame.setLineWidth(0)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setSpacing(16)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.layout = QHBoxLayout()
        self.layout.setObjectName(u"layout")
        self.layout.setSizeConstraint(QLayout.SetFixedSize)
        self.value_label = QLabel(self.frame)
        self.value_label.setObjectName(u"value_label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.value_label.sizePolicy().hasHeightForWidth())
        self.value_label.setSizePolicy(sizePolicy)
        self.value_label.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"padding-right: 16px;\n"
"\n"
"")

        self.layout.addWidget(self.value_label)


        self.horizontalLayout_2.addLayout(self.layout)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Form", None))
        self.value_label.setText(QCoreApplication.translate("Widget", u"Value", None))
    # retranslateUi

