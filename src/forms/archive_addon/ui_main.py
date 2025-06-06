# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel,
    QListView, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)
import src.resources_rc as resources_rc

class Ui_export_and_import_addon_widget(object):
    def setupUi(self, export_and_import_addon_widget):
        if not export_and_import_addon_widget.objectName():
            export_and_import_addon_widget.setObjectName(u"export_and_import_addon_widget")
        export_and_import_addon_widget.resize(400, 600)
        export_and_import_addon_widget.setMinimumSize(QSize(400, 600))
        export_and_import_addon_widget.setMaximumSize(QSize(400, 600))
        self.verticalLayout = QVBoxLayout(export_and_import_addon_widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalSpacer_2 = QSpacerItem(20, 13, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer_2)

        self.skip_non_default_folders_in_content_checkbox = QCheckBox(export_and_import_addon_widget)
        self.skip_non_default_folders_in_content_checkbox.setObjectName(u"skip_non_default_folders_in_content_checkbox")

        self.verticalLayout.addWidget(self.skip_non_default_folders_in_content_checkbox)

        self.compiled_maps_checkbox = QCheckBox(export_and_import_addon_widget)
        self.compiled_maps_checkbox.setObjectName(u"compiled_maps_checkbox")
        self.compiled_maps_checkbox.setChecked(True)

        self.verticalLayout.addWidget(self.compiled_maps_checkbox)

        self.compiled_materials_checkbox = QCheckBox(export_and_import_addon_widget)
        self.compiled_materials_checkbox.setObjectName(u"compiled_materials_checkbox")
        self.compiled_materials_checkbox.setChecked(True)

        self.verticalLayout.addWidget(self.compiled_materials_checkbox)

        self.compiled_models_checkbox = QCheckBox(export_and_import_addon_widget)
        self.compiled_models_checkbox.setObjectName(u"compiled_models_checkbox")
        self.compiled_models_checkbox.setChecked(True)

        self.verticalLayout.addWidget(self.compiled_models_checkbox)

        self.verticalSpacer = QSpacerItem(20, 13, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.export_addon_button = QPushButton(export_and_import_addon_widget)
        self.export_addon_button.setObjectName(u"export_addon_button")
        self.export_addon_button.setMinimumSize(QSize(96, 0))
        self.export_addon_button.setStyleSheet(u"padding: 5px;")
        icon = QIcon()
        icon.addFile(u":/icons/upload_2_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.export_addon_button.setIcon(icon)
        self.export_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.export_addon_button)

        self.import_addon_button = QPushButton(export_and_import_addon_widget)
        self.import_addon_button.setObjectName(u"import_addon_button")
        self.import_addon_button.setMinimumSize(QSize(96, 0))
        self.import_addon_button.setStyleSheet(u"padding: 5px;")
        icon1 = QIcon()
        icon1.addFile(u":/icons/download_2_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.import_addon_button.setIcon(icon1)
        self.import_addon_button.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.import_addon_button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.size_display = QLabel(export_and_import_addon_widget)
        self.size_display.setObjectName(u"size_display")
        self.size_display.setMaximumSize(QSize(16777215, 32))

        self.verticalLayout.addWidget(self.size_display)

        self.size_of_files_list = QListView(export_and_import_addon_widget)
        self.size_of_files_list.setObjectName(u"size_of_files_list")

        self.verticalLayout.addWidget(self.size_of_files_list)


        self.retranslateUi(export_and_import_addon_widget)

        QMetaObject.connectSlotsByName(export_and_import_addon_widget)
    # setupUi

    def retranslateUi(self, export_and_import_addon_widget):
        export_and_import_addon_widget.setWindowTitle(QCoreApplication.translate("export_and_import_addon_widget", u"Export and import", None))
        self.skip_non_default_folders_in_content_checkbox.setText(QCoreApplication.translate("export_and_import_addon_widget", u"skip non-default folders in content", None))
        self.compiled_maps_checkbox.setText(QCoreApplication.translate("export_and_import_addon_widget", u"compiled maps", None))
        self.compiled_materials_checkbox.setText(QCoreApplication.translate("export_and_import_addon_widget", u"compiled materials", None))
        self.compiled_models_checkbox.setText(QCoreApplication.translate("export_and_import_addon_widget", u"compiled models", None))
#if QT_CONFIG(tooltip)
        self.export_addon_button.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.export_addon_button.setText(QCoreApplication.translate("export_and_import_addon_widget", u"Export addon", None))
#if QT_CONFIG(tooltip)
        self.import_addon_button.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.import_addon_button.setText(QCoreApplication.translate("export_and_import_addon_widget", u"Import addon", None))
        self.size_display.setText(QCoreApplication.translate("export_and_import_addon_widget", u"Output  size before archiving:", None))
    # retranslateUi

