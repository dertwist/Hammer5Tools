# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'vector2d.ui'
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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFrame, QHBoxLayout,
    QLabel, QSizePolicy, QVBoxLayout, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(790, 64)
        Widget.setMinimumSize(QSize(0, 0))
        Widget.setMaximumSize(QSize(16777215, 64))
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
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"color: #ECA4A0;\n"
"")

        self.horizontalLayout_2.addWidget(self.label)

        self.vector_x = QDoubleSpinBox(self.frame)
        self.vector_x.setObjectName(u"vector_x")
        self.vector_x.setMinimumSize(QSize(0, 0))
        self.vector_x.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"border:0px;\n"
"color: #ECA4A0;\n"
"}\n"
"\n"
"QDoubleSpinBox:focus {\n"
"}\n"
"\n"
"QDoubleSpinBox:hover {\n"
"}\n"
"\n"
"QDoubleSpinBox:pressed {\n"
"	background-color: #121212;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-button {\n"
"    border: 0px solid black;\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    border-left: 2px solid black;\n"
"    border-bottom: 0px solid black;\n"
"    border-top-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-arrow {\n"
"    image: url(://icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"  "
                        "  subcontrol-position: bottom right;\n"
"	border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}")
        self.vector_x.setDecimals(2)
        self.vector_x.setMinimum(-99999999999.000000000000000)
        self.vector_x.setMaximum(99999999999.000000000000000)
        self.vector_x.setSingleStep(0.100000000000000)

        self.horizontalLayout_2.addWidget(self.vector_x)


        self.verticalLayout.addWidget(self.frame)

        self.frame_2 = QFrame(Widget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMaximumSize(QSize(16777215, 32))
        self.frame_2.setStyleSheet(u".QFrame {\n"
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
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.frame_2.setLineWidth(0)
        self.horizontalLayout_7 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.frame_2)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"color: #B6EFA2;")

        self.horizontalLayout_7.addWidget(self.label_2)

        self.vector_y = QDoubleSpinBox(self.frame_2)
        self.vector_y.setObjectName(u"vector_y")
        self.vector_y.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"border:0px;\n"
"color: #B6EFA2;\n"
"}\n"
"\n"
"QDoubleSpinBox:focus {\n"
"}\n"
"\n"
"QDoubleSpinBox:hover {\n"
"}\n"
"\n"
"QDoubleSpinBox:pressed {\n"
"	background-color: #121212;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-button {\n"
"    border: 0px solid black;\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    border-left: 2px solid black;\n"
"    border-bottom: 0px solid black;\n"
"    border-top-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-arrow {\n"
"    image: url(://icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"  "
                        "  subcontrol-position: bottom right;\n"
"	border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QDoubleSpinBox:disabled {\n"
"	color: rgba(125, 125, 125, 100);\n"
"}")
        self.vector_y.setDecimals(2)
        self.vector_y.setMinimum(-99999999999.000000000000000)
        self.vector_y.setMaximum(99999999999.000000000000000)
        self.vector_y.setSingleStep(0.100000000000000)

        self.horizontalLayout_7.addWidget(self.vector_y)


        self.verticalLayout.addWidget(self.frame_2)


        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Form", None))
        self.label.setText(QCoreApplication.translate("Widget", u"Vector X", None))
        self.label_2.setText(QCoreApplication.translate("Widget", u"Vector Y", None))
    # retranslateUi

