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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QHBoxLayout,
    QLabel, QLineEdit, QSizePolicy, QVBoxLayout,
    QWidget)
import resources_rc

class Ui_preferences_dialog(object):
    def setupUi(self, preferences_dialog):
        if not preferences_dialog.objectName():
            preferences_dialog.setObjectName(u"preferences_dialog")
        preferences_dialog.resize(1056, 240)
        preferences_dialog.setMinimumSize(QSize(600, 240))
        preferences_dialog.setMaximumSize(QSize(1300, 240))
        icon = QIcon()
        icon.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        preferences_dialog.setWindowIcon(icon)
        preferences_dialog.setModal(False)
        self.verticalLayout = QVBoxLayout(preferences_dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(preferences_dialog)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.lineEdit_preview = QLineEdit(preferences_dialog)
        self.lineEdit_preview.setObjectName(u"lineEdit_preview")
        self.lineEdit_preview.setReadOnly(True)

        self.horizontalLayout.addWidget(self.lineEdit_preview)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(preferences_dialog)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.lineEdit_custom = QLineEdit(preferences_dialog)
        self.lineEdit_custom.setObjectName(u"lineEdit_custom")

        self.horizontalLayout_2.addWidget(self.lineEdit_custom)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.checkBox_nocustomer_machine = QCheckBox(preferences_dialog)
        self.checkBox_nocustomer_machine.setObjectName(u"checkBox_nocustomer_machine")
        self.checkBox_nocustomer_machine.setMinimumSize(QSize(96, 32))
        self.checkBox_nocustomer_machine.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.checkBox_nocustomer_machine.setStyleSheet(u"\n"
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
        self.checkBox_nocustomer_machine.setTristate(False)

        self.horizontalLayout_3.addWidget(self.checkBox_nocustomer_machine)

        self.checkBox_gpuraytracing = QCheckBox(preferences_dialog)
        self.checkBox_gpuraytracing.setObjectName(u"checkBox_gpuraytracing")
        self.checkBox_gpuraytracing.setMinimumSize(QSize(96, 32))
        self.checkBox_gpuraytracing.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.checkBox_gpuraytracing.setStyleSheet(u"\n"
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
        self.checkBox_gpuraytracing.setTristate(False)

        self.horizontalLayout_3.addWidget(self.checkBox_gpuraytracing)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.checkBox_open_vmap = QCheckBox(preferences_dialog)
        self.checkBox_open_vmap.setObjectName(u"checkBox_open_vmap")
        self.checkBox_open_vmap.setMinimumSize(QSize(96, 32))
        self.checkBox_open_vmap.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.checkBox_open_vmap.setStyleSheet(u"\n"
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
        self.checkBox_open_vmap.setTristate(False)

        self.horizontalLayout_4.addWidget(self.checkBox_open_vmap)

        self.checkBox_open_tools = QCheckBox(preferences_dialog)
        self.checkBox_open_tools.setObjectName(u"checkBox_open_tools")
        self.checkBox_open_tools.setMinimumSize(QSize(96, 32))
        self.checkBox_open_tools.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.checkBox_open_tools.setStyleSheet(u"\n"
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
        self.checkBox_open_tools.setTristate(False)

        self.horizontalLayout_4.addWidget(self.checkBox_open_tools)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.checkBox_steam = QCheckBox(preferences_dialog)
        self.checkBox_steam.setObjectName(u"checkBox_steam")
        self.checkBox_steam.setMinimumSize(QSize(96, 32))
        self.checkBox_steam.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.checkBox_steam.setStyleSheet(u"\n"
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
        self.checkBox_steam.setTristate(False)

        self.horizontalLayout_5.addWidget(self.checkBox_steam)

        self.checkBox_show_retail = QCheckBox(preferences_dialog)
        self.checkBox_show_retail.setObjectName(u"checkBox_show_retail")
        self.checkBox_show_retail.setMinimumSize(QSize(96, 32))
        self.checkBox_show_retail.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.checkBox_show_retail.setStyleSheet(u"\n"
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
        self.checkBox_show_retail.setTristate(False)

        self.horizontalLayout_5.addWidget(self.checkBox_show_retail)

        self.checkBox_no_insecure = QCheckBox(preferences_dialog)
        self.checkBox_no_insecure.setObjectName(u"checkBox_no_insecure")
        self.checkBox_no_insecure.setMinimumSize(QSize(96, 32))
        self.checkBox_no_insecure.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.checkBox_no_insecure.setStyleSheet(u"\n"
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
        self.checkBox_no_insecure.setTristate(False)

        self.horizontalLayout_5.addWidget(self.checkBox_no_insecure)


        self.verticalLayout.addLayout(self.horizontalLayout_5)


        self.retranslateUi(preferences_dialog)

        QMetaObject.connectSlotsByName(preferences_dialog)
    # setupUi

    def retranslateUi(self, preferences_dialog):
        preferences_dialog.setWindowTitle(QCoreApplication.translate("preferences_dialog", u"Lanuch options", None))
        self.label.setText(QCoreApplication.translate("preferences_dialog", u"Preview", None))
        self.label_2.setText(QCoreApplication.translate("preferences_dialog", u"Custom", None))
        self.lineEdit_custom.setText("")
        self.lineEdit_custom.setPlaceholderText(QCoreApplication.translate("preferences_dialog", u"Custom commands", None))
        self.checkBox_nocustomer_machine.setText(QCoreApplication.translate("preferences_dialog", u"No customer machine", None))
        self.checkBox_gpuraytracing.setText(QCoreApplication.translate("preferences_dialog", u"Gpu ray tracing", None))
        self.checkBox_open_vmap.setText(QCoreApplication.translate("preferences_dialog", u"Open vmap", None))
        self.checkBox_open_tools.setText(QCoreApplication.translate("preferences_dialog", u"Open tools", None))
        self.checkBox_steam.setText(QCoreApplication.translate("preferences_dialog", u"Steam", None))
        self.checkBox_show_retail.setText(QCoreApplication.translate("preferences_dialog", u"Retail", None))
        self.checkBox_no_insecure.setText(QCoreApplication.translate("preferences_dialog", u"No insecure", None))
    # retranslateUi

