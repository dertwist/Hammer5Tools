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
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QToolButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)
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
        self.label = QLabel(self.frame_9)
        self.label.setObjectName(u"label")
        font = QFont()
        font.setPointSize(9)
        self.label.setFont(font)

        self.verticalLayout_5.addWidget(self.label)

        self.scrollArea = QScrollArea(self.frame_9)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 691, 674))
        self.verticalLayout_17 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_17.setSpacing(0)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.ClassProperties_layout_header = QFrame(self.scrollAreaWidgetContents)
        self.ClassProperties_layout_header.setObjectName(u"ClassProperties_layout_header")
        self.ClassProperties_layout_header.setMaximumSize(QSize(16777215, 24))
        self.ClassProperties_layout_header.setFrameShape(QFrame.StyledPanel)
        self.ClassProperties_layout_header.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.ClassProperties_layout_header)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.lineedit = QLineEdit(self.ClassProperties_layout_header)
        self.lineedit.setObjectName(u"lineedit")
        self.lineedit.setStyleSheet(u"QLineEdit {\n"
"	font: 8pt \"Segoe UI\";\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"color: #E3E3E3;\n"
"background-color: #242424;\n"
"}\n"
"QLineEdit:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"QLineEdit::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"")
        self.lineedit.setInputMethodHints(Qt.ImhLatinOnly|Qt.ImhLowercaseOnly)
        self.lineedit.setMaxLength(32)
        self.lineedit.setReadOnly(True)

        self.horizontalLayout_3.addWidget(self.lineedit)


        self.verticalLayout_17.addWidget(self.ClassProperties_layout_header)

        self.ClassProperties_layout_frame = QFrame(self.scrollAreaWidgetContents)
        self.ClassProperties_layout_frame.setObjectName(u"ClassProperties_layout_frame")
        self.ClassProperties_layout_frame.setFrameShape(QFrame.StyledPanel)
        self.ClassProperties_layout_frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_6 = QVBoxLayout(self.ClassProperties_layout_frame)
        self.verticalLayout_6.setSpacing(0)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.ClassProperties_layout = QVBoxLayout()
        self.ClassProperties_layout.setSpacing(0)
        self.ClassProperties_layout.setObjectName(u"ClassProperties_layout")
        self.ClassProperties_layout.setContentsMargins(12, 0, 0, -1)
        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.ClassProperties_layout.addItem(self.verticalSpacer_3)


        self.verticalLayout_6.addLayout(self.ClassProperties_layout)


        self.verticalLayout_17.addWidget(self.ClassProperties_layout_frame)

        self.Modifers_layout_header = QFrame(self.scrollAreaWidgetContents)
        self.Modifers_layout_header.setObjectName(u"Modifers_layout_header")
        self.Modifers_layout_header.setMaximumSize(QSize(16777215, 24))
        self.Modifers_layout_header.setFrameShape(QFrame.StyledPanel)
        self.Modifers_layout_header.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.Modifers_layout_header)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.Modifer_add_button = QToolButton(self.Modifers_layout_header)
        self.Modifer_add_button.setObjectName(u"Modifer_add_button")
        self.Modifer_add_button.setStyleSheet(u"QToolButton {\n"
"    font: 700 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:14px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:4px;\n"
"    color: #E3E3E3;\n"
"background-color: #242424;\n"
"    padding-left: 4px;\n"
"}\n"
"QToolButton:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"QToolButton{\n"
"	padding-left:5px;\n"
"	border-left: 0px solid black;\n"
"border-right: 0px solid black;\n"
"border-top: 0px solid black;\n"
"}")
        icon4 = QIcon()
        icon4.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Modifer_add_button.setIcon(icon4)

        self.horizontalLayout_4.addWidget(self.Modifer_add_button)

        self.lineedit_2 = QLineEdit(self.Modifers_layout_header)
        self.lineedit_2.setObjectName(u"lineedit_2")
        self.lineedit_2.setStyleSheet(u"QLineEdit {\n"
"	font: 8pt \"Segoe UI\";\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"color: #E3E3E3;\n"
"background-color: #242424;\n"
"}\n"
"QLineEdit:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"QLineEdit::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"")
        self.lineedit_2.setInputMethodHints(Qt.ImhLatinOnly|Qt.ImhLowercaseOnly)
        self.lineedit_2.setMaxLength(32)
        self.lineedit_2.setReadOnly(True)

        self.horizontalLayout_4.addWidget(self.lineedit_2)


        self.verticalLayout_17.addWidget(self.Modifers_layout_header)

        self.Modifers_layout_frame = QFrame(self.scrollAreaWidgetContents)
        self.Modifers_layout_frame.setObjectName(u"Modifers_layout_frame")
        self.Modifers_layout_frame.setMinimumSize(QSize(0, 128))
        self.Modifers_layout_frame.setFrameShape(QFrame.StyledPanel)
        self.Modifers_layout_frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_11 = QVBoxLayout(self.Modifers_layout_frame)
        self.verticalLayout_11.setSpacing(0)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.Modifers_layout = QVBoxLayout()
        self.Modifers_layout.setSpacing(0)
        self.Modifers_layout.setObjectName(u"Modifers_layout")
        self.Modifers_layout.setContentsMargins(12, 0, 0, -1)
        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.Modifers_layout.addItem(self.verticalSpacer_4)


        self.verticalLayout_11.addLayout(self.Modifers_layout)


        self.verticalLayout_17.addWidget(self.Modifers_layout_frame)

        self.SelectionCriteria_layout_header = QFrame(self.scrollAreaWidgetContents)
        self.SelectionCriteria_layout_header.setObjectName(u"SelectionCriteria_layout_header")
        self.SelectionCriteria_layout_header.setMaximumSize(QSize(16777215, 24))
        self.SelectionCriteria_layout_header.setFrameShape(QFrame.StyledPanel)
        self.SelectionCriteria_layout_header.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_8 = QHBoxLayout(self.SelectionCriteria_layout_header)
        self.horizontalLayout_8.setSpacing(0)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.SelectionCriteria_add_button = QToolButton(self.SelectionCriteria_layout_header)
        self.SelectionCriteria_add_button.setObjectName(u"SelectionCriteria_add_button")
        self.SelectionCriteria_add_button.setStyleSheet(u"QToolButton {\n"
"    font: 700 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:14px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:4px;\n"
"    color: #E3E3E3;\n"
"background-color: #242424;\n"
"    padding-left: 4px;\n"
"}\n"
"QToolButton:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"QToolButton{\n"
"	padding-left:5px;\n"
"	border-left: 0px solid black;\n"
"border-right: 0px solid black;\n"
"border-top: 0px solid black;\n"
"}")
        self.SelectionCriteria_add_button.setIcon(icon4)

        self.horizontalLayout_8.addWidget(self.SelectionCriteria_add_button)

        self.lineedit_5 = QLineEdit(self.SelectionCriteria_layout_header)
        self.lineedit_5.setObjectName(u"lineedit_5")
        self.lineedit_5.setStyleSheet(u"QLineEdit {\n"
"	font: 8pt \"Segoe UI\";\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"color: #E3E3E3;\n"
"background-color: #242424;\n"
"}\n"
"QLineEdit:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"QLineEdit::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"")
        self.lineedit_5.setInputMethodHints(Qt.ImhLatinOnly|Qt.ImhLowercaseOnly)
        self.lineedit_5.setMaxLength(32)
        self.lineedit_5.setReadOnly(True)

        self.horizontalLayout_8.addWidget(self.lineedit_5)


        self.verticalLayout_17.addWidget(self.SelectionCriteria_layout_header)

        self.SelectionCriteria_layout_frame = QFrame(self.scrollAreaWidgetContents)
        self.SelectionCriteria_layout_frame.setObjectName(u"SelectionCriteria_layout_frame")
        self.SelectionCriteria_layout_frame.setMinimumSize(QSize(0, 128))
        self.SelectionCriteria_layout_frame.setFrameShape(QFrame.StyledPanel)
        self.SelectionCriteria_layout_frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_13 = QVBoxLayout(self.SelectionCriteria_layout_frame)
        self.verticalLayout_13.setSpacing(0)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.verticalLayout_13.setContentsMargins(0, 0, 0, 0)
        self.SelectionCriteria_layout = QVBoxLayout()
        self.SelectionCriteria_layout.setSpacing(0)
        self.SelectionCriteria_layout.setObjectName(u"SelectionCriteria_layout")
        self.SelectionCriteria_layout.setContentsMargins(12, 0, 0, -1)
        self.verticalSpacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.SelectionCriteria_layout.addItem(self.verticalSpacer_6)


        self.verticalLayout_13.addLayout(self.SelectionCriteria_layout)


        self.verticalLayout_17.addWidget(self.SelectionCriteria_layout_frame)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_5.addWidget(self.scrollArea)

        self.frame_8 = QFrame(self.frame_9)
        self.frame_8.setObjectName(u"frame_8")
        self.frame_8.setFrameShape(QFrame.StyledPanel)
        self.frame_8.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_8)
        self.horizontalLayout_5.setSpacing(8)
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
        self.variables_scrollArea_widget.setGeometry(QRect(0, 0, 309, 197))
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
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.add_new_variable_button = QToolButton(self.frame)
        self.add_new_variable_button.setObjectName(u"add_new_variable_button")
        self.add_new_variable_button.setMaximumSize(QSize(28, 28))
        self.add_new_variable_button.setIcon(icon4)
        self.add_new_variable_button.setIconSize(QSize(16, 16))

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

        self.horizontalLayout.addWidget(self.add_new_variable_combobox)


        self.verticalLayout_7.addWidget(self.frame)

        self.dockWidget.setWidget(self.dockWidgetContents)
        MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget)
        self.dockWidget_10 = QDockWidget(MainWindow)
        self.dockWidget_10.setObjectName(u"dockWidget_10")
        self.dockWidget_10.setFeatures(QDockWidget.DockWidgetMovable)
        self.dockWidget_10.setAllowedAreas(Qt.BottomDockWidgetArea|Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        self.explorer_layout_widget = QWidget()
        self.explorer_layout_widget.setObjectName(u"explorer_layout_widget")
        self.verticalLayout_10 = QVBoxLayout(self.explorer_layout_widget)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.explorer_layout = QVBoxLayout()
        self.explorer_layout.setObjectName(u"explorer_layout")

        self.verticalLayout_10.addLayout(self.explorer_layout)

        self.frame_4 = QFrame(self.explorer_layout_widget)
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

        self.dockWidget_10.setWidget(self.explorer_layout_widget)
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
        self.label.setText(QCoreApplication.translate("MainWindow", u"Main window", None))
#if QT_CONFIG(tooltip)
        self.lineedit.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.lineedit.setText(QCoreApplication.translate("MainWindow", u"ClassProperties", None))
        self.Modifer_add_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.lineedit_2.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.lineedit_2.setText(QCoreApplication.translate("MainWindow", u"Modifers", None))
        self.SelectionCriteria_add_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
#if QT_CONFIG(tooltip)
        self.lineedit_5.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.lineedit_5.setText(QCoreApplication.translate("MainWindow", u"SelectionCriteria", None))
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
        self.variables_scroll_area_searchbar.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search...", None))
        self.add_new_variable_button.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.dockWidget_10.setWindowTitle(QCoreApplication.translate("MainWindow", u"Explorer", None))
        self.toolButton.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.cerate_file_button.setText(QCoreApplication.translate("MainWindow", u"Create", None))
        self.cerate_file_button_2.setText(QCoreApplication.translate("MainWindow", u"Save", None))
    # retranslateUi

