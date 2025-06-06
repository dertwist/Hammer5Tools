# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
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
    QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)
import resources_rc

class Ui_CurveWidget(object):
    def setupUi(self, CurveWidget):
        if not CurveWidget.objectName():
            CurveWidget.setObjectName(u"CurveWidget")
        CurveWidget.resize(800, 649)
        CurveWidget.setMinimumSize(QSize(512, 0))
        CurveWidget.setMaximumSize(QSize(16666, 16777215))
        self.verticalLayout = QVBoxLayout(CurveWidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setSpacing(9)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.preview = QFrame(CurveWidget)
        self.preview.setObjectName(u"preview")
        self.preview.setMinimumSize(QSize(0, 200))
        self.preview.setMaximumSize(QSize(16777215, 200))
        self.preview.setFrameShape(QFrame.Shape.NoFrame)
        self.preview.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.preview)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.preview)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(78, 0))
        self.label_2.setMaximumSize(QSize(78, 16777215))
        self.label_2.setStyleSheet(u"color: rgb(255, 149, 78);")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.frame = QFrame(self.preview)
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

        self.verticalLayout_3.addLayout(self.verticalLayout_4)


        self.horizontalLayout_2.addWidget(self.frame)


        self.verticalLayout_2.addWidget(self.preview)

        self.datapoints = QFrame(CurveWidget)
        self.datapoints.setObjectName(u"datapoints")
        self.datapoints.setFrameShape(QFrame.Shape.StyledPanel)
        self.datapoints.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.datapoints)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.datapoints)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(78, 0))
        self.label.setMaximumSize(QSize(78, 16777215))
        self.label.setStyleSheet(u"color: rgb(216, 75, 255);")

        self.horizontalLayout.addWidget(self.label)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setSpacing(6)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(-1, 4, -1, -1)
        self.add_data_point_button = QPushButton(self.datapoints)
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

        self.verticalLayout_5.addWidget(self.add_data_point_button)

        self.frame_2 = QVBoxLayout()
        self.frame_2.setSpacing(16)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setContentsMargins(-1, -1, 5, 5)
        self.datapoints_layout_root = QHBoxLayout()
        self.datapoints_layout_root.setObjectName(u"datapoints_layout_root")
        self.value_01 = QVBoxLayout()
        self.value_01.setObjectName(u"value_01")
        self.label_01 = QLabel(self.datapoints)
        self.label_01.setObjectName(u"label_01")
        self.label_01.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_01.addWidget(self.label_01)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.value_01.addItem(self.verticalSpacer_2)


        self.datapoints_layout_root.addLayout(self.value_01)

        self.value_02 = QVBoxLayout()
        self.value_02.setObjectName(u"value_02")
        self.label_02 = QLabel(self.datapoints)
        self.label_02.setObjectName(u"label_02")
        self.label_02.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_02.addWidget(self.label_02)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.value_02.addItem(self.verticalSpacer_3)


        self.datapoints_layout_root.addLayout(self.value_02)

        self.value_03 = QVBoxLayout()
        self.value_03.setObjectName(u"value_03")
        self.label_3 = QLabel(self.datapoints)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_03.addWidget(self.label_3)

        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.value_03.addItem(self.verticalSpacer_5)


        self.datapoints_layout_root.addLayout(self.value_03)

        self.value_04 = QVBoxLayout()
        self.value_04.setObjectName(u"value_04")
        self.label_4 = QLabel(self.datapoints)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_04.addWidget(self.label_4)

        self.verticalSpacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.value_04.addItem(self.verticalSpacer_6)


        self.datapoints_layout_root.addLayout(self.value_04)

        self.value_05 = QVBoxLayout()
        self.value_05.setObjectName(u"value_05")
        self.label_5 = QLabel(self.datapoints)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_05.addWidget(self.label_5)

        self.verticalSpacer_7 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.value_05.addItem(self.verticalSpacer_7)


        self.datapoints_layout_root.addLayout(self.value_05)

        self.value_06 = QVBoxLayout()
        self.value_06.setObjectName(u"value_06")
        self.label_6 = QLabel(self.datapoints)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.value_06.addWidget(self.label_6)

        self.verticalSpacer_8 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.value_06.addItem(self.verticalSpacer_8)


        self.datapoints_layout_root.addLayout(self.value_06)

        self.actions = QVBoxLayout()
        self.actions.setObjectName(u"actions")
        self.label_7 = QLabel(self.datapoints)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.actions.addWidget(self.label_7)

        self.verticalSpacer_9 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.actions.addItem(self.verticalSpacer_9)


        self.datapoints_layout_root.addLayout(self.actions)


        self.frame_2.addLayout(self.datapoints_layout_root)


        self.verticalLayout_5.addLayout(self.frame_2)


        self.horizontalLayout.addLayout(self.verticalLayout_5)


        self.verticalLayout_2.addWidget(self.datapoints)


        self.verticalLayout.addLayout(self.verticalLayout_2)


        self.retranslateUi(CurveWidget)

        QMetaObject.connectSlotsByName(CurveWidget)
    # setupUi

    def retranslateUi(self, CurveWidget):
        CurveWidget.setWindowTitle(QCoreApplication.translate("CurveWidget", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("CurveWidget", u"Preview", None))
        self.label.setText(QCoreApplication.translate("CurveWidget", u"Datapoints", None))
        self.add_data_point_button.setText(QCoreApplication.translate("CurveWidget", u"Add datapoint", None))
        self.label_01.setText(QCoreApplication.translate("CurveWidget", u"Distance", None))
        self.label_02.setText(QCoreApplication.translate("CurveWidget", u"Volume", None))
        self.label_3.setText(QCoreApplication.translate("CurveWidget", u"Slope Left", None))
        self.label_4.setText(QCoreApplication.translate("CurveWidget", u"Slope Right", None))
        self.label_5.setText(QCoreApplication.translate("CurveWidget", u"Mode Left", None))
        self.label_6.setText(QCoreApplication.translate("CurveWidget", u"Mode Right", None))
        self.label_7.setText(QCoreApplication.translate("CurveWidget", u"Actions", None))
    # retranslateUi

