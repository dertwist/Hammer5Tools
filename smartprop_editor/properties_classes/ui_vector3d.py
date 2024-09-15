# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'vector3d.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.setWindowModality(Qt.NonModal)
        Widget.resize(838, 122)
        Widget.setMinimumSize(QSize(0, 0))
        Widget.setMaximumSize(QSize(16777215, 200))
        Widget.setStyleSheet(u".QWidget {\n"
"    font: 580 10pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-left: 0px;\n"
"    border-right: 0px;\n"
"	border-top: 0px;\n"
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
        self.frame_5 = QFrame(Widget)
        self.frame_5.setObjectName(u"frame_5")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_5.sizePolicy().hasHeightForWidth())
        self.frame_5.setSizePolicy(sizePolicy)
        self.frame_5.setMinimumSize(QSize(0, 23))
        self.frame_5.setMaximumSize(QSize(16777215, 23))
        self.frame_5.setFrameShape(QFrame.NoFrame)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_5)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.property_class = QLineEdit(self.frame_5)
        self.property_class.setObjectName(u"property_class")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.property_class.sizePolicy().hasHeightForWidth())
        self.property_class.setSizePolicy(sizePolicy1)
        self.property_class.setFocusPolicy(Qt.NoFocus)
        self.property_class.setStyleSheet(u"QLineEdit {\n"
"font: 580  8pt \"Segoe UI\";\n"
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

        self.comboBox = QComboBox(self.frame_5)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")
        self.comboBox.setStyleSheet(u"QComboBox {\n"
"font: 580  8pt \"Segoe UI\";\n"
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
"QComboBox:focus {\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"}\n"
"\n"
"QComboBox::selection {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:item {\n"
"    font: 580  10pt \"Segoe UI\";\n"
"    color: #E3E3E3;\n"
"    padding-left: 5px;\n"
"    background-color: #1C1C1C;\n"
"    border-style: none;\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    color: #E3E3E3;\n"
"    padding: 2px;\n"
"    background: url(://icons/arrow_drop_down_16dp.svg) no-repeat center;\n"
"    border-bottom: 0px solid black;\n"
"    border-top: 0px solid black;\n"
"    border-right: 0px;\n"
"    border-left: 2px solid;\n"
"    margin-left: 5px;\n"
"    padding: 5px;\n"
"    width: 7px;\n"
"    border-"
                        "color: rgba(80, 80, 80, 255);\n"
"    background-color: #1C1C1C;\n"
"border:none;\n"
"}\n"
"\n"
"QComboBox::drop-down:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    border: 2px solid gray;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    selection-background-color: #414956;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"\n"
"QComboBox QAbstractItemView::item {\n"
"    height: 16px; /* Set the height of each item */\n"
"    padding: 4px; /* Add padding to each item */\n"
"    padding-left: 5px;\n"
"    padding-right: 5px;\n"
"    color: #ff8a8a8a;\n"
"    border-style: none;\n"
"    border-bottom: 0.5px solid black;\n"
"    border-color: rgba(255, 255, 255, 10);\n"
"}\n"
"\n"
"\n"
"QComboBox QAbstractItemView::item:selected {\n"
"    height: 16px; /* Set the height of each item */\n"
"    padding: 4px; /* Add padding to each item */\n"
"    padding-left: 5px;\n"
"    padding-right: 5px;\n"
"    background-color: #414956;\n"
"    "
                        "color: white;\n"
"    border: none; /* Remove border */\n"
"    outline: none; /* Remove outline */\n"
"}")

        self.horizontalLayout.addWidget(self.comboBox)


        self.verticalLayout.addWidget(self.frame_5)

        self.frame_4 = QFrame(Widget)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.NoFrame)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.frame_4.setLineWidth(0)
        self.verticalLayout_2 = QVBoxLayout(self.frame_4)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.frame = QFrame(self.frame_4)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(0, 32))
        self.frame.setMaximumSize(QSize(16777215, 32))
        self.frame.setStyleSheet(u".QFrame {\n"
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
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.frame.setLineWidth(0)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"color: #ECA4A0;\n"
"")

        self.horizontalLayout_2.addWidget(self.label)

        self.vector_x = QDoubleSpinBox(self.frame)
        self.vector_x.setObjectName(u"vector_x")
        self.vector_x.setMinimumSize(QSize(0, 0))
        self.vector_x.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"border:0px;\n"
"color: #ECA4A0;\n"
"}\n"
"\n"
"QDoubleSpinBox:focus {\n"
"}\n"
"\n"
"QDoubleSpinBox:hover {\n"
"}\n"
"\n"
"QDoubleSpinBox:pressed {\n"
"	background-color: #121212;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-button {\n"
"    border: 0px solid black;\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    border-left: 2px solid black;\n"
"    border-bottom: 0px solid black;\n"
"    border-top-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-arrow {\n"
"    image: url(://icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"  "
                        "  subcontrol-position: bottom right;\n"
