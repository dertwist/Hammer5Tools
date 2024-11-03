# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'int.ui'
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
    QLabel, QSizePolicy, QSpinBox, QVBoxLayout,
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

        self.value_spinBox = QSpinBox(self.frame)
        self.value_spinBox.setObjectName(u"value_spinBox")
        self.value_spinBox.setEnabled(True)
        self.value_spinBox.setMinimumSize(QSize(0, 0))
        self.value_spinBox.setStyleSheet(u"QSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox:focus {\n"
"}\n"
"\n"
"QSpinBox:hover {\n"
"}\n"
"\n"
"QSpinBox:pressed {\n"
"    background-color: #121212;\n"
"}\n"
"\n"
"QSpinBox:disabled {\n"
"	color: rgba(125, 125, 125, 100);\n"
"}\n"
"\n"
"\n"
"QSpinBox::up-button {\n"
"    border: 0px solid black;\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    border-left: 2px solid black;\n"
"    border-bottom: 0px solid black;\n"
"    border-top-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    width: 16px;\n"
"    margin: 0px;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox::up-arrow {\n"
"    image: url(://icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QSpinBox::down-button {\n"
"   "
                        " subcontrol-origin: border;\n"
"    subcontrol-position: bottom right;\n"
"    border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"    border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    width: 16px;\n"
"    margin: 0px;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}")
        self.value_spinBox.setMinimum(-99999999)
        self.value_spinBox.setMaximum(99999999)

        self.horizontalLayout_2.addWidget(self.value_spinBox)


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

        self.min_spinBox = QSpinBox(self.frame_2)
        self.min_spinBox.setObjectName(u"min_spinBox")
        self.min_spinBox.setStyleSheet(u"QSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox:focus {\n"
"}\n"
"\n"
"QSpinBox:hover {\n"
"}\n"
"\n"
"QSpinBox:pressed {\n"
"    background-color: #121212;\n"
"}\n"
"\n"
"QSpinBox:disabled {\n"
"	color: rgba(125, 125, 125, 100);\n"
"}\n"
"\n"
"\n"
"QSpinBox::up-button {\n"
"    border: 0px solid black;\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    border-left: 2px solid black;\n"
"    border-bottom: 0px solid black;\n"
"    border-top-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    width: 16px;\n"
"    margin: 0px;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox::up-arrow {\n"
"    image: url(://icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QSpinBox::down-button {\n"
"   "
                        " subcontrol-origin: border;\n"
"    subcontrol-position: bottom right;\n"
"    border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"    border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    width: 16px;\n"
"    margin: 0px;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}")
        self.min_spinBox.setMinimum(-99999999)
        self.min_spinBox.setMaximum(99999999)

        self.horizontalLayout_7.addWidget(self.min_spinBox)


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

        self.max_spinBox = QSpinBox(self.frame_3)
        self.max_spinBox.setObjectName(u"max_spinBox")
        self.max_spinBox.setEnabled(True)
        self.max_spinBox.setStyleSheet(u"QSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox:focus {\n"
"}\n"
"\n"
"QSpinBox:hover {\n"
"}\n"
"\n"
"QSpinBox:pressed {\n"
"    background-color: #121212;\n"
"}\n"
"\n"
"QSpinBox:disabled {\n"
"	color: rgba(125, 125, 125, 100);\n"
"}\n"
"\n"
"\n"
"QSpinBox::up-button {\n"
"    border: 0px solid black;\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    border-left: 2px solid black;\n"
"    border-bottom: 0px solid black;\n"
"    border-top-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    width: 16px;\n"
"    margin: 0px;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox::up-arrow {\n"
"    image: url(://icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QSpinBox::down-button {\n"
"   "
                        " subcontrol-origin: border;\n"
"    subcontrol-position: bottom right;\n"
"    border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"    border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    width: 16px;\n"
"    margin: 0px;\n"
"    border: 0px;\n"
"}\n"
"\n"
"QSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}")
        self.max_spinBox.setMinimum(-99999999)
        self.max_spinBox.setMaximum(99999999)

        self.horizontalLayout_8.addWidget(self.max_spinBox)


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

