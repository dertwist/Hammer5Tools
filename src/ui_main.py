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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QSizePolicy,
    QTabWidget, QToolButton, QVBoxLayout, QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1144, 799)
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
        icon1.addFile(u":/valve_common/icons/tools/common/image.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.Loading_Editor_Tab, icon1, "")
        self.soundeditor_tab = QWidget()
        self.soundeditor_tab.setObjectName(u"soundeditor_tab")
        self.soundeditor_tab.setEnabled(True)
        self.verticalLayout_5 = QVBoxLayout(self.soundeditor_tab)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        icon2 = QIcon()
        icon2.addFile(u":/icons/tools/vmixtool/appicon.ico", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.soundeditor_tab, icon2, "")
        self.smartpropeditor_tab = QWidget()
        self.smartpropeditor_tab.setObjectName(u"smartpropeditor_tab")
        self.verticalLayout_4 = QVBoxLayout(self.smartpropeditor_tab)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(-1, 0, -1, -1)
        icon3 = QIcon()
        icon3.addFile(u":/icons/smartprop_editor.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.smartpropeditor_tab, icon3, "")
        self.BatchCreator_tab = QWidget()
        self.BatchCreator_tab.setObjectName(u"BatchCreator_tab")
        self.verticalLayout_2 = QVBoxLayout(self.BatchCreator_tab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        icon4 = QIcon()
        icon4.addFile(u":/valve_common/icons/tools/model_editor/hierarchy_sequence_group_referenced.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.BatchCreator_tab, icon4, "")
        self.hotkeyeditor_tab = QWidget()
        self.hotkeyeditor_tab.setObjectName(u"hotkeyeditor_tab")
        self.hotkeyeditor_tab.setEnabled(True)
        self.verticalLayout_3 = QVBoxLayout(self.hotkeyeditor_tab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        icon5 = QIcon()
        icon5.addFile(u":/valve_common/icons/tools/common/help_keybinding_list.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.MainWindowTools_tabs.addTab(self.hotkeyeditor_tab, icon5, "")

        self.verticalLayout.addWidget(self.MainWindowTools_tabs)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.my_twitter_button = QPushButton(self.centralwidget)
        self.my_twitter_button.setObjectName(u"my_twitter_button")
        self.my_twitter_button.setMinimumSize(QSize(32, 0))
        self.my_twitter_button.setMaximumSize(QSize(32, 16777210))
        self.my_twitter_button.setStyleSheet(u"padding: 5px;")
        icon6 = QIcon()
        icon6.addFile(u":/social/icons/social/twitter.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.my_twitter_button.setIcon(icon6)
        self.my_twitter_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.my_twitter_button)

        self.discord = QPushButton(self.centralwidget)
        self.discord.setObjectName(u"discord")
        self.discord.setMinimumSize(QSize(32, 0))
        self.discord.setMaximumSize(QSize(32, 16777210))
        self.discord.setStyleSheet(u"padding: 5px;")
        icon7 = QIcon()
        icon7.addFile(u":/social/icons/social/discord.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.discord.setIcon(icon7)
        self.discord.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.discord)

        self.documentation_button = QPushButton(self.centralwidget)
        self.documentation_button.setObjectName(u"documentation_button")
        self.documentation_button.setMinimumSize(QSize(32, 0))
        self.documentation_button.setMaximumSize(QSize(32, 16777210))
        self.documentation_button.setStyleSheet(u"padding: 5px;")
        icon8 = QIcon()
        icon8.addFile(u":/icons/help_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.documentation_button.setIcon(icon8)
        self.documentation_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.documentation_button)

        self.preferences_button = QPushButton(self.centralwidget)
        self.preferences_button.setObjectName(u"preferences_button")
        self.preferences_button.setMinimumSize(QSize(130, 0))
        self.preferences_button.setStyleSheet(u"padding: 5px;\n"
"font: 580 10pt \"Segoe UI\";")
        icon9 = QIcon()
        icon9.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.preferences_button.setIcon(icon9)
        self.preferences_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.preferences_button)

        self.console_label = QLabel(self.centralwidget)
        self.console_label.setObjectName(u"console_label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.console_label.sizePolicy().hasHeightForWidth())
        self.console_label.setSizePolicy(sizePolicy)
        self.console_label.setStyleSheet(u"color: #9D9D9D;\n"
"padding-left: 8px;\n"
"padding-right: 8px;\n"
"font: 580 9pt \"Segoe UI\";")
        self.console_label.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.console_label)

        self.utilities_button = QToolButton(self.centralwidget)
        self.utilities_button.setObjectName(u"utilities_button")
        self.utilities_button.setMinimumSize(QSize(110, 0))
        self.utilities_button.setStyleSheet(u"padding: 5px;\n"
"font: 580 10pt \"Segoe UI\";")
        icon10 = QIcon()
        icon10.addFile(u":/icons/apps_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.utilities_button.setIcon(icon10)
        self.utilities_button.setIconSize(QSize(20, 20))
        self.utilities_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.utilities_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self.horizontalLayout_2.addWidget(self.utilities_button)

        self.addon_actions_button = QToolButton(self.centralwidget)
        self.addon_actions_button.setObjectName(u"addon_actions_button")
        icon11 = QIcon()
        icon11.addFile(u":/icons/menu_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.addon_actions_button.setIcon(icon11)
        self.addon_actions_button.setIconSize(QSize(20, 20))
        self.addon_actions_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.horizontalLayout_2.addWidget(self.addon_actions_button)

        self.ComboBoxSelectAddon = QComboBox(self.centralwidget)
        self.ComboBoxSelectAddon.setObjectName(u"ComboBoxSelectAddon")
        self.ComboBoxSelectAddon.setMinimumSize(QSize(220, 0))
        self.ComboBoxSelectAddon.setStyleSheet(u"font: 700 10pt \"Segoe UI\";")

        self.horizontalLayout_2.addWidget(self.ComboBoxSelectAddon)

        self.Launch_Addon_Button = QPushButton(self.centralwidget)
        self.Launch_Addon_Button.setObjectName(u"Launch_Addon_Button")
        self.Launch_Addon_Button.setEnabled(True)
        self.Launch_Addon_Button.setMinimumSize(QSize(128, 0))
        self.Launch_Addon_Button.setStyleSheet(u"padding: 5px;\n"
"font: 700 10pt \"Segoe UI\";")
        icon12 = QIcon()
        icon12.addFile(u":/icons/icons/hammer_icon.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Launch_Addon_Button.setIcon(icon12)
        self.Launch_Addon_Button.setIconSize(QSize(20, 20))
        self.Launch_Addon_Button.setCheckable(False)

        self.horizontalLayout_2.addWidget(self.Launch_Addon_Button)

        self.mapbuilder = QToolButton(self.centralwidget)
        self.mapbuilder.setObjectName(u"mapbuilder")
        icon13 = QIcon()
        icon13.addFile(u":/icons/emoji_objects_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.mapbuilder.setIcon(icon13)
        self.mapbuilder.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.mapbuilder)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.MainWindowTools_tabs.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Hammer 5 Tools", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.Loading_Editor_Tab), QCoreApplication.translate("MainWindow", u"Loading Editor", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.soundeditor_tab), QCoreApplication.translate("MainWindow", u"SoundEvent Editor", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.smartpropeditor_tab), QCoreApplication.translate("MainWindow", u"SmartProp Editor", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.BatchCreator_tab), QCoreApplication.translate("MainWindow", u"AssetGroup Maker", None))
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
        self.documentation_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Discord server</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.documentation_button.setText("")
        self.preferences_button.setText(QCoreApplication.translate("MainWindow", u"Settings", None))
#if QT_CONFIG(tooltip)
        self.console_label.setToolTip(QCoreApplication.translate("MainWindow", u"Console: recent saved files, launched addons and tool activity.", None))
#endif // QT_CONFIG(tooltip)
        self.console_label.setText("")
#if QT_CONFIG(tooltip)
        self.utilities_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Utilities</span></p><p>Open a utility tool (Cleanup, Unreal Converter).</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.utilities_button.setText(QCoreApplication.translate("MainWindow", u"Utilities", None))
#if QT_CONFIG(tooltip)
        self.addon_actions_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Addon actions</span></p><p>Launch parameters, create/delete/export/import addon, open folders.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.addon_actions_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.ComboBoxSelectAddon.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:11pt; font-weight:700;\">Addon selection</span></p><p>All tools apply changes to the addon selected in this section.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.Launch_Addon_Button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Addon launch</span></p><p>Launches the current addon selected in the addon selection.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.Launch_Addon_Button.setText(QCoreApplication.translate("MainWindow", u"Edit map", None))
#if QT_CONFIG(tooltip)
        self.mapbuilder.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Mapbuilder: an external tool to compile vmap files (by addon name)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.mapbuilder.setText(QCoreApplication.translate("MainWindow", u"...", None))
    # retranslateUi

