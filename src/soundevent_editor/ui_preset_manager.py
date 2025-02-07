# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preset_manager.ui'
##
## Created by: Qt User Interface Compiler version 6.8.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QDockWidget, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1240, 941)
        icon = QIcon()
        icon.addFile(u":/icons/appicon.ico", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.actionCreateNewsmartprop = QAction(MainWindow)
        self.actionCreateNewsmartprop.setObjectName(u"actionCreateNewsmartprop")
        icon1 = QIcon()
        icon1.addFile(u":/valve_common/icons/tools/common/new.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionCreateNewsmartprop.setIcon(icon1)
        self.actionCreateNewsmartprop.setMenuRole(QAction.MenuRole.NoRole)
        self.actionOpen_from_Explorer = QAction(MainWindow)
        self.actionOpen_from_Explorer.setObjectName(u"actionOpen_from_Explorer")
        icon2 = QIcon()
        icon2.addFile(u":/valve_common/icons/tools/common/open.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionOpen_from_Explorer.setIcon(icon2)
        self.actionSave_as = QAction(MainWindow)
        self.actionSave_as.setObjectName(u"actionSave_as")
        icon3 = QIcon()
        icon3.addFile(u":/valve_common/icons/tools/common/save_all.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSave_as.setIcon(icon3)
        self.actionSave_current_file = QAction(MainWindow)
        self.actionSave_current_file.setObjectName(u"actionSave_current_file")
        icon4 = QIcon()
        icon4.addFile(u":/valve_common/icons/tools/common/save.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSave_current_file.setIcon(icon4)
        self.actionRecompile_file = QAction(MainWindow)
        self.actionRecompile_file.setObjectName(u"actionRecompile_file")
        icon5 = QIcon()
        icon5.addFile(u":/valve_common/icons/tools/common/options_activated.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionRecompile_file.setIcon(icon5)
        self.actionRecompile_all_in_addon = QAction(MainWindow)
        self.actionRecompile_all_in_addon.setObjectName(u"actionRecompile_all_in_addon")
        self.actionRecompile_all_in_addon.setIcon(icon5)
        self.actionConvert_all_vsmart_file_to_vdata = QAction(MainWindow)
        self.actionConvert_all_vsmart_file_to_vdata.setObjectName(u"actionConvert_all_vsmart_file_to_vdata")
        icon6 = QIcon()
        icon6.addFile(u":/valve_common/icons/tools/common/move_to_changelist.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionConvert_all_vsmart_file_to_vdata.setIcon(icon6)
        self.actionFormat_serttings = QAction(MainWindow)
        self.actionFormat_serttings.setObjectName(u"actionFormat_serttings")
        icon7 = QIcon()
        icon7.addFile(u":/valve_common/icons/tools/common/setting.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionFormat_serttings.setIcon(icon7)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_6 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setStyleSheet(u"        QFrame#frame {\n"
"            border: 2px solid black; \n"
"            border-color: rgba(80, 80, 80, 255);\n"
"        }\n"
"        QFrame#frame QLabel {\n"
"            border: 0px solid black; \n"
"        }")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.frame)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(9)
        self.label.setFont(font)

        self.verticalLayout_5.addWidget(self.label)


        self.verticalLayout_6.addWidget(self.frame)

        MainWindow.setCentralWidget(self.centralwidget)
        self.ExplorerDockWidget = QDockWidget(MainWindow)
        self.ExplorerDockWidget.setObjectName(u"ExplorerDockWidget")
        self.ExplorerDockWidget.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.ExplorerDockWidget.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea|Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea)
        self.explorer_layout_widget = QWidget()
        self.explorer_layout_widget.setObjectName(u"explorer_layout_widget")
        self.verticalLayout_10 = QVBoxLayout(self.explorer_layout_widget)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.explorer_layout = QVBoxLayout()
        self.explorer_layout.setObjectName(u"explorer_layout")

        self.verticalLayout_10.addLayout(self.explorer_layout)

        self.save_button = QPushButton(self.explorer_layout_widget)
        self.save_button.setObjectName(u"save_button")
        self.save_button.setStyleSheet(u"\n"
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
        icon8 = QIcon()
        icon8.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_button.setIcon(icon8)
        self.save_button.setIconSize(QSize(20, 20))

        self.verticalLayout_10.addWidget(self.save_button)

        self.open_button = QPushButton(self.explorer_layout_widget)
        self.open_button.setObjectName(u"open_button")
        self.open_button.setStyleSheet(u"\n"
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
        icon9 = QIcon()
        icon9.addFile(u":/icons/file_open_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_button.setIcon(icon9)
        self.open_button.setIconSize(QSize(20, 20))

        self.verticalLayout_10.addWidget(self.open_button)

        self.frame_3 = QFrame(self.explorer_layout_widget)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16777215, 32))
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.new_button = QPushButton(self.frame_3)
        self.new_button.setObjectName(u"new_button")
        self.new_button.setStyleSheet(u"\n"
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
        icon10 = QIcon()
        icon10.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.new_button.setIcon(icon10)
        self.new_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.new_button)


        self.verticalLayout_10.addWidget(self.frame_3)

        self.verticalSpacer = QSpacerItem(20, 8, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout_10.addItem(self.verticalSpacer)

        self.frame_4 = QFrame(self.explorer_layout_widget)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setMaximumSize(QSize(16777215, 32))
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.open_folder_button = QPushButton(self.frame_4)
        self.open_folder_button.setObjectName(u"open_folder_button")
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
        icon11 = QIcon()
        icon11.addFile(u":/icons/folder_open.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_folder_button.setIcon(icon11)
        self.open_folder_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.open_folder_button)


        self.verticalLayout_10.addWidget(self.frame_4)

        self.ExplorerDockWidget.setWidget(self.explorer_layout_widget)
        MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.ExplorerDockWidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"SoundEvent Editor - Preset Manager ", None))
        self.actionCreateNewsmartprop.setText(QCoreApplication.translate("MainWindow", u"CreateNewsmartprop", None))
        self.actionOpen_from_Explorer.setText(QCoreApplication.translate("MainWindow", u"Open as", None))
        self.actionSave_as.setText(QCoreApplication.translate("MainWindow", u"Save as", None))
        self.actionSave_current_file.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.actionRecompile_file.setText(QCoreApplication.translate("MainWindow", u"Recompile file", None))
        self.actionRecompile_all_in_addon.setText(QCoreApplication.translate("MainWindow", u"Recompile all in addon", None))
        self.actionConvert_all_vsmart_file_to_vdata.setText(QCoreApplication.translate("MainWindow", u"Convert all vsmart file to vdata", None))
#if QT_CONFIG(tooltip)
        self.actionConvert_all_vsmart_file_to_vdata.setToolTip(QCoreApplication.translate("MainWindow", u"Convert all to data", None))
#endif // QT_CONFIG(tooltip)
        self.actionFormat_serttings.setText(QCoreApplication.translate("MainWindow", u"Format serttings", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Properties", None))
        self.ExplorerDockWidget.setWindowTitle(QCoreApplication.translate("MainWindow", u"Explorer", None))
#if QT_CONFIG(tooltip)
        self.save_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Ctrl + S</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.save_button.setText(QCoreApplication.translate("MainWindow", u"Save", None))
#if QT_CONFIG(shortcut)
        self.save_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.open_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Ctrl + O</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_button.setText(QCoreApplication.translate("MainWindow", u"Open", None))
#if QT_CONFIG(shortcut)
        self.open_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.new_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Ctrl + N</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.new_button.setText(QCoreApplication.translate("MainWindow", u"New", None))
#if QT_CONFIG(shortcut)
        self.new_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.open_folder_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><br/>Ctrl + Shift + O</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_folder_button.setText(QCoreApplication.translate("MainWindow", u"Open Folder", None))
#if QT_CONFIG(shortcut)
        self.open_folder_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+O", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

