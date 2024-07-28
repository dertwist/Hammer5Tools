# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'loading_editor_image_frame_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget)
import rc_resources

class Ui_loading_editor_image_frame_widget_ui(object):
    def setupUi(self, loading_editor_image_frame_widget_ui):
        if not loading_editor_image_frame_widget_ui.objectName():
            loading_editor_image_frame_widget_ui.setObjectName(u"loading_editor_image_frame_widget_ui")
        loading_editor_image_frame_widget_ui.resize(210, 171)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(loading_editor_image_frame_widget_ui.sizePolicy().hasHeightForWidth())
        loading_editor_image_frame_widget_ui.setSizePolicy(sizePolicy)
        loading_editor_image_frame_widget_ui.setMaximumSize(QSize(210, 171))
        loading_editor_image_frame_widget_ui.setStyleSheet(u"border: 2px solid rgb(176, 176, 176);\n"
"border-radius: 2px;\n"
"border: 2px solid;\n"
"border-color: rgba(80, 80, 80, 255);\n"
"")
        self.verticalLayout = QVBoxLayout(loading_editor_image_frame_widget_ui)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.image_name = QLabel(loading_editor_image_frame_widget_ui)
        self.image_name.setObjectName(u"image_name")
        self.image_name.setMinimumSize(QSize(0, 16))
        self.image_name.setMaximumSize(QSize(16777215, 24))
        self.image_name.setStyleSheet(u"border-radius: 2px;\n"
"border: 2px solid;\n"
"border-color: rgba(80, 80, 80, 255);\n"
"")
        self.image_name.setAlignment(Qt.AlignCenter)

        self.horizontalLayout.addWidget(self.image_name)

        self.close_image_button = QToolButton(loading_editor_image_frame_widget_ui)
        self.close_image_button.setObjectName(u"close_image_button")
        self.close_image_button.setMaximumSize(QSize(16777215, 24))
        self.close_image_button.setStyleSheet(u"border-radius: 2px;\n"
"border: 2px solid;\n"
"border-color: rgba(80, 80, 80, 255);\n"
"")
        icon = QIcon()
        icon.addFile(u":/icons/close_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.close_image_button.setIcon(icon)

        self.horizontalLayout.addWidget(self.close_image_button)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.image_src_frame = QLabel(loading_editor_image_frame_widget_ui)
        self.image_src_frame.setObjectName(u"image_src_frame")
        self.image_src_frame.setMinimumSize(QSize(0, 140))
        self.image_src_frame.setStyleSheet(u"border-radius: 2px;\n"
"border: 2px solid;\n"
"border-color: rgba(80, 80, 80, 255);\n"
"")

        self.verticalLayout.addWidget(self.image_src_frame)


        self.retranslateUi(loading_editor_image_frame_widget_ui)

        QMetaObject.connectSlotsByName(loading_editor_image_frame_widget_ui)
    # setupUi

    def retranslateUi(self, loading_editor_image_frame_widget_ui):
        loading_editor_image_frame_widget_ui.setWindowTitle(QCoreApplication.translate("loading_editor_image_frame_widget_ui", u"Form", None))
        self.image_name.setText(QCoreApplication.translate("loading_editor_image_frame_widget_ui", u"TextLabel", None))
        self.close_image_button.setText(QCoreApplication.translate("loading_editor_image_frame_widget_ui", u"...", None))
        self.image_src_frame.setText(QCoreApplication.translate("loading_editor_image_frame_widget_ui", u"TextLabel", None))
    # retranslateUi

