# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'document.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDockWidget,
    QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QScrollArea, QSizePolicy,
    QSpacerItem, QToolButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(987, 808)
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
        self.verticalLayout_9 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_9.setSpacing(0)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.PropertiesFrame = QFrame(self.centralwidget)
        self.PropertiesFrame.setObjectName(u"PropertiesFrame")
        self.PropertiesFrame.setStyleSheet(u"        QFrame#PropertiesFrame {\n"
"            border: 2px solid black; \n"
"            border-color: rgba(80, 80, 80, 255);\n"
"        }\n"
"        QFrame#PropertiesFrame QLabel {\n"
"            border: 0px solid black; \n"
"        }")
        self.PropertiesFrame.setFrameShape(QFrame.Shape.StyledPanel)
        self.PropertiesFrame.setFrameShadow(QFrame.Shadow.Raised)
        self.PropertiesFrame.setLineWidth(0)
        self.verticalLayout_5 = QVBoxLayout(self.PropertiesFrame)
        self.verticalLayout_5.setSpacing(0)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.PropertiesArea = QScrollArea(self.PropertiesFrame)
        self.PropertiesArea.setObjectName(u"PropertiesArea")
        self.PropertiesArea.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.PropertiesArea.setStyleSheet(u"QScrollArea {\n"
"    border: 0px solid black;\n"
"}")
        self.PropertiesArea.setLineWidth(0)
        self.PropertiesArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.PropertiesArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 721, 804))
        self.scrollAreaWidgetContents.setStyleSheet(u"QWidget: {\n"
"	border: 0px;\n"
"}")
        self.verticalLayout_17 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_17.setSpacing(0)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.properties_layout = QVBoxLayout()
        self.properties_layout.setObjectName(u"properties_layout")
        self.properties_placeholder = QLabel(self.scrollAreaWidgetContents)
        self.properties_placeholder.setObjectName(u"properties_placeholder")
        self.properties_placeholder.setStyleSheet(u"color: gray; font-size: 13px;")
        self.properties_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.properties_layout.addWidget(self.properties_placeholder)

        self.properties_spacer = QFrame(self.scrollAreaWidgetContents)
        self.properties_spacer.setObjectName(u"properties_spacer")
        self.properties_spacer.setFrameShape(QFrame.Shape.StyledPanel)
        self.properties_spacer.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.properties_spacer)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalSpacer = QSpacerItem(20, 655, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)


        self.properties_layout.addWidget(self.properties_spacer)


        self.verticalLayout_17.addLayout(self.properties_layout)

        self.PropertiesArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_5.addWidget(self.PropertiesArea)


        self.verticalLayout_9.addWidget(self.PropertiesFrame)

        MainWindow.setCentralWidget(self.centralwidget)
        self.HierarchyDock = QDockWidget(MainWindow)
        self.HierarchyDock.setObjectName(u"HierarchyDock")
        self.HierarchyDock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.HierarchyDock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea|Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea)
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
        self.tree_hierarchy_search_bar_widget = QLineEdit(self.frame_2)
        self.tree_hierarchy_search_bar_widget.setObjectName(u"tree_hierarchy_search_bar_widget")

        self.verticalLayout_3.addWidget(self.tree_hierarchy_search_bar_widget)

        self.tree_hierarchy_widget = QTreeWidget(self.frame_2)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"Label");
        self.tree_hierarchy_widget.setHeaderItem(__qtreewidgetitem)
        self.tree_hierarchy_widget.setObjectName(u"tree_hierarchy_widget")
        self.tree_hierarchy_widget.setDragEnabled(True)
        self.tree_hierarchy_widget.setDragDropOverwriteMode(True)
        self.tree_hierarchy_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree_hierarchy_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree_hierarchy_widget.setAlternatingRowColors(True)
        self.tree_hierarchy_widget.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.tree_hierarchy_widget.setUniformRowHeights(True)
        self.tree_hierarchy_widget.setAllColumnsShowFocus(False)
        self.tree_hierarchy_widget.setWordWrap(False)
        self.tree_hierarchy_widget.setHeaderHidden(False)
        self.tree_hierarchy_widget.setColumnCount(4)
        self.tree_hierarchy_widget.header().setVisible(True)
        self.tree_hierarchy_widget.header().setCascadingSectionResizes(False)
        self.tree_hierarchy_widget.header().setMinimumSectionSize(20)
        self.tree_hierarchy_widget.header().setDefaultSectionSize(135)
        self.tree_hierarchy_widget.header().setProperty(u"showSortIndicator", False)
        self.tree_hierarchy_widget.header().setStretchLastSection(True)

        self.verticalLayout_3.addWidget(self.tree_hierarchy_widget)


        self.verticalLayout_8.addWidget(self.frame_2)

        self.HierarchyDock.setWidget(self.dockWidgetContents_2)
        MainWindow.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.HierarchyDock)
        self.ChoicesDock = QDockWidget(MainWindow)
        self.ChoicesDock.setObjectName(u"ChoicesDock")
        self.ChoicesDock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.dockWidgetContents_3 = QWidget()
        self.dockWidgetContents_3.setObjectName(u"dockWidgetContents_3")
        self.verticalLayout = QVBoxLayout(self.dockWidgetContents_3)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.choices_tree_widget = QTreeWidget(self.dockWidgetContents_3)
        self.choices_tree_widget.setObjectName(u"choices_tree_widget")
        self.choices_tree_widget.setDragEnabled(False)
        self.choices_tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.choices_tree_widget.setAlternatingRowColors(True)
        self.choices_tree_widget.setUniformRowHeights(True)
        self.choices_tree_widget.header().setVisible(True)
        self.choices_tree_widget.header().setCascadingSectionResizes(False)
        self.choices_tree_widget.header().setMinimumSectionSize(150)
        self.choices_tree_widget.header().setDefaultSectionSize(180)
        self.choices_tree_widget.header().setProperty(u"showSortIndicator", True)

        self.verticalLayout.addWidget(self.choices_tree_widget)

        self.ChoicesDock.setWidget(self.dockWidgetContents_3)
        MainWindow.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ChoicesDock)
        self.VariablesDock = QDockWidget(MainWindow)
        self.VariablesDock.setObjectName(u"VariablesDock")
        self.VariablesDock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.VariablesDock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea|Qt.DockWidgetArea.TopDockWidgetArea)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout_7 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_7.setSpacing(2)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.variables_scroll_area_searchbar = QLineEdit(self.dockWidgetContents)
        self.variables_scroll_area_searchbar.setObjectName(u"variables_scroll_area_searchbar")

        self.verticalLayout_7.addWidget(self.variables_scroll_area_searchbar)

        self.variables_QscrollArea = QScrollArea(self.dockWidgetContents)
        self.variables_QscrollArea.setObjectName(u"variables_QscrollArea")
        self.variables_QscrollArea.setWidgetResizable(True)
        self.variables_scrollArea_widget = QWidget()
        self.variables_scrollArea_widget.setObjectName(u"variables_scrollArea_widget")
        self.variables_scrollArea_widget.setGeometry(QRect(0, 0, 256, 100))
        self.variables_scrollArea_widget.setStyleSheet(u"")
        self.verticalLayout_2 = QVBoxLayout(self.variables_scrollArea_widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.variables_scrollArea = QVBoxLayout()
        self.variables_scrollArea.setSpacing(0)
        self.variables_scrollArea.setObjectName(u"variables_scrollArea")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.variables_scrollArea.addItem(self.verticalSpacer_2)


        self.verticalLayout_2.addLayout(self.variables_scrollArea)

        self.variables_QscrollArea.setWidget(self.variables_scrollArea_widget)

        self.verticalLayout_7.addWidget(self.variables_QscrollArea)

        self.frame = QFrame(self.dockWidgetContents)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(0, 0))
        self.frame.setMaximumSize(QSize(16777215, 28))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.paste_variable_button = QToolButton(self.frame)
        self.paste_variable_button.setObjectName(u"paste_variable_button")
        self.paste_variable_button.setMaximumSize(QSize(28, 28))
        self.paste_variable_button.setStyleSheet(u"\n"
"    /* QPushButton default and hover styles */\n"
"    QToolButton {\n"
"\n"
"        font: 580 9pt \"Segoe UI\";\n"
"\n"
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
"    QToolButton:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QToolButton:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"\n"
"    }")
        icon7 = QIcon()
        icon7.addFile(u":/icons/content_paste_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.paste_variable_button.setIcon(icon7)
        self.paste_variable_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.paste_variable_button)

        self.add_new_variable_button = QToolButton(self.frame)
        self.add_new_variable_button.setObjectName(u"add_new_variable_button")
        self.add_new_variable_button.setMaximumSize(QSize(28, 28))
        self.add_new_variable_button.setStyleSheet(u"\n"
"    /* QPushButton default and hover styles */\n"
"    QToolButton {\n"
"\n"
"        font: 580 9pt \"Segoe UI\";\n"
"\n"
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
"    QToolButton:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QToolButton:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"\n"
"    }")
        icon8 = QIcon()
        icon8.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_new_variable_button.setIcon(icon8)
        self.add_new_variable_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.add_new_variable_button)

        self.add_new_variable_combobox = QComboBox(self.frame)
        self.add_new_variable_combobox.setObjectName(u"add_new_variable_combobox")
        self.add_new_variable_combobox.setStyleSheet(u"QMenu {\n"
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
"    border-radius: 2px;\n"
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
"    border-radius: 2px;\n"
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

        self.horizontalLayout.addWidget(self.add_new_variable_combobox)


        self.verticalLayout_7.addWidget(self.frame)

        self.VariablesDock.setWidget(self.dockWidgetContents)
        MainWindow.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.VariablesDock)

        self.retranslateUi(MainWindow)

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
        self.properties_placeholder.setText(QCoreApplication.translate("MainWindow", u"Select an element in the hierarchy", None))
        self.HierarchyDock.setWindowTitle(QCoreApplication.translate("MainWindow", u"Hierarchy", None))
        self.tree_hierarchy_search_bar_widget.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search...", None))
        ___qtreewidgetitem = self.tree_hierarchy_widget.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("MainWindow", u"ID", None));
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("MainWindow", u"Class", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Data", None));
        self.ChoicesDock.setWindowTitle(QCoreApplication.translate("MainWindow", u"Choices", None))
        ___qtreewidgetitem1 = self.choices_tree_widget.headerItem()
        ___qtreewidgetitem1.setText(2, QCoreApplication.translate("MainWindow", u"Type", None));
        ___qtreewidgetitem1.setText(1, QCoreApplication.translate("MainWindow", u"Value", None));
        ___qtreewidgetitem1.setText(0, QCoreApplication.translate("MainWindow", u"Label", None));
        self.VariablesDock.setWindowTitle(QCoreApplication.translate("MainWindow", u"Variables", None))
        self.variables_scroll_area_searchbar.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search...", None))
#if QT_CONFIG(tooltip)
        self.paste_variable_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Paste variable</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.paste_variable_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.add_new_variable_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Create variable</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.add_new_variable_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
    # retranslateUi

