# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'property_frame.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QLabel, QLayout, QLineEdit,
    QPushButton, QSizePolicy, QToolButton, QVBoxLayout,
    QWidget)
import rc_resources

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(668, 76)
        Form.setStyleSheet(u"background-color: #1C1C1C;")
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(16777215, 24))
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
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
        self.show_child.setFocusPolicy(Qt.NoFocus)
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

        self.enable = QCheckBox(self.frame)
        self.enable.setObjectName(u"enable")
        self.enable.setFocusPolicy(Qt.NoFocus)
        self.enable.setStyleSheet(u"QCheckBox::indicator:checked {\n"
"image: url(://icons/select_check_box_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"   \n"
"	height:16px;\n"
"	width:16px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/check_box_outline_blank_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg);\n"
"	height:16px;\n"
"	width:16px;\n"
"}\n"
"\n"
"\n"
"QCheckBox {\n"
"    font: 700 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height:14px;\n"
"    padding-top: 2px;\n"
"    padding-bottom:2px;\n"
"    color: #E3E3E3;\n"
"    padding-left: 4px;\n"
"background-color: #242424;\n"
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
        self.enable.setChecked(False)
        self.enable.setAutoRepeat(False)
        self.enable.setAutoExclusive(False)
        self.enable.setTristate(False)

        self.horizontalLayout.addWidget(self.enable)

        self.property_icon = QToolButton(self.frame)
        self.property_icon.setObjectName(u"property_icon")
        self.property_icon.setEnabled(False)
        self.property_icon.setFocusPolicy(Qt.NoFocus)
        self.property_icon.setStyleSheet(u"QToolButton {\n"
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
        icon.addFile(u":/icons/linear_scale_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.property_icon.setIcon(icon)
        self.property_icon.setIconSize(QSize(24, 24))

        self.horizontalLayout.addWidget(self.property_icon)

        self.property_class = QLineEdit(self.frame)
        self.property_class.setObjectName(u"property_class")
        self.property_class.setFocusPolicy(Qt.NoFocus)
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
        self.property_class.setInputMethodHints(Qt.ImhLatinOnly|Qt.ImhLowercaseOnly)
        self.property_class.setMaxLength(32)
        self.property_class.setReadOnly(True)

        self.horizontalLayout.addWidget(self.property_class)

        self.emable_variable = QComboBox(self.frame)
        self.emable_variable.setObjectName(u"emable_variable")
        self.emable_variable.setMinimumSize(QSize(128, 0))
        self.emable_variable.setStyleSheet(u"QComboBox {\n"
"    font-size: 8pt;\n"
"    font-family: \"Segoe UI\";\n"
"    border-top: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"    border-bottom: 2px solid rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 4px;\n"
"    color: #E3E3E3;\n"
"    background-color: #242424;\n"
"}\n"
"\n"
"QComboBox:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"\n"
"QComboBox::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}")

        self.horizontalLayout.addWidget(self.emable_variable)

        self.delete_button = QPushButton(self.frame)
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

        self.copy_button = QPushButton(self.frame)
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


        self.verticalLayout.addWidget(self.frame)

        self.frame_layout = QFrame(Form)
        self.frame_layout.setObjectName(u"frame_layout")
        self.frame_layout.setFrameShape(QFrame.StyledPanel)
        self.frame_layout.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_layout)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(8)
        self.layout.setObjectName(u"layout")
        self.layout.setSizeConstraint(QLayout.SetDefaultConstraint)

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
#if QT_CONFIG(tooltip)
        self.enable.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:8pt; font-weight:400;\">Show in editor</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.enable.setText("")
        self.property_icon.setText("")
#if QT_CONFIG(tooltip)
        self.property_class.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.property_class.setText(QCoreApplication.translate("Form", u"Class properties", None))
#if QT_CONFIG(tooltip)
        self.emable_variable.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Set Enable status from Variable</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.delete_button.setText(QCoreApplication.translate("Form", u"Delete", None))
        self.copy_button.setText(QCoreApplication.translate("Form", u"Copy", None))
    # retranslateUi

