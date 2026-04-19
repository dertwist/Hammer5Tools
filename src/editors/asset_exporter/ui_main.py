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
from PySide6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QHeaderView,
    QLineEdit, QProgressBar, QPushButton, QRadioButton,
    QSizePolicy, QTreeView, QVBoxLayout, QWidget)

class Ui_AssetExporterWidget(object):
    def setupUi(self, AssetExporterWidget):
        if not AssetExporterWidget.objectName():
            AssetExporterWidget.setObjectName(u"AssetExporterWidget")
        AssetExporterWidget.resize(800, 600)
        self.horizontalLayout = QHBoxLayout(AssetExporterWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.source_tree = QTreeView(AssetExporterWidget)
        self.source_tree.setObjectName(u"source_tree")

        self.horizontalLayout.addWidget(self.source_tree)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.btn_resolve = QPushButton(AssetExporterWidget)
        self.btn_resolve.setObjectName(u"btn_resolve")

        self.verticalLayout.addWidget(self.btn_resolve)

        self.deps_list = QTreeView(AssetExporterWidget)
        self.deps_list.setObjectName(u"deps_list")

        self.verticalLayout.addWidget(self.deps_list)

        self.groupBox = QGroupBox(AssetExporterWidget)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.radio_preserve = QRadioButton(self.groupBox)
        self.radio_preserve.setObjectName(u"radio_preserve")
        self.radio_preserve.setChecked(True)

        self.verticalLayout_2.addWidget(self.radio_preserve)

        self.radio_thirdparty = QRadioButton(self.groupBox)
        self.radio_thirdparty.setObjectName(u"radio_thirdparty")

        self.verticalLayout_2.addWidget(self.radio_thirdparty)

        self.edit_addon_name = QLineEdit(self.groupBox)
        self.edit_addon_name.setObjectName(u"edit_addon_name")

        self.verticalLayout_2.addWidget(self.edit_addon_name)

        self.edit_asset_stem = QLineEdit(self.groupBox)
        self.edit_asset_stem.setObjectName(u"edit_asset_stem")

        self.verticalLayout_2.addWidget(self.edit_asset_stem)


        self.verticalLayout.addWidget(self.groupBox)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.edit_output_dir = QLineEdit(AssetExporterWidget)
        self.edit_output_dir.setObjectName(u"edit_output_dir")

        self.horizontalLayout_2.addWidget(self.edit_output_dir)

        self.btn_browse = QPushButton(AssetExporterWidget)
        self.btn_browse.setObjectName(u"btn_browse")

        self.horizontalLayout_2.addWidget(self.btn_browse)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.progress_bar = QProgressBar(AssetExporterWidget)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.verticalLayout.addWidget(self.progress_bar)

        self.btn_export = QPushButton(AssetExporterWidget)
        self.btn_export.setObjectName(u"btn_export")

        self.verticalLayout.addWidget(self.btn_export)


        self.horizontalLayout.addLayout(self.verticalLayout)


        self.retranslateUi(AssetExporterWidget)

        QMetaObject.connectSlotsByName(AssetExporterWidget)
    # setupUi

    def retranslateUi(self, AssetExporterWidget):
        AssetExporterWidget.setWindowTitle(QCoreApplication.translate("AssetExporterWidget", u"Asset Exporter", None))
        self.btn_resolve.setText(QCoreApplication.translate("AssetExporterWidget", u"Resolve Dependencies", None))
        self.groupBox.setTitle(QCoreApplication.translate("AssetExporterWidget", u"Export Options", None))
        self.radio_preserve.setText(QCoreApplication.translate("AssetExporterWidget", u"Preserve Addon Structure", None))
        self.radio_thirdparty.setText(QCoreApplication.translate("AssetExporterWidget", u"Third-Party Package Layout (folder_thirdparty/...)", None))
        self.edit_addon_name.setPlaceholderText(QCoreApplication.translate("AssetExporterWidget", u"Addon Name", None))
        self.edit_asset_stem.setPlaceholderText(QCoreApplication.translate("AssetExporterWidget", u"Asset Stem", None))
        self.edit_output_dir.setPlaceholderText(QCoreApplication.translate("AssetExporterWidget", u"Output Directory", None))
        self.btn_browse.setText(QCoreApplication.translate("AssetExporterWidget", u"Browse...", None))
        self.btn_export.setText(QCoreApplication.translate("AssetExporterWidget", u"Export", None))
    # retranslateUi

