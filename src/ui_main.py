# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QMainWindow, QPushButton, QSizePolicy, QSpacerItem,
    QTabWidget, QToolButton, QVBoxLayout, QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1194, 880)
        icon = QIcon()
        icon.addFile(u":/icons/appicon.ico", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet(u"")
        MainWindow.setDocumentMode(False)
        MainWindow.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks|QMainWindow.DockOption.AnimatedDocks)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(9, 4, 9, 9)
        self.MainWindowTools_tabs = QTabWidget(self.centralwidget)
        self.MainWindowTools_tabs.setObjectName(u"MainWindowTools_tabs")
        self.MainWindowTools_tabs.setEnabled(True)
        self.MainWindowTools_tabs.setMinimumSize(QSize(0, 0))
        self.MainWindowTools_tabs.setStyleSheet(u"background-color: #1d1d1f;\n"
"QTabWidget::pane {\n"
"    background-color: solid red;\n"
"    border-radius: 0px;\n"
"    border: 2px solid gray;\n"
"    border-color: #363639;\n"
"    background-color: #1d1d1f;\n"
"}\n"
"/* ========================================================== */\n"
"QTabBar::tab {\n"
"    background-color: #323232;\n"
"    color: #9A9F91;\n"
"    border-radius: 0px;\n"
"    border-top-right-radius: 0px;\n"
"    border-top-left-radius: 0px;\n"
"    padding: 4px;\n"
"    padding-left:48px;\n"
"    padding-right: 48px;\n"
"\n"
"    border-top: 2px solid gray;\n"
"    border-bottom: 0px solid black;\n"
"\n"
"    font: 700 10pt \"Segoe UI\";\n"
"    border-left: 2px solid darkgray;\n"
"    border-top: 0px solid darkgray;\n"
"    border-color: #151515;\n"
"    border-right: 2px solid rgba(80, 80, 80, 80);\n"
"\n"
"\n"
"\n"
"    color: #E3E3E3;\n"
"    background-color: #151515;\n"
"\n"
"}\n"
"QTabBar::tab:selected {\n"
"    border-radius: 0px;\n"
"    border-top-right-radius: 7px;\n"
"    bo"
                        "rder-top-left-radius: 7px;\n"
"\n"
"    border-top: 2px solid gray;\n"
"    border-left: 2px solid gray;\n"
"    border-right: 2px solid gray;\n"
"    border-bottom: 0px solid black;\n"
"\n"
"    font: 700 10pt \"Segoe UI\";\n"
"    border-color: rgba(80, 80, 80, 180);\n"
"    height:20px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1d1d1f;\n"
"}")
        self.MainWindowTools_tabs.setTabsClosable(False)
        self.Loading_Editor_Tab = QWidget()
        self.Loading_Editor_Tab.setObjectName(u"Loading_Editor_Tab")
        self.gridLayout_3 = QGridLayout(self.Loading_Editor_Tab)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        icon1 = QIcon()
        icon1.addFile(u":/icons/imagesmode_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.Loading_Editor_Tab, icon1, "")
        self.soundeditor_tab = QWidget()
        self.soundeditor_tab.setObjectName(u"soundeditor_tab")
        self.soundeditor_tab.setEnabled(True)
        self.verticalLayout_5 = QVBoxLayout(self.soundeditor_tab)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        icon2 = QIcon()
        icon2.addFile(u":/icons/volume_up.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.soundeditor_tab, icon2, "")
        self.smartpropeditor_tab = QWidget()
        self.smartpropeditor_tab.setObjectName(u"smartpropeditor_tab")
        self.verticalLayout_4 = QVBoxLayout(self.smartpropeditor_tab)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        icon3 = QIcon()
        icon3.addFile(u":/icons/functions_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.smartpropeditor_tab, icon3, "")
        self.BatchCreator_tab = QWidget()
        self.BatchCreator_tab.setObjectName(u"BatchCreator_tab")
        self.verticalLayout_2 = QVBoxLayout(self.BatchCreator_tab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        icon4 = QIcon()
        icon4.addFile(u":/icons/dashboard_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.BatchCreator_tab, icon4, "")
        self.hotkeyeditor_tab = QWidget()
        self.hotkeyeditor_tab.setObjectName(u"hotkeyeditor_tab")
        self.hotkeyeditor_tab.setEnabled(True)
        self.verticalLayout_3 = QVBoxLayout(self.hotkeyeditor_tab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        icon5 = QIcon()
        icon5.addFile(u":/icons/keyboard.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.hotkeyeditor_tab, icon5, "")

        self.verticalLayout.addWidget(self.MainWindowTools_tabs)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.my_twitter_button = QPushButton(self.centralwidget)
        self.my_twitter_button.setObjectName(u"my_twitter_button")
        self.my_twitter_button.setMinimumSize(QSize(32, 0))
        self.my_twitter_button.setMaximumSize(QSize(32, 16777210))
        self.my_twitter_button.setStyleSheet(u"padding: 5px;")
        icon6 = QIcon()
        icon6.addFile(u":/social/icons/social/twitter.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.my_twitter_button.setIcon(icon6)
        self.my_twitter_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.my_twitter_button)

        self.discord = QPushButton(self.centralwidget)
        self.discord.setObjectName(u"discord")
        self.discord.setMinimumSize(QSize(32, 0))
        self.discord.setMaximumSize(QSize(32, 16777210))
        self.discord.setStyleSheet(u"padding: 5px;")
        icon7 = QIcon()
        icon7.addFile(u":/social/icons/social/discord.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.discord.setIcon(icon7)
        self.discord.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.discord)

        self.preferences_button = QPushButton(self.centralwidget)
        self.preferences_button.setObjectName(u"preferences_button")
        self.preferences_button.setMinimumSize(QSize(32, 0))
        self.preferences_button.setMaximumSize(QSize(32, 16777210))
        self.preferences_button.setStyleSheet(u"padding: 5px;")
        icon8 = QIcon()
        icon8.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.preferences_button.setIcon(icon8)
        self.preferences_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.preferences_button)


        self.horizontalLayout_2.addLayout(self.horizontalLayout)

        self.documentation_button = QPushButton(self.centralwidget)
        self.documentation_button.setObjectName(u"documentation_button")
        self.documentation_button.setMinimumSize(QSize(96, 0))
        self.documentation_button.setStyleSheet(u"padding: 5px;")
        icon9 = QIcon()
        icon9.addFile(u":/icons/developer_guide_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.documentation_button.setIcon(icon9)
        self.documentation_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.documentation_button)

        self.horizontalSpacer_3 = QSpacerItem(12, 6, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)

        self.export_and_import_addon_button = QToolButton(self.centralwidget)
        self.export_and_import_addon_button.setObjectName(u"export_and_import_addon_button")
        font = QFont()
        font.setPointSize(11)
        self.export_and_import_addon_button.setFont(font)
        icon10 = QIcon()
        icon10.addFile(u":/icons/publish_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.export_and_import_addon_button.setIcon(icon10)
        self.export_and_import_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.export_and_import_addon_button)

        self.delete_addon_button = QToolButton(self.centralwidget)
        self.delete_addon_button.setObjectName(u"delete_addon_button")
        self.delete_addon_button.setFont(font)
        icon11 = QIcon()
        icon11.addFile(u":/icons/delete_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_addon_button.setIcon(icon11)
        self.delete_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.delete_addon_button)

        self.create_new_addon_button = QToolButton(self.centralwidget)
        self.create_new_addon_button.setObjectName(u"create_new_addon_button")
        self.create_new_addon_button.setFont(font)
        icon12 = QIcon()
        icon12.addFile(u":/icons/post_add_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_new_addon_button.setIcon(icon12)
        self.create_new_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.create_new_addon_button)

        self.ComboBoxSelectAddon = QComboBox(self.centralwidget)
        self.ComboBoxSelectAddon.addItem("")
        self.ComboBoxSelectAddon.setObjectName(u"ComboBoxSelectAddon")
        self.ComboBoxSelectAddon.setMinimumSize(QSize(220, 0))
        self.ComboBoxSelectAddon.setStyleSheet(u"")

        self.horizontalLayout_2.addWidget(self.ComboBoxSelectAddon)

        self.launch_settings = QToolButton(self.centralwidget)
        self.launch_settings.setObjectName(u"launch_settings")
        self.launch_settings.setIcon(icon8)
        self.launch_settings.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.launch_settings)

        self.Launch_Addon_Button = QPushButton(self.centralwidget)
        self.Launch_Addon_Button.setObjectName(u"Launch_Addon_Button")
        self.Launch_Addon_Button.setEnabled(True)
        self.Launch_Addon_Button.setMinimumSize(QSize(128, 0))
        self.Launch_Addon_Button.setStyleSheet(u"padding: 5px;")
        icon13 = QIcon()
        icon13.addFile(u":/icons/edit_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Launch_Addon_Button.setIcon(icon13)
        self.Launch_Addon_Button.setIconSize(QSize(20, 20))
        self.Launch_Addon_Button.setCheckable(False)

        self.horizontalLayout_2.addWidget(self.Launch_Addon_Button)

        self.horizontalSpacer = QSpacerItem(12, 6, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.open_addons_folder_button = QToolButton(self.centralwidget)
        self.open_addons_folder_button.setObjectName(u"open_addons_folder_button")
        self.open_addons_folder_button.setFont(font)
        icon14 = QIcon()
        icon14.addFile(u":/icons/folder_open.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_addons_folder_button.setIcon(icon14)

        self.horizontalLayout_2.addWidget(self.open_addons_folder_button)

        self.open_addons_folder_downlist = QComboBox(self.centralwidget)
        self.open_addons_folder_downlist.addItem("")
        self.open_addons_folder_downlist.addItem("")
        self.open_addons_folder_downlist.setObjectName(u"open_addons_folder_downlist")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.open_addons_folder_downlist.sizePolicy().hasHeightForWidth())
        self.open_addons_folder_downlist.setSizePolicy(sizePolicy)
        self.open_addons_folder_downlist.setMinimumSize(QSize(22, 0))
        self.open_addons_folder_downlist.setStyleSheet(u"")

        self.horizontalLayout_2.addWidget(self.open_addons_folder_downlist)

        self.FixNoSteamLogon_Button = QPushButton(self.centralwidget)
        self.FixNoSteamLogon_Button.setObjectName(u"FixNoSteamLogon_Button")
        self.FixNoSteamLogon_Button.setMinimumSize(QSize(128, 0))
        self.FixNoSteamLogon_Button.setStyleSheet(u"padding: 5px;")
        icon15 = QIcon()
        icon15.addFile(u":/icons/bolt_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.FixNoSteamLogon_Button.setIcon(icon15)
        self.FixNoSteamLogon_Button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.FixNoSteamLogon_Button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.MainWindowTools_tabs.setCurrentIndex(4)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Hammer 5 Tools", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.Loading_Editor_Tab), QCoreApplication.translate("MainWindow", u"Loading Editor", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.soundeditor_tab), QCoreApplication.translate("MainWindow", u"SoundEvent Editor", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.smartpropeditor_tab), QCoreApplication.translate("MainWindow", u"SmartProp Editor", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.BatchCreator_tab), QCoreApplication.translate("MainWindow", u"BatchCreator", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.hotkeyeditor_tab), QCoreApplication.translate("MainWindow", u"Hotkey Editor", None))
#if QT_CONFIG(tooltip)
        self.my_twitter_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Twitter</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.my_twitter_button.setText("")
#if QT_CONFIG(tooltip)
        self.discord.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Discord server</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.discord.setText("")
#if QT_CONFIG(tooltip)
        self.preferences_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Discord server</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.preferences_button.setText("")
#if QT_CONFIG(tooltip)
        self.documentation_button.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.documentation_button.setText(QCoreApplication.translate("MainWindow", u"Help", None))
#if QT_CONFIG(tooltip)
        self.export_and_import_addon_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Archive addon</span></p><p>Create an archive on from game and content folders.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.export_and_import_addon_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.delete_addon_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Delete addon</span></p><p>Deletes selected addon.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.delete_addon_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.create_new_addon_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Create addon</span></p><p>Quick create an addon with custom presets.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.create_new_addon_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.ComboBoxSelectAddon.setItemText(0, QCoreApplication.translate("MainWindow", u"de_addon", None))

#if QT_CONFIG(tooltip)
        self.ComboBoxSelectAddon.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:11pt; font-weight:700;\">Addon selection</span></p><p>In the Addon selection, all tools apply changes to the addon selected in this section.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.launch_settings.setText(QCoreApplication.translate("MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.Launch_Addon_Button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Addon launch</span></p><p>Launches the current addon selected in the addon selection.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.Launch_Addon_Button.setText(QCoreApplication.translate("MainWindow", u"Edit map", None))
#if QT_CONFIG(tooltip)
        self.open_addons_folder_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Open Game/Content Addons folder</span></p><p><span style=\" font-size:9pt;\">Opens the game addons or content addons folder for the current addon selection. </span></p><p><span style=\" font-size:9pt;\">To choose the folder type to open, select a folder in the </span><span style=\" font-size:9pt; font-style:italic;\">Addon Folder Selection</span><span style=\" font-size:9pt;\">.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_addons_folder_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.open_addons_folder_downlist.setItemText(0, QCoreApplication.translate("MainWindow", u"Content", None))
        self.open_addons_folder_downlist.setItemText(1, QCoreApplication.translate("MainWindow", u"Game", None))

#if QT_CONFIG(tooltip)
        self.open_addons_folder_downlist.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Addon Folder Selection</span></p><p>Used to choose the folder that should be oppened in the <span style=\" font-style:italic;\">Open Game/Content Addons Folder.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_addons_folder_downlist.setCurrentText("")
        self.open_addons_folder_downlist.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Open Folder", None))
#if QT_CONFIG(tooltip)
        self.FixNoSteamLogon_Button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Fix No Steam Logon</span></p><p>This script restarts Steam and launches the current addon.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.FixNoSteamLogon_Button.setText(QCoreApplication.translate("MainWindow", u"Restart Steam", None))
    # retranslateUi

