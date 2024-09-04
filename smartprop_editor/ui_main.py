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
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QDockWidget, QFrame,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QSpacerItem, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
import rc_resources

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1280, 720)
        MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.actionDebug_output = QAction(MainWindow)
        self.actionDebug_output.setObjectName(u"actionDebug_output")
        icon = QIcon()
        icon.addFile(u":/icons/find_in_page_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionDebug_output.setIcon(icon)
        self.actionCreateNewsmartprop = QAction(MainWindow)
        self.actionCreateNewsmartprop.setObjectName(u"actionCreateNewsmartprop")
        icon1 = QIcon()
        icon1.addFile(u":/icons/add_circle_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionCreateNewsmartprop.setIcon(icon1)
        self.actionCreateNewsmartprop.setMenuRole(QAction.NoRole)
        self.actionSaveSmarptop = QAction(MainWindow)
        self.actionSaveSmarptop.setObjectName(u"actionSaveSmarptop")
        icon2 = QIcon()
        icon2.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSaveSmarptop.setIcon(icon2)
        self.actionSaveSmarptop.setMenuRole(QAction.NoRole)
        self.actionSaveSmartpropAs = QAction(MainWindow)
        self.actionSaveSmartpropAs.setObjectName(u"actionSaveSmartpropAs")
        self.actionSaveSmartpropAs.setCheckable(True)
        icon3 = QIcon()
        icon3.addFile(u":/icons/save_as_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSaveSmartpropAs.setIcon(icon3)
        self.actionSaveSmartpropAs.setMenuRole(QAction.NoRole)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_9 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_9.setSpacing(0)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.frame_9 = QFrame(self.centralwidget)
        self.frame_9.setObjectName(u"frame_9")
        self.frame_9.setFrameShape(QFrame.StyledPanel)
        self.frame_9.setFrameShadow(QFrame.Raised)
        self.frame_9.setLineWidth(0)
        self.verticalLayout_5 = QVBoxLayout(self.frame_9)
        self.verticalLayout_5.setSpacing(0)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(self.frame_9)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 538, 690))
        self.verticalLayout_17 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.group_class_properties = QGroupBox(self.scrollAreaWidgetContents)
        self.group_class_properties.setObjectName(u"group_class_properties")
        self.group_class_properties.setStyleSheet(u"/* QGroupBox Style */\n"
"QGroupBox {\n"
"    border: 1px solid gray; /* Set the border color and width */\n"
"    border-bottom: none; /* Remove the bottom border */\n"
"    border-left: none; /* Remove the left border */\n"
"    border-right: none; /* Remove the right border */\n"
"    margin-top: 8px; /* Space for the title */\n"
"	padding-top: 8px;\n"
"}\n"
"\n"
"/* Title Style */\n"
"QGroupBox::title {\n"
"    subcontrol-origin: margin;\n"
"    subcontrol-position: top left;\n"
"    padding: 0 6;\n"
"    color: white; \n"
"}\n"
"\n"
"QGroupBox::indicator {\n"
"    width: 13px;\n"
"    height: 13px;\n"
"}\n"
"\n"
"QGroupBox::indicator:checked {\n"
"    image: url(://icons/arrow_drop_right.png);\n"
"}\n"
"\n"
"QGroupBox::indicator:unchecked {\n"
"    image: url(://icons/arrow_drop_down.png); \n"
"}")
        self.group_class_properties.setFlat(False)
        self.group_class_properties.setCheckable(True)
        self.verticalLayout_13 = QVBoxLayout(self.group_class_properties)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.scrollArea__class_properties = QScrollArea(self.group_class_properties)
        self.scrollArea__class_properties.setObjectName(u"scrollArea__class_properties")
        self.scrollArea__class_properties.setStyleSheet(u"QScrollArea {\n"
"    border: 0px solid #CCCCCC;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 2px;\n"
"    color: #E3E3E3;\n"
"}")
        self.scrollArea__class_properties.setWidgetResizable(True)
        self._class_properties_widget = QWidget()
        self._class_properties_widget.setObjectName(u"_class_properties_widget")
        self._class_properties_widget.setGeometry(QRect(0, 0, 538, 123))
        self.verticalLayout_14 = QVBoxLayout(self._class_properties_widget)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.scrollArea__class_properties.setWidget(self._class_properties_widget)

        self.verticalLayout_13.addWidget(self.scrollArea__class_properties)


        self.verticalLayout_17.addWidget(self.group_class_properties)

        self.group_modifiers = QGroupBox(self.scrollAreaWidgetContents)
        self.group_modifiers.setObjectName(u"group_modifiers")
        self.group_modifiers.setStyleSheet(u"/* QGroupBox Style */\n"
"QGroupBox {\n"
"    border: 1px solid gray; /* Set the border color and width */\n"
"    border-bottom: none; /* Remove the bottom border */\n"
"    border-left: none; /* Remove the left border */\n"
"    border-right: none; /* Remove the right border */\n"
"    margin-top: 8px; /* Space for the title */\n"
"	padding-top: 8px;\n"
"}\n"
"\n"
"/* Title Style */\n"
"QGroupBox::title {\n"
"    subcontrol-origin: margin;\n"
"    subcontrol-position: top left;\n"
"    padding: 0 6;\n"
"    color: white; \n"
"}\n"
"\n"
"QGroupBox::indicator {\n"
"    width: 13px;\n"
"    height: 13px;\n"
"}\n"
"\n"
"QGroupBox::indicator:checked {\n"
"    image: url(://icons/arrow_drop_right.png);\n"
"}\n"
"\n"
"QGroupBox::indicator:unchecked {\n"
"    image: url(://icons/arrow_drop_down.png); \n"
"}")
        self.group_modifiers.setFlat(False)
        self.group_modifiers.setCheckable(True)
        self.verticalLayout = QVBoxLayout(self.group_modifiers)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_modifiers = QScrollArea(self.group_modifiers)
        self.scrollArea_modifiers.setObjectName(u"scrollArea_modifiers")
        self.scrollArea_modifiers.setStyleSheet(u"QScrollArea {\n"
"    border: 0px solid #CCCCCC;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 2px;\n"
"    color: #E3E3E3;\n"
"}")
        self.scrollArea_modifiers.setWidgetResizable(True)
        self.modifiers_widget = QWidget()
        self.modifiers_widget.setObjectName(u"modifiers_widget")
        self.modifiers_widget.setGeometry(QRect(0, 0, 538, 123))
        self.verticalLayout_4 = QVBoxLayout(self.modifiers_widget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.scrollArea_modifiers.setWidget(self.modifiers_widget)

        self.verticalLayout.addWidget(self.scrollArea_modifiers)


        self.verticalLayout_17.addWidget(self.group_modifiers)

        self.group_selection_criteria = QGroupBox(self.scrollAreaWidgetContents)
        self.group_selection_criteria.setObjectName(u"group_selection_criteria")
        self.group_selection_criteria.setStyleSheet(u"/* QGroupBox Style */\n"
"QGroupBox {\n"
"    border: 1px solid gray; /* Set the border color and width */\n"
"    border-bottom: none; /* Remove the bottom border */\n"
"    border-left: none; /* Remove the left border */\n"
"    border-right: none; /* Remove the right border */\n"
"    margin-top: 8px; /* Space for the title */\n"
"	padding-top: 8px;\n"
"}\n"
"\n"
"/* Title Style */\n"
"QGroupBox::title {\n"
"    subcontrol-origin: margin;\n"
"    subcontrol-position: top left;\n"
"    padding: 0 6;\n"
"    color: white; \n"
"}\n"
"\n"
"QGroupBox::indicator {\n"
"    width: 13px;\n"
"    height: 13px;\n"
"}\n"
"\n"
"QGroupBox::indicator:checked {\n"
"    image: url(://icons/arrow_drop_right.png);\n"
"}\n"
"\n"
"QGroupBox::indicator:unchecked {\n"
"    image: url(://icons/arrow_drop_down.png); \n"
"}")
        self.group_selection_criteria.setFlat(False)
        self.group_selection_criteria.setCheckable(True)
        self.verticalLayout_15 = QVBoxLayout(self.group_selection_criteria)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_selection_criteria = QScrollArea(self.group_selection_criteria)
        self.scrollArea_selection_criteria.setObjectName(u"scrollArea_selection_criteria")
        self.scrollArea_selection_criteria.setStyleSheet(u"QScrollArea {\n"
"    border: 0px solid #CCCCCC;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 2px;\n"
"    color: #E3E3E3;\n"
"}")
        self.scrollArea_selection_criteria.setWidgetResizable(True)
        self.selection_criteria_widget = QWidget()
        self.selection_criteria_widget.setObjectName(u"selection_criteria_widget")
        self.selection_criteria_widget.setGeometry(QRect(0, 0, 538, 123))
        self.verticalLayout_16 = QVBoxLayout(self.selection_criteria_widget)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.scrollArea_selection_criteria.setWidget(self.selection_criteria_widget)

        self.verticalLayout_15.addWidget(self.scrollArea_selection_criteria)


        self.verticalLayout_17.addWidget(self.group_selection_criteria)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_17.addItem(self.verticalSpacer)

        self.label = QLabel(self.scrollAreaWidgetContents)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"QLabel {\n"
"    font: 580 9pt \"Segoe UI\";\n"
"    padding-top: 2px;\n"
"    padding-bottom:2px;\n"
"    padding-left: 4px;\n"
"    padding-right: 4px;\n"
"    color: #E3E3E3;\n"
"}")

        self.verticalLayout_17.addWidget(self.label)

        self.plainTextEdit = QPlainTextEdit(self.scrollAreaWidgetContents)
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        self.plainTextEdit.setMaximumSize(QSize(16777215, 80))

        self.verticalLayout_17.addWidget(self.plainTextEdit)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_5.addWidget(self.scrollArea)

        self.frame_8 = QFrame(self.frame_9)
        self.frame_8.setObjectName(u"frame_8")
        self.frame_8.setFrameShape(QFrame.StyledPanel)
        self.frame_8.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_8)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.status_bar = QLineEdit(self.frame_8)
        self.status_bar.setObjectName(u"status_bar")
        self.status_bar.setReadOnly(True)

        self.horizontalLayout_5.addWidget(self.status_bar)

        self.version_label = QLabel(self.frame_8)
        self.version_label.setObjectName(u"version_label")
        self.version_label.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_5.addWidget(self.version_label)


        self.verticalLayout_5.addWidget(self.frame_8)


        self.verticalLayout_9.addWidget(self.frame_9)

        MainWindow.setCentralWidget(self.centralwidget)
        self.dockWidget_4 = QDockWidget(MainWindow)
        self.dockWidget_4.setObjectName(u"dockWidget_4")
        self.dockWidget_4.setFeatures(QDockWidget.DockWidgetMovable)
        self.dockWidget_4.setAllowedAreas(Qt.BottomDockWidgetArea|Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.dockWidgetContents_2 = QWidget()
        self.dockWidgetContents_2.setObjectName(u"dockWidgetContents_2")
        self.verticalLayout_8 = QVBoxLayout(self.dockWidgetContents_2)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.frame_2 = QFrame(self.dockWidgetContents_2)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.frame_2.setLineWidth(0)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.tree_hierarchy_search_bar_widget = QLineEdit(self.frame_2)
        self.tree_hierarchy_search_bar_widget.setObjectName(u"tree_hierarchy_search_bar_widget")

        self.verticalLayout_3.addWidget(self.tree_hierarchy_search_bar_widget)

        self.tree_hierarchy_widget = QTreeWidget(self.frame_2)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"Name");
        self.tree_hierarchy_widget.setHeaderItem(__qtreewidgetitem)
        __qtreewidgetitem1 = QTreeWidgetItem(self.tree_hierarchy_widget)
        QTreeWidgetItem(__qtreewidgetitem1)
        __qtreewidgetitem2 = QTreeWidgetItem(self.tree_hierarchy_widget)
        QTreeWidgetItem(__qtreewidgetitem2)
        self.tree_hierarchy_widget.setObjectName(u"tree_hierarchy_widget")
        self.tree_hierarchy_widget.header().setVisible(False)

        self.verticalLayout_3.addWidget(self.tree_hierarchy_widget)


        self.verticalLayout_8.addWidget(self.frame_2)

        self.dockWidget_4.setWidget(self.dockWidgetContents_2)
        MainWindow.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidget_4)
        self.dockWidget = QDockWidget(MainWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidget.setFeatures(QDockWidget.DockWidgetMovable)
        self.dockWidget.setAllowedAreas(Qt.BottomDockWidgetArea|Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout_7 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_7.setSpacing(6)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_2 = QScrollArea(self.dockWidgetContents)
        self.scrollArea_2.setObjectName(u"scrollArea_2")
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 348, 290))
        self.verticalLayout_2 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_7.addWidget(self.scrollArea_2)

        self.frame = QFrame(self.dockWidgetContents)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(0, 0))
        self.frame.setMaximumSize(QSize(16777215, 28))
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.add_new_variable_button = QToolButton(self.frame)
        self.add_new_variable_button.setObjectName(u"add_new_variable_button")
        icon4 = QIcon()
        icon4.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_new_variable_button.setIcon(icon4)
        self.add_new_variable_button.setIconSize(QSize(16, 16))

        self.horizontalLayout.addWidget(self.add_new_variable_button)

        self.add_new_variable_combobox = QComboBox(self.frame)
        self.add_new_variable_combobox.addItem("")
        self.add_new_variable_combobox.addItem("")
        self.add_new_variable_combobox.addItem("")
        self.add_new_variable_combobox.setObjectName(u"add_new_variable_combobox")
        self.add_new_variable_combobox.setStyleSheet(u"QMenu {\n"
"background-color: red;\n"
" }\n"
"\n"
"QMenu::item {\n"
"    padding: 5px 10px;\n"
"    font: 700 10pt \"Segoe UI\";\n"
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
"    font: 700 10pt \"Segoe UI\";\n"
"    border-top: "
                        "2px solid black;\n"
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
"    font: 600 9pt \"Segoe UI\";\n"
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
"    back"
                        "ground-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:pressed {\n"
"    background-color: #2E2F30;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:item {\n"
"    font: 600 12pt \"Segoe UI\";\n"
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
"QComboBox QAbstractItemView::item"
                        " {\n"
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

        self.dockWidget.setWidget(self.dockWidgetContents)
        MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget)
        self.dockWidget_10 = QDockWidget(MainWindow)
        self.dockWidget_10.setObjectName(u"dockWidget_10")
        self.dockWidget_10.setFeatures(QDockWidget.DockWidgetMovable)
        self.dockWidget_10.setAllowedAreas(Qt.BottomDockWidgetArea|Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.dockWidgetContents_10 = QWidget()
        self.dockWidgetContents_10.setObjectName(u"dockWidgetContents_10")
        self.verticalLayout_10 = QVBoxLayout(self.dockWidgetContents_10)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.tree_smartprops_explorer_widget = QTreeWidget(self.dockWidgetContents_10)
        __qtreewidgetitem3 = QTreeWidgetItem()
        __qtreewidgetitem3.setText(0, u"1");
        self.tree_smartprops_explorer_widget.setHeaderItem(__qtreewidgetitem3)
        self.tree_smartprops_explorer_widget.setObjectName(u"tree_smartprops_explorer_widget")

        self.verticalLayout_10.addWidget(self.tree_smartprops_explorer_widget)

        self.frame_4 = QFrame(self.dockWidgetContents_10)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setMaximumSize(QSize(16777215, 32))
        self.frame_4.setFrameShape(QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.toolButton = QToolButton(self.frame_4)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setMaximumSize(QSize(16777215, 16777215))
        icon5 = QIcon()
        icon5.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton.setIcon(icon5)
        self.toolButton.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.toolButton)

        self.cerate_file_button = QPushButton(self.frame_4)
        self.cerate_file_button.setObjectName(u"cerate_file_button")
        self.cerate_file_button.setStyleSheet(u"\n"
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
        self.cerate_file_button.setIcon(icon4)
        self.cerate_file_button.setIconSize(QSize(24, 24))

        self.horizontalLayout_2.addWidget(self.cerate_file_button)

        self.cerate_file_button_2 = QPushButton(self.frame_4)
        self.cerate_file_button_2.setObjectName(u"cerate_file_button_2")
        self.cerate_file_button_2.setStyleSheet(u"\n"
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
        self.cerate_file_button_2.setIcon(icon2)
        self.cerate_file_button_2.setIconSize(QSize(24, 24))

        self.horizontalLayout_2.addWidget(self.cerate_file_button_2)


        self.verticalLayout_10.addWidget(self.frame_4)

        self.dockWidget_10.setWidget(self.dockWidgetContents_10)
        MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget_10)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionDebug_output.setText(QCoreApplication.translate("MainWindow", u"Debug output", None))
        self.actionCreateNewsmartprop.setText(QCoreApplication.translate("MainWindow", u"CreateNewsmartprop", None))
        self.actionSaveSmarptop.setText(QCoreApplication.translate("MainWindow", u"SaveSmarptop", None))
        self.actionSaveSmartpropAs.setText(QCoreApplication.translate("MainWindow", u"SaveSmartpropAs", None))
        self.group_class_properties.setTitle(QCoreApplication.translate("MainWindow", u"Class Properties", None))
        self.group_modifiers.setTitle(QCoreApplication.translate("MainWindow", u"Modifiers", None))
        self.group_selection_criteria.setTitle(QCoreApplication.translate("MainWindow", u"Selection Criteria", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Comment", None))
        self.status_bar.setText(QCoreApplication.translate("MainWindow", u"Console output", None))
        self.version_label.setText(QCoreApplication.translate("MainWindow", u"TextLabel", None))
        self.dockWidget_4.setWindowTitle(QCoreApplication.translate("MainWindow", u"Hierarchy", None))
        self.tree_hierarchy_search_bar_widget.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search...", None))

        __sortingEnabled = self.tree_hierarchy_widget.isSortingEnabled()
        self.tree_hierarchy_widget.setSortingEnabled(False)
        ___qtreewidgetitem = self.tree_hierarchy_widget.topLevelItem(0)
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropElement_PickOne", None));
        ___qtreewidgetitem1 = ___qtreewidgetitem.child(0)
        ___qtreewidgetitem1.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropElement_Group", None));
        ___qtreewidgetitem2 = self.tree_hierarchy_widget.topLevelItem(1)
        ___qtreewidgetitem2.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropElement_Group", None));
        ___qtreewidgetitem3 = ___qtreewidgetitem2.child(0)
        ___qtreewidgetitem3.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropElement_SmartProp", None));
        self.tree_hierarchy_widget.setSortingEnabled(__sortingEnabled)

        self.dockWidget.setWindowTitle(QCoreApplication.translate("MainWindow", u"Variables", None))
        self.add_new_variable_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.add_new_variable_combobox.setItemText(0, QCoreApplication.translate("MainWindow", u"VariableCoordinateSpace", None))
        self.add_new_variable_combobox.setItemText(1, QCoreApplication.translate("MainWindow", u"VariableDirection", None))
        self.add_new_variable_combobox.setItemText(2, QCoreApplication.translate("MainWindow", u"VariableDistributionMode", None))

        self.dockWidget_10.setWindowTitle(QCoreApplication.translate("MainWindow", u"Explorer", None))
        self.toolButton.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.cerate_file_button.setText(QCoreApplication.translate("MainWindow", u"Create", None))
        self.cerate_file_button_2.setText(QCoreApplication.translate("MainWindow", u"Save", None))
    # retranslateUi

