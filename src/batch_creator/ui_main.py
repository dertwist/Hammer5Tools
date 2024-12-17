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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDockWidget, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPlainTextEdit, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QVBoxLayout, QWidget)
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
        self.frame_4 = QFrame(self.frame)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_7 = QVBoxLayout(self.frame_4)
        self.verticalLayout_7.setSpacing(0)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame_4)
        self.label.setObjectName(u"label")

        self.verticalLayout_7.addWidget(self.label)

        self.label_editor_placeholder = QLabel(self.frame_4)
        self.label_editor_placeholder.setObjectName(u"label_editor_placeholder")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_editor_placeholder.sizePolicy().hasHeightForWidth())
        self.label_editor_placeholder.setSizePolicy(sizePolicy)
        self.label_editor_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_7.addWidget(self.label_editor_placeholder)

        self.editor_widgets = QFrame(self.frame_4)
        self.editor_widgets.setObjectName(u"editor_widgets")
        self.editor_widgets.setFrameShape(QFrame.Shape.StyledPanel)
        self.editor_widgets.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_6 = QVBoxLayout(self.editor_widgets)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.splitter = QSplitter(self.editor_widgets)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.kv3_QplainTextEdit = QPlainTextEdit(self.splitter)
        self.kv3_QplainTextEdit.setObjectName(u"kv3_QplainTextEdit")
        self.kv3_QplainTextEdit.setStyleSheet(u"")
        self.splitter.addWidget(self.kv3_QplainTextEdit)
        self.groupBox = QGroupBox(self.splitter)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_11 = QVBoxLayout(self.groupBox)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalSpacer = QSpacerItem(20, 21, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_11.addItem(self.verticalSpacer)

        self.splitter.addWidget(self.groupBox)

        self.verticalLayout_6.addWidget(self.splitter)


        self.verticalLayout_7.addWidget(self.editor_widgets)


        self.verticalLayout.addWidget(self.frame_4)


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
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 9)
        self.layout = QVBoxLayout()
        self.layout.setObjectName(u"layout")

        self.verticalLayout_2.addLayout(self.layout)

        self.file_groupbox = QGroupBox(self.left_vertical_frame)
        self.file_groupbox.setObjectName(u"file_groupbox")
        self.file_groupbox.setMaximumSize(QSize(16777215, 72))
        self.verticalLayout_5 = QVBoxLayout(self.file_groupbox)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 4, 0, 0)
        self.frame_2 = QFrame(self.file_groupbox)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMaximumSize(QSize(16777215, 32))
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.open_button = QPushButton(self.frame_2)
        self.open_button.setObjectName(u"open_button")
        self.open_button.setMinimumSize(QSize(0, 18))
        self.open_button.setStyleSheet(u"    QPushButton {\n"
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
        icon = QIcon()
        icon.addFile(u":/icons/file_open_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_button.setIcon(icon)
        self.open_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.open_button)

        self.save_button = QPushButton(self.frame_2)
        self.save_button.setObjectName(u"save_button")
        self.save_button.setMinimumSize(QSize(0, 18))
        self.save_button.setStyleSheet(u"    QPushButton {\n"
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
        icon1 = QIcon()
        icon1.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_button.setIcon(icon1)
        self.save_button.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.save_button)

        self.create_file = QPushButton(self.frame_2)
        self.create_file.setObjectName(u"create_file")
        self.create_file.setMinimumSize(QSize(0, 18))
        self.create_file.setStyleSheet(u"    QPushButton {\n"
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
        icon2.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.create_file.setIcon(icon2)
        self.create_file.setIconSize(QSize(20, 20))

        self.horizontalLayout.addWidget(self.create_file)


        self.verticalLayout_5.addWidget(self.frame_2)


        self.verticalLayout_2.addWidget(self.file_groupbox)

        self.process_groupbox = QGroupBox(self.left_vertical_frame)
        self.process_groupbox.setObjectName(u"process_groupbox")
        self.process_groupbox.setMaximumSize(QSize(16777215, 110))
        self.verticalLayout_4 = QVBoxLayout(self.process_groupbox)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 4, 0, 0)
        self.frame_3 = QFrame(self.process_groupbox)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.process_options_button = QPushButton(self.frame_3)
        self.process_options_button.setObjectName(u"process_options_button")
        self.process_options_button.setMinimumSize(QSize(0, 18))
        self.process_options_button.setStyleSheet(u"    QPushButton {\n"
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
        icon3 = QIcon()
        icon3.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_options_button.setIcon(icon3)
        self.process_options_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_5.addWidget(self.process_options_button)

        self.return_button = QPushButton(self.frame_3)
        self.return_button.setObjectName(u"return_button")
        self.return_button.setEnabled(False)
        self.return_button.setMinimumSize(QSize(0, 18))
        self.return_button.setStyleSheet(u"    QPushButton {\n"
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
        icon4 = QIcon()
        icon4.addFile(u":/icons/undo_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.return_button.setIcon(icon4)
        self.return_button.setIconSize(QSize(20, 20))
        self.return_button.setCheckable(False)

        self.horizontalLayout_5.addWidget(self.return_button)

        self.process_all_button = QPushButton(self.frame_3)
        self.process_all_button.setObjectName(u"process_all_button")
        self.process_all_button.setMinimumSize(QSize(0, 18))
        self.process_all_button.setStyleSheet(u"    QPushButton {\n"
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
        icon5 = QIcon()
        icon5.addFile(u":/icons/tab_move_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_all_button.setIcon(icon5)
        self.process_all_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_5.addWidget(self.process_all_button)


        self.verticalLayout_4.addWidget(self.frame_3)

        self.extension_lineEdit = QLineEdit(self.process_groupbox)
        self.extension_lineEdit.setObjectName(u"extension_lineEdit")

        self.verticalLayout_4.addWidget(self.extension_lineEdit)


        self.verticalLayout_2.addWidget(self.process_groupbox)

        self.referencing_groupbox = QGroupBox(self.left_vertical_frame)
        self.referencing_groupbox.setObjectName(u"referencing_groupbox")
        self.referencing_groupbox.setMaximumSize(QSize(16777215, 110))
        self.verticalLayout_10 = QVBoxLayout(self.referencing_groupbox)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 4, 0, 9)
        self.frame_8 = QFrame(self.referencing_groupbox)
        self.frame_8.setObjectName(u"frame_8")
        self.frame_8.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_8.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_9 = QHBoxLayout(self.frame_8)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.process_options_button_4 = QPushButton(self.frame_8)
        self.process_options_button_4.setObjectName(u"process_options_button_4")
        self.process_options_button_4.setMinimumSize(QSize(0, 18))
        self.process_options_button_4.setStyleSheet(u"    QPushButton {\n"
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
        icon6 = QIcon()
        icon6.addFile(u":/icons/file_present_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_options_button_4.setIcon(icon6)
        self.process_options_button_4.setIconSize(QSize(20, 20))

        self.horizontalLayout_9.addWidget(self.process_options_button_4)

        self.lineEdit = QLineEdit(self.frame_8)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout_9.addWidget(self.lineEdit)


        self.verticalLayout_10.addWidget(self.frame_8)

        self.frame_9 = QFrame(self.referencing_groupbox)
        self.frame_9.setObjectName(u"frame_9")
        self.frame_9.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_9.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_9)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.checkBox = QCheckBox(self.frame_9)
        self.checkBox.setObjectName(u"checkBox")
        self.checkBox.setStyleSheet(u"QCheckBox {\n"
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

        self.horizontalLayout_3.addWidget(self.checkBox)

        self.checkBox_2 = QCheckBox(self.frame_9)
        self.checkBox_2.setObjectName(u"checkBox_2")
        self.checkBox_2.setEnabled(True)
        self.checkBox_2.setStyleSheet(u"QCheckBox {\n"
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

        self.horizontalLayout_3.addWidget(self.checkBox_2)


        self.verticalLayout_10.addWidget(self.frame_9)


        self.verticalLayout_2.addWidget(self.referencing_groupbox)


        self.verticalLayout_3.addWidget(self.left_vertical_frame)

        self.dockWidget.setWidget(self.dockWidgetContents)
        BatchCreator_MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget)

        self.retranslateUi(BatchCreator_MainWindow)

        QMetaObject.connectSlotsByName(BatchCreator_MainWindow)
    # setupUi

    def retranslateUi(self, BatchCreator_MainWindow):
        BatchCreator_MainWindow.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"MainWindow", None))
        self.label.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Editor", None))
        self.label_editor_placeholder.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Please, open a file for editing", None))
        self.kv3_QplainTextEdit.setPlainText("")
        self.kv3_QplainTextEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"Content", None))
        self.groupBox.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Replacements", None))
        self.dockWidget.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Explorer", None))
        self.file_groupbox.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"File", None))
        self.open_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Open", None))
        self.save_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Save", None))
        self.create_file.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Create", None))
        self.process_groupbox.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Process", None))
        self.process_options_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Options", None))
        self.return_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Return", None))
        self.process_all_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Process", None))
        self.extension_lineEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"File extension (vmdl, vmat etc).", None))
        self.referencing_groupbox.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Referencing", None))
        self.process_options_button_4.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Select", None))
        self.checkBox.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Realtime", None))
        self.checkBox_2.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Realtime process", None))
    # retranslateUi

