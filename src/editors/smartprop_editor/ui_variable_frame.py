# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'variable_frame.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout,
    QLabel, QLayout, QLineEdit, QSizePolicy,
    QToolButton, QVBoxLayout, QWidget)
import resources_rc

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(668, 285)
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
        self.show_child.setChecked(False)
        self.show_child.setTristate(False)

        self.horizontalLayout.addWidget(self.show_child)

        self.visible_in_editor = QCheckBox(self.frame)
        self.visible_in_editor.setObjectName(u"visible_in_editor")
        self.visible_in_editor.setStyleSheet(u"QCheckBox::indicator:checked {\n"
"    image: url(://icons/visibility_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png);\n"
"	height:16px;\n"
"	width:16px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/visibility_off_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png); \n"
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
        self.visible_in_editor.setChecked(False)
        self.visible_in_editor.setAutoRepeat(False)
        self.visible_in_editor.setAutoExclusive(False)
        self.visible_in_editor.setTristate(False)

        self.horizontalLayout.addWidget(self.visible_in_editor)

        self.variable_name = QLineEdit(self.frame)
        self.variable_name.setObjectName(u"variable_name")
        self.variable_name.setStyleSheet(u"QLineEdit {\n"
"	font: 8pt \"Segoe UI\";\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"color: #E3E3E3;\n"
"background-color: #242424;\n"
"}\n"
"QLineEdit:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"QLineEdit::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"")
        self.variable_name.setInputMethodHints(Qt.InputMethodHint.ImhLatinOnly|Qt.InputMethodHint.ImhLowercaseOnly)
        self.variable_name.setMaxLength(86)
        self.variable_name.setReadOnly(False)

        self.horizontalLayout.addWidget(self.variable_name)

        self.variable_class = QLineEdit(self.frame)
        self.variable_class.setObjectName(u"variable_class")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.variable_class.sizePolicy().hasHeightForWidth())
        self.variable_class.setSizePolicy(sizePolicy)
        self.variable_class.setMinimumSize(QSize(128, 0))
        self.variable_class.setMaximumSize(QSize(128, 16777215))
        self.variable_class.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.variable_class.setStyleSheet(u"QLineEdit {\n"
"	font: 8pt \"Segoe UI\";\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"	color: rgb(188, 188, 188);\n"
"	background-color: #242424;\n"
"}\n"
"QLineEdit:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"QLineEdit::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"")
        self.variable_class.setMaxLength(64)
        self.variable_class.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.variable_class.setReadOnly(True)

        self.horizontalLayout.addWidget(self.variable_class)

        self.change_class = QToolButton(self.frame)
        self.change_class.setObjectName(u"change_class")
        self.change_class.setStyleSheet(u"\n"
"\n"
"QToolButton {\n"
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
"QToolButton:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"QToolButton{\n"
"	padding-left:5px;\n"
"	border-left: 0px solid black;\n"
"border-right: 0px solid black;\n"
"border-top: 0px solid black;\n"
"}")
        icon = QIcon()
        icon.addFile(u":/icons/edit_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.change_class.setIcon(icon)

        self.horizontalLayout.addWidget(self.change_class)

        self.id_display_label = QLineEdit(self.frame)
        self.id_display_label.setObjectName(u"id_display_label")
        self.id_display_label.setMaximumSize(QSize(24, 16777215))
        self.id_display_label.setStyleSheet(u"QLineEdit {\n"
"	font: 8pt \"Segoe UI\";\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"	color: rgb(188, 188, 188);\n"
"	background-color: #242424;\n"
"}\n"
"QLineEdit:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"QLineEdit::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"")
        self.id_display_label.setMaxLength(64)
        self.id_display_label.setReadOnly(True)

        self.horizontalLayout.addWidget(self.id_display_label)

        self.id_display = QLineEdit(self.frame)
        self.id_display.setObjectName(u"id_display")
        self.id_display.setMaximumSize(QSize(36, 16777215))
        self.id_display.setStyleSheet(u"QLineEdit {\n"
"	font: 8pt \"Segoe UI\";\n"
"    border: 2px solid #CCCCCC;\n"
"	border-top: 0px;\n"
"	border-left: 0px;\n"
"	border-right: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 0px;\n"
"    padding: 2px;\n"
"	color: rgb(188, 188, 188);\n"
"	background-color: #242424;\n"
"}\n"
"QLineEdit:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"QLineEdit::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"")
        self.id_display.setMaxLength(64)
        self.id_display.setReadOnly(True)

        self.horizontalLayout.addWidget(self.id_display)


        self.verticalLayout.addWidget(self.frame)

        self.frame_layout = QFrame(Form)
        self.frame_layout.setObjectName(u"frame_layout")
        self.frame_layout.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_layout.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_layout)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setObjectName(u"layout")
        self.layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.frame_3 = QFrame(self.frame_layout)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16777215, 32))
        self.frame_3.setStyleSheet(u".QFrame {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"	border-top: 0px;\n"
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
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.frame_3.setLineWidth(0)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_2.setSpacing(16)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.frame_3)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"\n"
"")

        self.horizontalLayout_2.addWidget(self.label_2)

        self.varialbe_display_name = QLineEdit(self.frame_3)
        self.varialbe_display_name.setObjectName(u"varialbe_display_name")
        self.varialbe_display_name.setStyleSheet(u"QLineEdit {\n"
"    border: 0px solid #CCCCCC;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    border-radius: 2px;\n"
"    padding: 2px;\n"
"    color: #E3E3E3;\n"
"background-color: #1C1C1C;\n"
"\n"
"}\n"
"")

        self.horizontalLayout_2.addWidget(self.varialbe_display_name)


        self.layout.addWidget(self.frame_3)

        self.hide_expression_frame = QFrame(self.frame_layout)
        self.hide_expression_frame.setObjectName(u"hide_expression_frame")
        self.hide_expression_frame.setMaximumSize(QSize(16777215, 32))
        self.hide_expression_frame.setStyleSheet(u".QFrame {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"	border-top: 0px;\n"
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
        self.hide_expression_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.hide_expression_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.hide_expression_frame.setLineWidth(0)
        self.horizontalLayout_3 = QHBoxLayout(self.hide_expression_frame)
        self.horizontalLayout_3.setSpacing(16)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.hide_expression_frame)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"\n"
"")

        self.horizontalLayout_3.addWidget(self.label_3)


        self.layout.addWidget(self.hide_expression_frame)


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
        self.visible_in_editor.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p><span style=\" font-size:8pt; font-weight:400;\">Show in editor</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.visible_in_editor.setText("")
#if QT_CONFIG(tooltip)
        self.variable_name.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.variable_name.setText(QCoreApplication.translate("Form", u"Variable name", None))
#if QT_CONFIG(tooltip)
        self.variable_class.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>class</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.variable_class.setText(QCoreApplication.translate("Form", u"RadiusPlacementMode", None))
        self.change_class.setText("")
#if QT_CONFIG(tooltip)
        self.id_display_label.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>class</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.id_display_label.setText(QCoreApplication.translate("Form", u"ID", None))
#if QT_CONFIG(tooltip)
        self.id_display.setToolTip(QCoreApplication.translate("Form", u"<html><head/><body><p>class</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.id_display.setText(QCoreApplication.translate("Form", u"ID", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Display name", None))
        self.varialbe_display_name.setPlaceholderText(QCoreApplication.translate("Form", u"Not nessesary", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"Hide expression", None))
    # retranslateUi

