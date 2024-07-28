# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'loading_editor_mainwindow.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QMainWindow, QPlainTextEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_Loading_editorMainWindow(object):
    def setupUi(self, Loading_editorMainWindow):
        if not Loading_editorMainWindow.objectName():
            Loading_editorMainWindow.setObjectName(u"Loading_editorMainWindow")
        Loading_editorMainWindow.resize(1072, 745)
        self.centralwidget = QWidget(Loading_editorMainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setSpacing(6)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.Loading_editor_tab_images_import = QFrame(self.centralwidget)
        self.Loading_editor_tab_images_import.setObjectName(u"Loading_editor_tab_images_import")
        self.Loading_editor_tab_images_import.setStyleSheet(u"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;")
        self.Loading_editor_tab_images_import.setFrameShape(QFrame.StyledPanel)
        self.Loading_editor_tab_images_import.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.Loading_editor_tab_images_import)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)

        self.gridLayout.addWidget(self.Loading_editor_tab_images_import, 0, 0, 1, 1)

        self.frame_2 = QFrame(self.centralwidget)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setMaximumSize(QSize(360, 16777215))
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.svg_icon_frame = QFrame(self.frame_2)
        self.svg_icon_frame.setObjectName(u"svg_icon_frame")
        self.svg_icon_frame.setMinimumSize(QSize(0, 320))
        self.svg_icon_frame.setStyleSheet(u"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;")
        self.svg_icon_frame.setFrameShape(QFrame.StyledPanel)
        self.svg_icon_frame.setFrameShadow(QFrame.Raised)
        self.horizontalLayout = QHBoxLayout(self.svg_icon_frame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_3.addWidget(self.svg_icon_frame)

        self.apply_icon_button = QPushButton(self.frame_2)
        self.apply_icon_button.setObjectName(u"apply_icon_button")
        self.apply_icon_button.setEnabled(True)
        self.apply_icon_button.setMinimumSize(QSize(0, 32))
        self.apply_icon_button.setStyleSheet(u"     QLabel {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QPushButton:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QPushButton:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton:disabled {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px sol"
                        "id black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #8c8c8c;\n"
"        background-color: #1C1C1C;\n"
"    }")

        self.verticalLayout_3.addWidget(self.apply_icon_button)

        self.PlainTextEdit_Description_2 = QPlainTextEdit(self.frame_2)
        self.PlainTextEdit_Description_2.setObjectName(u"PlainTextEdit_Description_2")
        self.PlainTextEdit_Description_2.setStyleSheet(u"    QPlainTextEdit {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding: 4px;\n"
"        padding-left: 6px;\n"
"        padding-right: 6px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"\n"
"\n"
"\n"
"    QPlainTextEdit:focus {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding: 4px;\n"
"        padding-left: 6px;\n"
"        padding-right: 6px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QPlainTextEdit:hover {\n"
"    }\n"
"    QPlainTextEdit:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"        f"
                        "ont: 580 9pt \"Segoe UI\";\n"
"\n"
"    }")

        self.verticalLayout_3.addWidget(self.PlainTextEdit_Description_2)


        self.gridLayout.addWidget(self.frame_2, 0, 1, 1, 1)

        self.apply_images_button = QPushButton(self.centralwidget)
        self.apply_images_button.setObjectName(u"apply_images_button")
        self.apply_images_button.setMinimumSize(QSize(0, 32))
        self.apply_images_button.setStyleSheet(u"    QLabel {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QPushButton:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QPushButton:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"\n"
"    }")

        self.gridLayout.addWidget(self.apply_images_button, 1, 0, 1, 1)

        self.apply_description_button = QPushButton(self.centralwidget)
        self.apply_description_button.setObjectName(u"apply_description_button")
        self.apply_description_button.setMinimumSize(QSize(0, 32))
        self.apply_description_button.setStyleSheet(u"    QLabel {\n"
"        font-family: Sergo UI;\n"
"        color: #9D9D9D;\n"
"    }\n"
"\n"
"    /* QPushButton default and hover styles */\n"
"    QPushButton {\n"
"\n"
"        font: 580 10pt \"Segoe UI\";\n"
"        border: 2px solid black;\n"
"        border-radius: 4px;\n"
"        border-color: rgba(80, 80, 80, 255);\n"
"        height:18px;\n"
"        padding-top: 2px;\n"
"        padding-bottom:2px;\n"
"        padding-left: 4px;\n"
"        padding-right: 4px;\n"
"        color: #E3E3E3;\n"
"        background-color: #1C1C1C;\n"
"    }\n"
"    QPushButton:hover {\n"
"        background-color: #414956;\n"
"        color: white;\n"
"    }\n"
"    QPushButton:pressed {\n"
"        background-color: red;\n"
"        background-color: #1C1C1C;\n"
"        margin: 1 px;\n"
"        margin-left: 2px;\n"
"        margin-right: 2px;\n"
"\n"
"    }")

        self.gridLayout.addWidget(self.apply_description_button, 1, 1, 1, 1)

        Loading_editorMainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(Loading_editorMainWindow)

        QMetaObject.connectSlotsByName(Loading_editorMainWindow)
    # setupUi

    def retranslateUi(self, Loading_editorMainWindow):
        Loading_editorMainWindow.setWindowTitle(QCoreApplication.translate("Loading_editorMainWindow", u"MainWindow", None))
        self.apply_icon_button.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Apply Icon", None))
#if QT_CONFIG(tooltip)
        self.PlainTextEdit_Description_2.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.PlainTextEdit_Description_2.setPlainText("")
        self.PlainTextEdit_Description_2.setPlaceholderText(QCoreApplication.translate("Loading_editorMainWindow", u"A community map created by:", None))
#if QT_CONFIG(tooltip)
        self.apply_images_button.setToolTip(QCoreApplication.translate("Loading_editorMainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:10pt; font-weight:580; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:11pt; font-weight:700;\">Apply images</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Applies all images above to the loading screen of the selected addon. </p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\""
                        ">Be careful: old images stored in <span style=\" font-family:'Courier New';\">game\\addons\\%addon_name%\\panorama\\images\\map_icons\\screenshots\\1080p\\</span> will be deleted.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.apply_images_button.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Apply images", None))
        self.apply_description_button.setText(QCoreApplication.translate("Loading_editorMainWindow", u"Apply description", None))
    # retranslateUi

