# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDockWidget,
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QPushButton, QSizePolicy,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1490, 941)
        MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.actionCreateNewsmartprop = QAction(MainWindow)
        self.actionCreateNewsmartprop.setObjectName(u"actionCreateNewsmartprop")
        icon = QIcon()
        icon.addFile(u":/valve_common/icons/tools/common/new.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionCreateNewsmartprop.setIcon(icon)
        self.actionCreateNewsmartprop.setMenuRole(QAction.MenuRole.NoRole)
        self.actionOpen_from_Explorer = QAction(MainWindow)
        self.actionOpen_from_Explorer.setObjectName(u"actionOpen_from_Explorer")
        icon1 = QIcon()
        icon1.addFile(u":/valve_common/icons/tools/common/open.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionOpen_from_Explorer.setIcon(icon1)
        self.actionSave_as = QAction(MainWindow)
        self.actionSave_as.setObjectName(u"actionSave_as")
        icon2 = QIcon()
        icon2.addFile(u":/valve_common/icons/tools/common/save_all.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSave_as.setIcon(icon2)
        self.actionSave_current_file = QAction(MainWindow)
        self.actionSave_current_file.setObjectName(u"actionSave_current_file")
        icon3 = QIcon()
        icon3.addFile(u":/valve_common/icons/tools/common/save.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSave_current_file.setIcon(icon3)
        self.actionRecompile_file = QAction(MainWindow)
        self.actionRecompile_file.setObjectName(u"actionRecompile_file")
        icon4 = QIcon()
        icon4.addFile(u":/valve_common/icons/tools/common/options_activated.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionRecompile_file.setIcon(icon4)
        self.actionRecompile_all_in_addon = QAction(MainWindow)
        self.actionRecompile_all_in_addon.setObjectName(u"actionRecompile_all_in_addon")
        self.actionRecompile_all_in_addon.setIcon(icon4)
        self.actionConvert_all_vsmart_file_to_vdata = QAction(MainWindow)
        self.actionConvert_all_vsmart_file_to_vdata.setObjectName(u"actionConvert_all_vsmart_file_to_vdata")
        icon5 = QIcon()
        icon5.addFile(u":/valve_common/icons/tools/common/move_to_changelist.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionConvert_all_vsmart_file_to_vdata.setIcon(icon5)
        self.actionFormat_serttings = QAction(MainWindow)
        self.actionFormat_serttings.setObjectName(u"actionFormat_serttings")
        icon6 = QIcon()
        icon6.addFile(u":/valve_common/icons/tools/common/setting.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionFormat_serttings.setIcon(icon6)
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
        self.dockWidget_4 = QDockWidget(MainWindow)
        self.dockWidget_4.setObjectName(u"dockWidget_4")
        self.dockWidget_4.setMinimumSize(QSize(320, 189))
        self.dockWidget_4.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.dockWidget_4.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea|Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea)
        self.dockWidgetContents_2 = QWidget()
        self.dockWidgetContents_2.setObjectName(u"dockWidgetContents_2")
        self.verticalLayout_8 = QVBoxLayout(self.dockWidgetContents_2)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.frame_2 = QFrame(self.dockWidgetContents_2)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.frame_2.setLineWidth(0)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.hierarchy_search_bar_widget = QLineEdit(self.frame_2)
        self.hierarchy_search_bar_widget.setObjectName(u"hierarchy_search_bar_widget")

        self.verticalLayout_3.addWidget(self.hierarchy_search_bar_widget)

        self.hierarchy_widget = QTreeWidget(self.frame_2)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"Name");
        self.hierarchy_widget.setHeaderItem(__qtreewidgetitem)
        self.hierarchy_widget.setObjectName(u"hierarchy_widget")
        self.hierarchy_widget.setDragEnabled(True)
        self.hierarchy_widget.setDragDropOverwriteMode(True)
        self.hierarchy_widget.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.hierarchy_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.hierarchy_widget.setAlternatingRowColors(True)
        self.hierarchy_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.hierarchy_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.hierarchy_widget.setUniformRowHeights(True)
        self.hierarchy_widget.setAllColumnsShowFocus(False)
        self.hierarchy_widget.setWordWrap(False)
        self.hierarchy_widget.setHeaderHidden(False)
        self.hierarchy_widget.setColumnCount(2)
        self.hierarchy_widget.header().setVisible(True)
        self.hierarchy_widget.header().setCascadingSectionResizes(False)
        self.hierarchy_widget.header().setMinimumSectionSize(45)
        self.hierarchy_widget.header().setDefaultSectionSize(135)
        self.hierarchy_widget.header().setProperty(u"showSortIndicator", False)
        self.hierarchy_widget.header().setStretchLastSection(True)

        self.verticalLayout_3.addWidget(self.hierarchy_widget)

        self.open_preset_manager_button = QPushButton(self.frame_2)
        self.open_preset_manager_button.setObjectName(u"open_preset_manager_button")
        self.open_preset_manager_button.setEnabled(True)
        self.open_preset_manager_button.setStyleSheet(u"\n"
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
        icon7.addFile(u":/icons/schema_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_preset_manager_button.setIcon(icon7)
        self.open_preset_manager_button.setIconSize(QSize(20, 20))

        self.verticalLayout_3.addWidget(self.open_preset_manager_button)


        self.verticalLayout_8.addWidget(self.frame_2)

        self.dockWidget_4.setWidget(self.dockWidgetContents_2)
        MainWindow.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidget_4)
        self.dockWidget_10 = QDockWidget(MainWindow)
        self.dockWidget_10.setObjectName(u"dockWidget_10")
        self.dockWidget_10.setMinimumSize(QSize(320, 174))
        self.dockWidget_10.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.dockWidget_10.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea|Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea)
        self.explorer_layout_widget = QWidget()
        self.explorer_layout_widget.setObjectName(u"explorer_layout_widget")
        self.verticalLayout_10 = QVBoxLayout(self.explorer_layout_widget)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(self.explorer_layout_widget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.addon_sounds = QWidget()
        self.addon_sounds.setObjectName(u"addon_sounds")
        self.verticalLayout = QVBoxLayout(self.addon_sounds)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.explorer_layout = QVBoxLayout()
        self.explorer_layout.setObjectName(u"explorer_layout")

        self.verticalLayout.addLayout(self.explorer_layout)

        self.tabWidget.addTab(self.addon_sounds, "")
        self.internal_sounds = QWidget()
        self.internal_sounds.setObjectName(u"internal_sounds")
        self.verticalLayout_4 = QVBoxLayout(self.internal_sounds)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.internal_explorer_search_bar = QLineEdit(self.internal_sounds)
        self.internal_explorer_search_bar.setObjectName(u"internal_explorer_search_bar")

        self.verticalLayout_4.addWidget(self.internal_explorer_search_bar)

        self.internal_explorer_layout = QVBoxLayout()
        self.internal_explorer_layout.setObjectName(u"internal_explorer_layout")

        self.verticalLayout_4.addLayout(self.internal_explorer_layout)

        self.tabWidget.addTab(self.internal_sounds, "")

        self.verticalLayout_10.addWidget(self.tabWidget)

        self.frame_3 = QFrame(self.explorer_layout_widget)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16777215, 32))
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.save_file_button = QPushButton(self.frame_3)
        self.save_file_button.setObjectName(u"save_file_button")
        self.save_file_button.setStyleSheet(u"\n"
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
        self.save_file_button.setIcon(icon8)
        self.save_file_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.save_file_button)

        self.realtime_save_checkbox = QCheckBox(self.frame_3)
        self.realtime_save_checkbox.setObjectName(u"realtime_save_checkbox")
        self.realtime_save_checkbox.setStyleSheet(u"\n"
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

        self.horizontalLayout_4.addWidget(self.realtime_save_checkbox)


        self.verticalLayout_10.addWidget(self.frame_3)

        self.frame_4 = QFrame(self.explorer_layout_widget)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setMaximumSize(QSize(16777215, 32))
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.output_button = QPushButton(self.frame_4)
        self.output_button.setObjectName(u"output_button")
        self.output_button.setStyleSheet(u"\n"
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
        self.output_button.setIcon(icon9)
        self.output_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.output_button)

        self.reload_button = QPushButton(self.frame_4)
        self.reload_button.setObjectName(u"reload_button")
        self.reload_button.setStyleSheet(u"\n"
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
        icon10.addFile(u":/icons/sync_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.reload_button.setIcon(icon10)
        self.reload_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.reload_button)


        self.verticalLayout_10.addWidget(self.frame_4)

        self.dockWidget_10.setWidget(self.explorer_layout_widget)
        MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget_10)

        self.retranslateUi(MainWindow)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
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
        self.dockWidget_4.setWindowTitle(QCoreApplication.translate("MainWindow", u"Soundevents", None))
        self.hierarchy_search_bar_widget.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search...", None))
        ___qtreewidgetitem = self.hierarchy_widget.headerItem()
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Data", None));
#if QT_CONFIG(tooltip)
        self.open_preset_manager_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Oopen Preset Manager Ctrl + P</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_preset_manager_button.setText(QCoreApplication.translate("MainWindow", u"Preset manager", None))
#if QT_CONFIG(shortcut)
        self.open_preset_manager_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+P", None))
#endif // QT_CONFIG(shortcut)
        self.dockWidget_10.setWindowTitle(QCoreApplication.translate("MainWindow", u"Audio Explorer", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.addon_sounds), QCoreApplication.translate("MainWindow", u"Addon", None))
        self.internal_explorer_search_bar.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search...", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.internal_sounds), QCoreApplication.translate("MainWindow", u"Internal", None))
#if QT_CONFIG(tooltip)
        self.save_file_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Save soundevents_addon.vsndevts Ctrl + S</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.save_file_button.setText(QCoreApplication.translate("MainWindow", u"Save", None))
#if QT_CONFIG(shortcut)
        self.save_file_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.realtime_save_checkbox.setText(QCoreApplication.translate("MainWindow", u"Realtime save", None))
#if QT_CONFIG(tooltip)
        self.output_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Open soundevents_addon.vsndevts</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.output_button.setText(QCoreApplication.translate("MainWindow", u"Output", None))
#if QT_CONFIG(shortcut)
        self.output_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.reload_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Reload soundevents_addon.vsndevts Ctrl + R</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.reload_button.setText(QCoreApplication.translate("MainWindow", u"Reload", None))
#if QT_CONFIG(shortcut)
        self.reload_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Shift+S", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

