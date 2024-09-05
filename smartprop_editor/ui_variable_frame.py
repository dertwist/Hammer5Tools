# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'variable_frame.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(668, 285)
        Form.setStyleSheet(u"background-color: #1C1C1C;")
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.frame = QFrame(Form)
        self.frame.setObjectName(u"frame")
        self.frame.setMaximumSize(QSize(16777215, 24))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.checkBox_2 = QCheckBox(self.frame)
        self.checkBox_2.setObjectName(u"checkBox_2")
        self.checkBox_2.setStyleSheet(u"QCheckBox::indicator:checked {\n"
"    \n"
"image: url(://icons/arrow_drop_down.png);\n"
"	height:16px;\n"
"	width:16px;\n"
"}\n"
"\n"
"QCheckBox::indicator:unchecked {\n"
"    image: url(://icons/arrow_drop_right.png);\n"
"	height:16px;\n"
"	width:16px;\n"
"}\n"
"QCheckBox{\n"
"	padding-left:5px;\n"
"}")
        self.checkBox_2.setChecked(False)
        self.checkBox_2.setTristate(False)

        self.horizontalLayout.addWidget(self.checkBox_2)

        self.checkBox_3 = QCheckBox(self.frame)
        self.checkBox_3.setObjectName(u"checkBox_3")
        self.checkBox_3.setStyleSheet(u"QCheckBox::indicator:checked {\n"
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
"QCheckBox{\n"
"	padding-left:5px;\n"
"}")
        self.checkBox_3.setChecked(False)
        self.checkBox_3.setAutoRepeat(False)
        self.checkBox_3.setAutoExclusive(False)
        self.checkBox_3.setTristate(False)

        self.horizontalLayout.addWidget(self.checkBox_3)

        self.lineEdit_2 = QLineEdit(self.frame)
        self.lineEdit_2.setObjectName(u"lineEdit_2")
        self.lineEdit_2.setReadOnly(False)

        self.horizontalLayout.addWidget(self.lineEdit_2)

        self.lineEdit_3 = QLineEdit(self.frame)
        self.lineEdit_3.setObjectName(u"lineEdit_3")
        self.lineEdit_3.setMaximumSize(QSize(136, 16777215))
        self.lineEdit_3.setReadOnly(True)

        self.horizontalLayout.addWidget(self.lineEdit_3)


        self.verticalLayout.addWidget(self.frame)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.pushButton_2 = QPushButton(Form)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.verticalLayout_2.addWidget(self.pushButton_2)

        self.pushButton_3 = QPushButton(Form)
        self.pushButton_3.setObjectName(u"pushButton_3")

        self.verticalLayout_2.addWidget(self.pushButton_3)

        self.pushButton_4 = QPushButton(Form)
        self.pushButton_4.setObjectName(u"pushButton_4")

        self.verticalLayout_2.addWidget(self.pushButton_4)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)


        self.verticalLayout.addLayout(self.verticalLayout_2)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.checkBox_2.setText("")
        self.checkBox_3.setText("")
        self.lineEdit_2.setText(QCoreApplication.translate("Form", u"Variable name", None))
        self.lineEdit_3.setText(QCoreApplication.translate("Form", u"RadiusPlacementMode", None))
        self.pushButton_2.setText(QCoreApplication.translate("Form", u"PushButton", None))
        self.pushButton_3.setText(QCoreApplication.translate("Form", u"PushButton", None))
        self.pushButton_4.setText(QCoreApplication.translate("Form", u"PushButton", None))
    # retranslateUi

