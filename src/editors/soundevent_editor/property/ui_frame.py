# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'frame.ui'
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
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget)
import resources_rc

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(776, 346)
        Form.setMinimumSize(QSize(512, 0))
        Form.setMaximumSize(QSize(16666, 16777215))
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.header = QFrame(Form)
        self.header.setObjectName(u"header")
        self.header.setMinimumSize(QSize(0, 24))
        self.header.setMaximumSize(QSize(16777215, 24))
        self.header.setFrameShape(QFrame.Shape.StyledPanel)
        self.header.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.header)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.header)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setStyleSheet(u"image: url(:/icons/more_vert.png);\n"
"padding-left: 3px;\n"
"padding-right: 3px;\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"background-color: #242424;")

        self.horizontalLayout.addWidget(self.label_2)

        self.show_child = QCheckBox(self.header)
        self.show_child.setObjectName(u"show_child")
        self.show_child.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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

        self.frame_2 = QFrame(self.header)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMinimumSize(QSize(400, 0))
        self.frame_2.setMaximumSize(QSize(400, 16777215))
        self.frame_2.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gf = QToolButton(self.frame_2)
        self.gf.setObjectName(u"gf")
        self.gf.setEnabled(False)
        self.gf.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.gf.setStyleSheet(u"QToolButton {\n"
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
        icon.addFile(u":/icons/shapes_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.gf.setIcon(icon)
        self.gf.setIconSize(QSize(24, 24))

        self.horizontalLayout_2.addWidget(self.gf)

        self.property_class = QLineEdit(self.frame_2)
        self.property_class.setObjectName(u"property_class")
        self.property_class.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.property_class.setReadOnly(True)

        self.horizontalLayout_2.addWidget(self.property_class)


        self.horizontalLayout.addWidget(self.frame_2)

        self.element_id_display = QLineEdit(self.header)
        self.element_id_display.setObjectName(u"element_id_display")
        self.element_id_display.setEnabled(False)
        self.element_id_display.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.element_id_display.setStyleSheet(u"QLineEdit {\n"
"    font-size: 8pt;\n"
"    font-family: \"Segoe UI\";\n"
"    border-top: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"    border-bottom: 2px solid rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"    color: #6D6D6D;\n"
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
        self.element_id_display.setInputMethodHints(Qt.InputMethodHint.ImhLatinOnly|Qt.InputMethodHint.ImhLowercaseOnly)
        self.element_id_display.setMaxLength(32)
        self.element_id_display.setReadOnly(True)

        self.horizontalLayout.addWidget(self.element_id_display)

        self.delete_button = QPushButton(self.header)
        self.delete_button.setObjectName(u"delete_button")
        self.delete_button.setStyleSheet(u"\n"
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
        icon1.addFile(u":/icons/delete_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.delete_button.setIcon(icon1)

        self.horizontalLayout.addWidget(self.delete_button)

        self.copy_button = QPushButton(self.header)
        self.copy_button.setObjectName(u"copy_button")
        self.copy_button.setStyleSheet(u"\n"
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
        icon2 = QIcon()
        icon2.addFile(u":/icons/content_copy_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.copy_button.setIcon(icon2)

        self.horizontalLayout.addWidget(self.copy_button)


        self.verticalLayout.addWidget(self.header)

        self.content = QFrame(Form)
        self.content.setObjectName(u"content")
        self.content.setFrameShape(QFrame.Shape.StyledPanel)
        self.content.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.content)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout.addWidget(self.content)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.label_2.setText("")
#if QT_CONFIG(tooltip)
        self.show_child.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:8pt; font-weight:400;\">Show child</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.show_child.setText("")
        self.gf.setText("")
#if QT_CONFIG(tooltip)
        self.property_class.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.property_class.setText(QCoreApplication.translate("Form", u"Class properties", None))
#if QT_CONFIG(tooltip)
        self.element_id_display.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.element_id_display.setText("")
        self.element_id_display.setPlaceholderText("")
        self.delete_button.setText(QCoreApplication.translate("Form", u"Delete", None))
        self.copy_button.setText(QCoreApplication.translate("Form", u"Copy", None))
    # retranslateUi

