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
from PySide6.QtWidgets import (QApplication, QDockWidget, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLayout, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QPushButton,
    QScrollArea, QSizePolicy, QToolButton, QTreeView,
    QVBoxLayout, QWidget)
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
        self.frame_9 = QFrame(self.frame_3)
        self.frame_9.setObjectName(u"frame_9")
        self.frame_9.setFrameShape(QFrame.StyledPanel)
        self.frame_9.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_7 = QHBoxLayout(self.frame_9)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.status_bar = QLabel(self.frame_9)
        self.status_bar.setObjectName(u"status_bar")

        self.horizontalLayout_7.addWidget(self.status_bar)

        self.version = QLabel(self.frame_9)
        self.version.setObjectName(u"version")
        self.version.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_7.addWidget(self.version)


        self.verticalLayout_3.addWidget(self.frame_9)

        self.scrollArea = QScrollArea(self.frame_3)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)
        self.soundevent_properties = QWidget()
        self.soundevent_properties.setObjectName(u"soundevent_properties")
        self.soundevent_properties.setGeometry(QRect(0, 0, 639, 588))
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
        self.save_button = QPushButton(self.frame_2)
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
        icon = QIcon()
        icon.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_button.setIcon(icon)
        self.save_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.save_button)

        self.recompile_all_button = QPushButton(self.frame_2)
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
        icon1 = QIcon()
        icon1.addFile(u":/icons/menu_open_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.recompile_all_button.setIcon(icon1)
        self.recompile_all_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.recompile_all_button)

        self.open_output_file_button = QPushButton(self.frame_2)
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
        icon2 = QIcon()
        icon2.addFile(u":/icons/file_open_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_output_file_button.setIcon(icon2)
        self.open_output_file_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.open_output_file_button)


        self.verticalLayout_3.addWidget(self.frame_2)


        self.horizontalLayout_5.addWidget(self.frame_3)


        self.verticalLayout_4.addWidget(self.frame_7)


        self.horizontalLayout.addWidget(self.frame_6)

        SoundEvent_Editor_MainWindow.setCentralWidget(self.centralwidget)
        self.dockWidget = QDockWidget(SoundEvent_Editor_MainWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidget.setMinimumSize(QSize(340, 157))
        icon3 = QIcon()
        icon3.addFile(u":/icons/acute_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.dockWidget.setWindowIcon(icon3)
        self.dockWidget.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout_6 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_6.setSpacing(6)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.soundevents_list_search_bar = QLineEdit(self.dockWidgetContents)
        self.soundevents_list_search_bar.setObjectName(u"soundevents_list_search_bar")

        self.verticalLayout_6.addWidget(self.soundevents_list_search_bar)

        self.soundevents_list = QListWidget(self.dockWidgetContents)
        self.soundevents_list.setObjectName(u"soundevents_list")

        self.verticalLayout_6.addWidget(self.soundevents_list)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.create_new_soundevent_options_button = QToolButton(self.dockWidgetContents)
        self.create_new_soundevent_options_button.setObjectName(u"create_new_soundevent_options_button")
        icon4 = QIcon()
        icon4.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_new_soundevent_options_button.setIcon(icon4)
        self.create_new_soundevent_options_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_8.addWidget(self.create_new_soundevent_options_button)

        self.create_new_soundevent = QPushButton(self.dockWidgetContents)
        self.create_new_soundevent.setObjectName(u"create_new_soundevent")
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
        icon5 = QIcon()
        icon5.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_new_soundevent.setIcon(icon5)
        self.create_new_soundevent.setIconSize(QSize(20, 20))

        self.horizontalLayout_8.addWidget(self.create_new_soundevent)


        self.verticalLayout_6.addLayout(self.horizontalLayout_8)

        self.dockWidget.setWidget(self.dockWidgetContents)
        SoundEvent_Editor_MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget)
        self.dockWidget_2 = QDockWidget(SoundEvent_Editor_MainWindow)
        self.dockWidget_2.setObjectName(u"dockWidget_2")
        self.dockWidget_2.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.dockWidgetContents_2 = QWidget()
        self.dockWidgetContents_2.setObjectName(u"dockWidgetContents_2")
        self.verticalLayout_5 = QVBoxLayout(self.dockWidgetContents_2)
        self.verticalLayout_5.setSpacing(6)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.audio_files_explorer = QTreeView(self.dockWidgetContents_2)
        self.audio_files_explorer.setObjectName(u"audio_files_explorer")
        self.audio_files_explorer.setStyleSheet(u"/* styles/treeview.qss */\n"
"\n"
"/* General application background */\n"
"/* TreeView specific styles */\n"
"QTreeView {\n"
"    color: #E3E3E3;\n"
"    border: 1px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    font: 580 10pt \"Segoe UI\";\n"
"}\n"
"\n"
"QTreeView::item {\n"
"    height: 20px;\n"
"}\n"
"\n"
"QTreeView::item:selected {\n"
"    background-color: #272729;\n"
"    color: #E3E3E3;\n"
"}\n"
"\n"
"QTreeView::item:hover {\n"
"    background-color: #272729;\n"
"    color: #E3E3E3;\n"
"}\n"
"\n"
"/* Branch icons */\n"
"QTreeView::branch:closed:has-children {\n"
"    /* Ensure this path is correct and the image exists */\n"
"    image: url(:/icons/arrow_drop_down_16dp.svg);\n"
"}\n"
"\n"
"QTreeView::branch:open:has-children {\n"
"    /* Ensure this path is correct and the image exists */\n"
"    image: url(:/icons/arrow_right_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"/* Header styles */\n"
"QHeaderView::section {\n"
"    background-color"
                        ": #1d1d1f;\n"
"    color: #E3E3E3;\n"
"    font: 600 10pt \"Segoe UI\";\n"
"    height: 16px;\n"
"    border: 0px;\n"
"    border-bottom: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"\n"
"/* QHeaderView::section:hover {\n"
"    background-color: #565656;\n"
"}\n"
"\n"
"QHeaderView::section:pressed {\n"
"    background-color: #444444;\n"
"} */\n"
"\n"
"\n"
"\n"
"\n"
"QLineEdit {\n"
"    border: 1px solid #CCCCCC;\n"
"    border-radius: 2px;\n"
"    color: #E3E3E3;\n"
"	font: 700 10pt \"Segoe UI\";\n"
"margin: 0px;\n"
"padding: 0px;\n"
"}\n"
"QLineEdit:focus {\n"
"    border: 1px solid #008CBA;\n"
"    background-color: #1C1C1C;\n"
"margin: 0px;\n"
"padding: 0px;\n"
"}\n"
"QLineEdit::selection {\n"
"    color: white;\n"
"}")

        self.verticalLayout_5.addWidget(self.audio_files_explorer)

        self.frame_5 = QFrame(self.dockWidgetContents_2)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.open_sounds_folder_button = QToolButton(self.frame_5)
        self.open_sounds_folder_button.setObjectName(u"open_sounds_folder_button")
        icon6 = QIcon()
        icon6.addFile(u":/icons/folder_open.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_sounds_folder_button.setIcon(icon6)
        self.open_sounds_folder_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.open_sounds_folder_button)

        self.Import_audio_options_button = QToolButton(self.frame_5)
        self.Import_audio_options_button.setObjectName(u"Import_audio_options_button")
        self.Import_audio_options_button.setIcon(icon4)
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
        icon7.addFile(u":/icons/place_item_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Import_audio_button.setIcon(icon7)
        self.Import_audio_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.Import_audio_button)


        self.verticalLayout_5.addWidget(self.frame_5)

        self.dockWidget_2.setWidget(self.dockWidgetContents_2)
        SoundEvent_Editor_MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget_2)

        self.retranslateUi(SoundEvent_Editor_MainWindow)

        QMetaObject.connectSlotsByName(SoundEvent_Editor_MainWindow)
    # setupUi

    def retranslateUi(self, SoundEvent_Editor_MainWindow):
        SoundEvent_Editor_MainWindow.setWindowTitle(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"MainWindow", None))
        self.status_bar.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Press Ctrl + F to add a property", None))
        self.version.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Version", None))
#if QT_CONFIG(tooltip)
        self.save_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Save file (Ctrl + S)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.save_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Save", None))
#if QT_CONFIG(tooltip)
        self.recompile_all_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Recompiles all sounds and sound events</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.recompile_all_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Recompile All", None))
#if QT_CONFIG(tooltip)
        self.open_output_file_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Opens soundevents_addon.vsndevts in notepad</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_output_file_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Open output file", None))
        self.dockWidget.setWindowTitle(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Soundevents", None))
        self.soundevents_list_search_bar.setPlaceholderText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Search...", None))
#if QT_CONFIG(tooltip)
        self.create_new_soundevent_options_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Quick setup options (todo)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.create_new_soundevent_options_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.create_new_soundevent.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Create new soundevent</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.create_new_soundevent.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Creane new (music preset)", None))
        self.dockWidget_2.setWindowTitle(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Audio explorer", None))
#if QT_CONFIG(tooltip)
        self.open_sounds_folder_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Open sounds folder</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_sounds_folder_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.Import_audio_options_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Improt audio options (todo)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.Import_audio_options_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.Import_audio_button.setToolTip(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"<html><head/><body><p>Improt audio (todo)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.Import_audio_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Import audio", None))
    # retranslateUi

