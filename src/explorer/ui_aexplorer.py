# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'aexplorer.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGroupBox,
    QHBoxLayout, QHeaderView, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSplitter, QStatusBar,
    QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(848, 586)
        self.actionNew_file = QAction(MainWindow)
        self.actionNew_file.setObjectName(u"actionNew_file")
        icon = QIcon()
        icon.addFile(u":/valve_common/icons/tools/common/new.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionNew_file.setIcon(icon)
        self.actionOpen_file = QAction(MainWindow)
        self.actionOpen_file.setObjectName(u"actionOpen_file")
        icon1 = QIcon()
        icon1.addFile(u":/valve_common/icons/tools/common/open.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionOpen_file.setIcon(icon1)
        self.actionAdd_To_Favorites = QAction(MainWindow)
        self.actionAdd_To_Favorites.setObjectName(u"actionAdd_To_Favorites")
        icon2 = QIcon()
        icon2.addFile(u":/valve_common/icons/tools/common/bookmark.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionAdd_To_Favorites.setIcon(icon2)
        self.actionClear_All_Recent = QAction(MainWindow)
        self.actionClear_All_Recent.setObjectName(u"actionClear_All_Recent")
        icon3 = QIcon()
        icon3.addFile(u":/valve_common/icons/tools/common/clear_list_sm.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionClear_All_Recent.setIcon(icon3)
        self.actionClear_All_Favorites = QAction(MainWindow)
        self.actionClear_All_Favorites.setObjectName(u"actionClear_All_Favorites")
        self.actionClear_All_Favorites.setIcon(icon3)
        self.actionOpen_current_path_in_Explorer = QAction(MainWindow)
        self.actionOpen_current_path_in_Explorer.setObjectName(u"actionOpen_current_path_in_Explorer")
        self.actionOpen_current_path_in_Explorer.setIcon(icon3)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_5 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout_4 = QVBoxLayout(self.layoutWidget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.groupBox_3 = QGroupBox(self.layoutWidget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.recent_list = QListWidget(self.groupBox_3)
        self.recent_list.setObjectName(u"recent_list")

        self.verticalLayout_3.addWidget(self.recent_list)


        self.verticalLayout_4.addWidget(self.groupBox_3)

        self.groupBox = QGroupBox(self.layoutWidget)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout = QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.favorites_list = QListWidget(self.groupBox)
        self.favorites_list.setObjectName(u"favorites_list")

        self.verticalLayout.addWidget(self.favorites_list)


        self.verticalLayout_4.addWidget(self.groupBox)

        self.splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.verticalLayout_2 = QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.groupBox_4 = QGroupBox(self.layoutWidget1)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.horizontalLayout_3 = QHBoxLayout(self.groupBox_4)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.filter = QLineEdit(self.groupBox_4)
        self.filter.setObjectName(u"filter")

        self.horizontalLayout_3.addWidget(self.filter)

        self.subdir = QCheckBox(self.groupBox_4)
        self.subdir.setObjectName(u"subdir")

        self.horizontalLayout_3.addWidget(self.subdir)


        self.verticalLayout_2.addWidget(self.groupBox_4)

        self.frame = QFrame(self.layoutWidget1)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.up_dir = QToolButton(self.frame)
        self.up_dir.setObjectName(u"up_dir")
        icon4 = QIcon()
        icon4.addFile(u":/valve_common/icons/tools/common/arrow_right_up.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.up_dir.setIcon(icon4)

        self.horizontalLayout.addWidget(self.up_dir)

        self.path = QLineEdit(self.frame)
        self.path.setObjectName(u"path")

        self.horizontalLayout.addWidget(self.path)


        self.verticalLayout_2.addWidget(self.frame)

        self.filetree = QTreeWidget(self.layoutWidget1)
        self.filetree.setObjectName(u"filetree")

        self.verticalLayout_2.addWidget(self.filetree)

        self.groupBox_2 = QGroupBox(self.layoutWidget1)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.add_to_favorites = QPushButton(self.groupBox_2)
        self.add_to_favorites.setObjectName(u"add_to_favorites")
        self.add_to_favorites.setIcon(icon2)

        self.horizontalLayout_4.addWidget(self.add_to_favorites)

        self.new_file = QPushButton(self.groupBox_2)
        self.new_file.setObjectName(u"new_file")
        self.new_file.setIcon(icon)

        self.horizontalLayout_4.addWidget(self.new_file)

        self.open_file = QPushButton(self.groupBox_2)
        self.open_file.setObjectName(u"open_file")
        self.open_file.setIcon(icon1)

        self.horizontalLayout_4.addWidget(self.open_file)


        self.verticalLayout_2.addWidget(self.groupBox_2)

        self.splitter.addWidget(self.layoutWidget1)

        self.horizontalLayout_5.addWidget(self.splitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 848, 33))
        self.menuSetting = QMenu(self.menubar)
        self.menuSetting.setObjectName(u"menuSetting")
        self.menuOther = QMenu(self.menubar)
        self.menuOther.setObjectName(u"menuOther")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuSetting.menuAction())
        self.menubar.addAction(self.menuOther.menuAction())
        self.menuSetting.addAction(self.actionNew_file)
        self.menuSetting.addAction(self.actionOpen_file)
        self.menuSetting.addAction(self.actionAdd_To_Favorites)
        self.menuOther.addAction(self.actionClear_All_Recent)
        self.menuOther.addAction(self.actionClear_All_Favorites)
        self.menuOther.addAction(self.actionOpen_current_path_in_Explorer)

        self.retranslateUi(MainWindow)
        self.actionNew_file.triggered.connect(self.new_file.click)
        self.actionAdd_To_Favorites.triggered.connect(self.add_to_favorites.click)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionNew_file.setText(QCoreApplication.translate("MainWindow", u"New file", None))
        self.actionOpen_file.setText(QCoreApplication.translate("MainWindow", u"Open file", None))
        self.actionAdd_To_Favorites.setText(QCoreApplication.translate("MainWindow", u"Add To Favorites", None))
        self.actionClear_All_Recent.setText(QCoreApplication.translate("MainWindow", u"Clear All Recent", None))
        self.actionClear_All_Favorites.setText(QCoreApplication.translate("MainWindow", u"Clear All Favorites", None))
        self.actionOpen_current_path_in_Explorer.setText(QCoreApplication.translate("MainWindow", u"Open Current Folder In Explorer", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Recent", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"Favorites", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("MainWindow", u"Filter", None))
        self.filter.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.subdir.setText(QCoreApplication.translate("MainWindow", u"Subdir", None))
        self.up_dir.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.path.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Path", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Actions", None))
        self.add_to_favorites.setText(QCoreApplication.translate("MainWindow", u"Add to Favorites", None))
        self.new_file.setText(QCoreApplication.translate("MainWindow", u"New File", None))
        self.open_file.setText(QCoreApplication.translate("MainWindow", u"Open File", None))
        self.menuSetting.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuOther.setTitle(QCoreApplication.translate("MainWindow", u"Other", None))
    # retranslateUi

