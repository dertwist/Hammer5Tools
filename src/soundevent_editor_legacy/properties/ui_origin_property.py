# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'origin_property.ui'
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
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

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

        self.paste_button = QPushButton(self.frame)
        self.paste_button.setObjectName(u"paste_button")
        self.paste_button.setMinimumSize(QSize(128, 0))

        self.horizontalLayout_2.addWidget(self.paste_button)

        self.x_axis = QDoubleSpinBox(self.frame)
        self.x_axis.setObjectName(u"x_axis")
        self.x_axis.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    padding-left: 2px;\n"
"    padding-right: 2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
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
""
                        "    subcontrol-position: bottom right;\n"
"	border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}")
        self.x_axis.setDecimals(2)
        self.x_axis.setMinimum(-9999999.900000000372529)
        self.x_axis.setMaximum(9999999.900000000372529)
        self.x_axis.setSingleStep(0.100000000000000)

        self.horizontalLayout_2.addWidget(self.x_axis)

        self.y_axis = QDoubleSpinBox(self.frame)
        self.y_axis.setObjectName(u"y_axis")
        self.y_axis.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    padding-left: 2px;\n"
"    padding-right: 2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
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
""
                        "    subcontrol-position: bottom right;\n"
"	border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}")
        self.y_axis.setDecimals(2)
        self.y_axis.setMinimum(-9999999.900000000372529)
        self.y_axis.setMaximum(9999999.900000000372529)
        self.y_axis.setSingleStep(0.100000000000000)

        self.horizontalLayout_2.addWidget(self.y_axis)

        self.z_axis = QDoubleSpinBox(self.frame)
        self.z_axis.setObjectName(u"z_axis")
        self.z_axis.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    padding-left: 2px;\n"
"    padding-right: 2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
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
""
                        "    subcontrol-position: bottom right;\n"
"	border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}")
        self.z_axis.setDecimals(2)
        self.z_axis.setMinimum(-9999999.900000000372529)
        self.z_axis.setMaximum(9999999.900000000372529)
        self.z_axis.setSingleStep(0.100000000000000)

        self.horizontalLayout_2.addWidget(self.z_axis)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.horizontalLayout.addWidget(self.frame)


        self.retranslateUi(PropertyWidet)

        QMetaObject.connectSlotsByName(PropertyWidet)
    # setupUi

    def retranslateUi(self, PropertyWidet):
        PropertyWidet.setWindowTitle(QCoreApplication.translate("PropertyWidet", u"Form", None))
        self.label.setText(QCoreApplication.translate("PropertyWidet", u"Volume", None))
        self.paste_button.setText(QCoreApplication.translate("PropertyWidet", u"Paste", None))
        self.x_axis.setSpecialValueText("")
        self.x_axis.setPrefix(QCoreApplication.translate("PropertyWidet", u"X ", None))
        self.y_axis.setPrefix(QCoreApplication.translate("PropertyWidet", u"Y ", None))
        self.z_axis.setPrefix(QCoreApplication.translate("PropertyWidet", u"Z ", None))
    # retranslateUi

