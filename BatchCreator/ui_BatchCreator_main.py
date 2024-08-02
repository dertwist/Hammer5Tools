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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QMainWindow, QPlainTextEdit, QPushButton,
    QSizePolicy, QTextEdit, QToolButton, QTreeView,
    QVBoxLayout, QWidget)
import rc_resources

class Ui_BatchCreator_MainWindow(object):
    def setupUi(self, BatchCreator_MainWindow):
        if not BatchCreator_MainWindow.objectName():
            BatchCreator_MainWindow.setObjectName(u"BatchCreator_MainWindow")
        BatchCreator_MainWindow.resize(1053, 788)
        BatchCreator_MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.centralwidget = QWidget(BatchCreator_MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMaximumSize(QSize(330, 16777215))
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.MiniWindows_explorer = QTreeView(self.frame_2)
        self.MiniWindows_explorer.setObjectName(u"MiniWindows_explorer")
        self.MiniWindows_explorer.setMaximumSize(QSize(16777215, 16777215))

        self.verticalLayout_2.addWidget(self.MiniWindows_explorer)

        self.frame_3 = QFrame(self.frame_2)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16777215, 32))
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.Status_Line_Qedit = QTextEdit(self.frame_3)
        self.Status_Line_Qedit.setObjectName(u"Status_Line_Qedit")

        self.horizontalLayout_2.addWidget(self.Status_Line_Qedit)

        self.Copy_from_status_line_toolButton = QToolButton(self.frame_3)
        self.Copy_from_status_line_toolButton.setObjectName(u"Copy_from_status_line_toolButton")
        icon = QIcon()
        icon.addFile(u":/icons/file_copy_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.Copy_from_status_line_toolButton.setIcon(icon)
        self.Copy_from_status_line_toolButton.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.Copy_from_status_line_toolButton)


        self.verticalLayout_2.addWidget(self.frame_3)


        self.horizontalLayout.addWidget(self.frame_2)

        self.frame = QFrame(self.centralwidget)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frame)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
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

        self.verticalLayout.addWidget(self.kv3_QplainTextEdit)

        self.Import_Audio_button = QPushButton(self.frame)
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

        self.verticalLayout.addWidget(self.Import_Audio_button)


        self.horizontalLayout.addWidget(self.frame)

        BatchCreator_MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(BatchCreator_MainWindow)

        QMetaObject.connectSlotsByName(BatchCreator_MainWindow)
    # setupUi

    def retranslateUi(self, BatchCreator_MainWindow):
        BatchCreator_MainWindow.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"MainWindow", None))
        self.Copy_from_status_line_toolButton.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"...", None))
        self.folder_path_template.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Folder path", None))
        self.assets_name_template.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Asset name", None))
        self.Import_Audio_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Process all", None))
    # retranslateUi

