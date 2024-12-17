# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget)
import resources_rc

class Ui_BatchCreator_process_Dialog(object):
    def setupUi(self, BatchCreator_process_Dialog):
        if not BatchCreator_process_Dialog.objectName():
            BatchCreator_process_Dialog.setObjectName(u"BatchCreator_process_Dialog")
        BatchCreator_process_Dialog.resize(793, 645)
        icon = QIcon()
        icon.addFile(u":/icons/appicon.ico", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        BatchCreator_process_Dialog.setWindowIcon(icon)
        BatchCreator_process_Dialog.setStyleSheet(u"background-color: #1C1C1C;")
        self.verticalLayout = QVBoxLayout(BatchCreator_process_Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame_4 = QFrame(BatchCreator_process_Dialog)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_4)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame_3 = QFrame(self.frame_4)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_3)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.frame_5 = QFrame(self.frame_3)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_5)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.select_files_to_process_button = QPushButton(self.frame_5)
        self.select_files_to_process_button.setObjectName(u"select_files_to_process_button")
        self.select_files_to_process_button.setStyleSheet(u"    QPushButton {\n"
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
"    }\n"
"QPushButton:disabled {\n"
"color: gray;\n"
" background-color: #2C2C2C;\n"
"}")

        self.horizontalLayout_3.addWidget(self.select_files_to_process_button)

        self.load_from_the_folder_checkBox = QCheckBox(self.frame_5)
        self.load_from_the_folder_checkBox.setObjectName(u"load_from_the_folder_checkBox")
        self.load_from_the_folder_checkBox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.load_from_the_folder_checkBox.setStyleSheet(u"QCheckBox {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
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
"    QCheckBox:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QCheckBox:pressed {\n"
"\n"
"    }\n"
"\n"
"QCheckBox:disabled {\n"
"color: gray;\n"
" background-color: #2C2C2C;\n"
"}")
        self.load_from_the_folder_checkBox.setIconSize(QSize(20, 20))
        self.load_from_the_folder_checkBox.setChecked(True)

        self.horizontalLayout_3.addWidget(self.load_from_the_folder_checkBox)


        self.verticalLayout_3.addWidget(self.frame_5)

        self.Input_files_preview_scrollarea = QListWidget(self.frame_3)
        self.Input_files_preview_scrollarea.setObjectName(u"Input_files_preview_scrollarea")

        self.verticalLayout_3.addWidget(self.Input_files_preview_scrollarea)


        self.horizontalLayout.addWidget(self.frame_3)

        self.toolButton = QToolButton(self.frame_4)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setEnabled(False)
        icon1 = QIcon()
        icon1.addFile(u":/icons/arrow_forward_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton.setIcon(icon1)
        self.toolButton.setIconSize(QSize(16, 16))

        self.horizontalLayout.addWidget(self.toolButton)

        self.frame_2 = QFrame(self.frame_4)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.frame_6 = QFrame(self.frame_2)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.choose_output_button = QPushButton(self.frame_6)
        self.choose_output_button.setObjectName(u"choose_output_button")
        self.choose_output_button.setStyleSheet(u"    QPushButton {\n"
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
"    }\n"
"QPushButton:disabled {\n"
"color: gray;\n"
" background-color: #2C2C2C;\n"
"}")

        self.horizontalLayout_4.addWidget(self.choose_output_button)

        self.output_to_the_folder_checkBox = QCheckBox(self.frame_6)
        self.output_to_the_folder_checkBox.setObjectName(u"output_to_the_folder_checkBox")
        self.output_to_the_folder_checkBox.setStyleSheet(u"QCheckBox {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
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
"    QCheckBox:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QCheckBox:pressed {\n"
"\n"
"    }\n"
"\n"
"QCheckBox:disabled {\n"
"color: gray;\n"
" background-color: #2C2C2C;\n"
"}")
        self.output_to_the_folder_checkBox.setIconSize(QSize(20, 20))
        self.output_to_the_folder_checkBox.setChecked(True)

        self.horizontalLayout_4.addWidget(self.output_to_the_folder_checkBox)


        self.verticalLayout_2.addWidget(self.frame_6)

        self.output_files_preview_scrollarea = QListWidget(self.frame_2)
        self.output_files_preview_scrollarea.setObjectName(u"output_files_preview_scrollarea")

        self.verticalLayout_2.addWidget(self.output_files_preview_scrollarea)


        self.horizontalLayout.addWidget(self.frame_2)


        self.verticalLayout.addWidget(self.frame_4)

        self.frame_7 = QFrame(BatchCreator_process_Dialog)
        self.frame_7.setObjectName(u"frame_7")
        self.frame_7.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_7)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame_7)
        self.label.setObjectName(u"label")

        self.horizontalLayout_5.addWidget(self.label)

        self.ignore_extensions_lineEdit = QLineEdit(self.frame_7)
        self.ignore_extensions_lineEdit.setObjectName(u"ignore_extensions_lineEdit")

        self.horizontalLayout_5.addWidget(self.ignore_extensions_lineEdit)


        self.verticalLayout.addWidget(self.frame_7)

        self.frame_8 = QFrame(BatchCreator_process_Dialog)
        self.frame_8.setObjectName(u"frame_8")
        self.frame_8.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_8.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self.frame_8)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.frame_8)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_6.addWidget(self.label_2)

        self.ignore_files_lineEdit = QLineEdit(self.frame_8)
        self.ignore_files_lineEdit.setObjectName(u"ignore_files_lineEdit")

        self.horizontalLayout_6.addWidget(self.ignore_files_lineEdit)


        self.verticalLayout.addWidget(self.frame_8)

        self.output_folder = QLabel(BatchCreator_process_Dialog)
        self.output_folder.setObjectName(u"output_folder")

        self.verticalLayout.addWidget(self.output_folder)

        self.frame = QFrame(BatchCreator_process_Dialog)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.algorithm_select_comboBox = QComboBox(self.frame)
        self.algorithm_select_comboBox.addItem("")
        self.algorithm_select_comboBox.addItem("")
        self.algorithm_select_comboBox.setObjectName(u"algorithm_select_comboBox")
        self.algorithm_select_comboBox.setStyleSheet(u"\n"
"QComboBox {\n"
"    font: 700 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 4px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 18px;\n"
"    padding-top: 5px;\n"
"    padding-bottom: 5px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"    padding-left: 5px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    background-color: #414956;\n"
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
"    paddin"
                        "g: 5px;\n"
"    width: 7px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"/* Style the drop-down list view */\n"
"QComboBox QAbstractItemView {\n"
"    border: 2px solid gray;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    selection-background-color: #414956;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"/* Style individual items in the drop-down list */\n"
"QComboBox QAbstractItemView::item {\n"
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
"/* Style the selected item in the drop-down list */\n"
"QComboBox QAbstractItemView::item:selected {\n"
"    height: 16px; /* Set the height of each item */\n"
"    padding: 4px; /* Add padding to each item */\n"
"    padding-left: 5px;\n"
"    pa"
                        "dding-right: 5px;\n"
"    background-color: #414956;\n"
"    color: white;\n"
"    border: none; /* Remove border */\n"
"    outline: none; /* Remove outline */\n"
"}\n"
"\n"
"/* -------------------------- */")

        self.horizontalLayout_2.addWidget(self.algorithm_select_comboBox)

        self.process_button = QPushButton(self.frame)
        self.process_button.setObjectName(u"process_button")
        self.process_button.setStyleSheet(u"    QPushButton {\n"
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
"    }\n"
"QPushButton:disabled {\n"
"color: gray;\n"
" background-color: #2C2C2C;\n"
"}")
        icon2 = QIcon()
        icon2.addFile(u":/icons/tab_move_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_button.setIcon(icon2)
        self.process_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.process_button)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(BatchCreator_process_Dialog)

        QMetaObject.connectSlotsByName(BatchCreator_process_Dialog)
    # setupUi

    def retranslateUi(self, BatchCreator_process_Dialog):
        BatchCreator_process_Dialog.setWindowTitle(QCoreApplication.translate("BatchCreator_process_Dialog", u"Process options", None))
        self.select_files_to_process_button.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Select files to process", None))
        self.load_from_the_folder_checkBox.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Load from the folder", None))
        self.toolButton.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"...", None))
        self.choose_output_button.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Choose output", None))
        self.output_to_the_folder_checkBox.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Output to the folder", None))
        self.label.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Ignore extensions:", None))
        self.ignore_extensions_lineEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Ignore extensions: .blend", None))
        self.label_2.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Ignore: files", None))
        self.ignore_files_lineEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Ignore extensions: .blend", None))
        self.output_folder.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Output folder:", None))
        self.algorithm_select_comboBox.setItemText(0, QCoreApplication.translate("BatchCreator_process_Dialog", u"Process without interpretation", None))
        self.algorithm_select_comboBox.setItemText(1, QCoreApplication.translate("BatchCreator_process_Dialog", u"Remove underscore from the end", None))

        self.process_button.setText(QCoreApplication.translate("BatchCreator_process_Dialog", u"Process", None))
    # retranslateUi

