# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'documentation_dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
    QSizePolicy, QTabWidget, QTextBrowser, QVBoxLayout,
    QWidget)

class Ui_documentation_dialog(object):
    def setupUi(self, documentation_dialog):
        if not documentation_dialog.objectName():
            documentation_dialog.setObjectName(u"documentation_dialog")
        documentation_dialog.resize(1122, 770)
        documentation_dialog.setMinimumSize(QSize(1100, 720))
        documentation_dialog.setStyleSheet(u"background-color: #1C1C1C;")
        documentation_dialog.setSizeGripEnabled(False)
        documentation_dialog.setModal(False)
        self.horizontalLayout = QHBoxLayout(documentation_dialog)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.tabWidget = QTabWidget(documentation_dialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(True)
        self.tabWidget.setTabPosition(QTabWidget.North)
        self.tabWidget.setElideMode(Qt.ElideNone)
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setTabsClosable(False)
        self.tabWidget.setTabBarAutoHide(False)
        self.About = QWidget()
        self.About.setObjectName(u"About")
        self.verticalLayout_3 = QVBoxLayout(self.About)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.textBrowser_3 = QTextBrowser(self.About)
        self.textBrowser_3.setObjectName(u"textBrowser_3")
        self.textBrowser_3.setStyleSheet(u"border: 0px;\n"
"margin: 3px;")

        self.verticalLayout_3.addWidget(self.textBrowser_3)

        self.version = QLabel(self.About)
        self.version.setObjectName(u"version")

        self.verticalLayout_3.addWidget(self.version)

        self.tabWidget.addTab(self.About, "")
        self.loading_editor = QWidget()
        self.loading_editor.setObjectName(u"loading_editor")
        self.verticalLayout = QVBoxLayout(self.loading_editor)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.textBrowser = QTextBrowser(self.loading_editor)
        self.textBrowser.setObjectName(u"textBrowser")
        self.textBrowser.setStyleSheet(u"border: 0px;\n"
"margin: 3px;")

        self.verticalLayout.addWidget(self.textBrowser)

        self.tabWidget.addTab(self.loading_editor, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.verticalLayout_2 = QVBoxLayout(self.tab_4)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.textBrowser_2 = QTextBrowser(self.tab_4)
        self.textBrowser_2.setObjectName(u"textBrowser_2")
        self.textBrowser_2.setStyleSheet(u"border: 0px;\n"
"margin: 3px;")

        self.verticalLayout_2.addWidget(self.textBrowser_2)

        self.tabWidget.addTab(self.tab_4, "")

        self.horizontalLayout.addWidget(self.tabWidget)


        self.retranslateUi(documentation_dialog)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(documentation_dialog)
    # setupUi

    def retranslateUi(self, documentation_dialog):
        documentation_dialog.setWindowTitle(QCoreApplication.translate("documentation_dialog", u"Help", None))
        self.textBrowser_3.setHtml(QCoreApplication.translate("documentation_dialog", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:22pt; font-weight:700;\">Hammer 5 Tools</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">A bumch of tools for Counter-Strike 2 Workshop.<br />There are a bunch of useful tools for mapping:</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; ma"
                        "rgin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:16pt; font-weight:700;\">Loading Editor:</span><span style=\" font-size:12pt;\"><br />With this tool, you can add images, descriptions, and icons to the loading screen.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:16pt; font-weight:700;\">SoundEvent Editor:</span><span style=\" font-size:12pt;\"><br />A tool for more comfortable sound editing within the game.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:16pt; font-weight:700;\">Hotkey Editor:</span><span style=\" font-size:12pt;\"><br />Edit default keyboard shortcuts and add your own!</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style="
                        "\" font-size:16pt; font-weight:700;\">BatchCreator:</span><span style=\" font-size:12pt;\"><br />Allows you to edit multiple files with the same parameters at one time. For example, if you have a modular set with 15 models, it is tedious to use the default Model/Material Editor, but with BatchCreator, you can do it all with one click.</span></p>\n"
"<p style=\" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:16pt; font-weight:700;\">SmartProp Editor:</span><span style=\" font-size:12pt;\"><br />A tool that helps with smartprops creation in the game.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; "
                        "margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt; font-weight:700;\">Use tooltips for understanding the program: </span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">For almost all buttons, an explanation appears when you hold your cursor over a button.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><img src=\":/images/help/about/tooltip_help.png\" /></p></body></html>", None))
        self.version.setText(QCoreApplication.translate("documentation_dialog", u"Version: 1.0.0", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.About), QCoreApplication.translate("documentation_dialog", u"About", None))
        self.textBrowser.setHtml(QCoreApplication.translate("documentation_dialog", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:10pt; font-weight:580;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:22pt; font-weight:580;\">Loading editor</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; tex"
                        "t-indent:0px; font-size:22pt; font-weight:580;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec ipsum elit, aliquam vitae mi ut, auctor sollicitudin libero. Maecenas quam purus, ullamcorper ut ultricies quis, accumsan vitae nisi. Donec vel bibendum orci. Sed lacinia, elit nec sagittis vehicula, magna odio facilisis lectus, non rutrum ante quam auctor eros. Sed ut tortor ac justo sollicitudin vehicula sed ac quam. Proin sed est non ipsum imperdiet sollicitudin eget sit amet elit. Maecenas semper semper ullamcorper. Vestibulum venenatis auctor massa sed lobortis. Vestibulum sed nisl pharetra, porta purus eget, finibus arcu. Vestibulum quis pretium dui.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br "
                        "/></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p align=\"center\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Morbi sit amet rutrum nisi. Phasellus egestas sed est ac tempus. Suspendisse vel nisi finibus, fringilla eros eu, hendrerit arcu. Cras gravida est sed dui rutrum hendrerit. Aliquam tortor lectus, pulvinar a auctor sit amet, finibus in nunc. Nulla lectus elit, accumsan vitae augue eu, vestibulum condimentum metus. Duis fringilla mollis nisi, sit amet sollicitudin ante vestibulum nec. Aliquam erat volutpat. Donec commodo egestas lorem, at mattis felis ornare a. Pellentesque maximus non leo nec dignissim. Vestibulum a tellus eget quam sodales molestie vel non erat. Nunc sed dolor in neque cursus viverra.</span></p>\n"
"<p align=\"center\" style=\"-qt-paragraph-"
                        "type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Donec vitae elit iaculis velit placerat mollis quis quis velit. Nunc scelerisque dignissim molestie. Praesent dignissim posuere nulla non tempor. Nulla scelerisque ultrices quam congue sodales. Donec sed purus a odio dignissim mollis. Pellentesque tempus enim odio. Maecenas interdum ullamcorper sem sed molestie. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Sed gravida sapien ac pellentesque rutrum. Praesent venenatis elit ex, vitae accumsan neque sollicitudin id. Ut rhoncus consectetur fermentu"
                        "m. Donec pulvinar sem lacinia neque malesuada maximus nec a odio. Nunc venenatis lectus sed nunc malesuada porta. Nunc pellentesque fringilla est et molestie. Sed nisi sem, varius a ipsum a, tempor tempor ligula.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Donec imperdiet venenatis tortor at luctus. Proin non justo pretium mauris faucibus consequat non quis neque. Mauris tempor congue suscipit. Nunc mi dui, scelerisque et ullamcorper sed, volutpat nec massa. Maecenas sit amet tristique leo. Suspendisse potenti. Donec nibh nisl, fringilla se"
                        "d ligula vel, fermentum molestie diam.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Proin vestibulum lorem quis quam suscipit, et efficitur mi commodo. Praesent ac metus erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Praesent erat lacus, aliquam quis sapien in, venenatis finibus enim. Proin et est malesuada, cursus nulla porttitor, molestie eros. Maecenas tempus id metus in dictum. Ut ornare ante non lobortis pretium. Morbi et justo iaculis urna molestie faucibus. Duis viverra sem nec rhoncus te"
                        "mpor. Quisque ligula purus, sagittis ut imperdiet quis, luctus quis arcu. Etiam neque ipsum, vulputate non tellus vitae, vestibulum hendrerit velit. Vivamus semper est purus, nec suscipit felis volutpat ut. Aenean placerat nulla ligula, vel imperdiet elit rhoncus a. Nam porttitor nec lorem quis gravida. Etiam placerat vel magna in ornare.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent"
                        ":0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right"
                        ":0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec ipsum elit, aliquam vitae mi ut, auctor sollicitudin libero. Maecenas quam purus, ullamcorper ut ultricies quis, accumsan vitae nisi. Donec vel bibendum orci. Sed lacinia, elit nec sagittis vehicula, magna odio facilisis lectus, non rutrum ante quam auctor eros. Sed ut tortor ac justo sollicitudin vehicula sed ac quam. Proin sed est non ipsum imperdiet sollicitudin eget sit a"
                        "met elit. Maecenas semper semper ullamcorper. Vestibulum venenatis auctor massa sed lobortis. Vestibulum sed nisl pharetra, porta purus eget, finibus arcu. Vestibulum quis pretium dui.\\n\\nMorbi sit amet rutrum nisi. Phasellus egestas sed est ac tempus. Suspendisse vel nisi finibus, fringilla eros eu, hendrerit arcu. Cras gravida est sed dui rutrum hendrerit. Aliquam tortor lectus, pulvinar a auctor sit amet, finibus in nunc. Nulla lectus elit, accumsan vitae augue eu, vestibulum condimentum metus. Duis fringilla mollis nisi, sit amet sollicitudin ante vestibulum nec. Aliquam erat volutpat. Donec commodo egestas lorem, at mattis felis ornare a. Pellentesque maximus non leo nec dignissim. Vestibulum a tellus eget quam sodales molestie vel non erat. Nunc sed dolor in neque cursus viverra.\\n\\nDonec vitae elit iaculis velit placerat mollis quis quis velit. Nunc scelerisque dignissim molestie. Praesent dignissim posuere nulla non tempor. Nulla scelerisque ultrices quam congue sodales. Donec sed purus a odio dign"
                        "issim mollis. Pellentesque tempus enim odio. Maecenas interdum ullamcorper sem sed molestie. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Sed gravida sapien ac pellentesque rutrum. Praesent venenatis elit ex, vitae accumsan neque sollicitudin id. Ut rhoncus consectetur fermentum. Donec pulvinar sem lacinia neque malesuada maximus nec a odio. Nunc venenatis lectus sed nunc malesuada porta. Nunc pellentesque fringilla est et molestie. Sed nisi sem, varius a ipsum a, tempor tempor ligula.\\n\\nDonec imperdiet venenatis tortor at luctus. Proin non justo pretium mauris faucibus consequat non quis neque. Mauris tempor congue suscipit. Nunc mi dui, scelerisque et ullamcorper sed, volutpat nec massa. Maecenas sit amet tristique leo. Suspendisse potenti. Donec nibh nisl, fringilla sed ligula vel, fermentum molestie diam.\\n\\nProin vestibulum lorem quis quam suscipit, et efficitur mi commodo. Praesent ac metus erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultri"
                        "ces posuere cubilia curae; Praesent erat lacus, aliquam quis sapien in, venenatis finibus enim. Proin et est malesuada, cursus nulla porttitor, molestie eros. Maecenas tempus id metus in dictum. Ut ornare ante non lobortis pretium. Morbi et justo iaculis urna molestie faucibus. Duis viverra sem nec rhoncus tempor. Quisque ligula purus, sagittis ut imperdiet quis, luctus quis arcu. Etiam neque ipsum, vulputate non tellus vitae, vestibulum hendrerit velit. Vivamus semper est purus, nec suscipit felis volutpat ut. Aenean placerat nulla ligula, vel imperdiet elit rhoncus a. Nam porttitor nec lorem quis gravida. Etiam placerat vel magna in ornare.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p st"
                        "yle=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; f"
                        "ont-size:12pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec ipsum elit, aliquam vitae mi ut, auctor sollicitudin libero. Maecenas quam purus, ullamcorper ut ultricies quis, accumsan vitae nisi. Donec vel bibendum orci. Sed lacinia, elit nec sagittis vehicula, magna odio facilisis lectus, non rutrum ante quam auctor eros. Sed ut tortor ac justo sollicitudin vehicula sed ac quam. Proin sed est non ipsum imperdiet sollicitudin eget sit amet elit. Maecenas semper semper ullamcorper. Vestibulum venenatis auctor massa sed lobortis. Vestibulum sed nisl pharetra, porta purus eget, finibus arcu. Vestibulum quis pretium dui.\\n\\nMorbi sit amet rutrum nisi. Phasellus egestas sed est ac tempus. Suspendisse vel nisi finibus, fringilla eros eu, hendrerit arcu. Cras gravida est sed dui rutrum hendrerit. Aliquam tortor lectus, pulvinar a a"
                        "uctor sit amet, finibus in nunc. Nulla lectus elit, accumsan vitae augue eu, vestibulum condimentum metus. Duis fringilla mollis nisi, sit amet sollicitudin ante vestibulum nec. Aliquam erat volutpat. Donec commodo egestas lorem, at mattis felis ornare a. Pellentesque maximus non leo nec dignissim. Vestibulum a tellus eget quam sodales molestie vel non erat. Nunc sed dolor in neque cursus viverra.\\n\\nDonec vitae elit iaculis velit placerat mollis quis quis velit. Nunc scelerisque dignissim molestie. Praesent dignissim posuere nulla non tempor. Nulla scelerisque ultrices quam congue sodales. Donec sed purus a odio dignissim mollis. Pellentesque tempus enim odio. Maecenas interdum ullamcorper sem sed molestie. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Sed gravida sapien ac pellentesque rutrum. Praesent venenatis elit ex, vitae accumsan neque sollicitudin id. Ut rhoncus consectetur fermentum. Donec pulvinar sem lacinia neque malesuada maximus nec a odio. Nunc venena"
                        "tis lectus sed nunc malesuada porta. Nunc pellentesque fringilla est et molestie. Sed nisi sem, varius a ipsum a, tempor tempor ligula.\\n\\nDonec imperdiet venenatis tortor at luctus. Proin non justo pretium mauris faucibus consequat non quis neque. Mauris tempor congue suscipit. Nunc mi dui, scelerisque et ullamcorper sed, volutpat nec massa. Maecenas sit amet tristique leo. Suspendisse potenti. Donec nibh nisl, fringilla sed ligula vel, fermentum molestie diam.\\n\\nProin vestibulum lorem quis quam suscipit, et efficitur mi commodo. Praesent ac metus erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Praesent erat lacus, aliquam quis sapien in, venenatis finibus enim. Proin et est malesuada, cursus nulla porttitor, molestie eros. Maecenas tempus id metus in dictum. Ut ornare ante non lobortis pretium. Morbi et justo iaculis urna molestie faucibus. Duis viverra sem nec rhoncus tempor. Quisque ligula purus, sagittis ut imperdiet quis, luctus quis arcu. Etiam neque ip"
                        "sum, vulputate non tellus vitae, vestibulum hendrerit velit. Vivamus semper est purus, nec suscipit felis volutpat ut. Aenean placerat nulla ligula, vel imperdiet elit rhoncus a. Nam porttitor nec lorem quis gravida. Etiam placerat vel magna in ornare.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec ipsum eli"
                        "t, aliquam vitae mi ut, auctor sollicitudin libero. Maecenas quam purus, ullamcorper ut ultricies quis, accumsan vitae nisi. Donec vel bibendum orci. Sed lacinia, elit nec sagittis vehicula, magna odio facilisis lectus, non rutrum ante quam auctor eros. Sed ut tortor ac justo sollicitudin vehicula sed ac quam. Proin sed est non ipsum imperdiet sollicitudin eget sit amet elit. Maecenas semper semper ullamcorper. Vestibulum venenatis auctor massa sed lobortis. Vestibulum sed nisl pharetra, porta purus eget, finibus arcu. Vestibulum quis pretium dui.\\n\\nMorbi sit amet rutrum nisi. Phasellus egestas sed est ac tempus. Suspendisse vel nisi finibus, fringilla eros eu, hendrerit arcu. Cras gravida est sed dui rutrum hendrerit. Aliquam tortor lectus, pulvinar a auctor sit amet, finibus in nunc. Nulla lectus elit, accumsan vitae augue eu, vestibulum condimentum metus. Duis fringilla mollis nisi, sit amet sollicitudin ante vestibulum nec. Aliquam erat volutpat. Donec commodo egestas lorem, at mattis felis ornare a. Pe"
                        "llentesque maximus non leo nec dignissim. Vestibulum a tellus eget quam sodales molestie vel non erat. Nunc sed dolor in neque cursus viverra.\\n\\nDonec vitae elit iaculis velit placerat mollis quis quis velit. Nunc scelerisque dignissim molestie. Praesent dignissim posuere nulla non tempor. Nulla scelerisque ultrices quam congue sodales. Donec sed purus a odio dignissim mollis. Pellentesque tempus enim odio. Maecenas interdum ullamcorper sem sed molestie. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Sed gravida sapien ac pellentesque rutrum. Praesent venenatis elit ex, vitae accumsan neque sollicitudin id. Ut rhoncus consectetur fermentum. Donec pulvinar sem lacinia neque malesuada maximus nec a odio. Nunc venenatis lectus sed nunc malesuada porta. Nunc pellentesque fringilla est et molestie. Sed nisi sem, varius a ipsum a, tempor tempor ligula.\\n\\nDonec imperdiet venenatis tortor at luctus. Proin non justo pretium mauris faucibus consequat non quis neque. Mauris "
                        "tempor congue suscipit. Nunc mi dui, scelerisque et ullamcorper sed, volutpat nec massa. Maecenas sit amet tristique leo. Suspendisse potenti. Donec nibh nisl, fringilla sed ligula vel, fermentum molestie diam.\\n\\nProin vestibulum lorem quis quam suscipit, et efficitur mi commodo. Praesent ac metus erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Praesent erat lacus, aliquam quis sapien in, venenatis finibus enim. Proin et est malesuada, cursus nulla porttitor, molestie eros. Maecenas tempus id metus in dictum. Ut ornare ante non lobortis pretium. Morbi et justo iaculis urna molestie faucibus. Duis viverra sem nec rhoncus tempor. Quisque ligula purus, sagittis ut imperdiet quis, luctus quis arcu. Etiam neque ipsum, vulputate non tellus vitae, vestibulum hendrerit velit. Vivamus semper est purus, nec suscipit felis volutpat ut. Aenean placerat nulla ligula, vel imperdiet elit rhoncus a. Nam porttitor nec lorem quis gravida. Etiam placerat vel magna in ornare.</span"
                        "></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:12pt;\">Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec ipsum elit, aliquam vitae mi ut, auctor sollicitudin libero. Maecenas quam purus, ullamcorper ut ultricies quis, accumsan vitae nisi. Donec vel bibendum orci. Sed lacinia, elit nec sagittis vehicula, magna odio facilisis lectus, non rutrum ante quam auctor eros. Sed ut tortor ac justo sollicitudin vehicula sed ac quam. Proin sed est non ipsum imperdiet sollicitudin eget sit amet elit. Maecenas semper semper ullamcorper. Vestibulum venenatis auctor massa sed lobortis. Vestibulum sed nisl pharetra, porta purus eget, finibus arcu. Vestibulum quis pretium dui.\\n\\nMorbi sit amet rutrum nisi. Phasellus egestas sed est"
                        " ac tempus. Suspendisse vel nisi finibus, fringilla eros eu, hendrerit arcu. Cras gravida est sed dui rutrum hendrerit. Aliquam tortor lectus, pulvinar a auctor sit amet, finibus in nunc. Nulla lectus elit, accumsan vitae augue eu, vestibulum condimentum metus. Duis fringilla mollis nisi, sit amet sollicitudin ante vestibulum nec. Aliquam erat volutpat. Donec commodo egestas lorem, at mattis felis ornare a. Pellentesque maximus non leo nec dignissim. Vestibulum a tellus eget quam sodales molestie vel non erat. Nunc sed dolor in neque cursus viverra.\\n\\nDonec vitae elit iaculis velit placerat mollis quis quis velit. Nunc scelerisque dignissim molestie. Praesent dignissim posuere nulla non tempor. Nulla scelerisque ultrices quam congue sodales. Donec sed purus a odio dignissim mollis. Pellentesque tempus enim odio. Maecenas interdum ullamcorper sem sed molestie. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Sed gravida sapien ac pellentesque rutrum. Praesent venenatis "
                        "elit ex, vitae accumsan neque sollicitudin id. Ut rhoncus consectetur fermentum. Donec pulvinar sem lacinia neque malesuada maximus nec a odio. Nunc venenatis lectus sed nunc malesuada porta. Nunc pellentesque fringilla est et molestie. Sed nisi sem, varius a ipsum a, tempor tempor ligula.\\n\\nDonec imperdiet venenatis tortor at luctus. Proin non justo pretium mauris faucibus consequat non quis neque. Mauris tempor congue suscipit. Nunc mi dui, scelerisque et ullamcorper sed, volutpat nec massa. Maecenas sit amet tristique leo. Suspendisse potenti. Donec nibh nisl, fringilla sed ligula vel, fermentum molestie diam.\\n\\nProin vestibulum lorem quis quam suscipit, et efficitur mi commodo. Praesent ac metus erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Praesent erat lacus, aliquam quis sapien in, venenatis finibus enim. Proin et est malesuada, cursus nulla porttitor, molestie eros. Maecenas tempus id metus in dictum. Ut ornare ante non lobortis pretium. Morbi et ju"
                        "sto iaculis urna molestie faucibus. Duis viverra sem nec rhoncus tempor. Quisque ligula purus, sagittis ut imperdiet quis, luctus quis arcu. Etiam neque ipsum, vulputate non tellus vitae, vestibulum hendrerit velit. Vivamus semper est purus, nec suscipit felis volutpat ut. Aenean placerat nulla ligula, vel imperdiet elit rhoncus a. Nam porttitor nec lorem quis gravida. Etiam placerat vel magna in ornare.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:12pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:10pt; font-weight:580;\"><br /></p></body></html>", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.loading_editor), QCoreApplication.translate("documentation_dialog", u"Loading Editor", None))
        self.textBrowser_2.setHtml(QCoreApplication.translate("documentation_dialog", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:10pt; font-weight:580;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:22pt; font-weight:580;\">SoundEvent editor</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; "
                        "text-indent:0px; font-size:22pt; font-weight:580;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-size:11pt;\">Ah yes.</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:10pt; font-weight:580;\"><br /></p></body></html>", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QCoreApplication.translate("documentation_dialog", u"SoundEvent Editor", None))
    # retranslateUi

