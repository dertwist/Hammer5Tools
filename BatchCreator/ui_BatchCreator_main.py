# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'BatchCreator_main.ui'
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
    QHeaderView, QLabel, QLineEdit, QMainWindow,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem,
    QTextEdit, QToolButton, QTreeView, QVBoxLayout,
    QWidget)
import rc_resources

class Ui_BatchCreator_MainWindow(object):
    def setupUi(self, BatchCreator_MainWindow):
        if not BatchCreator_MainWindow.objectName():
            BatchCreator_MainWindow.setObjectName(u"BatchCreator_MainWindow")
        BatchCreator_MainWindow.resize(1088, 612)
        BatchCreator_MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.centralwidget = QWidget(BatchCreator_MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout_7 = QHBoxLayout(self.centralwidget)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel(self.frame)
        self.status_label.setObjectName(u"status_label")

        self.verticalLayout.addWidget(self.status_label)

        self.frame_4 = QFrame(self.frame)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.folder_path_template = QLabel(self.frame_4)
        self.folder_path_template.setObjectName(u"folder_path_template")
        self.folder_path_template.setStyleSheet(u"\n"
"    /* QPushButton default and hover styles */\n"
"    QLabel {\n"
"\n"
"        font: 600 10pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        padding-top: 4px;\n"
"        padding-bottom:4px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QLabel:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }")
        self.folder_path_template.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.folder_path_template)

        self.assets_name_template = QLabel(self.frame_4)
        self.assets_name_template.setObjectName(u"assets_name_template")
        self.assets_name_template.setStyleSheet(u"\n"
"    /* QPushButton default and hover styles */\n"
"    QLabel {\n"
"\n"
"        font: 600 10pt \"Segoe UI\";\n"
"	\n"
"\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        padding-top: 4px;\n"
"        padding-bottom:4px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QLabel:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }")
        self.assets_name_template.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_3.addWidget(self.assets_name_template)


        self.verticalLayout.addWidget(self.frame_4)

        self.kv3_QplainTextEdit = QPlainTextEdit(self.frame)
        self.kv3_QplainTextEdit.setObjectName(u"kv3_QplainTextEdit")
        self.kv3_QplainTextEdit.setStyleSheet(u"")

        self.verticalLayout.addWidget(self.kv3_QplainTextEdit)

        self.extension_lineEdit = QLineEdit(self.frame)
        self.extension_lineEdit.setObjectName(u"extension_lineEdit")

        self.verticalLayout.addWidget(self.extension_lineEdit)

        self.frame_5 = QFrame(self.frame)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.open_button = QPushButton(self.frame_5)
        self.open_button.setObjectName(u"open_button")
        self.open_button.setMinimumSize(QSize(0, 18))
        self.open_button.setStyleSheet(u"\n"
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
        icon = QIcon()
        icon.addFile(u":/icons/file_open_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_button.setIcon(icon)
        self.open_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.open_button)

        self.save_button = QPushButton(self.frame_5)
        self.save_button.setObjectName(u"save_button")
        self.save_button.setMinimumSize(QSize(0, 18))
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
        icon1 = QIcon()
        icon1.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_button.setIcon(icon1)
        self.save_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.save_button)

        self.horizontalSpacer = QSpacerItem(8, 5, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.process_options_button = QPushButton(self.frame_5)
        self.process_options_button.setObjectName(u"process_options_button")
        self.process_options_button.setMinimumSize(QSize(0, 18))
        self.process_options_button.setStyleSheet(u"\n"
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
        icon2 = QIcon()
        icon2.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_options_button.setIcon(icon2)
        self.process_options_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.process_options_button)

        self.process_all_button = QPushButton(self.frame_5)
        self.process_all_button.setObjectName(u"process_all_button")
        self.process_all_button.setMinimumSize(QSize(0, 18))
        self.process_all_button.setStyleSheet(u"\n"
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
        icon3 = QIcon()
        icon3.addFile(u":/icons/tab_move_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_all_button.setIcon(icon3)
        self.process_all_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.process_all_button)


        self.verticalLayout.addWidget(self.frame_5)


        self.horizontalLayout_7.addWidget(self.frame)

        BatchCreator_MainWindow.setCentralWidget(self.centralwidget)
        self.dockWidget = QDockWidget(BatchCreator_MainWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidget.setFeatures(QDockWidget.DockWidgetFloatable|QDockWidget.DockWidgetMovable)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout_3 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.left_vertical_frame = QFrame(self.dockWidgetContents)
        self.left_vertical_frame.setObjectName(u"left_vertical_frame")
        self.left_vertical_frame.setMaximumSize(QSize(16777215, 16777215))
        self.left_vertical_frame.setBaseSize(QSize(330, 0))
        self.left_vertical_frame.setFrameShape(QFrame.StyledPanel)
        self.left_vertical_frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.left_vertical_frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.MiniWindows_explorer = QTreeView(self.left_vertical_frame)
        self.MiniWindows_explorer.setObjectName(u"MiniWindows_explorer")
        self.MiniWindows_explorer.setMaximumSize(QSize(16777215, 16777215))

        self.verticalLayout_2.addWidget(self.MiniWindows_explorer)

        self.horizontal_frame = QFrame(self.left_vertical_frame)
        self.horizontal_frame.setObjectName(u"horizontal_frame")
        self.horizontal_frame.setMaximumSize(QSize(16777215, 32))
        self.horizontal_frame.setFrameShape(QFrame.StyledPanel)
        self.horizontal_frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.horizontal_frame)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.Status_Line_Qedit = QTextEdit(self.horizontal_frame)
        self.Status_Line_Qedit.setObjectName(u"Status_Line_Qedit")

        self.horizontalLayout_2.addWidget(self.Status_Line_Qedit)

        self.Copy_from_status_line_toolButton = QToolButton(self.horizontal_frame)
        self.Copy_from_status_line_toolButton.setObjectName(u"Copy_from_status_line_toolButton")
        icon4 = QIcon()
        icon4.addFile(u":/icons/file_copy_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Copy_from_status_line_toolButton.setIcon(icon4)
        self.Copy_from_status_line_toolButton.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.Copy_from_status_line_toolButton)

        self.file_initialize_button = QToolButton(self.horizontal_frame)
        self.file_initialize_button.setObjectName(u"file_initialize_button")
        icon5 = QIcon()
        icon5.addFile(u":/icons/add_circle_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.file_initialize_button.setIcon(icon5)
        self.file_initialize_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.file_initialize_button)


        self.verticalLayout_2.addWidget(self.horizontal_frame)


        self.verticalLayout_3.addWidget(self.left_vertical_frame)

        self.dockWidget.setWidget(self.dockWidgetContents)
        BatchCreator_MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget)

        self.retranslateUi(BatchCreator_MainWindow)

        QMetaObject.connectSlotsByName(BatchCreator_MainWindow)
    # setupUi

    def retranslateUi(self, BatchCreator_MainWindow):
        BatchCreator_MainWindow.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"MainWindow", None))
        self.status_label.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Oppened File: BatchCreator version:", None))
        self.folder_path_template.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Folder path", None))
        self.assets_name_template.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Asset name", None))
        self.kv3_QplainTextEdit.setPlainText("")
        self.kv3_QplainTextEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"Content", None))
        self.extension_lineEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"File extension (vmdl, vmat etc).", None))
        self.open_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Open", None))
        self.save_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Save", None))
        self.process_options_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Options", None))
        self.process_all_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Process", None))
        self.dockWidget.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Explorer", None))
        self.Copy_from_status_line_toolButton.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"...", None))
        self.file_initialize_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"...", None))
    # retranslateUi

