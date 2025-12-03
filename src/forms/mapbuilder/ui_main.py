# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QSplitter, QTabWidget, QVBoxLayout, QWidget)
import resources_rc

class Ui_mapbuilder_dialog(object):
    def setupUi(self, mapbuilder_dialog):
        if not mapbuilder_dialog.objectName():
            mapbuilder_dialog.setObjectName(u"mapbuilder_dialog")
        mapbuilder_dialog.resize(1031, 830)
        mapbuilder_dialog.setMinimumSize(QSize(0, 0))
        mapbuilder_dialog.setMaximumSize(QSize(16777215, 16777215))
        icon = QIcon()
        icon.addFile(u":/icons/settings_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        mapbuilder_dialog.setWindowIcon(icon)
        mapbuilder_dialog.setModal(False)
        self.verticalLayout_6 = QVBoxLayout(mapbuilder_dialog)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(mapbuilder_dialog)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout_2 = QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.build_presets = QScrollArea(self.layoutWidget)
        self.build_presets.setObjectName(u"build_presets")
        self.build_presets.setMaximumSize(QSize(16777215, 90))
        self.build_presets.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.build_presets.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 648, 88))
        self.horizontalLayout_6 = QHBoxLayout(self.scrollAreaWidgetContents)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.pushButton_6 = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_6.setObjectName(u"pushButton_6")
        self.pushButton_6.setMinimumSize(QSize(64, 64))
        self.pushButton_6.setMaximumSize(QSize(64, 64))
        self.pushButton_6.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.pushButton_6.setIconSize(QSize(16, 16))
        self.pushButton_6.setCheckable(False)
        self.pushButton_6.setAutoRepeat(False)
        self.pushButton_6.setAutoExclusive(False)
        self.pushButton_6.setAutoDefault(True)
        self.pushButton_6.setFlat(False)

        self.horizontalLayout_6.addWidget(self.pushButton_6)

        self.pushButton_5 = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_5.setObjectName(u"pushButton_5")
        self.pushButton_5.setMinimumSize(QSize(64, 64))
        self.pushButton_5.setMaximumSize(QSize(64, 64))
        self.pushButton_5.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.pushButton_5.setIconSize(QSize(16, 16))
        self.pushButton_5.setCheckable(False)
        self.pushButton_5.setAutoRepeat(False)
        self.pushButton_5.setAutoExclusive(False)
        self.pushButton_5.setAutoDefault(True)
        self.pushButton_5.setFlat(False)

        self.horizontalLayout_6.addWidget(self.pushButton_5)

        self.pushButton_7 = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_7.setObjectName(u"pushButton_7")
        self.pushButton_7.setMinimumSize(QSize(64, 64))
        self.pushButton_7.setMaximumSize(QSize(64, 64))
        self.pushButton_7.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.pushButton_7.setIconSize(QSize(16, 16))
        self.pushButton_7.setCheckable(False)
        self.pushButton_7.setAutoRepeat(False)
        self.pushButton_7.setAutoExclusive(False)
        self.pushButton_7.setAutoDefault(True)
        self.pushButton_7.setFlat(False)

        self.horizontalLayout_6.addWidget(self.pushButton_7)

        self.pushButton_8 = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_8.setObjectName(u"pushButton_8")
        self.pushButton_8.setMinimumSize(QSize(64, 64))
        self.pushButton_8.setMaximumSize(QSize(64, 64))
        self.pushButton_8.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.pushButton_8.setIconSize(QSize(16, 16))
        self.pushButton_8.setCheckable(False)
        self.pushButton_8.setAutoRepeat(False)
        self.pushButton_8.setAutoExclusive(False)
        self.pushButton_8.setAutoDefault(True)
        self.pushButton_8.setFlat(False)

        self.horizontalLayout_6.addWidget(self.pushButton_8)

        self.pushButton_12 = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_12.setObjectName(u"pushButton_12")
        self.pushButton_12.setMinimumSize(QSize(64, 64))
        self.pushButton_12.setMaximumSize(QSize(64, 64))
        self.pushButton_12.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.pushButton_12.setIconSize(QSize(16, 16))
        self.pushButton_12.setCheckable(False)
        self.pushButton_12.setAutoRepeat(False)
        self.pushButton_12.setAutoExclusive(False)
        self.pushButton_12.setAutoDefault(True)
        self.pushButton_12.setFlat(False)

        self.horizontalLayout_6.addWidget(self.pushButton_12)

        self.pushButton_11 = QPushButton(self.scrollAreaWidgetContents)
        self.pushButton_11.setObjectName(u"pushButton_11")
        self.pushButton_11.setMinimumSize(QSize(64, 64))
        self.pushButton_11.setMaximumSize(QSize(64, 64))
        self.pushButton_11.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.pushButton_11.setIconSize(QSize(16, 16))
        self.pushButton_11.setCheckable(False)
        self.pushButton_11.setAutoRepeat(False)
        self.pushButton_11.setAutoExclusive(False)
        self.pushButton_11.setAutoDefault(True)
        self.pushButton_11.setFlat(False)

        self.horizontalLayout_6.addWidget(self.pushButton_11)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer)

        self.build_presets.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.build_presets)

        self.build_settings_area = QScrollArea(self.layoutWidget)
        self.build_settings_area.setObjectName(u"build_settings_area")
        self.build_settings_area.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName(u"scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 648, 676))
        self.verticalLayout = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, -1)
        self.build_settings_content = QVBoxLayout()
        self.build_settings_content.setObjectName(u"build_settings_content")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.build_settings_content.addItem(self.verticalSpacer)


        self.verticalLayout.addLayout(self.build_settings_content)

        self.build_settings_area.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_2.addWidget(self.build_settings_area)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.build_button = QPushButton(self.layoutWidget)
        self.build_button.setObjectName(u"build_button")

        self.horizontalLayout_4.addWidget(self.build_button)

        self.run_button = QPushButton(self.layoutWidget)
        self.run_button.setObjectName(u"run_button")

        self.horizontalLayout_4.addWidget(self.run_button)

        self.abort_button = QPushButton(self.layoutWidget)
        self.abort_button.setObjectName(u"abort_button")

        self.horizontalLayout_4.addWidget(self.abort_button)


        self.verticalLayout_2.addLayout(self.horizontalLayout_4)

        self.last_build_stats_label = QLabel(self.layoutWidget)
        self.last_build_stats_label.setObjectName(u"last_build_stats_label")

        self.verticalLayout_2.addWidget(self.last_build_stats_label)

        self.splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.horizontalLayout_2 = QHBoxLayout(self.layoutWidget1)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(self.layoutWidget1)
        self.tabWidget.setObjectName(u"tabWidget")
        self.report = QWidget()
        self.report.setObjectName(u"report")
        self.verticalLayout_5 = QVBoxLayout(self.report)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(4, 4, 4, 0)
        self.report_widget = QListWidget(self.report)
        self.report_widget.setObjectName(u"report_widget")

        self.verticalLayout_5.addWidget(self.report_widget)

        self.frame_2 = QFrame(self.report)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.current_state_label = QLabel(self.frame_2)
        self.current_state_label.setObjectName(u"current_state_label")

        self.horizontalLayout_5.addWidget(self.current_state_label)

        self.current_state_progressbar = QProgressBar(self.frame_2)
        self.current_state_progressbar.setObjectName(u"current_state_progressbar")
        self.current_state_progressbar.setValue(24)

        self.horizontalLayout_5.addWidget(self.current_state_progressbar)


        self.verticalLayout_5.addWidget(self.frame_2)

        self.frame = QFrame(self.report)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.global_state_label = QLabel(self.frame)
        self.global_state_label.setObjectName(u"global_state_label")

        self.horizontalLayout.addWidget(self.global_state_label)

        self.global_state_progressbar = QProgressBar(self.frame)
        self.global_state_progressbar.setObjectName(u"global_state_progressbar")
        self.global_state_progressbar.setValue(24)

        self.horizontalLayout.addWidget(self.global_state_progressbar)


        self.verticalLayout_5.addWidget(self.frame)

        self.system_monitor = QFrame(self.report)
        self.system_monitor.setObjectName(u"system_monitor")
        self.system_monitor.setMinimumSize(QSize(0, 128))
        self.system_monitor.setMaximumSize(QSize(16777215, 128))
        self.system_monitor.setFrameShape(QFrame.Shape.StyledPanel)
        self.system_monitor.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_7 = QHBoxLayout(self.system_monitor)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_5.addWidget(self.system_monitor)

        self.tabWidget.addTab(self.report, "")
        self.output = QWidget()
        self.output.setObjectName(u"output")
        self.verticalLayout_3 = QVBoxLayout(self.output)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.output_list_widget = QListWidget(self.output)
        self.output_list_widget.setObjectName(u"output_list_widget")

        self.verticalLayout_3.addWidget(self.output_list_widget)

        self.tabWidget.addTab(self.output, "")
        self.logs = QWidget()
        self.logs.setObjectName(u"logs")
        self.verticalLayout_4 = QVBoxLayout(self.logs)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.logs_filelist = QListWidget(self.logs)
        self.logs_filelist.setObjectName(u"logs_filelist")

        self.verticalLayout_4.addWidget(self.logs_filelist)

        self.tabWidget.addTab(self.logs, "")

        self.horizontalLayout_2.addWidget(self.tabWidget)

        self.splitter.addWidget(self.layoutWidget1)

        self.verticalLayout_6.addWidget(self.splitter)


        self.retranslateUi(mapbuilder_dialog)

        self.pushButton_6.setDefault(False)
        self.pushButton_5.setDefault(False)
        self.pushButton_7.setDefault(False)
        self.pushButton_8.setDefault(False)
        self.pushButton_12.setDefault(False)
        self.pushButton_11.setDefault(False)
        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(mapbuilder_dialog)
    # setupUi

    def retranslateUi(self, mapbuilder_dialog):
        mapbuilder_dialog.setWindowTitle(QCoreApplication.translate("mapbuilder_dialog", u"Lanuch options", None))
        self.pushButton_6.setText(QCoreApplication.translate("mapbuilder_dialog", u"Full Compile", None))
        self.pushButton_5.setText(QCoreApplication.translate("mapbuilder_dialog", u"Full Compile", None))
        self.pushButton_7.setText(QCoreApplication.translate("mapbuilder_dialog", u"Full Compile", None))
        self.pushButton_8.setText(QCoreApplication.translate("mapbuilder_dialog", u"Full Compile", None))
        self.pushButton_12.setText(QCoreApplication.translate("mapbuilder_dialog", u"Full Compile", None))
        self.pushButton_11.setText(QCoreApplication.translate("mapbuilder_dialog", u"Full Compile", None))
        self.build_button.setText(QCoreApplication.translate("mapbuilder_dialog", u"Build", None))
        self.run_button.setText(QCoreApplication.translate("mapbuilder_dialog", u"Run (Skip Build)", None))
        self.abort_button.setText(QCoreApplication.translate("mapbuilder_dialog", u"Abort", None))
        self.last_build_stats_label.setText(QCoreApplication.translate("mapbuilder_dialog", u"Last Build time: 2h 15m", None))
        self.current_state_label.setText(QCoreApplication.translate("mapbuilder_dialog", u"Current progress (3m):", None))
        self.global_state_label.setText(QCoreApplication.translate("mapbuilder_dialog", u"Global progress (2h 14m):", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.report), QCoreApplication.translate("mapbuilder_dialog", u"Report", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.output), QCoreApplication.translate("mapbuilder_dialog", u"Output", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.logs), QCoreApplication.translate("mapbuilder_dialog", u"Logs", None))
    # retranslateUi

