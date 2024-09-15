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
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QLayout, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Widget(object):
    def setupUi(self, Widget):
        if not Widget.objectName():
            Widget.setObjectName(u"Widget")
        Widget.setWindowModality(Qt.NonModal)
        Widget.resize(838, 119)
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
        self.frame_5.setMinimumSize(QSize(0, 32))
        self.frame_5.setMaximumSize(QSize(16777215, 32))
        self.frame_5.setStyleSheet(u".QFrame {\n"
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
        self.frame_5.setFrameShape(QFrame.NoFrame)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.frame_5)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.layout = QHBoxLayout()
        self.layout.setObjectName(u"layout")
        self.layout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.property_class = QLabel(self.frame_5)
        self.property_class.setObjectName(u"property_class")
        self.property_class.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"")

        self.layout.addWidget(self.property_class)

        self.logic_switch = QComboBox(self.frame_5)
        self.logic_switch.addItem("")
        self.logic_switch.addItem("")
        self.logic_switch.setObjectName(u"logic_switch")
        self.logic_switch.setStyleSheet(u"QComboBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom: 2px;\n"
"	border-top:none;\n"
"border-bottom:none;\n"
"border:none;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:pressed {\n"
"}\n"
"\n"
"QComboBox:item {\n"
"    font: 580  8pt \"Segoe UI\";\n"
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
"    width: 7px;"
                        "\n"
"    border-color: rgba(80, 80, 80, 255);\n"
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
"    background-color: #"
                        "414956;\n"
"    color: white;\n"
"    border: none; /* Remove border */\n"
"    outline: none; /* Remove outline */\n"
"}\n"
"")

        self.layout.addWidget(self.logic_switch)

        self.variable_combobox = QComboBox(self.frame_5)
        self.variable_combobox.setObjectName(u"variable_combobox")
        self.variable_combobox.setStyleSheet(u"QComboBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom: 2px;\n"
"	border-top:none;\n"
"border-bottom:none;\n"
"border:none;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:pressed {\n"
"}\n"
"\n"
"QComboBox:item {\n"
"    font: 580  8pt \"Segoe UI\";\n"
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
"    width: 7px;"
                        "\n"
"    border-color: rgba(80, 80, 80, 255);\n"
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
"    background-color: #"
                        "414956;\n"
"    color: white;\n"
"    border: none; /* Remove border */\n"
"    outline: none; /* Remove outline */\n"
"}\n"
"")

        self.layout.addWidget(self.variable_combobox)


        self.horizontalLayout.addLayout(self.layout)


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
        self.frame.setFrameShape(QFrame.NoFrame)
        self.frame.setFrameShadow(QFrame.Raised)
        self.frame.setLineWidth(0)
        self.horizontalLayout_2 = QHBoxLayout(self.frame)
        self.horizontalLayout_2.setSpacing(0)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.layout_x = QHBoxLayout()
        self.layout_x.setObjectName(u"layout_x")
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy1)
        self.label.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"color: #ECA4A0;\n"
"padding-right: 16px;")

        self.layout_x.addWidget(self.label)

        self.comboBox = QComboBox(self.frame)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")
        self.comboBox.setStyleSheet(u"QComboBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom: 2px;\n"
"	border-top:none;\n"
"border-bottom:none;\n"
"border:none;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:pressed {\n"
"}\n"
"\n"
"QComboBox:item {\n"
"    font: 580  8pt \"Segoe UI\";\n"
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
"    width: 7px;"
                        "\n"
"    border-color: rgba(80, 80, 80, 255);\n"
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
"    background-color: #"
                        "414956;\n"
"    color: white;\n"
"    border: none; /* Remove border */\n"
"    outline: none; /* Remove outline */\n"
"}\n"
"")

        self.layout_x.addWidget(self.comboBox)


        self.horizontalLayout_2.addLayout(self.layout_x)


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
        self.frame_2.setFrameShape(QFrame.NoFrame)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.frame_2.setLineWidth(0)
        self.horizontalLayout_7 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.layout_y = QHBoxLayout()
        self.layout_y.setObjectName(u"layout_y")
        self.label_2 = QLabel(self.frame_2)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)
        self.label_2.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"color: #B6EFA2;\n"
