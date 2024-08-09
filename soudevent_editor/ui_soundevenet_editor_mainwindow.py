# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'soundevenet_editor_mainwindow.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QHeaderView,
    QLineEdit, QMainWindow, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QToolButton, QTreeView,
    QVBoxLayout, QWidget)
import rc_resources

class Ui_SoundEvent_Editor_MainWindow(object):
    def setupUi(self, SoundEvent_Editor_MainWindow):
        if not SoundEvent_Editor_MainWindow.objectName():
            SoundEvent_Editor_MainWindow.setObjectName(u"SoundEvent_Editor_MainWindow")
        SoundEvent_Editor_MainWindow.resize(1035, 660)
        SoundEvent_Editor_MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.centralwidget = QWidget(SoundEvent_Editor_MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame_6 = QFrame(self.centralwidget)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.frame_6)
        self.verticalLayout_4.setSpacing(6)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.frame_7 = QFrame(self.frame_6)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setFrameShape(QFrame.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_7)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(self.frame_7)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(400, 16777215))
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frame)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea = QScrollArea(self.frame)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 396, 312))
        self.verticalLayout_2 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.pushButton = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton.setObjectName(u"pushButton")

        self.verticalLayout_2.addWidget(self.pushButton)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)

        self.verticalSpacer_2 = QSpacerItem(340, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.audio_files_explorer = QTreeView(self.frame)
        self.audio_files_explorer.setObjectName(u"audio_files_explorer")
        self.audio_files_explorer.setStyleSheet(u"/* styles/treeview.qss */\n"
"\n"
"/* General application background */\n"
"/* TreeView specific styles */\n"
"QTreeView {\n"
"    color: #E3E3E3;\n"
"    border: 1px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    font: 580 10pt \"Segoe UI\";\n"
"}\n"
"\n"
"QTreeView::item {\n"
"    height: 20px;\n"
"}\n"
"\n"
"QTreeView::item:selected {\n"
"    background-color: #272729;\n"
"    color: #E3E3E3;\n"
"}\n"
"\n"
"QTreeView::item:hover {\n"
"    background-color: #272729;\n"
"    color: #E3E3E3;\n"
"}\n"
"\n"
"/* Branch icons */\n"
"QTreeView::branch:closed:has-children {\n"
"    /* Ensure this path is correct and the image exists */\n"
"    image: url(:/icons/arrow_drop_down_16dp.svg);\n"
"}\n"
"\n"
"QTreeView::branch:open:has-children {\n"
"    /* Ensure this path is correct and the image exists */\n"
"    image: url(:/icons/arrow_right_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"}\n"
"\n"
"/* Header styles */\n"
"QHeaderView::section {\n"
"    background-color"
                        ": #1d1d1f;\n"
"    color: #E3E3E3;\n"
"    font: 600 10pt \"Segoe UI\";\n"
"    height: 16px;\n"
"    border: 0px;\n"
"    border-bottom: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"\n"
"/* QHeaderView::section:hover {\n"
"    background-color: #565656;\n"
"}\n"
"\n"
"QHeaderView::section:pressed {\n"
"    background-color: #444444;\n"
"} */\n"
"\n"
"\n"
"\n"
"\n"
"QLineEdit {\n"
"    border: 1px solid #CCCCCC;\n"
"    border-radius: 2px;\n"
"    color: #E3E3E3;\n"
"	font: 700 10pt \"Segoe UI\";\n"
"margin: 0px;\n"
"padding: 0px;\n"
"}\n"
"QLineEdit:focus {\n"
"    border: 1px solid #008CBA;\n"
"    background-color: #1C1C1C;\n"
"margin: 0px;\n"
"padding: 0px;\n"
"}\n"
"QLineEdit::selection {\n"
"    color: white;\n"
"}")

        self.verticalLayout.addWidget(self.audio_files_explorer)

        self.frame_5 = QFrame(self.frame)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.Import_Audio_button = QPushButton(self.frame_5)
        self.Import_Audio_button.setObjectName(u"Import_Audio_button")
        self.Import_Audio_button.setMinimumSize(QSize(0, 18))
        self.Import_Audio_button.setStyleSheet(u"\n"
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

        self.horizontalLayout_3.addWidget(self.Import_Audio_button)


        self.verticalLayout.addWidget(self.frame_5)


        self.horizontalLayout_5.addWidget(self.frame)

        self.frame_3 = QFrame(self.frame_7)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_3)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.sound_event_editor_viewport_widget = QHBoxLayout()
        self.sound_event_editor_viewport_widget.setObjectName(u"sound_event_editor_viewport_widget")

        self.verticalLayout_3.addLayout(self.sound_event_editor_viewport_widget)

        self.frame_2 = QFrame(self.frame_3)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.frame_4 = QFrame(self.frame_2)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.toolButton = QToolButton(self.frame_4)
        self.toolButton.setObjectName(u"toolButton")
        icon = QIcon()
        icon.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton.setIcon(icon)
        self.toolButton.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.toolButton)

        self.Import_Audio_button_2 = QPushButton(self.frame_4)
        self.Import_Audio_button_2.setObjectName(u"Import_Audio_button_2")
        self.Import_Audio_button_2.setMinimumSize(QSize(0, 18))
        self.Import_Audio_button_2.setStyleSheet(u"\n"
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

        self.horizontalLayout_4.addWidget(self.Import_Audio_button_2)


        self.horizontalLayout_2.addWidget(self.frame_4)


        self.verticalLayout_3.addWidget(self.frame_2)


        self.horizontalLayout_5.addWidget(self.frame_3)


        self.verticalLayout_4.addWidget(self.frame_7)

        self.lineEdit = QLineEdit(self.frame_6)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setReadOnly(True)

        self.verticalLayout_4.addWidget(self.lineEdit)


        self.horizontalLayout.addWidget(self.frame_6)

        SoundEvent_Editor_MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(SoundEvent_Editor_MainWindow)

        QMetaObject.connectSlotsByName(SoundEvent_Editor_MainWindow)
    # setupUi

    def retranslateUi(self, SoundEvent_Editor_MainWindow):
        SoundEvent_Editor_MainWindow.setWindowTitle(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"MainWindow", None))
        self.pushButton.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"PushButton", None))
        self.Import_Audio_button.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Import audio", None))
        self.toolButton.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"...", None))
        self.Import_Audio_button_2.setText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Quick setup", None))
        self.lineEdit.setPlaceholderText(QCoreApplication.translate("SoundEvent_Editor_MainWindow", u"Status line", None))
    # retranslateUi

