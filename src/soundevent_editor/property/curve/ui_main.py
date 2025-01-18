# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsView, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)
import resources_rc

class Ui_CurveWidget(object):
    def setupUi(self, CurveWidget):
        if not CurveWidget.objectName():
            CurveWidget.setObjectName(u"CurveWidget")
        CurveWidget.resize(851, 566)
        CurveWidget.setMinimumSize(QSize(512, 0))
        CurveWidget.setMaximumSize(QSize(16666, 16777215))
        self.verticalLayout = QVBoxLayout(CurveWidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setSpacing(9)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.top = QFrame(CurveWidget)
        self.top.setObjectName(u"top")
        self.top.setFrameShape(QFrame.Shape.StyledPanel)
        self.top.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.top)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.top)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(78, 0))
        self.label.setMaximumSize(QSize(78, 16777215))
        self.label.setStyleSheet(u"color: rgb(216, 75, 255);")

        self.horizontalLayout.addWidget(self.label)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setSpacing(6)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(-1, 4, -1, -1)
        self.Header = QHBoxLayout()
        self.Header.setObjectName(u"Header")
        self.label_01 = QLabel(self.top)
        self.label_01.setObjectName(u"label_01")

        self.Header.addWidget(self.label_01)

        self.label_02 = QLabel(self.top)
        self.label_02.setObjectName(u"label_02")

        self.Header.addWidget(self.label_02)


        self.verticalLayout_5.addLayout(self.Header)

        self.datapoints_layout = QVBoxLayout()
        self.datapoints_layout.setSpacing(0)
        self.datapoints_layout.setObjectName(u"datapoints_layout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.datapoints_layout.addItem(self.verticalSpacer)


        self.verticalLayout_5.addLayout(self.datapoints_layout)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(8, -1, 8, 0)
        self.add_data_point_button = QPushButton(self.top)
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
        icon = QIcon()
        icon.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_data_point_button.setIcon(icon)

        self.horizontalLayout_4.addWidget(self.add_data_point_button)


        self.verticalLayout_5.addLayout(self.horizontalLayout_4)


        self.horizontalLayout.addLayout(self.verticalLayout_5)


        self.verticalLayout_2.addWidget(self.top)

        self.bottom = QFrame(CurveWidget)
        self.bottom.setObjectName(u"bottom")
        self.bottom.setMinimumSize(QSize(0, 200))
        self.bottom.setMaximumSize(QSize(16777215, 200))
        self.bottom.setFrameShape(QFrame.Shape.NoFrame)
        self.bottom.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.bottom)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.bottom)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(78, 0))
        self.label_2.setMaximumSize(QSize(78, 16777215))
        self.label_2.setStyleSheet(u"color: rgb(255, 149, 78);")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.frame = QFrame(self.bottom)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(0, 200))
        self.frame.setMaximumSize(QSize(16777215, 200))
        self.frame.setStyleSheet(u"QFrame#frame {\n"
"        border: None;\n"
"}")
        self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.frame.setLineWidth(0)
        self.verticalLayout_3 = QVBoxLayout(self.frame)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(-1, -1, -1, 0)
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(-1, -1, -1, 0)
        self.frame_2 = QFrame(self.frame)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setStyleSheet(u"QFrame#frame_2 {\n"
"        border: 2px solid black;\n"
"        border-radius: 2px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"}")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_6 = QVBoxLayout(self.frame_2)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.preview_label_01 = QLabel(self.frame_2)
        self.preview_label_01.setObjectName(u"preview_label_01")

        self.verticalLayout_6.addWidget(self.preview_label_01)

        self.graphicsView_01 = QGraphicsView(self.frame_2)
        self.graphicsView_01.setObjectName(u"graphicsView_01")
        self.graphicsView_01.setMinimumSize(QSize(0, 150))
        self.graphicsView_01.setMaximumSize(QSize(16777215, 16777215))
        self.graphicsView_01.setStyleSheet(u"\n"
"        font: 580 9pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: None;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;")

        self.verticalLayout_6.addWidget(self.graphicsView_01)


        self.horizontalLayout_8.addWidget(self.frame_2)

        self.frame_3 = QFrame(self.frame)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setStyleSheet(u"QFrame#frame_3 {\n"
"        border: 2px solid black;\n"
"        border-radius: 2px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"}")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_7 = QVBoxLayout(self.frame_3)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.preview_label_02 = QLabel(self.frame_3)
        self.preview_label_02.setObjectName(u"preview_label_02")

        self.verticalLayout_7.addWidget(self.preview_label_02)

        self.graphicsView_02 = QGraphicsView(self.frame_3)
        self.graphicsView_02.setObjectName(u"graphicsView_02")
        self.graphicsView_02.setMinimumSize(QSize(0, 150))
        self.graphicsView_02.setMaximumSize(QSize(16777215, 16777215))
        self.graphicsView_02.setStyleSheet(u"\n"
"        font: 580 9pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: None;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;")

        self.verticalLayout_7.addWidget(self.graphicsView_02)


        self.horizontalLayout_8.addWidget(self.frame_3)


        self.verticalLayout_4.addLayout(self.horizontalLayout_8)


        self.verticalLayout_3.addLayout(self.verticalLayout_4)


        self.horizontalLayout_2.addWidget(self.frame)


        self.verticalLayout_2.addWidget(self.bottom)


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
        self.label_2.setText(QCoreApplication.translate("CurveWidget", u"Preview", None))
        self.preview_label_01.setText(QCoreApplication.translate("CurveWidget", u"Distance", None))
        self.preview_label_02.setText(QCoreApplication.translate("CurveWidget", u"Volume", None))
    # retranslateUi

