# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'float.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QFrame,
    QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(790, 97)
        Widget.setMinimumSize(QSize(0, 0))
        Widget.setMaximumSize(QSize(16777215, 97))
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
"\n"
"")

        self.horizontalLayout_2.addWidget(self.label)

        self.value_doubleSpinBox = QDoubleSpinBox(self.frame)
        self.value_doubleSpinBox.setObjectName(u"value_doubleSpinBox")
        self.value_doubleSpinBox.setMinimumSize(QSize(0, 0))
        self.value_doubleSpinBox.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"border:0px;\n"
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
"    subcontrol-positio"
                        "n: bottom right;\n"
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
        self.value_doubleSpinBox.setDecimals(2)
        self.value_doubleSpinBox.setMinimum(-99999999999.000000000000000)
        self.value_doubleSpinBox.setMaximum(99999999999.000000000000000)
        self.value_doubleSpinBox.setSingleStep(0.100000000000000)

        self.horizontalLayout_2.addWidget(self.value_doubleSpinBox)


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
        self.min_checkBox = QCheckBox(self.frame_2)
        self.min_checkBox.setObjectName(u"min_checkBox")
        self.min_checkBox.setStyleSheet(u"QCheckBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:4px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"	border:0px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}")

        self.horizontalLayout_7.addWidget(self.min_checkBox)

        self.min_doubleSpinBox = QDoubleSpinBox(self.frame_2)
        self.min_doubleSpinBox.setObjectName(u"min_doubleSpinBox")
        self.min_doubleSpinBox.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"border:0px;\n"
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
"    subcontrol-positio"
                        "n: bottom right;\n"
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
        self.min_doubleSpinBox.setDecimals(2)
        self.min_doubleSpinBox.setMinimum(-99999999999.000000000000000)
        self.min_doubleSpinBox.setMaximum(99999999999.000000000000000)
        self.min_doubleSpinBox.setSingleStep(0.100000000000000)

        self.horizontalLayout_7.addWidget(self.min_doubleSpinBox)


        self.verticalLayout.addWidget(self.frame_2)

        self.frame_3 = QFrame(Widget)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16777215, 32))
        self.frame_3.setStyleSheet(u".QFrame {\n"
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
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.frame_3.setLineWidth(0)
        self.horizontalLayout_8 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_8.setSpacing(0)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.max_checkBox = QCheckBox(self.frame_3)
        self.max_checkBox.setObjectName(u"max_checkBox")
        self.max_checkBox.setStyleSheet(u"QCheckBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:4px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"	border:0px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}")

        self.horizontalLayout_8.addWidget(self.max_checkBox)

        self.max_doubleSpinBox = QDoubleSpinBox(self.frame_3)
        self.max_doubleSpinBox.setObjectName(u"max_doubleSpinBox")
        self.max_doubleSpinBox.setEnabled(True)
        self.max_doubleSpinBox.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"border:0px;\n"
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
"    subcontrol-positio"
                        "n: bottom right;\n"
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
        self.max_doubleSpinBox.setDecimals(2)
        self.max_doubleSpinBox.setMinimum(-99999999999.000000000000000)
        self.max_doubleSpinBox.setMaximum(99999999999.000000000000000)
        self.max_doubleSpinBox.setSingleStep(0.100000000000000)

        self.horizontalLayout_8.addWidget(self.max_doubleSpinBox)


        self.verticalLayout.addWidget(self.frame_3)


        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Form", None))
        self.label.setText(QCoreApplication.translate("Widget", u"Value", None))
        self.min_checkBox.setText(QCoreApplication.translate("Widget", u"Min Value", None))
        self.max_checkBox.setText(QCoreApplication.translate("Widget", u"Max Value", None))
    # retranslateUi

