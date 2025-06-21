# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGroupBox,
    QHBoxLayout, QMainWindow, QPlainTextEdit, QPushButton,
    QSizePolicy, QSplitter, QTabWidget, QVBoxLayout,
    QWidget)
import resources_rc

class Ui_Loading_editorMainWindow(object):
    def setupUi(self, Loading_editorMainWindow):
        if not Loading_editorMainWindow.objectName():
            Loading_editorMainWindow.setObjectName(u"Loading_editorMainWindow")
        Loading_editorMainWindow.resize(1292, 983)
        Loading_editorMainWindow.setStyleSheet(u"background-color: rgb(28, 28, 28);")
        self.centralwidget = QWidget(Loading_editorMainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_7 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_7.setSpacing(0)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.splitter_2 = QSplitter(self.centralwidget)
        self.splitter_2.setObjectName(u"splitter_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter_2.sizePolicy().hasHeightForWidth())
        self.splitter_2.setSizePolicy(sizePolicy)
        self.splitter_2.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_2.setOpaqueResize(True)
        self.splitter_2.setHandleWidth(4)
        self.screenshots = QGroupBox(self.splitter_2)
        self.screenshots.setObjectName(u"screenshots")
        sizePolicy.setHeightForWidth(self.screenshots.sizePolicy().hasHeightForWidth())
        self.screenshots.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(self.screenshots)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.screenshots_tabwidget = QTabWidget(self.screenshots)
        self.screenshots_tabwidget.setObjectName(u"screenshots_tabwidget")
        self.explorer_tab = QWidget()
        self.explorer_tab.setObjectName(u"explorer_tab")
        self.verticalLayout_8 = QVBoxLayout(self.explorer_tab)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.explorer = QFrame(self.explorer_tab)
        self.explorer.setObjectName(u"explorer")
        self.explorer.setFrameShape(QFrame.Shape.StyledPanel)
        self.explorer.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.explorer)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 4, 0, 4)

        self.verticalLayout_8.addWidget(self.explorer)

        self.screenshots_tabwidget.addTab(self.explorer_tab, "")
        self.timeline_tab = QWidget()
        self.timeline_tab.setObjectName(u"timeline_tab")
        self.verticalLayout_9 = QVBoxLayout(self.timeline_tab)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(1, 4, 1, 4)
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.refresh = QPushButton(self.timeline_tab)
        self.refresh.setObjectName(u"refresh")
        self.refresh.setMinimumSize(QSize(0, 32))
        self.refresh.setStyleSheet(u"\n"
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
        icon.addFile(u":/valve_common/icons/tools/common/refresh.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.refresh.setIcon(icon)
        self.refresh.setIconSize(QSize(20, 20))

        self.horizontalLayout_6.addWidget(self.refresh)

        self.generate_gifs = QPushButton(self.timeline_tab)
        self.generate_gifs.setObjectName(u"generate_gifs")
        self.generate_gifs.setMinimumSize(QSize(0, 32))
        self.generate_gifs.setStyleSheet(u"\n"
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
        icon1 = QIcon()
        icon1.addFile(u":/valve_common/icons/tools/common/control_play.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.generate_gifs.setIcon(icon1)
        self.generate_gifs.setIconSize(QSize(20, 20))

        self.horizontalLayout_6.addWidget(self.generate_gifs)


        self.verticalLayout_9.addLayout(self.horizontalLayout_6)

        self.screenshots_tabwidget.addTab(self.timeline_tab, "")

        self.verticalLayout.addWidget(self.screenshots_tabwidget)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.open_folder_button = QPushButton(self.screenshots)
        self.open_folder_button.setObjectName(u"open_folder_button")
        self.open_folder_button.setMinimumSize(QSize(0, 32))
        self.open_folder_button.setStyleSheet(u"\n"
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
        icon2 = QIcon()
        icon2.addFile(u":/icons/folder_open.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_folder_button.setIcon(icon2)
        self.open_folder_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.open_folder_button)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.history_mode = QCheckBox(self.screenshots)
        self.history_mode.setObjectName(u"history_mode")
        self.history_mode.setStyleSheet(u"\n"
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
        icon3 = QIcon()
        icon3.addFile(u":/icons/acute_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.history_mode.setIcon(icon3)
        self.history_mode.setIconSize(QSize(20, 20))
        self.history_mode.setChecked(True)

        self.horizontalLayout_4.addWidget(self.history_mode)

        self.make_commands = QPushButton(self.screenshots)
        self.make_commands.setObjectName(u"make_commands")
        self.make_commands.setMinimumSize(QSize(0, 32))
        self.make_commands.setStyleSheet(u"\n"
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
        icon4 = QIcon()
        icon4.addFile(u":/icons/data_object_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.make_commands.setIcon(icon4)
        self.make_commands.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.make_commands)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.delete_existings = QCheckBox(self.screenshots)
        self.delete_existings.setObjectName(u"delete_existings")
        self.delete_existings.setStyleSheet(u"\n"
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
        icon5 = QIcon()
        icon5.addFile(u":/icons/delete_sweep_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_existings.setIcon(icon5)
        self.delete_existings.setIconSize(QSize(20, 20))
        self.delete_existings.setChecked(True)

        self.horizontalLayout_2.addWidget(self.delete_existings)

        self.camera_name_mode = QCheckBox(self.screenshots)
        self.camera_name_mode.setObjectName(u"camera_name_mode")
        self.camera_name_mode.setStyleSheet(u"\n"
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
        icon6 = QIcon()
        icon6.addFile(u":/icons/colors_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.camera_name_mode.setIcon(icon6)
        self.camera_name_mode.setIconSize(QSize(20, 20))
        self.camera_name_mode.setChecked(True)

        self.horizontalLayout_2.addWidget(self.camera_name_mode)

        self.apply_screenshots_button = QPushButton(self.screenshots)
        self.apply_screenshots_button.setObjectName(u"apply_screenshots_button")
        self.apply_screenshots_button.setMinimumSize(QSize(0, 32))
        self.apply_screenshots_button.setStyleSheet(u"\n"
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
        icon7 = QIcon()
        icon7.addFile(u":/icons/check_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.apply_screenshots_button.setIcon(icon7)
        self.apply_screenshots_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.apply_screenshots_button)


        self.verticalLayout_5.addLayout(self.horizontalLayout_2)


        self.verticalLayout.addLayout(self.verticalLayout_5)

        self.splitter_2.addWidget(self.screenshots)
        self.splitter = QSplitter(self.splitter_2)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setMidLineWidth(0)
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.screenshot_preview = QGroupBox(self.splitter)
        self.screenshot_preview.setObjectName(u"screenshot_preview")
        sizePolicy.setHeightForWidth(self.screenshot_preview.sizePolicy().hasHeightForWidth())
        self.screenshot_preview.setSizePolicy(sizePolicy)
        self.screenshot_preview.setMinimumSize(QSize(400, 0))
        self.screenshot_preview.setMaximumSize(QSize(16777215, 16777215))
        self.screenshot_preview.setBaseSize(QSize(1200, 0))
        self.verticalLayout_6 = QVBoxLayout(self.screenshot_preview)
        self.verticalLayout_6.setSpacing(6)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 4, 0, 4)
        self.splitter.addWidget(self.screenshot_preview)
        self.frame_2 = QFrame(self.splitter)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMaximumSize(QSize(360, 16777215))
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.groupBox_2 = QGroupBox(self.frame_2)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(4, 4, 4, 4)
        self.svg_icon_frame = QFrame(self.groupBox_2)
        self.svg_icon_frame.setObjectName(u"svg_icon_frame")
        self.svg_icon_frame.setMinimumSize(QSize(0, 320))
        self.svg_icon_frame.setStyleSheet(u"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;")
        self.svg_icon_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.svg_icon_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.svg_icon_frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_4.addWidget(self.svg_icon_frame)

        self.apply_icon_button = QPushButton(self.groupBox_2)
        self.apply_icon_button.setObjectName(u"apply_icon_button")
        self.apply_icon_button.setEnabled(True)
        self.apply_icon_button.setMinimumSize(QSize(0, 32))
        self.apply_icon_button.setStyleSheet(u"\n"
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
        self.apply_icon_button.setIcon(icon7)
        self.apply_icon_button.setIconSize(QSize(20, 20))

        self.verticalLayout_4.addWidget(self.apply_icon_button)


        self.verticalLayout_3.addWidget(self.groupBox_2)

        self.groupBox = QGroupBox(self.frame_2)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(4, 4, 4, 4)
        self.PlainTextEdit_Description_2 = QPlainTextEdit(self.groupBox)
        self.PlainTextEdit_Description_2.setObjectName(u"PlainTextEdit_Description_2")
        self.PlainTextEdit_Description_2.setStyleSheet(u"    QPlainTextEdit {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding: 4px;\n"
"        padding-left: 6px;\n"
"        padding-right: 6px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"\n"
"\n"
"\n"
"    QPlainTextEdit:focus {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding: 4px;\n"
"        padding-left: 6px;\n"
"        padding-right: 6px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QPlainTextEdit:hover {\n"
"    }\n"
"    QPlainTextEdit:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"        f"
                        "ont: 580 9pt \"Segoe UI\";\n"
"\n"
"    }")

        self.verticalLayout_2.addWidget(self.PlainTextEdit_Description_2)

        self.apply_description_button = QPushButton(self.groupBox)
        self.apply_description_button.setObjectName(u"apply_description_button")
        self.apply_description_button.setMinimumSize(QSize(0, 32))
        self.apply_description_button.setStyleSheet(u"\n"
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
        self.apply_description_button.setIcon(icon7)
        self.apply_description_button.setIconSize(QSize(20, 20))

        self.verticalLayout_2.addWidget(self.apply_description_button)


        self.verticalLayout_3.addWidget(self.groupBox)

        self.splitter.addWidget(self.frame_2)
        self.splitter_2.addWidget(self.splitter)

        self.verticalLayout_7.addWidget(self.splitter_2)

        Loading_editorMainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(Loading_editorMainWindow)

        self.screenshots_tabwidget.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(Loading_editorMainWindow)
    # setupUi

    def retranslateUi(self, Loading_editorMainWindow):
        Loading_editorMainWindow.setWindowTitle(QCoreApplication.translate("Loading_editorMainWindow", u"MainWindow", None))
        self.screenshots.setTitle(QCoreApplication.translate("Loading_editorMainWindow", u"Screenshots", None))
        self.screenshots_tabwidget.setTabText(self.screenshots_tabwidget.indexOf(self.explorer_tab), QCoreApplication.translate("Loading_editorMainWindow", u"Explorer", None))
#if QT_CONFIG(tooltip)
        self.refresh.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:10pt; font-weight:580; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.refresh.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Refresh", None))
#if QT_CONFIG(tooltip)
        self.generate_gifs.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:10pt; font-weight:580; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.generate_gifs.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Generate gifs", None))
        self.screenshots_tabwidget.setTabText(self.screenshots_tabwidget.indexOf(self.timeline_tab), QCoreApplication.translate("Loading_editorMainWindow", u"Timeline", None))
#if QT_CONFIG(tooltip)
        self.open_folder_button.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:10pt; font-weight:580; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_folder_button.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Open folder", None))
#if QT_CONFIG(tooltip)
        self.history_mode.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<html><head/><body><p><br/></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.history_mode.setText(QCoreApplication.translate("Loading_editorMainWindow", u"History mode", None))
#if QT_CONFIG(tooltip)
        self.make_commands.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:580; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Generates screenshot commands based on <span style=\" font-family:'Courier New';\">point_camera</span> positions. Paste into the console to create images.<br />Images will be saved in:<br /><span style=\" font-family:'Courier New';\">game/screenshots/Hammer5Tools/LoadingScreen</span><br /><span style=\" font-weight:700;\">Warning:</span> All previous images will be deleted.</p>\n"
"<p style=\" margi"
                        "n-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">In History mode, images will be saved in:<br /><span style=\" font-family:'Courier New';\">game/screenshots/Hammer5Tools/History/Date</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.make_commands.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Generate commands", None))
#if QT_CONFIG(tooltip)
        self.delete_existings.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<html><head/><body><p>Deletes all existing screenshots on the loading screen.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.delete_existings.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Delete existing", None))
#if QT_CONFIG(tooltip)
        self.camera_name_mode.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<html><head/><body><p>Deletes all existing screenshots on the loading screen.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.camera_name_mode.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Camera Name", None))
#if QT_CONFIG(tooltip)
        self.apply_screenshots_button.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:10pt; font-weight:580; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.apply_screenshots_button.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Set loading screenshots", None))
        self.screenshot_preview.setTitle(QCoreApplication.translate("Loading_editorMainWindow", u"Screenshot Preview", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Loading_editorMainWindow", u"Icon", None))
        self.apply_icon_button.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Apply Icon", None))
        self.groupBox.setTitle(QCoreApplication.translate("Loading_editorMainWindow", u"Description", None))
#if QT_CONFIG(tooltip)
        self.PlainTextEdit_Description_2.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.PlainTextEdit_Description_2.setPlainText("")
        self.PlainTextEdit_Description_2.setPlaceholderText(QCoreApplication.translate("Loading_editorMainWindow", u"A community map created by:", None))
        self.apply_description_button.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Apply description", None))
    # retranslateUi