"	border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}")
        self.vector_x.setDecimals(2)
        self.vector_x.setMinimum(-99999999999.000000000000000)
        self.vector_x.setMaximum(99999999999.000000000000000)
        self.vector_x.setSingleStep(0.100000000000000)

        self.horizontalLayout_2.addWidget(self.vector_x)


        self.verticalLayout_2.addWidget(self.frame)

        self.frame_2 = QFrame(self.frame_4)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMinimumSize(QSize(0, 32))
        self.frame_2.setMaximumSize(QSize(16777215, 32))
        self.frame_2.setStyleSheet(u".QFrame {\n"
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
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.frame_2.setLineWidth(0)
        self.horizontalLayout_7 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.frame_2)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"color: #B6EFA2;")

        self.horizontalLayout_7.addWidget(self.label_2)

        self.vector_y = QDoubleSpinBox(self.frame_2)
        self.vector_y.setObjectName(u"vector_y")
        self.vector_y.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"border:0px;\n"
"color: #B6EFA2;\n"
"}\n"
"\n"
"QDoubleSpinBox:focus {\n"
"}\n"
"\n"
"QDoubleSpinBox:hover {\n"
"}\n"
"\n"
"QDoubleSpinBox:pressed {\n"
"	background-color: #121212;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-button {\n"
"    border: 0px solid black;\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    border-left: 2px solid black;\n"
"    border-bottom: 0px solid black;\n"
"    border-top-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-arrow {\n"
"    image: url(://icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"  "
                        "  subcontrol-position: bottom right;\n"
"	border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QDoubleSpinBox:disabled {\n"
"	color: rgba(125, 125, 125, 100);\n"
"}")
        self.vector_y.setDecimals(2)
        self.vector_y.setMinimum(-99999999999.000000000000000)
        self.vector_y.setMaximum(99999999999.000000000000000)
        self.vector_y.setSingleStep(0.100000000000000)

        self.horizontalLayout_7.addWidget(self.vector_y)


        self.verticalLayout_2.addWidget(self.frame_2)

        self.frame_3 = QFrame(self.frame_4)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMinimumSize(QSize(0, 32))
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
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.frame_3.setLineWidth(0)
        self.horizontalLayout_8 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_8.setSpacing(0)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.frame_3)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"\n"
"color: #A4B6EF;")

        self.horizontalLayout_8.addWidget(self.label_3)

        self.vector_z = QDoubleSpinBox(self.frame_3)
        self.vector_z.setObjectName(u"vector_z")
        self.vector_z.setEnabled(True)
        self.vector_z.setStyleSheet(u"QDoubleSpinBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"border:0px;\n"
"color: #A4B6EF;\n"
"}\n"
"\n"
"QDoubleSpinBox:focus {\n"
"}\n"
"\n"
"QDoubleSpinBox:hover {\n"
"}\n"
"\n"
"QDoubleSpinBox:pressed {\n"
"	background-color: #121212;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-button {\n"
"    border: 0px solid black;\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
"    border-left: 2px solid black;\n"
"    border-bottom: 0px solid black;\n"
"    border-top-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::up-arrow {\n"
"    image: url(://icons/arrow_drop_up_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"  "
                        "  subcontrol-position: bottom right;\n"
"	border: 0px solid black;\n"
"    border-left: 2px solid black;\n"
"    border-top: 2px solid black;\n"
"border-bottom-right-radius: 2px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"	width:16px;\n"
"    margin:0px;\n"
"border:0px;\n"
"}\n"
"\n"
"QDoubleSpinBox::down-arrow {\n"
"    image: url(://icons/arrow_drop_down_16dp.svg);\n"
"    width: 20px;\n"
"    height: 20px;\n"
"}\n"
"\n"
"QDoubleSpinBox:disabled {\n"
"	color: rgba(125, 125, 125, 100);\n"
"}")
        self.vector_z.setDecimals(2)
        self.vector_z.setMinimum(-99999999999.000000000000000)
        self.vector_z.setMaximum(99999999999.000000000000000)
        self.vector_z.setSingleStep(0.100000000000000)

        self.horizontalLayout_8.addWidget(self.vector_z)


        self.verticalLayout_2.addWidget(self.frame_3)


        self.verticalLayout.addWidget(self.frame_4)


        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Form", None))
#if QT_CONFIG(tooltip)
        self.property_class.setToolTip(QCoreApplication.translate("Widget", u"<html><head/><body><p>Variable name and display name</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.property_class.setText(QCoreApplication.translate("Widget", u"Start point", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("Widget", u"Variable source", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("Widget", u"Vector3d", None))

        self.label.setText(QCoreApplication.translate("Widget", u"Vector X", None))
        self.label_2.setText(QCoreApplication.translate("Widget", u"Vector Y", None))
        self.label_3.setText(QCoreApplication.translate("Widget", u"Vector Z", None))
    # retranslateUi

