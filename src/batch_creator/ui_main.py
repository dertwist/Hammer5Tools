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
from PySide6.QtWidgets import (QApplication, QDockWidget, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy,
    QSpacerItem, QSplitter, QVBoxLayout, QWidget)
import resources_rc

class Ui_BatchCreator_MainWindow(object):
    def setupUi(self, BatchCreator_MainWindow):
        if not BatchCreator_MainWindow.objectName():
            BatchCreator_MainWindow.setObjectName(u"BatchCreator_MainWindow")
        BatchCreator_MainWindow.resize(1271, 578)
        BatchCreator_MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.centralwidget = QWidget(BatchCreator_MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_9 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_9.setSpacing(0)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setContentsMargins(0, 0, 0, 0)
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
        self.editor_widgets.setFrameShape(QFrame.Shape.NoFrame)
        self.editor_widgets.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_6 = QVBoxLayout(self.editor_widgets)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(self.editor_widgets)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setBaseSize(QSize(0, 0))
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter.setOpaqueResize(True)
        self.splitter.setChildrenCollapsible(False)
        self.kv3_QplainTextEdit = QPlainTextEdit(self.splitter)
        self.kv3_QplainTextEdit.setObjectName(u"kv3_QplainTextEdit")
        self.kv3_QplainTextEdit.setStyleSheet(u"")
        self.splitter.addWidget(self.kv3_QplainTextEdit)
        self.frame_5 = QFrame(self.splitter)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_12 = QVBoxLayout(self.frame_5)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.frame_6 = QFrame(self.frame_5)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.viewport_searchbar = QLineEdit(self.frame_6)
        self.viewport_searchbar.setObjectName(u"viewport_searchbar")

        self.horizontalLayout_4.addWidget(self.viewport_searchbar)

        self.viewport_search_label = QLabel(self.frame_6)
        self.viewport_search_label.setObjectName(u"viewport_search_label")

        self.horizontalLayout_4.addWidget(self.viewport_search_label)

        self.viewport_search_previous_button = QPushButton(self.frame_6)
        self.viewport_search_previous_button.setObjectName(u"viewport_search_previous_button")
        self.viewport_search_previous_button.setMinimumSize(QSize(0, 18))
        self.viewport_search_previous_button.setStyleSheet(u"    QPushButton {\n"
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
        icon.addFile(u":/icons/arrow_back_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.viewport_search_previous_button.setIcon(icon)
        self.viewport_search_previous_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.viewport_search_previous_button)

        self.viewport_search_next_button = QPushButton(self.frame_6)
        self.viewport_search_next_button.setObjectName(u"viewport_search_next_button")
        self.viewport_search_next_button.setMinimumSize(QSize(0, 18))
        self.viewport_search_next_button.setStyleSheet(u"    QPushButton {\n"
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
        icon1.addFile(u":/icons/arrow_forward_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.viewport_search_next_button.setIcon(icon1)
        self.viewport_search_next_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.viewport_search_next_button)


        self.verticalLayout_12.addWidget(self.frame_6)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.label_2 = QLabel(self.frame_5)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.new_replacement_button = QPushButton(self.frame_5)
        self.new_replacement_button.setObjectName(u"new_replacement_button")
        self.new_replacement_button.setMinimumSize(QSize(0, 32))
        self.new_replacement_button.setMaximumSize(QSize(128, 16777215))
        self.new_replacement_button.setStyleSheet(u"    QPushButton {\n"
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
        self.new_replacement_button.setIcon(icon2)
        self.new_replacement_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.new_replacement_button)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_2)


        self.verticalLayout_12.addLayout(self.horizontalLayout_2)

        self.replacements_scrollarea = QScrollArea(self.frame_5)
        self.replacements_scrollarea.setObjectName(u"replacements_scrollarea")
        self.replacements_scrollarea.setMinimumSize(QSize(0, 128))
        self.replacements_scrollarea.setWidgetResizable(True)
        self.replacements_layout = QWidget()
        self.replacements_layout.setObjectName(u"replacements_layout")
        self.replacements_layout.setGeometry(QRect(0, 0, 640, 126))
        self.verticalLayout_11 = QVBoxLayout(self.replacements_layout)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_11.addItem(self.verticalSpacer)

        self.replacements_scrollarea.setWidget(self.replacements_layout)

        self.verticalLayout_12.addWidget(self.replacements_scrollarea)

        self.splitter.addWidget(self.frame_5)

        self.verticalLayout_6.addWidget(self.splitter)


        self.verticalLayout_7.addWidget(self.editor_widgets)


        self.verticalLayout.addWidget(self.frame_4)


        self.verticalLayout_9.addWidget(self.frame)

        BatchCreator_MainWindow.setCentralWidget(self.centralwidget)
        self.dockWidget = QDockWidget(BatchCreator_MainWindow)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidget.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
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
        icon3 = QIcon()
        icon3.addFile(u":/icons/file_open_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_button.setIcon(icon3)
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
        icon4 = QIcon()
        icon4.addFile(u":/icons/save_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.save_button.setIcon(icon4)
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
        icon5 = QIcon()
        icon5.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_options_button.setIcon(icon5)
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
        icon6 = QIcon()
        icon6.addFile(u":/icons/undo_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.return_button.setIcon(icon6)
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
        icon7 = QIcon()
        icon7.addFile(u":/icons/tab_move_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.process_all_button.setIcon(icon7)
        self.process_all_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_5.addWidget(self.process_all_button)


        self.verticalLayout_4.addWidget(self.frame_3)

        self.extension_lineEdit = QLineEdit(self.process_groupbox)
        self.extension_lineEdit.setObjectName(u"extension_lineEdit")

        self.verticalLayout_4.addWidget(self.extension_lineEdit)


        self.verticalLayout_2.addWidget(self.process_groupbox)

        self.referencing_groupbox = QGroupBox(self.left_vertical_frame)
        self.referencing_groupbox.setObjectName(u"referencing_groupbox")
        self.referencing_groupbox.setMaximumSize(QSize(16777215, 60))
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
        self.select_reference_button = QPushButton(self.frame_8)
        self.select_reference_button.setObjectName(u"select_reference_button")
        self.select_reference_button.setMinimumSize(QSize(0, 18))
        self.select_reference_button.setStyleSheet(u"    QPushButton {\n"
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
        icon8 = QIcon()
        icon8.addFile(u":/icons/file_present_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.select_reference_button.setIcon(icon8)
        self.select_reference_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_9.addWidget(self.select_reference_button)


        self.verticalLayout_10.addWidget(self.frame_8)


        self.verticalLayout_2.addWidget(self.referencing_groupbox)


        self.verticalLayout_3.addWidget(self.left_vertical_frame)

        self.dockWidget.setWidget(self.dockWidgetContents)
        BatchCreator_MainWindow.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidget)
        self.dockWidget_2 = QDockWidget(BatchCreator_MainWindow)
        self.dockWidget_2.setObjectName(u"dockWidget_2")
        self.dockWidget_2.setMinimumSize(QSize(354, 200))
        self.dockWidget_2.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.dockWidgetContents_2 = QWidget()
        self.dockWidgetContents_2.setObjectName(u"dockWidgetContents_2")
        self.verticalLayout_8 = QVBoxLayout(self.dockWidgetContents_2)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, -1)
        self.monitoring_content = QVBoxLayout()
        self.monitoring_content.setObjectName(u"monitoring_content")

        self.verticalLayout_8.addLayout(self.monitoring_content)

        self.monitor_searchbar = QLineEdit(self.dockWidgetContents_2)
        self.monitor_searchbar.setObjectName(u"monitor_searchbar")

        self.verticalLayout_8.addWidget(self.monitor_searchbar)

        self.dockWidget_2.setWidget(self.dockWidgetContents_2)
        BatchCreator_MainWindow.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidget_2)

        self.retranslateUi(BatchCreator_MainWindow)

        QMetaObject.connectSlotsByName(BatchCreator_MainWindow)
    # setupUi

    def retranslateUi(self, BatchCreator_MainWindow):
        BatchCreator_MainWindow.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"MainWindow", None))
        self.label.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Editor", None))
        self.label_editor_placeholder.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Please, open a file for editing", None))
        self.kv3_QplainTextEdit.setPlainText("")
        self.kv3_QplainTextEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"Content", None))
        self.viewport_searchbar.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"Search in viewport...", None))
        self.viewport_search_label.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Found: 0", None))
        self.viewport_search_previous_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Previous", None))
        self.viewport_search_next_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Next", None))
        self.label_2.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Replacements", None))
