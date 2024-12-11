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
from PySide6.QtWidgets import (QApplication, QDockWidget, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)
import resources_rc

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
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout = QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.frame_6 = QFrame(self.frame)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.kv3_QplainTextEdit = QPlainTextEdit(self.frame_6)
        self.kv3_QplainTextEdit.setObjectName(u"kv3_QplainTextEdit")
        self.kv3_QplainTextEdit.setStyleSheet(u"")

        self.horizontalLayout_2.addWidget(self.kv3_QplainTextEdit)

        self.groupBox_3 = QGroupBox(self.frame_6)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.groupBox_3.setMinimumSize(QSize(128, 0))
        self.verticalLayout_6 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.folder_path_template = QLabel(self.groupBox_3)
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
        self.folder_path_template.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_6.addWidget(self.folder_path_template)

        self.assets_name_template = QLabel(self.groupBox_3)
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
        self.assets_name_template.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_6.addWidget(self.assets_name_template)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_6.addItem(self.verticalSpacer)


        self.horizontalLayout_2.addWidget(self.groupBox_3)


        self.verticalLayout.addWidget(self.frame_6)


        self.horizontalLayout_7.addWidget(self.frame)

        BatchCreator_MainWindow.setCentralWidget(self.centralwidget)
        self.dockWidget = QDockWidget(BatchCreator_MainWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidget.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
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
        self.left_vertical_frame.setStyleSheet(u"")
        self.left_vertical_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.left_vertical_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.left_vertical_frame)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.layout = QVBoxLayout()
        self.layout.setObjectName(u"layout")

        self.verticalLayout_2.addLayout(self.layout)

        self.recent_files = QGroupBox(self.left_vertical_frame)
        self.recent_files.setObjectName(u"recent_files")
        self.recent_files.setCheckable(True)
        self.recent_files.setChecked(False)

        self.verticalLayout_2.addWidget(self.recent_files)

        self.groupBox_2 = QGroupBox(self.left_vertical_frame)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setMaximumSize(QSize(16777215, 72))
        self.verticalLayout_5 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.frame_2 = QFrame(self.groupBox_2)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMaximumSize(QSize(16777215, 32))
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.create_file = QPushButton(self.frame_2)
        self.create_file.setObjectName(u"create_file")
        self.create_file.setMinimumSize(QSize(0, 18))
        self.create_file.setStyleSheet(u"\n"
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
        icon.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_file.setIcon(icon)
        self.create_file.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.create_file)

        self.open_button = QPushButton(self.frame_2)
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
        icon1 = QIcon()
        icon1.addFile(u":/icons/file_open_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_button.setIcon(icon1)
        self.open_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.open_button)

        self.save_button = QPushButton(self.frame_2)
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
        icon2 = QIcon()
        icon2.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_button.setIcon(icon2)
        self.save_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.save_button)


        self.verticalLayout_5.addWidget(self.frame_2)


        self.verticalLayout_2.addWidget(self.groupBox_2)

        self.groupBox = QGroupBox(self.left_vertical_frame)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setMaximumSize(QSize(16777215, 110))
        self.verticalLayout_4 = QVBoxLayout(self.groupBox)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.frame_3 = QFrame(self.groupBox)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.process_options_button = QPushButton(self.frame_3)
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
        icon3 = QIcon()
        icon3.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_options_button.setIcon(icon3)
        self.process_options_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_5.addWidget(self.process_options_button)

        self.process_all_button = QPushButton(self.frame_3)
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
        icon4 = QIcon()
        icon4.addFile(u":/icons/tab_move_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_all_button.setIcon(icon4)
        self.process_all_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_5.addWidget(self.process_all_button)


        self.verticalLayout_4.addWidget(self.frame_3)

        self.extension_lineEdit = QLineEdit(self.groupBox)
        self.extension_lineEdit.setObjectName(u"extension_lineEdit")

        self.verticalLayout_4.addWidget(self.extension_lineEdit)


        self.verticalLayout_2.addWidget(self.groupBox)


        self.verticalLayout_3.addWidget(self.left_vertical_frame)

        self.dockWidget.setWidget(self.dockWidgetContents)
        BatchCreator_MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget)

        self.retranslateUi(BatchCreator_MainWindow)

        QMetaObject.connectSlotsByName(BatchCreator_MainWindow)
    # setupUi

    def retranslateUi(self, BatchCreator_MainWindow):
        BatchCreator_MainWindow.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"MainWindow", None))
        self.label.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Editor", None))
        self.kv3_QplainTextEdit.setPlainText("")
        self.kv3_QplainTextEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"Content", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Variables", None))
        self.folder_path_template.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Folder path", None))
        self.assets_name_template.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Asset name", None))
        self.dockWidget.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Explorer", None))
        self.recent_files.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Recent files", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"File", None))
        self.create_file.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Create", None))
        self.open_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Open", None))
        self.save_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Save", None))
        self.groupBox.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Process", None))
        self.process_options_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Options", None))
        self.process_all_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Process", None))
        self.extension_lineEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"File extension (vmdl, vmat etc).", None))
    # retranslateUi

