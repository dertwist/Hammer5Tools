# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'CurveWidgetDialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QSizePolicy,
    QSpacerItem, QToolButton, QVBoxLayout, QWidget)

from CurveWidget import CurveWidget

class Ui_CurveWidgetDialog(object):
    def setupUi(self, CurveWidgetDialog):
        if not CurveWidgetDialog.objectName():
            CurveWidgetDialog.setObjectName(u"CurveWidgetDialog")
        CurveWidgetDialog.resize(575, 291)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(CurveWidgetDialog.sizePolicy().hasHeightForWidth())
        CurveWidgetDialog.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(CurveWidgetDialog)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(6, 6, 6, 6)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.toolButton = QToolButton(CurveWidgetDialog)
        self.toolButton.setObjectName(u"toolButton")

        self.horizontalLayout.addWidget(self.toolButton)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.curveWidget = CurveWidget(CurveWidgetDialog)
        self.curveWidget.setObjectName(u"curveWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.curveWidget.sizePolicy().hasHeightForWidth())
        self.curveWidget.setSizePolicy(sizePolicy1)

        self.verticalLayout.addWidget(self.curveWidget)


        self.retranslateUi(CurveWidgetDialog)

        QMetaObject.connectSlotsByName(CurveWidgetDialog)
    # setupUi

    def retranslateUi(self, CurveWidgetDialog):
        CurveWidgetDialog.setWindowTitle(QCoreApplication.translate("CurveWidgetDialog", u"Curve", None))
        self.toolButton.setText(QCoreApplication.translate("CurveWidgetDialog", u"Normalize", None))
    # retranslateUi

