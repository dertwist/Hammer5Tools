# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'create_addon_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFrame,
    QHBoxLayout, QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)
import src.resources_rc as resources_rc

class Ui_Create_addon_Dialog(object):
    def setupUi(self, Create_addon_Dialog):
        if not Create_addon_Dialog.objectName():
            Create_addon_Dialog.setObjectName(u"Create_addon_Dialog")
        Create_addon_Dialog.resize(656, 76)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Create_addon_Dialog.sizePolicy().hasHeightForWidth())
        Create_addon_Dialog.setSizePolicy(sizePolicy)
        Create_addon_Dialog.setMinimumSize(QSize(0, 0))
        Create_addon_Dialog.setMaximumSize(QSize(8999, 999))
        Create_addon_Dialog.setStyleSheet(u"")
        self.verticalLayout = QVBoxLayout(Create_addon_Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(2, 2, 2, 2)
        self.lineEdit_addon_name = QLineEdit(Create_addon_Dialog)
        self.lineEdit_addon_name.setObjectName(u"lineEdit_addon_name")
        self.lineEdit_addon_name.setMinimumSize(QSize(0, 32))
        self.lineEdit_addon_name.setMaximumSize(QSize(16777215, 32))
        self.lineEdit_addon_name.setStyleSheet(u"QLineEdit {\n"
"    border: 1px solid #CCCCCC;\n"
"    border-radius: 2px;\n"
"    color: #E3E3E3;\n"
"	font: 700 10pt \"Segoe UI\";\n"
"margin: 0px;\n"
"padding: 0px;\n"
"padding-top: 0px;\n"
"padding-bottom: 0px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"QLineEdit:focus {\n"
"    border: 1px solid #008CBA;\n"
"    background-color: #1C1C1C;\n"
"   margin: 0px;\n"
"   padding: 0px;\n"
"}\n"
"QLineEdit::selection {\n"
"    color: white;\n"
"}")
        self.lineEdit_addon_name.setMaxLength(32)
        self.lineEdit_addon_name.setClearButtonEnabled(True)

        self.verticalLayout.addWidget(self.lineEdit_addon_name)

        self.frame = QFrame(Create_addon_Dialog)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.presets_comobox = QComboBox(self.frame)
        self.presets_comobox.setObjectName(u"presets_comobox")
        self.presets_comobox.setMaximumSize(QSize(16777215, 32))

        self.horizontalLayout.addWidget(self.presets_comobox)

        self.create_addon_button = QPushButton(self.frame)
        self.create_addon_button.setObjectName(u"create_addon_button")
        self.create_addon_button.setMinimumSize(QSize(0, 32))
        self.create_addon_button.setStyleSheet(u"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 600 10pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
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
        icon.addFile(u":/icons/post_add_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_addon_button.setIcon(icon)
        self.create_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.create_addon_button)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(Create_addon_Dialog)

        QMetaObject.connectSlotsByName(Create_addon_Dialog)
    # setupUi

    def retranslateUi(self, Create_addon_Dialog):
        Create_addon_Dialog.setWindowTitle(QCoreApplication.translate("Create_addon_Dialog", u"Create Addon", None))
        self.lineEdit_addon_name.setInputMask("")
        self.lineEdit_addon_name.setPlaceholderText(QCoreApplication.translate("Create_addon_Dialog", u"de_mapname", None))
        self.presets_comobox.setPlaceholderText(QCoreApplication.translate("Create_addon_Dialog", u"No presets", None))
        self.create_addon_button.setText(QCoreApplication.translate("Create_addon_Dialog", u"Create Addon", None))
    # retranslateUi

