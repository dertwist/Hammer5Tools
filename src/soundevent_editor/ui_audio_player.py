# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'audio_player.ui'
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
    QLabel, QPushButton, QSizePolicy, QSlider,
    QVBoxLayout, QWidget)
import resources_rc

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1190, 64)
        Form.setMinimumSize(QSize(512, 0))
        Form.setMaximumSize(QSize(16666, 64))
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.content = QFrame(Form)
        self.content.setObjectName(u"content")
        self.content.setMaximumSize(QSize(16777215, 16777215))
        self.content.setFrameShape(QFrame.Shape.StyledPanel)
        self.content.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.content)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.time = QLabel(self.content)
        self.time.setObjectName(u"time")

        self.horizontalLayout.addWidget(self.time)

        self.timeline_slider = QSlider(self.content)
        self.timeline_slider.setObjectName(u"timeline_slider")
        self.timeline_slider.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout.addWidget(self.timeline_slider)

        self.play_button = QPushButton(self.content)
        self.play_button.setObjectName(u"play_button")
        self.play_button.setStyleSheet(u"\n"
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
        icon.addFile(u":/valve_common/icons/tools/common/control_play.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.play_button.setIcon(icon)
        self.play_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.play_button)

        self.loop_checkbox = QCheckBox(self.content)
        self.loop_checkbox.setObjectName(u"loop_checkbox")
        self.loop_checkbox.setMaximumSize(QSize(16777215, 30))
        self.loop_checkbox.setStyleSheet(u"\n"
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
"    }\n"
"QCheckBox::indicator {\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://valve_common/icons/tools/common/control_no_loop.png);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    image: url(://valve_common/icons/tools/common/control_loop.png);\n"
"}")

        self.horizontalLayout.addWidget(self.loop_checkbox)


        self.verticalLayout.addWidget(self.content)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.time.setText(QCoreApplication.translate("Form", u"00:00 : 00:00", None))
        self.play_button.setText(QCoreApplication.translate("Form", u"Play", None))
        self.loop_checkbox.setText(QCoreApplication.translate("Form", u"Loop", None))
    # retranslateUi

