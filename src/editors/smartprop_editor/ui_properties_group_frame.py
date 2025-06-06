# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'properties_group_frame.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout,
    QLabel, QLayout, QLineEdit, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)
import src.resources_rc as resources_rc

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(668, 285)
        Form.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        Form.setStyleSheet(u"background-color: #1C1C1C;")
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(16777215, 24))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"image: url(:/icons/more_vert.png);\n"
"padding-left: 3px;\n"
"padding-right: 3px;\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"background-color: #242424;")

        self.horizontalLayout.addWidget(self.label)

        self.show_child = QCheckBox(self.frame)
        self.show_child.setObjectName(u"show_child")
        self.show_child.setStyleSheet(u"QCheckBox::indicator:checked {\n"
"    \n"
"image: url(://icons/arrow_drop_down.png);\n"
"	height:14px;\n"
"	width:14px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/arrow_drop_right.png);\n"
"	height:14px;\n"
"	width:14px;\n"
"}\n"
"QCheckBox {\n"
"    font: 700 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:14px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:4px;\n"
"    color: #E3E3E3;\n"
"background-color: #242424;\n"
"    padding-left: 4px;\n"
"}\n"
"QCheckBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"QCheckBox{\n"
"	padding-left:5px;\n"
"	border-left: 0px solid black;\n"
"border-right: 0px solid black;\n"
"border-top: 0px solid black;\n"
"}")
        self.show_child.setChecked(True)
        self.show_child.setTristate(False)

        self.horizontalLayout.addWidget(self.show_child)

        self.add_button = QPushButton(self.frame)
        self.add_button.setObjectName(u"add_button")
        self.add_button.setStyleSheet(u"\n"
"QPushButton {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	border-top:0px;\n"
"border-left:0px;\n"
"border-right:0px;\n"
"    height:14px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:4px;\n"
"	background-color: #242424;\n"
"    padding-left: 8px;\n"
"	padding-right: 8px;\n"
"	color: #E3E3E3;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"\n"
"QPushButton:pressed {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	border-top:0px;\n"
"border-left:0px;\n"
"border-right:0px;\n"
"    height:14px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:4px;\n"
"	background-color: #242424;\n"
"    padding-left: 8px;\n"
"	padding-right: 8px;\n"
"	color: #E3E3E3;\n"
"}")
        icon = QIcon()
        icon.addFile(u":/icons/add_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.add_button.setIcon(icon)

        self.horizontalLayout.addWidget(self.add_button)

        self.property_class = QLineEdit(self.frame)
        self.property_class.setObjectName(u"property_class")
        self.property_class.setStyleSheet(u"QLineEdit {\n"
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
        self.property_class.setInputMethodHints(Qt.InputMethodHint.ImhLatinOnly|Qt.InputMethodHint.ImhLowercaseOnly)
        self.property_class.setMaxLength(32)
        self.property_class.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.property_class.setReadOnly(True)

        self.horizontalLayout.addWidget(self.property_class)

        self.paste_button = QPushButton(self.frame)
        self.paste_button.setObjectName(u"paste_button")
        self.paste_button.setStyleSheet(u"\n"
"QPushButton {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	border-top:0px;\n"
"border-left:0px;\n"
"border-right:0px;\n"
"    height:14px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:4px;\n"
"	background-color: #242424;\n"
"    padding-left: 8px;\n"
"	padding-right: 8px;\n"
"	color: #E3E3E3;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"\n"
"QPushButton:pressed {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	border-top:0px;\n"
"border-left:0px;\n"
"border-right:0px;\n"
"    height:14px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:4px;\n"
"	background-color: #242424;\n"
"    padding-left: 8px;\n"
"	padding-right: 8px;\n"
"	color: #E3E3E3;\n"
"}")
        icon1 = QIcon()
        icon1.addFile(u":/icons/content_paste_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.paste_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.paste_button)


        self.verticalLayout.addWidget(self.frame)

        self.frame_layout = QFrame(Form)
        self.frame_layout.setObjectName(u"frame_layout")
        self.frame_layout.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.frame_layout.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_layout.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_layout)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(12, 0, 0, 0)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setObjectName(u"layout")
        self.layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.layout.setContentsMargins(-1, 6, -1, 6)
        self.frame_2 = QFrame(self.frame_layout)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setStyleSheet(u"padding:0px;")
        self.frame_2.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setSpacing(4)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 4, 0, 0)

        self.layout.addWidget(self.frame_2)


        self.verticalLayout_2.addLayout(self.layout)


        self.verticalLayout.addWidget(self.frame_layout)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label.setText("")
#if QT_CONFIG(tooltip)
        self.show_child.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:8pt; font-weight:400;\">Show child</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.show_child.setText("")
        self.add_button.setText(QCoreApplication.translate("Form", u"Create new", None))
#if QT_CONFIG(tooltip)
        self.property_class.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.property_class.setText(QCoreApplication.translate("Form", u"Modifiers", None))
        self.paste_button.setText(QCoreApplication.translate("Form", u"Paste", None))
    # retranslateUi

