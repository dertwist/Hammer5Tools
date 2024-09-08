# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preferences.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame,
    QHBoxLayout, QLabel, QLayout, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QTabWidget,
    QVBoxLayout, QWidget)
import rc_resources

class Ui_preferences_dialog(object):
    def setupUi(self, preferences_dialog):
        if not preferences_dialog.objectName():
            preferences_dialog.setObjectName(u"preferences_dialog")
        preferences_dialog.resize(800, 400)
        preferences_dialog.setMinimumSize(QSize(600, 300))
        preferences_dialog.setMaximumSize(QSize(1000, 1600))
        preferences_dialog.setModal(False)
        self.verticalLayout = QVBoxLayout(preferences_dialog)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(preferences_dialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setTabPosition(QTabWidget.North)
        self.tabWidget.setTabShape(QTabWidget.Rounded)
        self.tabWidget.setTabBarAutoHide(False)
        self.Paths = QWidget()
        self.Paths.setObjectName(u"Paths")
        self.verticalLayout_2 = QVBoxLayout(self.Paths)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.frame_8 = QFrame(self.Paths)
        self.frame_8.setObjectName(u"frame_8")
        self.frame_8.setMaximumSize(QSize(16777215, 48))
        self.frame_8.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame_8.setFrameShape(QFrame.NoFrame)
        self.frame_8.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_8 = QHBoxLayout(self.frame_8)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.frame_10 = QFrame(self.frame_8)
        self.frame_10.setObjectName(u"frame_10")
        self.frame_10.setStyleSheet(u"border:0px;")
        self.frame_10.setFrameShape(QFrame.StyledPanel)
        self.frame_10.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_9 = QHBoxLayout(self.frame_10)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.label_9 = QLabel(self.frame_10)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setMinimumSize(QSize(130, 0))
        self.label_9.setMaximumSize(QSize(130, 16777215))
        self.label_9.setStyleSheet(u"        font: 580 10pt \"Segoe UI\";\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;")
        self.label_9.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_9.addWidget(self.label_9)


        self.horizontalLayout_8.addWidget(self.frame_10)

        self.preferences_lineedit_steam_path = QLineEdit(self.frame_8)
        self.preferences_lineedit_steam_path.setObjectName(u"preferences_lineedit_steam_path")
        self.preferences_lineedit_steam_path.setStyleSheet(u"    QLineEdit {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QLineEdit {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QLineEdit:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QLineEdit:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"        font: 580 9pt \"Segoe UI\";\n"
"\n"
"    }")
        self.preferences_lineedit_steam_path.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_8.addWidget(self.preferences_lineedit_steam_path)


        self.verticalLayout_2.addWidget(self.frame_8)

        self.frame = QFrame(self.Paths)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(16777215, 48))
        self.frame.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame.setFrameShape(QFrame.NoFrame)
        self.frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_8 = QLabel(self.frame)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setMinimumSize(QSize(130, 0))
        self.label_8.setMaximumSize(QSize(130, 16777215))
        self.label_8.setStyleSheet(u"        font: 580 10pt \"Segoe UI\";\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;")
        self.label_8.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_2.addWidget(self.label_8)

        self.preferences_lineedit_cs2_path = QLineEdit(self.frame)
        self.preferences_lineedit_cs2_path.setObjectName(u"preferences_lineedit_cs2_path")
        self.preferences_lineedit_cs2_path.setStyleSheet(u"    QLineEdit {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QLineEdit {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QLineEdit:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QLineEdit:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"        font: 580 9pt \"Segoe UI\";\n"
"\n"
"    }")
        self.preferences_lineedit_cs2_path.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_2.addWidget(self.preferences_lineedit_cs2_path)


        self.verticalLayout_2.addWidget(self.frame)

        self.frame_4 = QFrame(self.Paths)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setMaximumSize(QSize(16777215, 48))
        self.frame_4.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame_4.setFrameShape(QFrame.NoFrame)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.frame_5 = QFrame(self.frame_4)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setStyleSheet(u"border:0px;")
        self.frame_5.setFrameShape(QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_5)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.label_6 = QLabel(self.frame_5)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setMinimumSize(QSize(130, 0))
        self.label_6.setMaximumSize(QSize(130, 16777215))
        self.label_6.setStyleSheet(u"        font: 580 10pt \"Segoe UI\";\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;")
        self.label_6.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout.addWidget(self.label_6)


        self.horizontalLayout_6.addWidget(self.frame_5)

        self.preferences_lineedit_user_presets_path = QLineEdit(self.frame_4)
        self.preferences_lineedit_user_presets_path.setObjectName(u"preferences_lineedit_user_presets_path")
        self.preferences_lineedit_user_presets_path.setStyleSheet(u"    QLineEdit {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QLineEdit {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QLineEdit:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QLineEdit:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"        font: 580 9pt \"Segoe UI\";\n"
"\n"
"    }")
        self.preferences_lineedit_user_presets_path.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_6.addWidget(self.preferences_lineedit_user_presets_path)


        self.verticalLayout_2.addWidget(self.frame_4)

        self.frame_3 = QFrame(self.Paths)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16777215, 48))
        self.frame_3.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame_3.setFrameShape(QFrame.NoFrame)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.frame_6 = QFrame(self.frame_3)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setStyleSheet(u"border:0px;")
        self.frame_6.setFrameShape(QFrame.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_7 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.label_7 = QLabel(self.frame_6)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setMinimumSize(QSize(130, 0))
        self.label_7.setMaximumSize(QSize(130, 16777215))
        self.label_7.setStyleSheet(u"        font: 580 10pt \"Segoe UI\";\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;")
        self.label_7.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_7.addWidget(self.label_7)


        self.horizontalLayout_4.addWidget(self.frame_6)

        self.preferences_lineedit_archive_path = QLineEdit(self.frame_3)
        self.preferences_lineedit_archive_path.setObjectName(u"preferences_lineedit_archive_path")
        self.preferences_lineedit_archive_path.setStyleSheet(u"    QLineEdit {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QLineEdit {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QLineEdit:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QLineEdit:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"        font: 580 9pt \"Segoe UI\";\n"
"\n"
"    }")
        self.preferences_lineedit_archive_path.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_4.addWidget(self.preferences_lineedit_archive_path)


        self.verticalLayout_2.addWidget(self.frame_3)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)

        self.tabWidget.addTab(self.Paths, "")
        self.Discord_status = QWidget()
        self.Discord_status.setObjectName(u"Discord_status")
        self.verticalLayout_3 = QVBoxLayout(self.Discord_status)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.frame_7 = QFrame(self.Discord_status)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setEnabled(True)
        self.frame_7.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame_7.setFrameShape(QFrame.NoFrame)
        self.frame_7.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_7)
        self.horizontalLayout_5.setSpacing(18)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(9, 9, 9, 9)
        self.checkBox_show_in_hammer_discord_status = QCheckBox(self.frame_7)
        self.checkBox_show_in_hammer_discord_status.setObjectName(u"checkBox_show_in_hammer_discord_status")
        self.checkBox_show_in_hammer_discord_status.setMinimumSize(QSize(96, 32))
        self.checkBox_show_in_hammer_discord_status.setLayoutDirection(Qt.LeftToRight)
        self.checkBox_show_in_hammer_discord_status.setStyleSheet(u"QCheckBox {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    padding-left: 4px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"/* -------------------------- */\n"
"\n"
"\n"
"QCheckBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")
        self.checkBox_show_in_hammer_discord_status.setTristate(False)

        self.horizontalLayout_5.addWidget(self.checkBox_show_in_hammer_discord_status)

        self.checkBox_hide_project_name_discord_status = QCheckBox(self.frame_7)
        self.checkBox_hide_project_name_discord_status.setObjectName(u"checkBox_hide_project_name_discord_status")
        self.checkBox_hide_project_name_discord_status.setMinimumSize(QSize(196, 32))
        self.checkBox_hide_project_name_discord_status.setStyleSheet(u"QCheckBox {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    padding-left: 4px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"/* -------------------------- */\n"
"\n"
"\n"
"QCheckBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")

        self.horizontalLayout_5.addWidget(self.checkBox_hide_project_name_discord_status)


        self.verticalLayout_3.addWidget(self.frame_7)

        self.frame_13 = QFrame(self.Discord_status)
        self.frame_13.setObjectName(u"frame_13")
        self.frame_13.setFrameShape(QFrame.NoFrame)
        self.frame_13.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_15 = QHBoxLayout(self.frame_13)
        self.horizontalLayout_15.setSpacing(0)
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.horizontalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.frame_9 = QFrame(self.frame_13)
        self.frame_9.setObjectName(u"frame_9")
        self.frame_9.setMaximumSize(QSize(16777215, 48))
        self.frame_9.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame_9.setFrameShape(QFrame.NoFrame)
        self.frame_9.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_13 = QHBoxLayout(self.frame_9)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.frame_12 = QFrame(self.frame_9)
        self.frame_12.setObjectName(u"frame_12")
        self.frame_12.setStyleSheet(u"border:0px;")
        self.frame_12.setFrameShape(QFrame.StyledPanel)
        self.frame_12.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_14 = QHBoxLayout(self.frame_12)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(0, 0, 0, 0)

        self.horizontalLayout_13.addWidget(self.frame_12)

        self.label_12 = QLabel(self.frame_9)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setMinimumSize(QSize(130, 0))
        self.label_12.setMaximumSize(QSize(130, 16777215))
        self.label_12.setStyleSheet(u"        font: 580 10pt \"Segoe UI\";\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;")
        self.label_12.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_13.addWidget(self.label_12)

        self.editline_custom_discord_status = QLineEdit(self.frame_9)
        self.editline_custom_discord_status.setObjectName(u"editline_custom_discord_status")
        self.editline_custom_discord_status.setStyleSheet(u"    QLineEdit {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QLineEdit {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QLineEdit:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QLineEdit:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"        font: 580 9pt \"Segoe UI\";\n"
"\n"
"    }")
        self.editline_custom_discord_status.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.horizontalLayout_13.addWidget(self.editline_custom_discord_status)


        self.horizontalLayout_15.addWidget(self.frame_9)


        self.verticalLayout_3.addWidget(self.frame_13)

        self.frame_14 = QFrame(self.Discord_status)
        self.frame_14.setObjectName(u"frame_14")
        self.frame_14.setFrameShape(QFrame.NoFrame)
        self.frame_14.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_16 = QHBoxLayout(self.frame_14)
        self.horizontalLayout_16.setSpacing(0)
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.horizontalLayout_16.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_3.addWidget(self.frame_14)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_2)

        self.tabWidget.addTab(self.Discord_status, "")
        self.onter_preferences_tab = QWidget()
        self.onter_preferences_tab.setObjectName(u"onter_preferences_tab")
        self.verticalLayout_4 = QVBoxLayout(self.onter_preferences_tab)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.frame_11 = QFrame(self.onter_preferences_tab)
        self.frame_11.setObjectName(u"frame_11")
        self.frame_11.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame_11.setFrameShape(QFrame.NoFrame)
        self.frame_11.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_10 = QHBoxLayout(self.frame_11)
        self.horizontalLayout_10.setSpacing(18)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(9, 9, 9, 9)
        self.setup_ncm_mode = QPushButton(self.frame_11)
        self.setup_ncm_mode.setObjectName(u"setup_ncm_mode")
        self.setup_ncm_mode.setStyleSheet(u"    QLabel {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
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

        self.horizontalLayout_10.addWidget(self.setup_ncm_mode)

        self.checkBox_start_with_system = QCheckBox(self.frame_11)
        self.checkBox_start_with_system.setObjectName(u"checkBox_start_with_system")
        self.checkBox_start_with_system.setEnabled(True)
        self.checkBox_start_with_system.setMinimumSize(QSize(96, 32))
        self.checkBox_start_with_system.setLayoutDirection(Qt.LeftToRight)
        self.checkBox_start_with_system.setStyleSheet(u"QCheckBox {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    padding-left: 4px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"/* -------------------------- */\n"
"\n"
"\n"
"QCheckBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")
        self.checkBox_start_with_system.setTristate(False)

        self.horizontalLayout_10.addWidget(self.checkBox_start_with_system)


        self.verticalLayout_4.addWidget(self.frame_11)

        self.frame_17 = QFrame(self.onter_preferences_tab)
        self.frame_17.setObjectName(u"frame_17")
        self.frame_17.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame_17.setFrameShape(QFrame.NoFrame)
        self.frame_17.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_18 = QHBoxLayout(self.frame_17)
        self.horizontalLayout_18.setSpacing(18)
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.horizontalLayout_18.setContentsMargins(9, 9, 9, 9)
        self.launch_addon_after_nosteamlogon_fix = QCheckBox(self.frame_17)
        self.launch_addon_after_nosteamlogon_fix.setObjectName(u"launch_addon_after_nosteamlogon_fix")
        self.launch_addon_after_nosteamlogon_fix.setEnabled(True)
        self.launch_addon_after_nosteamlogon_fix.setMinimumSize(QSize(96, 32))
        self.launch_addon_after_nosteamlogon_fix.setLayoutDirection(Qt.LeftToRight)
        self.launch_addon_after_nosteamlogon_fix.setStyleSheet(u"QCheckBox {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    padding-left: 4px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"/* -------------------------- */\n"
"\n"
"\n"
"QCheckBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")
        self.launch_addon_after_nosteamlogon_fix.setTristate(False)

        self.horizontalLayout_18.addWidget(self.launch_addon_after_nosteamlogon_fix)

        self.checkBox_enable_console = QCheckBox(self.frame_17)
        self.checkBox_enable_console.setObjectName(u"checkBox_enable_console")
        self.checkBox_enable_console.setEnabled(True)
        self.checkBox_enable_console.setMinimumSize(QSize(96, 32))
        self.checkBox_enable_console.setLayoutDirection(Qt.LeftToRight)
        self.checkBox_enable_console.setStyleSheet(u"QCheckBox {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    padding-left: 4px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"/* -------------------------- */\n"
"\n"
"\n"
"QCheckBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")
        self.checkBox_enable_console.setTristate(False)

        self.horizontalLayout_18.addWidget(self.checkBox_enable_console)


        self.verticalLayout_4.addWidget(self.frame_17)

        self.frame_15 = QFrame(self.onter_preferences_tab)
        self.frame_15.setObjectName(u"frame_15")
        self.frame_15.setStyleSheet(u"background-color: #1C1C1C;")
        self.frame_15.setFrameShape(QFrame.NoFrame)
        self.frame_15.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_17 = QHBoxLayout(self.frame_15)
        self.horizontalLayout_17.setSpacing(18)
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.horizontalLayout_17.setContentsMargins(9, 9, 9, 9)
        self.check_update_button = QPushButton(self.frame_15)
        self.check_update_button.setObjectName(u"check_update_button")
        self.check_update_button.setStyleSheet(u"    QLabel {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
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

        self.horizontalLayout_17.addWidget(self.check_update_button)

        self.version_label = QLabel(self.frame_15)
        self.version_label.setObjectName(u"version_label")

        self.horizontalLayout_17.addWidget(self.version_label)


        self.verticalLayout_4.addWidget(self.frame_15)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_3)

        self.tabWidget.addTab(self.onter_preferences_tab, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.frame_2 = QFrame(preferences_dialog)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMaximumSize(QSize(16777215, 48))
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_3.setSpacing(6)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.frame_16 = QFrame(self.frame_2)
        self.frame_16.setObjectName(u"frame_16")
        self.frame_16.setFrameShape(QFrame.StyledPanel)
        self.frame_16.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_11 = QHBoxLayout(self.frame_16)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.open_presets_folder_button = QPushButton(self.frame_16)
        self.open_presets_folder_button.setObjectName(u"open_presets_folder_button")
        self.open_presets_folder_button.setMinimumSize(QSize(0, 32))
        self.open_presets_folder_button.setStyleSheet(u"    QLabel {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 600 10pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
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
        icon.addFile(u":/icons/folder_open.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_presets_folder_button.setIcon(icon)
        self.open_presets_folder_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_11.addWidget(self.open_presets_folder_button)

        self.open_settings_folder_button = QPushButton(self.frame_16)
        self.open_settings_folder_button.setObjectName(u"open_settings_folder_button")
        self.open_settings_folder_button.setMinimumSize(QSize(0, 32))
        self.open_settings_folder_button.setStyleSheet(u"    QLabel {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 600 10pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
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
        self.open_settings_folder_button.setIcon(icon)
        self.open_settings_folder_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_11.addWidget(self.open_settings_folder_button)


        self.horizontalLayout_3.addWidget(self.frame_16)

        self.preferences_apply_button = QPushButton(self.frame_2)
        self.preferences_apply_button.setObjectName(u"preferences_apply_button")
        self.preferences_apply_button.setMinimumSize(QSize(0, 32))
        self.preferences_apply_button.setStyleSheet(u"    QLabel {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 600 10pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
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
        icon1.addFile(u":/icons/check_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.preferences_apply_button.setIcon(icon1)
        self.preferences_apply_button.setIconSize(QSize(24, 24))

        self.horizontalLayout_3.addWidget(self.preferences_apply_button)


        self.verticalLayout.addWidget(self.frame_2)


        self.retranslateUi(preferences_dialog)

        self.tabWidget.setCurrentIndex(2)


        QMetaObject.connectSlotsByName(preferences_dialog)
    # setupUi

    def retranslateUi(self, preferences_dialog):
        preferences_dialog.setWindowTitle(QCoreApplication.translate("preferences_dialog", u"Settings", None))
        self.label_9.setText(QCoreApplication.translate("preferences_dialog", u"Steam path:", None))
        self.label_8.setText(QCoreApplication.translate("preferences_dialog", u"Path to cs2:", None))
        self.label_6.setText(QCoreApplication.translate("preferences_dialog", u"User presets path:", None))
        self.label_7.setText(QCoreApplication.translate("preferences_dialog", u"Archive path:", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Paths), QCoreApplication.translate("preferences_dialog", u"Paths", None))
        self.checkBox_show_in_hammer_discord_status.setText(QCoreApplication.translate("preferences_dialog", u"Show hammer status in Discord", None))
        self.checkBox_hide_project_name_discord_status.setText(QCoreApplication.translate("preferences_dialog", u"Hide project name", None))
        self.label_12.setText(QCoreApplication.translate("preferences_dialog", u"Custom status:", None))
        self.editline_custom_discord_status.setText(QCoreApplication.translate("preferences_dialog", u"Doing stuff", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.Discord_status), QCoreApplication.translate("preferences_dialog", u"Discord Status", None))
        self.setup_ncm_mode.setText(QCoreApplication.translate("preferences_dialog", u"Setup NCM mode", None))
        self.checkBox_start_with_system.setText(QCoreApplication.translate("preferences_dialog", u"Start with system", None))
        self.launch_addon_after_nosteamlogon_fix.setText(QCoreApplication.translate("preferences_dialog", u"Launch the addon after NoSteamLogon fix", None))
        self.checkBox_enable_console.setText(QCoreApplication.translate("preferences_dialog", u"Enable console", None))
        self.check_update_button.setText(QCoreApplication.translate("preferences_dialog", u"Check Update", None))
        self.version_label.setText(QCoreApplication.translate("preferences_dialog", u"TextLabel", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.onter_preferences_tab), QCoreApplication.translate("preferences_dialog", u"Other", None))
        self.open_presets_folder_button.setText(QCoreApplication.translate("preferences_dialog", u" Presets", None))
        self.open_settings_folder_button.setText(QCoreApplication.translate("preferences_dialog", u" Settings", None))
        self.preferences_apply_button.setText(QCoreApplication.translate("preferences_dialog", u"Apply", None))
    # retranslateUi

