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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)
import resources_rc

class Ui_documentation_dialog(object):
    def setupUi(self, documentation_dialog):
        if not documentation_dialog.objectName():
            documentation_dialog.setObjectName(u"documentation_dialog")
        documentation_dialog.resize(645, 505)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(documentation_dialog.sizePolicy().hasHeightForWidth())
        documentation_dialog.setSizePolicy(sizePolicy)
        documentation_dialog.setMinimumSize(QSize(645, 505))
        documentation_dialog.setMaximumSize(QSize(645, 505))
        documentation_dialog.setStyleSheet(u"background-color: #1C1C1C;")
        documentation_dialog.setSizeGripEnabled(False)
        documentation_dialog.setModal(False)
        self.verticalLayout = QVBoxLayout(documentation_dialog)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(documentation_dialog)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(0, 180))
        self.frame.setMaximumSize(QSize(16777215, 180))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"image: url(:/images/help/header.png);")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.label)

        self.version = QLabel(self.frame)
        self.version.setObjectName(u"version")
        self.version.setMaximumSize(QSize(16777215, 16))
        font = QFont()
        font.setFamilies([u"Segoe UI Black"])
        font.setPointSize(13)
        self.version.setFont(font)
        self.version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.version)


        self.verticalLayout.addWidget(self.frame)

        self.frame_4 = QFrame(documentation_dialog)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_4)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_3 = QLabel(self.frame_4)
        self.label_3.setObjectName(u"label_3")
        font1 = QFont()
        font1.setPointSize(11)
        self.label_3.setFont(font1)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_2.addWidget(self.label_3)

        self.label_4 = QLabel(self.frame_4)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setMinimumSize(QSize(400, 200))
        self.label_4.setStyleSheet(u"image: url(:/images/help/about/tooltip_help.png);")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_2.addWidget(self.label_4)


        self.verticalLayout.addWidget(self.frame_4)

        self.frame_3 = QFrame(documentation_dialog)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16777215, 44))
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_3.setSpacing(6)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(9, 0, 9, 0)
        self.open_documentation_button = QPushButton(self.frame_3)
        self.open_documentation_button.setObjectName(u"open_documentation_button")
        self.open_documentation_button.setStyleSheet(u"    QPushButton {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"    \n"
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
        icon.addFile(u":/icons/developer_guide_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_documentation_button.setIcon(icon)
        self.open_documentation_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.open_documentation_button)

        self.request_a_new_feature_button = QPushButton(self.frame_3)
        self.request_a_new_feature_button.setObjectName(u"request_a_new_feature_button")
        self.request_a_new_feature_button.setStyleSheet(u"    QPushButton {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"    \n"
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
        icon1 = QIcon()
        icon1.addFile(u":/icons/emoji_objects_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.request_a_new_feature_button.setIcon(icon1)
        self.request_a_new_feature_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.request_a_new_feature_button)


        self.verticalLayout.addWidget(self.frame_3)


        self.retranslateUi(documentation_dialog)

        QMetaObject.connectSlotsByName(documentation_dialog)
    # setupUi

    def retranslateUi(self, documentation_dialog):
        documentation_dialog.setWindowTitle(QCoreApplication.translate("documentation_dialog", u"About", None))
        self.label.setText("")
        self.version.setText(QCoreApplication.translate("documentation_dialog", u"Version: 1.0.0", None))
        self.label_3.setText(QCoreApplication.translate("documentation_dialog", u"Use tooltips for understanding the program: \n"
"For almost all buttons, an explanation appears when you hold your cursor over a button.", None))
        self.label_4.setText("")
        self.open_documentation_button.setText(QCoreApplication.translate("documentation_dialog", u"Documentation", None))
        self.request_a_new_feature_button.setText(QCoreApplication.translate("documentation_dialog", u"Feedback", None))
    # retranslateUi

