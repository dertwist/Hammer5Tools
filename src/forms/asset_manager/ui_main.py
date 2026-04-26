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
from PySide6.QtWidgets import (QApplication, QHeaderView, QPushButton, QSizePolicy,
    QSplitter, QTextEdit, QTreeView, QVBoxLayout,
    QWidget)

class Ui_AssetManagerWidget(object):
    def setupUi(self, AssetManagerWidget):
        if not AssetManagerWidget.objectName():
            AssetManagerWidget.setObjectName(u"AssetManagerWidget")
        AssetManagerWidget.resize(800, 600)
        self.verticalLayout = QVBoxLayout(AssetManagerWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.splitter = QSplitter(AssetManagerWidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Horizontal)
        self.source_tree = QTreeView(self.splitter)
        self.source_tree.setObjectName(u"source_tree")
        self.splitter.addWidget(self.source_tree)
        self.dest_tree = QTreeView(self.splitter)
        self.dest_tree.setObjectName(u"dest_tree")
        self.splitter.addWidget(self.dest_tree)

        self.verticalLayout.addWidget(self.splitter)

        self.btn_preview = QPushButton(AssetManagerWidget)
        self.btn_preview.setObjectName(u"btn_preview")

        self.verticalLayout.addWidget(self.btn_preview)

        self.btn_apply = QPushButton(AssetManagerWidget)
        self.btn_apply.setObjectName(u"btn_apply")

        self.verticalLayout.addWidget(self.btn_apply)

        self.btn_undo = QPushButton(AssetManagerWidget)
        self.btn_undo.setObjectName(u"btn_undo")

        self.verticalLayout.addWidget(self.btn_undo)

        self.log_output = QTextEdit(AssetManagerWidget)
        self.log_output.setObjectName(u"log_output")

        self.verticalLayout.addWidget(self.log_output)


        self.retranslateUi(AssetManagerWidget)

        QMetaObject.connectSlotsByName(AssetManagerWidget)
    # setupUi

    def retranslateUi(self, AssetManagerWidget):
        AssetManagerWidget.setWindowTitle(QCoreApplication.translate("AssetManagerWidget", u"Asset Manager", None))
        self.btn_preview.setText(QCoreApplication.translate("AssetManagerWidget", u"Preview Move", None))
        self.btn_apply.setText(QCoreApplication.translate("AssetManagerWidget", u"Apply", None))
        self.btn_undo.setText(QCoreApplication.translate("AssetManagerWidget", u"Undo Last Move", None))
    # retranslateUi

