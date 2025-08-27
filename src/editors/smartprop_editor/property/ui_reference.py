# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'reference.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QLayout, QLineEdit, QSizePolicy, QSpacerItem,
    QToolButton, QVBoxLayout, QWidget)

import resources_rc

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.resize(790, 32)
        Widget.setMinimumSize(QSize(0, 0))
        Widget.setMaximumSize(QSize(16777215, 32))
        Widget.setStyleSheet(u".QWidget {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"\tborder-top: 0px;\n"
"    border-color: rgba(50, 50, 50, 255);\n"
"    padding: 8px;\n"
"    padding-left: 6px;\n"
"    padding-right: 6px;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
".QWidget::hover {\n"
"}\n"
".QWidget::selected {\n"
"    background-color: #414956;\n"
"}")
        self.verticalLayout = QVBoxLayout(Widget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(Widget)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(0, 32))
        self.frame.setMaximumSize(QSize(16777215, 32))
        self.frame.setStyleSheet(u".QFrame {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"\tborder-top: 0px;\n"
"    border-color: rgba(50, 50, 50, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
".QFrame::hover {\n"
"}\n"
".QFrame::selected {\n"
"    background-color: #414956;\n"
"}")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.frame.setLineWidth(0)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setSpacing(16)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.layout = QHBoxLayout()
        self.layout.setObjectName(u"layout")
        self.layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.property_class = QLabel(self.frame)
        self.property_class.setObjectName(u"property_class")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.property_class.sizePolicy().hasHeightForWidth())
        self.property_class.setSizePolicy(sizePolicy)
        self.property_class.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"padding-right: 16px;\n"
"\n"
"color: rgb(255, 189, 190);")

        self.layout.addWidget(self.property_class)

        self.reference_id = QLineEdit(self.frame)
        self.reference_id.setObjectName(u"reference_id")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.reference_id.sizePolicy().hasHeightForWidth())
        self.reference_id.setSizePolicy(sizePolicy1)
        self.reference_id.setMaximumSize(QSize(72, 16777215))
        self.reference_id.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.reference_id.setStyleSheet(u"QLineEdit {\n"
"    font-size: 8pt;\n"
"    font-family: \"Segoe UI\";\n"
"    border-top: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"    border-bottom: 2px solid rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #242424;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"\n"
"QLineEdit::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")
        self.reference_id.setInputMethodHints(Qt.InputMethodHint.ImhLatinOnly|Qt.InputMethodHint.ImhLowercaseOnly)
        self.reference_id.setMaxLength(32)
        self.reference_id.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reference_id.setReadOnly(True)

        self.layout.addWidget(self.reference_id)

        self.reference_clear = QToolButton(self.frame)
        self.reference_clear.setObjectName(u"reference_clear")
        self.reference_clear.setEnabled(True)
        self.reference_clear.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.reference_clear.setStyleSheet(u"QToolButton {\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"border-left: None;\n"
"border-top: None;\n"
"border-right: None;\n"
"    padding: 2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #242424;\n"
"height:16px;\n"
"width:16px;\n"
"}\n"
"QToolButton:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")
        icon = QIcon()
        icon.addFile(u":/icons/cancel_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.reference_clear.setIcon(icon)
        self.reference_clear.setIconSize(QSize(24, 24))

        self.layout.addWidget(self.reference_clear)

        self.reference_search = QToolButton(self.frame)
        self.reference_search.setObjectName(u"reference_search")
        self.reference_search.setEnabled(True)
        self.reference_search.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.reference_search.setStyleSheet(u"QToolButton {\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"border-left: None;\n"
"border-top: None;\n"
"border-right: None;\n"
"    padding: 2px;\n"
"    color: #E3E3E3;\n"
"    background-color: #242424;\n"
"height:16px;\n"
"width:16px;\n"
"}\n"
"QToolButton:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")
        icon1 = QIcon()
        icon1.addFile(u":/icons/search_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.reference_search.setIcon(icon1)
        self.reference_search.setIconSize(QSize(24, 24))

        self.layout.addWidget(self.reference_search)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.layout.addItem(self.horizontalSpacer)


        self.horizontalLayout_2.addLayout(self.layout)


        self.verticalLayout.addWidget(self.frame)


        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Form", None))
        self.property_class.setText(QCoreApplication.translate("Widget", u"Reference", None))
        self.reference_id.setPlaceholderText(QCoreApplication.translate("Widget", u"ID", None))
        self.reference_clear.setText("")
        self.reference_search.setText("")
    # retranslateUi