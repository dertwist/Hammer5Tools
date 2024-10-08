# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'soundevenet_editor_mainwindow.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDockWidget, QFrame,
    QHBoxLayout, QLayout, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QScrollArea,
    QSizePolicy, QToolButton, QVBoxLayout, QWidget)
import rc_resources

class Ui_SoundEvent_Editor_MainWindow(object):
    def setupUi(self, SoundEvent_Editor_MainWindow):
        if not SoundEvent_Editor_MainWindow.objectName():
            SoundEvent_Editor_MainWindow.setObjectName(u"SoundEvent_Editor_MainWindow")
        SoundEvent_Editor_MainWindow.resize(1035, 660)
        SoundEvent_Editor_MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.centralwidget = QWidget(SoundEvent_Editor_MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame_6 = QFrame(self.centralwidget)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.frame_6)
        self.verticalLayout_4.setSpacing(6)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.frame_7 = QFrame(self.frame_6)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setFrameShape(QFrame.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_7)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.frame_3 = QFrame(self.frame_7)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_3)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.add_a_property_button = QPushButton(self.frame_3)
        self.add_a_property_button.setObjectName(u"add_a_property_button")
        self.add_a_property_button.setStyleSheet(u"\n"
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

        self.verticalLayout_3.addWidget(self.add_a_property_button)

        self.scrollArea = QScrollArea(self.frame_3)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.soundevent_properties = QWidget()
        self.soundevent_properties.setObjectName(u"soundevent_properties")
        self.soundevent_properties.setGeometry(QRect(0, 0, 262, 608))
        self.verticalLayout_2 = QVBoxLayout(self.soundevent_properties)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setSizeConstraint(QLayout.SetFixedSize)
        self.scrollArea.setWidget(self.soundevent_properties)

        self.verticalLayout_3.addWidget(self.scrollArea)

        self.frame_2 = QFrame(self.frame_3)
        self.frame_2.setObjectName(u"frame_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy)
        self.frame_2.setMaximumSize(QSize(16777215, 38))
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_2.setSpacing(6)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_3.addWidget(self.frame_2)


        self.horizontalLayout_5.addWidget(self.frame_3)


        self.verticalLayout_4.addWidget(self.frame_7)


        self.horizontalLayout.addWidget(self.frame_6)

        SoundEvent_Editor_MainWindow.setCentralWidget(self.centralwidget)
        self.dockWidget = QDockWidget(SoundEvent_Editor_MainWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidget.setMinimumSize(QSize(340, 229))
        self.dockWidget.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout_6 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_6.setSpacing(6)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(2, 0, 2, 0)
        self.soundevents_list_search_bar = QLineEdit(self.dockWidgetContents)
        self.soundevents_list_search_bar.setObjectName(u"soundevents_list_search_bar")

        self.verticalLayout_6.addWidget(self.soundevents_list_search_bar)

        self.soundevents_list = QListWidget(self.dockWidgetContents)
        self.soundevents_list.setObjectName(u"soundevents_list")

        self.verticalLayout_6.addWidget(self.soundevents_list)

        self.frame = QFrame(self.dockWidgetContents)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(16777215, 32))
        self.horizontalLayout_8 = QHBoxLayout(self.frame)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.create_new_soundevent_options_button = QToolButton(self.frame)
        self.create_new_soundevent_options_button.setObjectName(u"create_new_soundevent_options_button")
        icon = QIcon()
        icon.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_new_soundevent_options_button.setIcon(icon)
        self.create_new_soundevent_options_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_8.addWidget(self.create_new_soundevent_options_button)

        self.create_new_soundevent = QPushButton(self.frame)
        self.create_new_soundevent.setObjectName(u"create_new_soundevent")
        font = QFont()
        font.setFamilies([u"Segoe UI"])
        font.setPointSize(10)
        font.setWeight(QFont.DemiBold)
        font.setItalic(False)
        self.create_new_soundevent.setFont(font)
        self.create_new_soundevent.setStyleSheet(u"\n"
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
        icon1 = QIcon()
        icon1.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_new_soundevent.setIcon(icon1)
        self.create_new_soundevent.setIconSize(QSize(20, 20))

        self.horizontalLayout_8.addWidget(self.create_new_soundevent)

        self.comboBox = QComboBox(self.frame)
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")
        self.comboBox.setStyleSheet(u"QMenu {\n"
"background-color: red;\n"
" }\n"
"\n"
"QMenu::item {\n"
"    padding: 5px 10px;\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"}\n"
"QMenu::item:selected {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"QWidget {\n"
"    background-color: #151515;\n"
"    outline: none;\n"
"}\n"
"\n"
"QWidget:item:checked {\n"
"    background-color: #151515;\n"
"    color: white;\n"
"}\n"
"\n"
"QWidget:item:selected {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"    border: 0px;\n"
"}\n"
"\n"
"\n"
"\n"
"QMenu {\n"
"    background-color: #1d1d1f;\n"
"    color: #FFFFFF;\n"
"    border: 1px solid #555555;\n"
"    /* padding-top: 5px; */\n"
"    /* padding-bottom: 5px; */\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"\n"
"QMenu::item {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border-top: 2p"
                        "x solid black;\n"
"    border: 0px;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    padding-left: 12px;\n"
"    padding-right: 12px;\n"
"    color: #E3E3E3;\n"
"}\n"
"\n"
"QMenu::item:selected {\n"
"    background-color: #666666;\n"
"    color: #FFFFFF;\n"
"}\n"
"\n"
"QMenu::separator {\n"
"    height: 1px;\n"
"    background: #AAAAAA;\n"
"    margin: 5px 0;\n"
"}\n"
"\n"
"QMenu::indicator {\n"
"    width: 13px;\n"
"    height: 13px;\n"
"}\n"
"\n"
"QMenu::indicator:checked {\n"
"    image: url(:/images/checkmark.png);\n"
"}\n"
"\n"
"QMenu::indicator:unchecked {\n"
"    image: url(:/images/empty.png);\n"
"}\n"
"\n"
"\n"
"QComboBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 12px;\n"
"    padding-top: 5px;\n"
"    padding-bottom: 5px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    padding-left: 5px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    backgr"
                        "ound-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:pressed {\n"
"    background-color: #2E2F30;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:item {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    color: #E3E3E3;\n"
"    padding-left: 5px;\n"
"    background-color: #1C1C1C;\n"
"    border-style: none;\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    color: #E3E3E3;\n"
"    padding: 2px;\n"
"    background: url(://icons/arrow_drop_down_16dp.svg) no-repeat center;\n"
"    border-bottom: 0px solid black;\n"
"    border-top: 0px solid black;\n"
"    border-right: 0px;\n"
"    border-left: 2px solid;\n"
"    margin-left: 5px;\n"
"    padding: 5px;\n"
"    width: 7px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    border: 2px solid gray;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    selection-background-color: #414956;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"\n"
"QComboBox QAbstractItemView::item {\n"
""
                        "    height: 16px; /* Set the height of each item */\n"
"    padding: 4px; /* Add padding to each item */\n"
"    padding-left: 5px;\n"
"    padding-right: 5px;\n"
"    color: #ff8a8a8a;\n"
"    border-style: none;\n"
"    border-bottom: 0.5px solid black;\n"
"    border-color: rgba(255, 255, 255, 10);\n"
"}\n"
"\n"
"\n"
"QComboBox QAbstractItemView::item:selected {\n"
"    height: 16px; /* Set the height of each item */\n"
"    padding: 4px; /* Add padding to each item */\n"
"    padding-left: 5px;\n"
"    padding-right: 5px;\n"
"    background-color: #414956;\n"
"    color: white;\n"
"    border: none; /* Remove border */\n"
"    outline: none; /* Remove outline */\n"
"}")

        self.horizontalLayout_8.addWidget(self.comboBox)


        self.verticalLayout_6.addWidget(self.frame)

        self.dockWidget.setWidget(self.dockWidgetContents)
        SoundEvent_Editor_MainWindow.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidget)
        self.dockWidget_3 = QDockWidget(SoundEvent_Editor_MainWindow)
        self.dockWidget_3.setObjectName(u"dockWidget_3")
        self.dockWidget_3.setMinimumSize(QSize(350, 107))
        self.dockWidget_3.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.dockWidgetContents_8 = QWidget()
        self.dockWidgetContents_8.setObjectName(u"dockWidgetContents_8")
        self.verticalLayout_13 = QVBoxLayout(self.dockWidgetContents_8)
        self.verticalLayout_13.setSpacing(6)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(4, 0, 0, 4)
        self.audio_files_explorer_frame = QFrame(self.dockWidgetContents_8)
        self.audio_files_explorer_frame.setObjectName(u"audio_files_explorer_frame")
        self.audio_files_explorer_frame.setFrameShape(QFrame.StyledPanel)
        self.audio_files_explorer_frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.audio_files_explorer_frame)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.audio_files_explorer_layout = QVBoxLayout()
        self.audio_files_explorer_layout.setObjectName(u"audio_files_explorer_layout")

        self.verticalLayout.addLayout(self.audio_files_explorer_layout)


        self.verticalLayout_13.addWidget(self.audio_files_explorer_frame)

        self.frame_5 = QFrame(self.dockWidgetContents_8)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setMaximumSize(QSize(16777215, 36))
        self.frame_5.setFrameShape(QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.open_sounds_folder_button = QToolButton(self.frame_5)
        self.open_sounds_folder_button.setObjectName(u"open_sounds_folder_button")
        icon2 = QIcon()
        icon2.addFile(u":/icons/folder_open.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_sounds_folder_button.setIcon(icon2)
        self.open_sounds_folder_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.open_sounds_folder_button)

        self.Import_audio_options_button = QToolButton(self.frame_5)
        self.Import_audio_options_button.setObjectName(u"Import_audio_options_button")
        self.Import_audio_options_button.setIcon(icon)
        self.Import_audio_options_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.Import_audio_options_button)

        self.Import_audio_button = QPushButton(self.frame_5)
        self.Import_audio_button.setObjectName(u"Import_audio_button")
        self.Import_audio_button.setMinimumSize(QSize(0, 32))
        self.Import_audio_button.setStyleSheet(u"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 600 10pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:20px;\n"
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
        icon3 = QIcon()
        icon3.addFile(u":/icons/place_item_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Import_audio_button.setIcon(icon3)
        self.Import_audio_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.Import_audio_button)

        self.save_button = QPushButton(self.frame_5)
        self.save_button.setObjectName(u"save_button")
        self.save_button.setMinimumSize(QSize(0, 32))
        self.save_button.setStyleSheet(u"\n"
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
        icon4 = QIcon()
        icon4.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_button.setIcon(icon4)
        self.save_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.save_button)


        self.verticalLayout_13.addWidget(self.frame_5)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.open_output_file_button = QPushButton(self.dockWidgetContents_8)
        self.open_output_file_button.setObjectName(u"open_output_file_button")
        self.open_output_file_button.setMinimumSize(QSize(0, 32))
        self.open_output_file_button.setStyleSheet(u"\n"
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
        icon5 = QIcon()
        icon5.addFile(u":/icons/file_open_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_output_file_button.setIcon(icon5)
        self.open_output_file_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_9.addWidget(self.open_output_file_button)

        self.recompile_all_button = QPushButton(self.dockWidgetContents_8)
        self.recompile_all_button.setObjectName(u"recompile_all_button")
        self.recompile_all_button.setMinimumSize(QSize(0, 32))
        self.recompile_all_button.setStyleSheet(u"\n"
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
        icon6 = QIcon()
        icon6.addFile(u":/icons/menu_open_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.recompile_all_button.setIcon(icon6)
        self.recompile_all_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_9.addWidget(self.recompile_all_button)


        self.verticalLayout_13.addLayout(self.horizontalLayout_9)

        self.dockWidget_3.setWidget(self.dockWidgetContents_8)
        SoundEvent_Editor_MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget_3)
        self.dockWidget.raise_()

        self.retranslateUi(SoundEvent_Editor_MainWindow)

        QMetaObject.connectSlotsByName(SoundEvent_Editor_MainWindow)
    # setupUi

    def retranslateUi(self, SoundEvent_Editor_MainWindow):
        SoundEvent_Editor_MainWindow.setWindowTitle(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"MainWindow", None))
#if QT_CONFIG(tooltip)
        self.add_a_property_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Press Ctrl + F for shortcut</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.add_a_property_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Add", None))
        self.dockWidget.setWindowTitle(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Soundevents", None))
        self.soundevents_list_search_bar.setPlaceholderText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Search...", None))
#if QT_CONFIG(tooltip)
        self.create_new_soundevent_options_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Quick setup options (todo)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.create_new_soundevent_options_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.create_new_soundevent.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Create new soundevent</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.create_new_soundevent.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Creane new ", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Todo Preset", None))

        self.dockWidget_3.setWindowTitle(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Explorer", None))
#if QT_CONFIG(tooltip)
        self.open_sounds_folder_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Open sounds folder</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_sounds_folder_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Open folder", None))
#if QT_CONFIG(tooltip)
        self.Import_audio_options_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Improt audio options (todo)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.Import_audio_options_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.Import_audio_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Improt audio (todo)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.Import_audio_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Import audio", None))
#if QT_CONFIG(tooltip)
        self.save_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Save file (Ctrl + S)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.save_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Save", None))
#if QT_CONFIG(tooltip)
        self.open_output_file_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Opens soundevents_addon.vsndevts in notepad</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_output_file_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Output", None))
#if QT_CONFIG(tooltip)
        self.recompile_all_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Recompiles all sounds and sound events</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.recompile_all_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Recompile All", None))
    # retranslateUi

