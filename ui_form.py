# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QHBoxLayout, QLabel, QLayout, QPushButton,
    QSizePolicy, QSpacerItem, QTabWidget, QToolButton,
    QVBoxLayout, QWidget)
import rc_resources

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.setEnabled(True)
        Widget.resize(1306, 900)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Widget.sizePolicy().hasHeightForWidth())
        Widget.setSizePolicy(sizePolicy)
        Widget.setMinimumSize(QSize(1280, 720))
        Widget.setBaseSize(QSize(499, 699))
        font = QFont()
        font.setPointSize(7)
        Widget.setFont(font)
        Widget.setAcceptDrops(False)
        Widget.setWindowTitle(u"Hammer 5 Tools")
        icon = QIcon()
        icon.addFile(u":/icons/appicon.ico", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        Widget.setWindowIcon(icon)
        Widget.setWindowOpacity(1.000000000000000)
        Widget.setToolTipDuration(-1)
        Widget.setAutoFillBackground(True)
        Widget.setStyleSheet(u"")
        Widget.setInputMethodHints(Qt.ImhNone)
        self.verticalLayout = QVBoxLayout(Widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.MainWindowTools_tabs = QTabWidget(Widget)
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
        self.MainWindowTools_tabs.addTab(self.Loading_Editor_Tab, "")
        self.soundeditor_tab = QWidget()
        self.soundeditor_tab.setObjectName(u"soundeditor_tab")
        self.soundeditor_tab.setEnabled(True)
        self.verticalLayout_5 = QVBoxLayout(self.soundeditor_tab)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.MainWindowTools_tabs.addTab(self.soundeditor_tab, "")
        self.hotkeyeditor_tab = QWidget()
        self.hotkeyeditor_tab.setObjectName(u"hotkeyeditor_tab")
        self.hotkeyeditor_tab.setEnabled(True)
        self.verticalLayout_3 = QVBoxLayout(self.hotkeyeditor_tab)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label = QLabel(self.hotkeyeditor_tab)
        self.label.setObjectName(u"label")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy1)
        self.label.setStyleSheet(u"font: 24pt \"Segoe UI\";")
        self.label.setScaledContents(False)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMargin(0)

        self.verticalLayout_3.addWidget(self.label)

        self.MainWindowTools_tabs.addTab(self.hotkeyeditor_tab, "")
        self.BatchCreator_tab = QWidget()
        self.BatchCreator_tab.setObjectName(u"BatchCreator_tab")
        self.verticalLayout_2 = QVBoxLayout(self.BatchCreator_tab)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.MainWindowTools_tabs.addTab(self.BatchCreator_tab, "")
        self.smartpropeditor_tab = QWidget()
        self.smartpropeditor_tab.setObjectName(u"smartpropeditor_tab")
        self.verticalLayout_4 = QVBoxLayout(self.smartpropeditor_tab)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.MainWindowTools_tabs.addTab(self.smartpropeditor_tab, "")
        self.synchronization_tab = QWidget()
        self.synchronization_tab.setObjectName(u"synchronization_tab")
        self.synchronization_tab.setEnabled(True)
        self.verticalLayout_6 = QVBoxLayout(self.synchronization_tab)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.label_4 = QLabel(self.synchronization_tab)
        self.label_4.setObjectName(u"label_4")
        sizePolicy1.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy1)
        self.label_4.setStyleSheet(u"font: 24pt \"Segoe UI\";")
        self.label_4.setScaledContents(False)
        self.label_4.setAlignment(Qt.AlignCenter)
        self.label_4.setMargin(0)

        self.verticalLayout_6.addWidget(self.label_4)

        self.MainWindowTools_tabs.addTab(self.synchronization_tab, "")

        self.verticalLayout.addWidget(self.MainWindowTools_tabs)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.my_twitter_button = QPushButton(Widget)
        self.my_twitter_button.setObjectName(u"my_twitter_button")
        self.my_twitter_button.setMinimumSize(QSize(128, 0))
        self.my_twitter_button.setMaximumSize(QSize(16777215, 16777210))
        self.my_twitter_button.setStyleSheet(u"padding: 5px;")
        icon1 = QIcon()
        icon1.addFile(u":/icons/public_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.my_twitter_button.setIcon(icon1)
        self.my_twitter_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.my_twitter_button)

        self.preferences_button = QPushButton(Widget)
        self.preferences_button.setObjectName(u"preferences_button")
        self.preferences_button.setMinimumSize(QSize(128, 0))
        self.preferences_button.setStyleSheet(u"padding: 5px;")
        icon2 = QIcon()
        icon2.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.preferences_button.setIcon(icon2)
        self.preferences_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.preferences_button)

        self.documentation_button = QPushButton(Widget)
        self.documentation_button.setObjectName(u"documentation_button")
        self.documentation_button.setMinimumSize(QSize(96, 0))
        self.documentation_button.setStyleSheet(u"padding: 5px;")
        icon3 = QIcon()
        icon3.addFile(u":/icons/developer_guide_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.documentation_button.setIcon(icon3)
        self.documentation_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.documentation_button)

        self.horizontalSpacer_3 = QSpacerItem(12, 6, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)

        self.export_and_import_addon_button = QToolButton(Widget)
        self.export_and_import_addon_button.setObjectName(u"export_and_import_addon_button")
        font1 = QFont()
        font1.setPointSize(11)
        self.export_and_import_addon_button.setFont(font1)
        icon4 = QIcon()
        icon4.addFile(u":/icons/publish_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.export_and_import_addon_button.setIcon(icon4)
        self.export_and_import_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.export_and_import_addon_button)

        self.delete_addon_button = QToolButton(Widget)
        self.delete_addon_button.setObjectName(u"delete_addon_button")
        self.delete_addon_button.setFont(font1)
        icon5 = QIcon()
        icon5.addFile(u":/icons/delete_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_addon_button.setIcon(icon5)
        self.delete_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.delete_addon_button)

        self.create_new_addon_button = QToolButton(Widget)
        self.create_new_addon_button.setObjectName(u"create_new_addon_button")
        self.create_new_addon_button.setFont(font1)
        icon6 = QIcon()
        icon6.addFile(u":/icons/post_add_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_new_addon_button.setIcon(icon6)
        self.create_new_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.create_new_addon_button)

        self.ComboBoxSelectAddon = QComboBox(Widget)
        self.ComboBoxSelectAddon.setObjectName(u"ComboBoxSelectAddon")
        self.ComboBoxSelectAddon.setMinimumSize(QSize(220, 0))
        self.ComboBoxSelectAddon.setStyleSheet(u"")

        self.horizontalLayout_2.addWidget(self.ComboBoxSelectAddon)

        self.check_Box_NCM_Mode = QCheckBox(Widget)
        self.check_Box_NCM_Mode.setObjectName(u"check_Box_NCM_Mode")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.check_Box_NCM_Mode.sizePolicy().hasHeightForWidth())
        self.check_Box_NCM_Mode.setSizePolicy(sizePolicy2)
        self.check_Box_NCM_Mode.setMinimumSize(QSize(72, 0))
        self.check_Box_NCM_Mode.setMaximumSize(QSize(72, 32))
        font2 = QFont()
        font2.setFamilies([u"Segoe UI"])
        font2.setPointSize(7)
        self.check_Box_NCM_Mode.setFont(font2)
        self.check_Box_NCM_Mode.setIconSize(QSize(20, 20))
        self.check_Box_NCM_Mode.setChecked(False)
        self.check_Box_NCM_Mode.setAutoRepeat(False)
        self.check_Box_NCM_Mode.setAutoExclusive(False)
        self.check_Box_NCM_Mode.setTristate(False)

        self.horizontalLayout_2.addWidget(self.check_Box_NCM_Mode)

        self.Launch_Addon_Button = QPushButton(Widget)
        self.Launch_Addon_Button.setObjectName(u"Launch_Addon_Button")
        self.Launch_Addon_Button.setEnabled(True)
        self.Launch_Addon_Button.setMinimumSize(QSize(128, 0))
        self.Launch_Addon_Button.setStyleSheet(u"padding: 5px;")
        icon7 = QIcon()
        icon7.addFile(u":/icons/open_in_new_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Launch_Addon_Button.setIcon(icon7)
        self.Launch_Addon_Button.setIconSize(QSize(20, 20))
        self.Launch_Addon_Button.setCheckable(False)

        self.horizontalLayout_2.addWidget(self.Launch_Addon_Button)

        self.horizontalSpacer = QSpacerItem(12, 6, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.open_addons_folder_button = QToolButton(Widget)
        self.open_addons_folder_button.setObjectName(u"open_addons_folder_button")
        self.open_addons_folder_button.setFont(font1)
        icon8 = QIcon()
        icon8.addFile(u":/icons/folder_open.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_addons_folder_button.setIcon(icon8)

        self.horizontalLayout_2.addWidget(self.open_addons_folder_button)

        self.open_addons_folder_downlist = QComboBox(Widget)
        self.open_addons_folder_downlist.addItem("")
        self.open_addons_folder_downlist.addItem("")
        self.open_addons_folder_downlist.setObjectName(u"open_addons_folder_downlist")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.open_addons_folder_downlist.sizePolicy().hasHeightForWidth())
        self.open_addons_folder_downlist.setSizePolicy(sizePolicy3)
        self.open_addons_folder_downlist.setMinimumSize(QSize(22, 0))

        self.horizontalLayout_2.addWidget(self.open_addons_folder_downlist)

        self.FixNoSteamLogon_Button = QPushButton(Widget)
        self.FixNoSteamLogon_Button.setObjectName(u"FixNoSteamLogon_Button")
        self.FixNoSteamLogon_Button.setMinimumSize(QSize(156, 0))
        self.FixNoSteamLogon_Button.setStyleSheet(u"padding: 5px;")
        icon9 = QIcon()
        icon9.addFile(u":/icons/auto_towing_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.FixNoSteamLogon_Button.setIcon(icon9)
        self.FixNoSteamLogon_Button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.FixNoSteamLogon_Button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.retranslateUi(Widget)

        self.MainWindowTools_tabs.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
#if QT_CONFIG(statustip)
        Widget.setStatusTip("")
#endif // QT_CONFIG(statustip)
#if QT_CONFIG(whatsthis)
        Widget.setWhatsThis(QCoreApplication.translate("Widget", u"<html><head/><body><p>Hammer</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
#if QT_CONFIG(accessibility)
        Widget.setAccessibleName("")
#endif // QT_CONFIG(accessibility)
        Widget.setWindowFilePath("")
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.Loading_Editor_Tab), QCoreApplication.translate("Widget", u"Loading Editor", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.soundeditor_tab), QCoreApplication.translate("Widget", u"SoundEvent Editor", None))
        self.label.setText(QCoreApplication.translate("Widget", u"Will be soon", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.hotkeyeditor_tab), QCoreApplication.translate("Widget", u"Hotkey Editor", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.BatchCreator_tab), QCoreApplication.translate("Widget", u"BatchCreator", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.smartpropeditor_tab), QCoreApplication.translate("Widget", u"SmartProp Editor", None))
        self.label_4.setText(QCoreApplication.translate("Widget", u"Will be soon", None))
        self.MainWindowTools_tabs.setTabText(self.MainWindowTools_tabs.indexOf(self.synchronization_tab), QCoreApplication.translate("Widget", u"Sync Editor", None))
        self.my_twitter_button.setText(QCoreApplication.translate("Widget", u"My Twitter", None))
#if QT_CONFIG(tooltip)
        self.preferences_button.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.preferences_button.setText(QCoreApplication.translate("Widget", u"Settings", None))
#if QT_CONFIG(tooltip)
        self.documentation_button.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.documentation_button.setText(QCoreApplication.translate("Widget", u"Help", None))
#if QT_CONFIG(tooltip)
        self.export_and_import_addon_button.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Archive addon</span></p><p>Create an archive on from game and content folders.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.export_and_import_addon_button.setText(QCoreApplication.translate("Widget", u"...", None))
#if QT_CONFIG(tooltip)
        self.delete_addon_button.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Delete addon</span></p><p>Deletes selected addon.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.delete_addon_button.setText(QCoreApplication.translate("Widget", u"...", None))
#if QT_CONFIG(tooltip)
        self.create_new_addon_button.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Create addon</span></p><p>Quick create an addon with custom presets.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.create_new_addon_button.setText(QCoreApplication.translate("Widget", u"...", None))
#if QT_CONFIG(tooltip)
        self.ComboBoxSelectAddon.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:11pt; font-weight:700;\">Addon selection</span></p><p>In the Addon selection, all tools apply changes to the addon selected in this section.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.check_Box_NCM_Mode.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">NCM (--nocustomermachine)</span> is a launch parameter that enable<span style=\" font-weight:700;\">s baking lightmaps with CPU</span> and <span style=\" font-weight:700;\">smartprops compilation</span>.</p><p>However, when CS2 is launched with this parameter, default assets will not be visible; only your own assets will appear.</p><p><img src=\":/images/tooltip/tooltip_ncm_01.png\" width=\"259\"/></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(whatsthis)
        self.check_Box_NCM_Mode.setWhatsThis(QCoreApplication.translate("Widget", u"<html><head/><body><p><br/></p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.check_Box_NCM_Mode.setText(QCoreApplication.translate("Widget", u"NCM", None))
#if QT_CONFIG(tooltip)
        self.Launch_Addon_Button.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Addon launch</span></p><p>Launches the current addon selected in the addon selection.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.Launch_Addon_Button.setText(QCoreApplication.translate("Widget", u"Launch Addon", None))
#if QT_CONFIG(tooltip)
        self.open_addons_folder_button.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Open Game/Content Addons folder</span></p><p><span style=\" font-size:9pt;\">Opens the game addons or content addons folder for the current addon selection. </span></p><p><span style=\" font-size:9pt;\">To choose the folder type to open, select a folder in the </span><span style=\" font-size:9pt; font-style:italic;\">Addon Folder Selection</span><span style=\" font-size:9pt;\">.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_addons_folder_button.setText(QCoreApplication.translate("Widget", u"...", None))
        self.open_addons_folder_downlist.setItemText(0, QCoreApplication.translate("Widget", u"Content", None))
        self.open_addons_folder_downlist.setItemText(1, QCoreApplication.translate("Widget", u"Game", None))

#if QT_CONFIG(tooltip)
        self.open_addons_folder_downlist.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Addon Folder Selection</span></p><p>Used to choose the folder that should be oppened in the <span style=\" font-style:italic;\">Open Game/Content Addons Folder.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_addons_folder_downlist.setCurrentText("")
        self.open_addons_folder_downlist.setPlaceholderText(QCoreApplication.translate("Widget", u"Open Folder", None))
#if QT_CONFIG(tooltip)
        self.FixNoSteamLogon_Button.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p><span style=\" font-size:12pt; font-weight:700;\">Fix No Steam Logon</span></p><p>This script restarts Steam and launches the current addon.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.FixNoSteamLogon_Button.setText(QCoreApplication.translate("Widget", u"Fix NoLogon", None))
    # retranslateUi

