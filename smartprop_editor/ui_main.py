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
from PySide6.QtWidgets import (QApplication, QDockWidget, QFrame, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QSizePolicy,
    QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)
import rc_resources

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1280, 720)
        MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame_9 = QFrame(self.centralwidget)
        self.frame_9.setObjectName(u"frame_9")
        self.frame_9.setFrameShape(QFrame.StyledPanel)
        self.frame_9.setFrameShadow(QFrame.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.frame_9)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
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

        self.frame_10 = QFrame(self.frame_9)
        self.frame_10.setObjectName(u"frame_10")
        self.frame_10.setFrameShape(QFrame.StyledPanel)
        self.frame_10.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self.frame_10)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.tabWidget_2 = QTabWidget(self.frame_10)
        self.tabWidget_2.setObjectName(u"tabWidget_2")
        self.tabWidget_2.setMaximumSize(QSize(380, 16777215))
        self.explorer = QWidget()
        self.explorer.setObjectName(u"explorer")
        self.horizontalLayout_8 = QHBoxLayout(self.explorer)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.frame_3 = QFrame(self.explorer)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16666, 16777215))
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frame_3)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.treeWidget = QTreeWidget(self.frame_3)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.treeWidget.setHeaderItem(__qtreewidgetitem)
        self.treeWidget.setObjectName(u"treeWidget")

        self.verticalLayout.addWidget(self.treeWidget)

        self.frame_4 = QFrame(self.frame_3)
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
        icon = QIcon()
        icon.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton.setIcon(icon)
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

        self.horizontalLayout_2.addWidget(self.cerate_file_button)


        self.verticalLayout.addWidget(self.frame_4)


        self.horizontalLayout_8.addWidget(self.frame_3)

        self.tabWidget_2.addTab(self.explorer, "")
        self.Variables = QWidget()
        self.Variables.setObjectName(u"Variables")
        self.verticalLayout_4 = QVBoxLayout(self.Variables)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.treeWidget_2 = QTreeWidget(self.Variables)
        __qtreewidgetitem1 = QTreeWidgetItem(self.treeWidget_2)
        QTreeWidgetItem(__qtreewidgetitem1)
        QTreeWidgetItem(__qtreewidgetitem1)
        QTreeWidgetItem(__qtreewidgetitem1)
        QTreeWidgetItem(self.treeWidget_2)
        QTreeWidgetItem(self.treeWidget_2)
        self.treeWidget_2.setObjectName(u"treeWidget_2")
        self.treeWidget_2.header().setVisible(True)
        self.treeWidget_2.header().setCascadingSectionResizes(False)
        self.treeWidget_2.header().setDefaultSectionSize(200)
        self.treeWidget_2.header().setHighlightSections(False)
        self.treeWidget_2.header().setProperty("showSortIndicator", False)

        self.verticalLayout_4.addWidget(self.treeWidget_2)

        self.listWidget = QListWidget(self.Variables)
        self.listWidget.setObjectName(u"listWidget")

        self.verticalLayout_4.addWidget(self.listWidget)

        self.pushButton = QPushButton(self.Variables)
        self.pushButton.setObjectName(u"pushButton")

        self.verticalLayout_4.addWidget(self.pushButton)

        self.tabWidget_2.addTab(self.Variables, "")

        self.horizontalLayout_6.addWidget(self.tabWidget_2)

        self.frame_7 = QFrame(self.frame_10)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setFrameShape(QFrame.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Raised)
        self.frame_7.setLineWidth(0)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_7)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(self.frame_7)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_4 = QLabel(self.frame)
        self.label_4.setObjectName(u"label_4")

        self.verticalLayout_2.addWidget(self.label_4)

        self.treeWidget_3 = QTreeWidget(self.frame)
        QTreeWidgetItem(self.treeWidget_3)
        __qtreewidgetitem2 = QTreeWidgetItem(self.treeWidget_3)
        QTreeWidgetItem(__qtreewidgetitem2)
        QTreeWidgetItem(__qtreewidgetitem2)
        QTreeWidgetItem(__qtreewidgetitem2)
        __qtreewidgetitem3 = QTreeWidgetItem(self.treeWidget_3)
        QTreeWidgetItem(__qtreewidgetitem3)
        self.treeWidget_3.setObjectName(u"treeWidget_3")
        self.treeWidget_3.header().setVisible(True)
        self.treeWidget_3.header().setCascadingSectionResizes(False)
        self.treeWidget_3.header().setDefaultSectionSize(280)
        self.treeWidget_3.header().setHighlightSections(False)
        self.treeWidget_3.header().setProperty("showSortIndicator", False)

        self.verticalLayout_2.addWidget(self.treeWidget_3)

        self.label_3 = QLabel(self.frame)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_2.addWidget(self.label_3)

        self.properties_widget_list = QListWidget(self.frame)
        QListWidgetItem(self.properties_widget_list)
        self.properties_widget_list.setObjectName(u"properties_widget_list")

        self.verticalLayout_2.addWidget(self.properties_widget_list)

        self.frame_5 = QFrame(self.frame)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.save_button = QPushButton(self.frame_5)
        self.save_button.setObjectName(u"save_button")
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

        self.horizontalLayout_3.addWidget(self.save_button)


        self.verticalLayout_2.addWidget(self.frame_5)


        self.horizontalLayout_4.addWidget(self.frame)

        self.frame_2 = QFrame(self.frame_7)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.frame_2.setLineWidth(0)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame_2)
        self.label.setObjectName(u"label")

        self.verticalLayout_3.addWidget(self.label)

        self.search_bar_elements = QLineEdit(self.frame_2)
        self.search_bar_elements.setObjectName(u"search_bar_elements")

        self.verticalLayout_3.addWidget(self.search_bar_elements)

        self.elements_widget_tree = QTreeWidget(self.frame_2)
        __qtreewidgetitem4 = QTreeWidgetItem()
        __qtreewidgetitem4.setText(0, u"Name");
        self.elements_widget_tree.setHeaderItem(__qtreewidgetitem4)
        __qtreewidgetitem5 = QTreeWidgetItem(self.elements_widget_tree)
        QTreeWidgetItem(__qtreewidgetitem5)
        __qtreewidgetitem6 = QTreeWidgetItem(self.elements_widget_tree)
        QTreeWidgetItem(__qtreewidgetitem6)
        self.elements_widget_tree.setObjectName(u"elements_widget_tree")
        self.elements_widget_tree.header().setVisible(False)

        self.verticalLayout_3.addWidget(self.elements_widget_tree)


        self.horizontalLayout_4.addWidget(self.frame_2)


        self.horizontalLayout_6.addWidget(self.frame_7)


        self.verticalLayout_5.addWidget(self.frame_10)


        self.horizontalLayout.addWidget(self.frame_9)

        MainWindow.setCentralWidget(self.centralwidget)
        self.dockWidget_2 = QDockWidget(MainWindow)
        self.dockWidget_2.setObjectName(u"dockWidget_2")
        self.dockWidget_2.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.dockWidgetContents_5 = QWidget()
        self.dockWidgetContents_5.setObjectName(u"dockWidgetContents_5")
        self.horizontalLayout_9 = QHBoxLayout(self.dockWidgetContents_5)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.treeWidget_4 = QTreeWidget(self.dockWidgetContents_5)
        __qtreewidgetitem7 = QTreeWidgetItem(self.treeWidget_4)
        QTreeWidgetItem(__qtreewidgetitem7)
        QTreeWidgetItem(__qtreewidgetitem7)
        QTreeWidgetItem(__qtreewidgetitem7)
        QTreeWidgetItem(self.treeWidget_4)
        QTreeWidgetItem(self.treeWidget_4)
        self.treeWidget_4.setObjectName(u"treeWidget_4")
        self.treeWidget_4.header().setVisible(True)
        self.treeWidget_4.header().setCascadingSectionResizes(False)
        self.treeWidget_4.header().setDefaultSectionSize(200)
        self.treeWidget_4.header().setHighlightSections(False)
        self.treeWidget_4.header().setProperty("showSortIndicator", False)

        self.horizontalLayout_9.addWidget(self.treeWidget_4)

        self.dockWidget_2.setWidget(self.dockWidgetContents_5)
        MainWindow.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.dockWidget_2)
        self.dockWidget_3 = QDockWidget(MainWindow)
        self.dockWidget_3.setObjectName(u"dockWidget_3")
        self.dockWidget_3.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.dockWidgetContents_6 = QWidget()
        self.dockWidgetContents_6.setObjectName(u"dockWidgetContents_6")
        self.verticalLayout_6 = QVBoxLayout(self.dockWidgetContents_6)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.treeWidget_5 = QTreeWidget(self.dockWidgetContents_6)
        __qtreewidgetitem8 = QTreeWidgetItem(self.treeWidget_5)
        QTreeWidgetItem(__qtreewidgetitem8)
        QTreeWidgetItem(__qtreewidgetitem8)
        QTreeWidgetItem(__qtreewidgetitem8)
        QTreeWidgetItem(self.treeWidget_5)
        QTreeWidgetItem(self.treeWidget_5)
        self.treeWidget_5.setObjectName(u"treeWidget_5")
        self.treeWidget_5.header().setVisible(True)
        self.treeWidget_5.header().setCascadingSectionResizes(False)
        self.treeWidget_5.header().setDefaultSectionSize(200)
        self.treeWidget_5.header().setHighlightSections(False)
        self.treeWidget_5.header().setProperty("showSortIndicator", False)

        self.verticalLayout_6.addWidget(self.treeWidget_5)

        self.dockWidget_3.setWidget(self.dockWidgetContents_6)
        MainWindow.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.dockWidget_3)

        self.retranslateUi(MainWindow)

        self.tabWidget_2.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.status_bar.setText(QCoreApplication.translate("MainWindow", u"asfasfasdf", None))
        self.version_label.setText(QCoreApplication.translate("MainWindow", u"TextLabel", None))
        self.toolButton.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.cerate_file_button.setText(QCoreApplication.translate("MainWindow", u"Create", None))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.explorer), QCoreApplication.translate("MainWindow", u"Explorer", None))
        ___qtreewidgetitem = self.treeWidget_2.headerItem()
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Value", None));
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"Name", None));

        __sortingEnabled = self.treeWidget_2.isSortingEnabled()
        self.treeWidget_2.setSortingEnabled(False)
        ___qtreewidgetitem1 = self.treeWidget_2.topLevelItem(0)
        ___qtreewidgetitem1.setText(1, QCoreApplication.translate("MainWindow", u"VariableCoordinateSpace", None));
        ___qtreewidgetitem1.setText(0, QCoreApplication.translate("MainWindow", u"Cords", None));
        ___qtreewidgetitem2 = ___qtreewidgetitem1.child(0)
        ___qtreewidgetitem2.setText(1, QCoreApplication.translate("MainWindow", u"Element", None));
        ___qtreewidgetitem2.setText(0, QCoreApplication.translate("MainWindow", u"Default Value", None));
        ___qtreewidgetitem3 = ___qtreewidgetitem1.child(1)
        ___qtreewidgetitem3.setText(0, QCoreApplication.translate("MainWindow", u"Display Name", None));
        ___qtreewidgetitem4 = ___qtreewidgetitem1.child(2)
        ___qtreewidgetitem4.setText(0, QCoreApplication.translate("MainWindow", u"Visible in editor", None));
        ___qtreewidgetitem5 = self.treeWidget_2.topLevelItem(1)
        ___qtreewidgetitem5.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropVariable_Float", None));
        ___qtreewidgetitem6 = self.treeWidget_2.topLevelItem(2)
        ___qtreewidgetitem6.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropVariable_Bool", None));
        self.treeWidget_2.setSortingEnabled(__sortingEnabled)

        self.pushButton.setText(QCoreApplication.translate("MainWindow", u"Add new", None))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.Variables), QCoreApplication.translate("MainWindow", u"Variables", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Properties", None))
        ___qtreewidgetitem7 = self.treeWidget_3.headerItem()
        ___qtreewidgetitem7.setText(0, QCoreApplication.translate("MainWindow", u"Name", None));

        __sortingEnabled1 = self.treeWidget_3.isSortingEnabled()
        self.treeWidget_3.setSortingEnabled(False)
        ___qtreewidgetitem8 = self.treeWidget_3.topLevelItem(0)
        ___qtreewidgetitem8.setText(0, QCoreApplication.translate("MainWindow", u"m_vHandleOffset", None));
        ___qtreewidgetitem9 = self.treeWidget_3.topLevelItem(1)
        ___qtreewidgetitem9.setText(0, QCoreApplication.translate("MainWindow", u"m_Modifiers", None));
        ___qtreewidgetitem10 = ___qtreewidgetitem9.child(0)
        ___qtreewidgetitem10.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropFilter_VariableValue", None));
        ___qtreewidgetitem11 = ___qtreewidgetitem9.child(1)
        ___qtreewidgetitem11.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropOperation_RestoreState", None));
        ___qtreewidgetitem12 = ___qtreewidgetitem9.child(2)
        ___qtreewidgetitem12.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropOperation_SetVariable", None));
        ___qtreewidgetitem13 = self.treeWidget_3.topLevelItem(2)
        ___qtreewidgetitem13.setText(0, QCoreApplication.translate("MainWindow", u"m_vHandleOffset", None));
        ___qtreewidgetitem14 = ___qtreewidgetitem13.child(0)
        ___qtreewidgetitem14.setText(0, QCoreApplication.translate("MainWindow", u"m_Components", None));
        self.treeWidget_3.setSortingEnabled(__sortingEnabled1)

        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Property edit", None))

        __sortingEnabled2 = self.properties_widget_list.isSortingEnabled()
        self.properties_widget_list.setSortingEnabled(False)
        ___qlistwidgetitem = self.properties_widget_list.item(0)
        ___qlistwidgetitem.setText(QCoreApplication.translate("MainWindow", u"CSmartPropFilter_VariableValue", None));
        self.properties_widget_list.setSortingEnabled(__sortingEnabled2)

        self.save_button.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Hierarchy", None))
        self.search_bar_elements.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search...", None))

        __sortingEnabled3 = self.elements_widget_tree.isSortingEnabled()
        self.elements_widget_tree.setSortingEnabled(False)
        ___qtreewidgetitem15 = self.elements_widget_tree.topLevelItem(0)
        ___qtreewidgetitem15.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropElement_PickOne", None));
        ___qtreewidgetitem16 = ___qtreewidgetitem15.child(0)
        ___qtreewidgetitem16.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropElement_Group", None));
        ___qtreewidgetitem17 = self.elements_widget_tree.topLevelItem(1)
        ___qtreewidgetitem17.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropElement_Group", None));
        ___qtreewidgetitem18 = ___qtreewidgetitem17.child(0)
        ___qtreewidgetitem18.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropElement_SmartProp", None));
        self.elements_widget_tree.setSortingEnabled(__sortingEnabled3)

        self.dockWidget_2.setWindowTitle(QCoreApplication.translate("MainWindow", u"Properties", None))
        ___qtreewidgetitem19 = self.treeWidget_4.headerItem()
        ___qtreewidgetitem19.setText(1, QCoreApplication.translate("MainWindow", u"Value", None));
        ___qtreewidgetitem19.setText(0, QCoreApplication.translate("MainWindow", u"Name", None));

        __sortingEnabled4 = self.treeWidget_4.isSortingEnabled()
        self.treeWidget_4.setSortingEnabled(False)
        ___qtreewidgetitem20 = self.treeWidget_4.topLevelItem(0)
        ___qtreewidgetitem20.setText(1, QCoreApplication.translate("MainWindow", u"VariableCoordinateSpace", None));
        ___qtreewidgetitem20.setText(0, QCoreApplication.translate("MainWindow", u"Cords", None));
        ___qtreewidgetitem21 = ___qtreewidgetitem20.child(0)
        ___qtreewidgetitem21.setText(1, QCoreApplication.translate("MainWindow", u"Element", None));
        ___qtreewidgetitem21.setText(0, QCoreApplication.translate("MainWindow", u"Default Value", None));
        ___qtreewidgetitem22 = ___qtreewidgetitem20.child(1)
        ___qtreewidgetitem22.setText(0, QCoreApplication.translate("MainWindow", u"Display Name", None));
        ___qtreewidgetitem23 = ___qtreewidgetitem20.child(2)
        ___qtreewidgetitem23.setText(0, QCoreApplication.translate("MainWindow", u"Visible in editor", None));
        ___qtreewidgetitem24 = self.treeWidget_4.topLevelItem(1)
        ___qtreewidgetitem24.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropVariable_Float", None));
        ___qtreewidgetitem25 = self.treeWidget_4.topLevelItem(2)
        ___qtreewidgetitem25.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropVariable_Bool", None));
        self.treeWidget_4.setSortingEnabled(__sortingEnabled4)

        self.dockWidget_3.setWindowTitle(QCoreApplication.translate("MainWindow", u"Modifiers", None))
        ___qtreewidgetitem26 = self.treeWidget_5.headerItem()
        ___qtreewidgetitem26.setText(1, QCoreApplication.translate("MainWindow", u"Value", None));
        ___qtreewidgetitem26.setText(0, QCoreApplication.translate("MainWindow", u"Name", None));

        __sortingEnabled5 = self.treeWidget_5.isSortingEnabled()
        self.treeWidget_5.setSortingEnabled(False)
        ___qtreewidgetitem27 = self.treeWidget_5.topLevelItem(0)
        ___qtreewidgetitem27.setText(1, QCoreApplication.translate("MainWindow", u"VariableCoordinateSpace", None));
        ___qtreewidgetitem27.setText(0, QCoreApplication.translate("MainWindow", u"Cords", None));
        ___qtreewidgetitem28 = ___qtreewidgetitem27.child(0)
        ___qtreewidgetitem28.setText(1, QCoreApplication.translate("MainWindow", u"Element", None));
        ___qtreewidgetitem28.setText(0, QCoreApplication.translate("MainWindow", u"Default Value", None));
        ___qtreewidgetitem29 = ___qtreewidgetitem27.child(1)
        ___qtreewidgetitem29.setText(0, QCoreApplication.translate("MainWindow", u"Display Name", None));
        ___qtreewidgetitem30 = ___qtreewidgetitem27.child(2)
        ___qtreewidgetitem30.setText(0, QCoreApplication.translate("MainWindow", u"Visible in editor", None));
        ___qtreewidgetitem31 = self.treeWidget_5.topLevelItem(1)
        ___qtreewidgetitem31.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropVariable_Float", None));
        ___qtreewidgetitem32 = self.treeWidget_5.topLevelItem(2)
        ___qtreewidgetitem32.setText(0, QCoreApplication.translate("MainWindow", u"CSmartPropVariable_Bool", None));
        self.treeWidget_5.setSortingEnabled(__sortingEnabled5)

    # retranslateUi

