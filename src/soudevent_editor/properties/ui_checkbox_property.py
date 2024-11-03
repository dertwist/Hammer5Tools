# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'checkbox_property.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout,
    QLabel, QSizePolicy, QSpacerItem, QWidget)

class Ui_PropertyWidet(object):
    def setupUi(self, PropertyWidet):
        if not PropertyWidet.objectName():
            PropertyWidet.setObjectName(u"PropertyWidet")
        PropertyWidet.resize(683, 48)
        PropertyWidet.setMinimumSize(QSize(0, 48))
        PropertyWidet.setMaximumSize(QSize(16777215, 48))
        PropertyWidet.setStyleSheet(u"")
        self.horizontalLayout = QHBoxLayout(PropertyWidet)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(PropertyWidet)
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
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);")

        self.horizontalLayout_2.addWidget(self.label)

        self.checkBox = QCheckBox(self.frame)
        self.checkBox.setObjectName(u"checkBox")

        self.horizontalLayout_2.addWidget(self.checkBox)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.horizontalLayout.addWidget(self.frame)


        self.retranslateUi(PropertyWidet)

        QMetaObject.connectSlotsByName(PropertyWidet)
    # setupUi

    def retranslateUi(self, PropertyWidet):
        PropertyWidet.setWindowTitle(QCoreApplication.translate("PropertyWidet", u"Form", None))
        self.label.setText(QCoreApplication.translate("PropertyWidet", u"Volume", None))
        self.checkBox.setText("")
    # retranslateUi