#if QT_CONFIG(tooltip)
        self.new_replacement_button.setToolTip(QCoreApplication.translate("BatchCreator_MainWindow", u"<html><head/><body><p>Creates a new replacement</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.new_replacement_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"New", None))
        self.dockWidget.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Explorer", None))
        self.file_groupbox.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"File", None))
        self.open_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Open", None))
#if QT_CONFIG(tooltip)
        self.save_button.setToolTip(QCoreApplication.translate("BatchCreator_MainWindow", u"<html><head/><body><p>Sacing curent file (Ctrl + S)</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.save_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Save", None))
#if QT_CONFIG(shortcut)
        self.save_button.setShortcut(QCoreApplication.translate("BatchCreator_MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
#if QT_CONFIG(tooltip)
        self.create_file.setToolTip(QCoreApplication.translate("BatchCreator_MainWindow", u"<html><head/><body><p>Creaating new file according to selected folder.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.create_file.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Create", None))
        self.process_groupbox.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Process", None))
#if QT_CONFIG(tooltip)
        self.process_options_button.setToolTip(QCoreApplication.translate("BatchCreator_MainWindow", u"<html><head/><body><p>Opens a window with process options</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.process_options_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Options", None))
#if QT_CONFIG(tooltip)
        self.return_button.setToolTip(QCoreApplication.translate("BatchCreator_MainWindow", u"<html><head/><body><p>Deletes file that were generated by process. Expection is reference</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.return_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Return", None))
#if QT_CONFIG(tooltip)
        self.process_all_button.setToolTip(QCoreApplication.translate("BatchCreator_MainWindow", u"<html><head/><body><p>Generates files depending on the process options.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.process_all_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Process", None))
        self.extension_lineEdit.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"File extension (vmdl, vmat etc).", None))
        self.referencing_groupbox.setTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Referencing", None))
#if QT_CONFIG(tooltip)
        self.select_reference_button.setToolTip(QCoreApplication.translate("BatchCreator_MainWindow", u"<html><head/><body><p>Select reference file, the reference file loads in the content field. To reload referenced file click Reload button.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.select_reference_button.setText(QCoreApplication.translate("BatchCreator_MainWindow", u"Select", None))
        self.dockWidget_2.setWindowTitle(QCoreApplication.translate("BatchCreator_MainWindow", u"Config Inspector", None))
        self.monitor_searchbar.setPlaceholderText(QCoreApplication.translate("BatchCreator_MainWindow", u"Filter...", None))
    # retranslateUi

