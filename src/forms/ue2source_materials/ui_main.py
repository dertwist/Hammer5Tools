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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_UE2SourceMaterialsWidget(object):
    def setupUi(self, UE2SourceMaterialsWidget):
        if not UE2SourceMaterialsWidget.objectName():
            UE2SourceMaterialsWidget.setObjectName(u"UE2SourceMaterialsWidget")
        UE2SourceMaterialsWidget.resize(800, 600)
        self.verticalLayout = QVBoxLayout(UE2SourceMaterialsWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox = QGroupBox(UE2SourceMaterialsWidget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout = QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.input_folder_edit = QLineEdit(self.groupBox)
        self.input_folder_edit.setObjectName(u"input_folder_edit")

        self.gridLayout.addWidget(self.input_folder_edit, 0, 1, 1, 1)

        self.browse_input_button = QPushButton(self.groupBox)
        self.browse_input_button.setObjectName(u"browse_input_button")

        self.gridLayout.addWidget(self.browse_input_button, 0, 2, 1, 1)

        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.output_folder_edit = QLineEdit(self.groupBox)
        self.output_folder_edit.setObjectName(u"output_folder_edit")

        self.gridLayout.addWidget(self.output_folder_edit, 1, 1, 1, 1)

        self.browse_output_button = QPushButton(self.groupBox)
        self.browse_output_button.setObjectName(u"browse_output_button")

        self.gridLayout.addWidget(self.browse_output_button, 1, 2, 1, 1)

        self.verticalSpacer_paths = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer_paths, 3, 1, 1, 1)


        self.verticalLayout.addWidget(self.groupBox)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.scan_button = QPushButton(UE2SourceMaterialsWidget)
        self.scan_button.setObjectName(u"scan_button")

        self.horizontalLayout.addWidget(self.scan_button)

        self.convert_button = QPushButton(UE2SourceMaterialsWidget)
        self.convert_button.setObjectName(u"convert_button")
        self.convert_button.setEnabled(False)

        self.horizontalLayout.addWidget(self.convert_button)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.clear_log_button = QPushButton(UE2SourceMaterialsWidget)
        self.clear_log_button.setObjectName(u"clear_log_button")

        self.horizontalLayout.addWidget(self.clear_log_button)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.splitter = QSplitter(UE2SourceMaterialsWidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.group_list = QListWidget(self.splitter)
        self.group_list.setObjectName(u"group_list")
        self.group_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.splitter.addWidget(self.group_list)
        self.log_edit = QTextEdit(self.splitter)
        self.log_edit.setObjectName(u"log_edit")
        self.log_edit.setReadOnly(True)
        self.splitter.addWidget(self.log_edit)

        self.verticalLayout.addWidget(self.splitter)

        self.progress_bar = QProgressBar(UE2SourceMaterialsWidget)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.verticalLayout.addWidget(self.progress_bar)


        self.retranslateUi(UE2SourceMaterialsWidget)

        QMetaObject.connectSlotsByName(UE2SourceMaterialsWidget)
    # setupUi

    def retranslateUi(self, UE2SourceMaterialsWidget):
        UE2SourceMaterialsWidget.setWindowTitle(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Material Importer (UE \u2192 Source 2)", None))
        self.groupBox.setTitle(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Paths", None))
        self.label.setText(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Input folder (UE PNGs):", None))
        self.browse_input_button.setText(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Browse", None))
        self.label_2.setText(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Output folder (TGA/VMAT):", None))
        self.browse_output_button.setText(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Browse", None))
        self.scan_button.setText(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Scan Folder", None))
        self.convert_button.setText(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Convert Selected", None))
        self.clear_log_button.setText(QCoreApplication.translate("UE2SourceMaterialsWidget", u"Clear Log", None))
    # retranslateUi

