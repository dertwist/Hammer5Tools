# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'curve.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGraphicsView, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)
import resources_rc

class Ui_CurveWidget(object):
    def setupUi(self, CurveWidget):
        if not CurveWidget.objectName():
            CurveWidget.setObjectName(u"CurveWidget")
        CurveWidget.resize(776, 346)
        CurveWidget.setMinimumSize(QSize(512, 0))
        CurveWidget.setMaximumSize(QSize(16666, 16777215))
        self.verticalLayout = QVBoxLayout(CurveWidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setSpacing(9)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(CurveWidget)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(78, 0))
        self.label.setMaximumSize(QSize(78, 16777215))

        self.horizontalLayout.addWidget(self.label)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.Header = QHBoxLayout()
        self.Header.setObjectName(u"Header")
        self.label_01 = QLabel(CurveWidget)
        self.label_01.setObjectName(u"label_01")

        self.Header.addWidget(self.label_01)

        self.label_02 = QLabel(CurveWidget)
        self.label_02.setObjectName(u"label_02")

        self.Header.addWidget(self.label_02)


        self.verticalLayout_5.addLayout(self.Header)

        self.datapoints_layout = QVBoxLayout()
        self.datapoints_layout.setObjectName(u"datapoints_layout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.datapoints_layout.addItem(self.verticalSpacer)


        self.verticalLayout_5.addLayout(self.datapoints_layout)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setSpacing(16)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(8, -1, 8, 0)
        self.add_data_point_button = QPushButton(CurveWidget)
        self.add_data_point_button.setObjectName(u"add_data_point_button")
        self.add_data_point_button.setStyleSheet(u"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 580 9pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 2px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:22px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QPushButton:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QPushButton:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"\n"
"    }")

        self.horizontalLayout_4.addWidget(self.add_data_point_button)

        self.advanced_mode_checkBox = QCheckBox(CurveWidget)
        self.advanced_mode_checkBox.setObjectName(u"advanced_mode_checkBox")
        self.advanced_mode_checkBox.setStyleSheet(u"\n"
"    /* QPushButton default and hover styles */\n"
"    QCheckBox {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 2px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:22px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QCheckBox:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QCheckBox:pressed {\n"
"\n"
"    }")

        self.horizontalLayout_4.addWidget(self.advanced_mode_checkBox)


        self.verticalLayout_5.addLayout(self.horizontalLayout_4)


        self.horizontalLayout.addLayout(self.verticalLayout_5)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(CurveWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(78, 0))
        self.label_2.setMaximumSize(QSize(78, 16777215))

        self.horizontalLayout_2.addWidget(self.label_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, -1, -1, 0)
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(-1, -1, -1, 0)
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.preview_label_01 = QLabel(CurveWidget)
        self.preview_label_01.setObjectName(u"preview_label_01")

        self.horizontalLayout_7.addWidget(self.preview_label_01)

        self.preview_label_02 = QLabel(CurveWidget)
        self.preview_label_02.setObjectName(u"preview_label_02")

        self.horizontalLayout_7.addWidget(self.preview_label_02)


        self.verticalLayout_4.addLayout(self.horizontalLayout_7)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(-1, -1, -1, 0)
        self.graphicsView_01 = QGraphicsView(CurveWidget)
        self.graphicsView_01.setObjectName(u"graphicsView_01")

        self.horizontalLayout_8.addWidget(self.graphicsView_01)

        self.graphicsView_02 = QGraphicsView(CurveWidget)
        self.graphicsView_02.setObjectName(u"graphicsView_02")

        self.horizontalLayout_8.addWidget(self.graphicsView_02)


        self.verticalLayout_4.addLayout(self.horizontalLayout_8)


        self.horizontalLayout_3.addLayout(self.verticalLayout_4)


        self.horizontalLayout_2.addLayout(self.horizontalLayout_3)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)


        self.verticalLayout.addLayout(self.verticalLayout_2)


        self.retranslateUi(CurveWidget)

        QMetaObject.connectSlotsByName(CurveWidget)
    # setupUi

    def retranslateUi(self, CurveWidget):
        CurveWidget.setWindowTitle(QCoreApplication.translate("CurveWidget", u"Form", None))
        self.label.setText(QCoreApplication.translate("CurveWidget", u"Datapoints", None))
        self.label_01.setText(QCoreApplication.translate("CurveWidget", u"Distance", None))
        self.label_02.setText(QCoreApplication.translate("CurveWidget", u"Volume", None))
        self.add_data_point_button.setText(QCoreApplication.translate("CurveWidget", u"Add datapoint", None))
        self.advanced_mode_checkBox.setText(QCoreApplication.translate("CurveWidget", u"Advanced mode", None))
        self.label_2.setText(QCoreApplication.translate("CurveWidget", u"Preview", None))
        self.preview_label_01.setText(QCoreApplication.translate("CurveWidget", u"Distance", None))
        self.preview_label_02.setText(QCoreApplication.translate("CurveWidget", u"Volume", None))
    # retranslateUi

