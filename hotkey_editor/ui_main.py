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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QHeaderView, QKeySequenceEdit, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QPushButton,
    QSizePolicy, QSplitter, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)
import rc_resources

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1171, 698)
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName(u"actionSave")
        self.actionSave_as = QAction(MainWindow)
        self.actionSave_as.setObjectName(u"actionSave_as")
        self.actionOpen = QAction(MainWindow)
        self.actionOpen.setObjectName(u"actionOpen")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.frame)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(self.frame)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setHandleWidth(8)
        self.splitter.setChildrenCollapsible(False)
        self.widget = QWidget(self.splitter)
        self.widget.setObjectName(u"widget")
        self.verticalLayout_4 = QVBoxLayout(self.widget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.widget)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_4.addWidget(self.label_3)

        self.comboBox = QComboBox(self.widget)
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")
        self.comboBox.setStyleSheet(u"QMenu {\n"
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

        self.verticalLayout_4.addWidget(self.comboBox)

        self.presets_list = QListWidget(self.widget)
        self.presets_list.setObjectName(u"presets_list")

        self.verticalLayout_4.addWidget(self.presets_list)

        self.current_preset = QLineEdit(self.widget)
        self.current_preset.setObjectName(u"current_preset")
        self.current_preset.setReadOnly(True)

        self.verticalLayout_4.addWidget(self.current_preset)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.open_file_as_button_2 = QPushButton(self.widget)
        self.open_file_as_button_2.setObjectName(u"open_file_as_button_2")
        self.open_file_as_button_2.setStyleSheet(u"\n"
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
        icon = QIcon()
        icon.addFile(u":/icons/check_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_file_as_button_2.setIcon(icon)
        self.open_file_as_button_2.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.open_file_as_button_2)

        self.cerate_file_button = QPushButton(self.widget)
        self.cerate_file_button.setObjectName(u"cerate_file_button")
        self.cerate_file_button.setStyleSheet(u"\n"
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
        icon1 = QIcon()
        icon1.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cerate_file_button.setIcon(icon1)
        self.cerate_file_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.cerate_file_button)


        self.verticalLayout_4.addLayout(self.horizontalLayout_3)

        self.splitter.addWidget(self.widget)
        self.widget1 = QWidget(self.splitter)
        self.widget1.setObjectName(u"widget1")
        self.verticalLayout_3 = QVBoxLayout(self.widget1)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.widget1)
        self.label.setObjectName(u"label")

        self.verticalLayout_3.addWidget(self.label)

        self.treeWidget = QTreeWidget(self.widget1)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"Context");
        self.treeWidget.setHeaderItem(__qtreewidgetitem)
        self.treeWidget.setObjectName(u"treeWidget")
        self.treeWidget.header().setMinimumSectionSize(150)
        self.treeWidget.header().setDefaultSectionSize(200)

        self.verticalLayout_3.addWidget(self.treeWidget)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.lineEdit = QLineEdit(self.widget1)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout_4.addWidget(self.lineEdit)

        self.lineEdit_3 = QLineEdit(self.widget1)
        self.lineEdit_3.setObjectName(u"lineEdit_3")

        self.horizontalLayout_4.addWidget(self.lineEdit_3)

        self.lineEdit_2 = QLineEdit(self.widget1)
        self.lineEdit_2.setObjectName(u"lineEdit_2")

        self.horizontalLayout_4.addWidget(self.lineEdit_2)


        self.verticalLayout_3.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.keySequenceEdit = QKeySequenceEdit(self.widget1)
        self.keySequenceEdit.setObjectName(u"keySequenceEdit")

        self.horizontalLayout_6.addWidget(self.keySequenceEdit)

        self.cerate_file_button_4 = QPushButton(self.widget1)
        self.cerate_file_button_4.setObjectName(u"cerate_file_button_4")
        self.cerate_file_button_4.setMinimumSize(QSize(128, 0))
        self.cerate_file_button_4.setStyleSheet(u"\n"
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
        icon2 = QIcon()
        icon2.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cerate_file_button_4.setIcon(icon2)
        self.cerate_file_button_4.setIconSize(QSize(20, 20))

        self.horizontalLayout_6.addWidget(self.cerate_file_button_4)

        self.cerate_file_button_3 = QPushButton(self.widget1)
        self.cerate_file_button_3.setObjectName(u"cerate_file_button_3")
        self.cerate_file_button_3.setMinimumSize(QSize(256, 0))
        self.cerate_file_button_3.setStyleSheet(u"\n"
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
        icon3 = QIcon()
        icon3.addFile(u":/icons/all_match_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.cerate_file_button_3.setIcon(icon3)
        self.cerate_file_button_3.setIconSize(QSize(20, 20))

        self.horizontalLayout_6.addWidget(self.cerate_file_button_3)


        self.verticalLayout_3.addLayout(self.horizontalLayout_6)

        self.splitter.addWidget(self.widget1)

        self.verticalLayout_5.addWidget(self.splitter)


        self.verticalLayout_2.addWidget(self.frame)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionSave.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.actionSave_as.setText(QCoreApplication.translate("MainWindow", u"Save as", None))
        self.actionOpen.setText(QCoreApplication.translate("MainWindow", u"Open", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Keybindings presets", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("MainWindow", u"Hammer", None))

        self.current_preset.setText(QCoreApplication.translate("MainWindow", u"Current hotkey preset", None))
#if QT_CONFIG(tooltip)
        self.open_file_as_button_2.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Ctrl + O</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.open_file_as_button_2.setText(QCoreApplication.translate("MainWindow", u"Set current", None))
#if QT_CONFIG(shortcut)
        self.open_file_as_button_2.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+O", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.cerate_file_button.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Ctrl + N</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.cerate_file_button.setText(QCoreApplication.translate("MainWindow", u"New preset", None))
#if QT_CONFIG(shortcut)
        self.cerate_file_button.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
        self.label.setText(QCoreApplication.translate("MainWindow", u"Keybindings editor", None))
        ___qtreewidgetitem = self.treeWidget.headerItem()
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("MainWindow", u"Input", None));
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("MainWindow", u"Command", None));
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Context", None))
        self.lineEdit_3.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Command", None))
        self.lineEdit_2.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Input", None))
#if QT_CONFIG(tooltip)
        self.cerate_file_button_4.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Ctrl + N</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.cerate_file_button_4.setText(QCoreApplication.translate("MainWindow", u"Save preset", None))
#if QT_CONFIG(shortcut)
        self.cerate_file_button_4.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.cerate_file_button_3.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Ctrl + N</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.cerate_file_button_3.setText(QCoreApplication.translate("MainWindow", u"Save and restart the editor", None))
#if QT_CONFIG(shortcut)
        self.cerate_file_button_3.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+N", None))
#endif // QT_CONFIG(shortcut)
    # retranslateUi