"padding-right: 16px;")

        self.layout_y.addWidget(self.label_2)

        self.comboBox_2 = QComboBox(self.frame_2)
        self.comboBox_2.addItem("")
        self.comboBox_2.addItem("")
        self.comboBox_2.addItem("")
        self.comboBox_2.setObjectName(u"comboBox_2")
        self.comboBox_2.setStyleSheet(u"QComboBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom: 2px;\n"
"	border-top:none;\n"
"border-bottom:none;\n"
"border:none;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:pressed {\n"
"}\n"
"\n"
"QComboBox:item {\n"
"    font: 580  8pt \"Segoe UI\";\n"
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
"    width: 7px;"
                        "\n"
"    border-color: rgba(80, 80, 80, 255);\n"
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
"    background-color: #"
                        "414956;\n"
"    color: white;\n"
"    border: none; /* Remove border */\n"
"    outline: none; /* Remove outline */\n"
"}\n"
"")

        self.layout_y.addWidget(self.comboBox_2)


        self.horizontalLayout_7.addLayout(self.layout_y)


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
        self.frame_3.setFrameShape(QFrame.NoFrame)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.frame_3.setLineWidth(0)
        self.horizontalLayout_8 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_8.setSpacing(0)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.layout_z = QHBoxLayout()
        self.layout_z.setObjectName(u"layout_z")
        self.label_3 = QLabel(self.frame_3)
        self.label_3.setObjectName(u"label_3")
        sizePolicy1.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy1)
        self.label_3.setStyleSheet(u"border:0px;\n"
"background-color: rgba(255, 255, 255, 0);\n"
"font: 8pt \"Segoe UI\";\n"
"\n"
"color: #A4B6EF;\n"
"padding-right: 16px;")

        self.layout_z.addWidget(self.label_3)

        self.comboBox_3 = QComboBox(self.frame_3)
        self.comboBox_3.addItem("")
        self.comboBox_3.addItem("")
        self.comboBox_3.addItem("")
        self.comboBox_3.setObjectName(u"comboBox_3")
        self.comboBox_3.setStyleSheet(u"QComboBox {\n"
"    font: 580 8pt \"Segoe UI\";\n"
"    border: 2px solid black;\n"
"    border-radius: 0px;\n"
"    border-color: rgba(80, 80, 80, 255);\n"
"    height: 18px;\n"
"    padding-top: 2px;\n"
"    padding-bottom: 2px;\n"
"	border-top:none;\n"
"border-bottom:none;\n"
"border:none;\n"
"    color: #E3E3E3;\n"
"    background-color: #1C1C1C;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    background-color: #414956;\n"
"    color: white;\n"
"}\n"
"\n"
"QComboBox:pressed {\n"
"}\n"
"\n"
"QComboBox:item {\n"
"    font: 580  8pt \"Segoe UI\";\n"
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
"    width: 7px;"
                        "\n"
"    border-color: rgba(80, 80, 80, 255);\n"
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
"    background-color: #"
                        "414956;\n"
"    color: white;\n"
"    border: none; /* Remove border */\n"
"    outline: none; /* Remove outline */\n"
"}\n"
"")

        self.layout_z.addWidget(self.comboBox_3)


        self.horizontalLayout_8.addLayout(self.layout_z)


        self.verticalLayout_2.addWidget(self.frame_3)


        self.verticalLayout.addWidget(self.frame_4)


        self.retranslateUi(Widget)

        QMetaObject.connectSlotsByName(Widget)
    # setupUi

    def retranslateUi(self, Widget):
        Widget.setWindowTitle(QCoreApplication.translate("Widget", u"Form", None))
        self.property_class.setText(QCoreApplication.translate("Widget", u"class", None))
        self.logic_switch.setItemText(0, QCoreApplication.translate("Widget", u"Variable source", None))
        self.logic_switch.setItemText(1, QCoreApplication.translate("Widget", u"Vector3d", None))

        self.label.setText(QCoreApplication.translate("Widget", u"Vector X", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("Widget", u"Float", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("Widget", u"Variable", None))
        self.comboBox.setItemText(2, QCoreApplication.translate("Widget", u"Expression", None))

        self.label_2.setText(QCoreApplication.translate("Widget", u"Vector Y", None))
        self.comboBox_2.setItemText(0, QCoreApplication.translate("Widget", u"Float", None))
        self.comboBox_2.setItemText(1, QCoreApplication.translate("Widget", u"Variable", None))
        self.comboBox_2.setItemText(2, QCoreApplication.translate("Widget", u"Expression", None))

        self.label_3.setText(QCoreApplication.translate("Widget", u"Vector Z", None))
        self.comboBox_3.setItemText(0, QCoreApplication.translate("Widget", u"Float", None))
        self.comboBox_3.setItemText(1, QCoreApplication.translate("Widget", u"Variable", None))
        self.comboBox_3.setItemText(2, QCoreApplication.translate("Widget", u"Expression", None))

    # retranslateUi

