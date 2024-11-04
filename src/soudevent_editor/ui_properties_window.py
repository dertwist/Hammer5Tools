# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'properties_window.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGroupBox, QLabel,
    QMainWindow, QPlainTextEdit, QScrollArea, QSizePolicy,
    QSpacerItem, QSplitter, QVBoxLayout, QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1490, 941)
        MainWindow.setStyleSheet(u"background-color: #1C1C1C;")
        self.actionCreateNewsmartprop = QAction(MainWindow)
        self.actionCreateNewsmartprop.setObjectName(u"actionCreateNewsmartprop")
        icon = QIcon()
        icon.addFile(u":/valve_common/icons/tools/common/new.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionCreateNewsmartprop.setIcon(icon)
        self.actionCreateNewsmartprop.setMenuRole(QAction.MenuRole.NoRole)
        self.actionOpen_from_Explorer = QAction(MainWindow)
        self.actionOpen_from_Explorer.setObjectName(u"actionOpen_from_Explorer")
        icon1 = QIcon()
        icon1.addFile(u":/valve_common/icons/tools/common/open.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionOpen_from_Explorer.setIcon(icon1)
        self.actionSave_as = QAction(MainWindow)
        self.actionSave_as.setObjectName(u"actionSave_as")
        icon2 = QIcon()
        icon2.addFile(u":/valve_common/icons/tools/common/save_all.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSave_as.setIcon(icon2)
        self.actionSave_current_file = QAction(MainWindow)
        self.actionSave_current_file.setObjectName(u"actionSave_current_file")
        icon3 = QIcon()
        icon3.addFile(u":/valve_common/icons/tools/common/save.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSave_current_file.setIcon(icon3)
        self.actionRecompile_file = QAction(MainWindow)
        self.actionRecompile_file.setObjectName(u"actionRecompile_file")
        icon4 = QIcon()
        icon4.addFile(u":/valve_common/icons/tools/common/options_activated.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionRecompile_file.setIcon(icon4)
        self.actionRecompile_all_in_addon = QAction(MainWindow)
        self.actionRecompile_all_in_addon.setObjectName(u"actionRecompile_all_in_addon")
        self.actionRecompile_all_in_addon.setIcon(icon4)
        self.actionConvert_all_vsmart_file_to_vdata = QAction(MainWindow)
        self.actionConvert_all_vsmart_file_to_vdata.setObjectName(u"actionConvert_all_vsmart_file_to_vdata")
        icon5 = QIcon()
        icon5.addFile(u":/valve_common/icons/tools/common/move_to_changelist.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionConvert_all_vsmart_file_to_vdata.setIcon(icon5)
        self.actionFormat_serttings = QAction(MainWindow)
        self.actionFormat_serttings.setObjectName(u"actionFormat_serttings")
        icon6 = QIcon()
        icon6.addFile(u":/valve_common/icons/tools/common/setting.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionFormat_serttings.setIcon(icon6)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_5 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(6)
        self.scrollArea = QScrollArea(self.splitter)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scrollArea.setStyleSheet(u"QScrollArea {\n"
"    border: 0px solid black;\n"
"}")
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 1490, 591))
        self.scrollAreaWidgetContents.setStyleSheet(u"QWidget: {\n"
"	border: 0px;\n"
"}")
        self.verticalLayout_17 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_17.setSpacing(0)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.verticalLayout_17.setContentsMargins(0, 0, 0, 0)
        self.properties_layout = QVBoxLayout()
        self.properties_layout.setObjectName(u"properties_layout")
        self.properties_placeholder = QLabel(self.scrollAreaWidgetContents)
        self.properties_placeholder.setObjectName(u"properties_placeholder")
        self.properties_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.properties_layout.addWidget(self.properties_placeholder)

        self.properties_spacer = QFrame(self.scrollAreaWidgetContents)
        self.properties_spacer.setObjectName(u"properties_spacer")
        self.properties_spacer.setStyleSheet(u"color:#bbb;\n"
"border: none;")
        self.properties_spacer.setFrameShape(QFrame.Shape.StyledPanel)
        self.properties_spacer.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.properties_spacer)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalSpacer = QSpacerItem(20, 655, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)


        self.properties_layout.addWidget(self.properties_spacer)


        self.verticalLayout_17.addLayout(self.properties_layout)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.splitter.addWidget(self.scrollArea)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.groupBox = QGroupBox(self.layoutWidget)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(6, 6, 6, 6)
        self.plainTextEdit = QPlainTextEdit(self.groupBox)
        self.plainTextEdit.setObjectName(u"plainTextEdit")

        self.verticalLayout_2.addWidget(self.plainTextEdit)


        self.verticalLayout.addWidget(self.groupBox)

        self.splitter.addWidget(self.layoutWidget)

        self.verticalLayout_5.addWidget(self.splitter)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionCreateNewsmartprop.setText(QCoreApplication.translate("MainWindow", u"CreateNewsmartprop", None))
        self.actionOpen_from_Explorer.setText(QCoreApplication.translate("MainWindow", u"Open as", None))
        self.actionSave_as.setText(QCoreApplication.translate("MainWindow", u"Save as", None))
        self.actionSave_current_file.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.actionRecompile_file.setText(QCoreApplication.translate("MainWindow", u"Recompile file", None))
        self.actionRecompile_all_in_addon.setText(QCoreApplication.translate("MainWindow", u"Recompile all in addon", None))
        self.actionConvert_all_vsmart_file_to_vdata.setText(QCoreApplication.translate("MainWindow", u"Convert all vsmart file to vdata", None))
#if QT_CONFIG(tooltip)
        self.actionConvert_all_vsmart_file_to_vdata.setToolTip(QCoreApplication.translate("MainWindow", u"Convert all to data", None))
#endif // QT_CONFIG(tooltip)
        self.actionFormat_serttings.setText(QCoreApplication.translate("MainWindow", u"Format serttings", None))
        self.properties_placeholder.setText(QCoreApplication.translate("MainWindow", u"Select event in the hierarchy", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"Comment", None))
    # retranslateUi

