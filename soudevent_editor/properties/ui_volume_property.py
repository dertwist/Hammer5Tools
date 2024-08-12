# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'volume_property.ui'
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
    QLabel, QSizePolicy, QSlider, QWidget)

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

        self.horizontalSlider = QSlider(self.frame)
        self.horizontalSlider.setObjectName(u"horizontalSlider")
        self.horizontalSlider.setStyleSheet(u"QSlider::groove:horizontal {\n"
"    border: 2px solid black;\n"
"    border-color: rgba(80, 80, 80, 0);\n"
"    height: 8px;\n"
"    margin: 2px 0;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background: #414956 ;\n"
"    border: 2px solid black;\n"
"	border-color: rgba(80, 80, 80, 255);\n"
"    width: 6px;\n"
"    height: 24px;\n"
"    margin: -5px 0;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background: #23272d;\n"
"    border: 2px solid black;\n"
"    border-radius: 1px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 8px;\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    border: 2px solid black;\n"
"    border-radius: 1px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 8px;\n"
"}\n"
"")
        self.horizontalSlider.setMinimum(-99)
        self.horizontalSlider.setMaximum(99)
        self.horizontalSlider.setSingleStep(1)
        self.horizontalSlider.setValue(10)
        self.horizontalSlider.setSliderPosition(10)
        self.horizontalSlider.setOrientation(Qt.Horizontal)

        self.horizontalLayout_2.addWidget(self.horizontalSlider)

        self.doubleSpinBox = QDoubleSpinBox(self.frame)
        self.doubleSpinBox.setObjectName(u"doubleSpinBox")
        self.doubleSpinBox.setStyleSheet(u"QDoubleSpinBox {\n"
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
        self.doubleSpinBox.setDecimals(1)
        self.doubleSpinBox.setMinimum(-9.900000000000000)
        self.doubleSpinBox.setMaximum(9.900000000000000)
        self.doubleSpinBox.setSingleStep(0.100000000000000)

        self.horizontalLayout_2.addWidget(self.doubleSpinBox)


        self.horizontalLayout.addWidget(self.frame)


        self.retranslateUi(LegacyPropertyWidet)

        QMetaObject.connectSlotsByName(LegacyPropertyWidet)
    # setupUi

    def retranslateUi(self, LegacyPropertyWidet):
        LegacyPropertyWidet.setWindowTitle(QCoreApplication.translate("LegacyPropertyWidet", u"Form", None))
        self.label.setText(QCoreApplication.translate("LegacyPropertyWidet", u"Volume", None))
    # retranslateUi

