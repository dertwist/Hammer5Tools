# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
################################################################################

import os
from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget, QScrollArea)
import resources_rc

class Ui_documentation_dialog(object):
    def setupUi(self, documentation_dialog):
        if not documentation_dialog.objectName():
            documentation_dialog.setObjectName(u"documentation_dialog")
        documentation_dialog.resize(680, 670)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(documentation_dialog.sizePolicy().hasHeightForWidth())
        documentation_dialog.setSizePolicy(sizePolicy)
        documentation_dialog.setMinimumSize(QSize(680, 670))
        documentation_dialog.setMaximumSize(QSize(680, 670))
        documentation_dialog.setStyleSheet(u"background-color: #1C1C1C; color: #E3E3E3;")
        documentation_dialog.setSizeGripEnabled(False)
        documentation_dialog.setModal(False)

        self.verticalLayout = QVBoxLayout(documentation_dialog)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(16, 12, 16, 12)

        # Header Frame (Hammer 5 Tools Header Logo with sharp borders)
        self.frame = QFrame(documentation_dialog)
        self.frame.setObjectName(u"frame")
        self.frame.setMinimumSize(QSize(0, 160))
        self.frame.setMaximumSize(QSize(16777215, 160))
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)

        # Original Logo Label
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setStyleSheet(u"image: url(:/images/help/header.png);")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalLayout_3.addWidget(self.label)

        # Version Label
        self.version = QLabel(self.frame)
        self.version.setObjectName(u"version")
        self.version.setMaximumSize(QSize(16777215, 20))
        font = QFont()
        font.setFamilies([u"Segoe UI Black", u"Segoe UI"])
        font.setPointSize(12)
        font.setBold(True)
        self.version.setFont(font)
        self.version.setStyleSheet(u"color: #9D9D9D;")
        self.version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalLayout_3.addWidget(self.version)

        self.verticalLayout.addWidget(self.frame)

        # Main Content Frame (Tutorials & YouTube Video Widget with sharp borders)
        self.content_frame = QFrame(documentation_dialog)
        self.content_frame.setObjectName(u"content_frame")
        self.content_frame.setStyleSheet(u"background-color: #242424; border: 1px solid #333333; border-radius: 0px;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(12, 12, 12, 12)

        # Video Card with YouTube Preview (sharp borders)
        self.video_card = QFrame(self.content_frame)
        self.video_card.setObjectName(u"video_card")
        self.video_card.setStyleSheet(u"background-color: #1E222A; border: 1px solid #333A48; border-radius: 0px;")
        self.video_layout = QHBoxLayout(self.video_card)
        self.video_layout.setSpacing(12)
        self.video_layout.setContentsMargins(10, 10, 10, 10)

        # YouTube Thumbnail Preview Label (sharp borders)
        self.yt_preview_label = QLabel(self.video_card)
        self.yt_preview_label.setObjectName(u"yt_preview_label")
        self.yt_preview_label.setFixedSize(QSize(264, 148))
        self.yt_preview_label.setStyleSheet(u"border: 1px solid #3E4451; border-radius: 0px; background-color: #000000;")
        self.yt_preview_label.setScaledContents(True)
        self.yt_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load local preview image if available
        preview_path = os.path.join(os.path.dirname(__file__), "yt_preview.jpg")
        if os.path.exists(preview_path):
            self.yt_preview_label.setPixmap(QPixmap(preview_path))

        self.video_layout.addWidget(self.yt_preview_label)

        # Video Info & Button Side Layout
        self.video_info_layout = QVBoxLayout()
        self.video_info_layout.setSpacing(4)
        
        self.video_title = QLabel(self.video_card)
        self.video_title.setObjectName(u"video_title")
        font_vtitle = QFont()
        font_vtitle.setFamilies([u"Segoe UI"])
        font_vtitle.setPointSize(10.5)
        font_vtitle.setBold(True)
        self.video_title.setFont(font_vtitle)
        self.video_title.setStyleSheet(u"color: #61AFEF; border: none;")
        self.video_info_layout.addWidget(self.video_title)

        self.video_desc = QLabel(self.video_card)
        self.video_desc.setObjectName(u"video_desc")
        font_vdesc = QFont()
        font_vdesc.setFamilies([u"Segoe UI"])
        font_vdesc.setPointSize(8.5)
        self.video_desc.setFont(font_vdesc)
        self.video_desc.setWordWrap(True)
        self.video_desc.setStyleSheet(u"color: #ABB2BF; border: none;")
        self.video_info_layout.addWidget(self.video_desc)

        self.video_info_layout.addStretch()

        self.watch_video_button = QPushButton(self.video_card)
        self.watch_video_button.setObjectName(u"watch_video_button")
        self.watch_video_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.watch_video_button.setStyleSheet(u"""
            QPushButton {
                font: 600 9.5pt "Segoe UI";
                border: 1px solid #E05252;
                border-radius: 0px;
                padding: 6px 14px;
                color: #FFFFFF;
                background-color: #C0392B;
            }
            QPushButton:hover {
                background-color: #E74C3C;
                border-color: #FF6B6B;
            }
            QPushButton:pressed {
                background-color: #962D22;
            }
        """)
        icon_play = QIcon()
        icon_play.addFile(u":/icons/play_arrow_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.watch_video_button.setIcon(icon_play)
        self.watch_video_button.setIconSize(QSize(18, 18))
        self.video_info_layout.addWidget(self.watch_video_button)

        self.video_layout.addLayout(self.video_info_layout)
        self.content_layout.addWidget(self.video_card)

        # Guides Section (sharp borders)
        self.guides_card = QFrame(self.content_frame)
        self.guides_card.setObjectName(u"guides_card")
        self.guides_card.setStyleSheet(u"background-color: #1E1E1E; border: 1px solid #333333; border-radius: 0px;")
        self.guides_layout = QVBoxLayout(self.guides_card)
        self.guides_layout.setSpacing(8)
        self.guides_layout.setContentsMargins(10, 10, 10, 10)

        self.guides_header = QLabel(self.guides_card)
        self.guides_header.setObjectName(u"guides_header")
        font_ghead = QFont()
        font_ghead.setFamilies([u"Segoe UI"])
        font_ghead.setPointSize(10.5)
        font_ghead.setBold(True)
        self.guides_header.setFont(font_ghead)
        self.guides_header.setStyleSheet(u"color: #E5C07B; border: none;")
        self.guides_layout.addWidget(self.guides_header)

        # Buttons layout for documentation guides
        self.guides_btn_layout = QHBoxLayout()
        self.guides_btn_layout.setSpacing(8)

        self.btn_style = u"""
            QPushButton {
                font: 580 9pt "Segoe UI";
                border: 1px solid #4E5563;
                border-radius: 0px;
                padding: 6px 12px;
                color: #E3E3E3;
                background-color: #282C34;
            }
            QPushButton:hover {
                background-color: #3E4451;
                color: #FFFFFF;
                border-color: #61AFEF;
            }
            QPushButton:pressed {
                background-color: #1E222A;
            }
        """

        self.open_documentation_button = QPushButton(self.guides_card)
        self.open_documentation_button.setObjectName(u"open_documentation_button")
        self.open_documentation_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_documentation_button.setStyleSheet(self.btn_style)
        icon_doc = QIcon()
        icon_doc.addFile(u":/icons/developer_guide_16dp_9D9D9D_FILL0_wght400_GRAD0_opsz20.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.open_documentation_button.setIcon(icon_doc)
        self.open_documentation_button.setIconSize(QSize(18, 18))
        self.guides_btn_layout.addWidget(self.open_documentation_button)

        self.open_radio_sound_guide_button = QPushButton(self.guides_card)
        self.open_radio_sound_guide_button.setObjectName(u"open_radio_sound_guide_button")
        self.open_radio_sound_guide_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_radio_sound_guide_button.setStyleSheet(self.btn_style)
        self.open_radio_sound_guide_button.setIcon(icon_doc)
        self.open_radio_sound_guide_button.setIconSize(QSize(18, 18))
        self.guides_btn_layout.addWidget(self.open_radio_sound_guide_button)

        self.guides_layout.addLayout(self.guides_btn_layout)
        self.content_layout.addWidget(self.guides_card)
        self.verticalLayout.addWidget(self.content_frame)

        # Bottom Frame
        self.frame_3 = QFrame(documentation_dialog)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMaximumSize(QSize(16777215, 44))
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_3.setSpacing(8)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 4, 0, 0)

        # Small button to toggle don't show on startup (sharp borders)
        self.dont_show_button = QPushButton(self.frame_3)
        self.dont_show_button.setObjectName(u"dont_show_button")
        self.dont_show_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.dont_show_button.setStyleSheet(u"""
            QPushButton {
                font: 500 8.5pt "Segoe UI";
                border: 1px solid #444444;
                border-radius: 0px;
                padding: 4px 8px;
                color: #B0B0B0;
                background-color: #242424;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #FFFFFF;
                border-color: #666666;
            }
            QPushButton:checked {
                background-color: #3A2323;
                border-color: #A54242;
                color: #FF9999;
            }
        """)
        self.horizontalLayout_3.addWidget(self.dont_show_button)
        self.horizontalLayout_3.addStretch()

        self.request_a_new_feature_button = QPushButton(self.frame_3)
        self.request_a_new_feature_button.setObjectName(u"request_a_new_feature_button")
        self.request_a_new_feature_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.request_a_new_feature_button.setStyleSheet(u"""
            QPushButton {
                font: 580 9pt "Segoe UI";
                border: 1px solid #505050;
                border-radius: 0px;
                padding: 4px 12px;
                color: #E3E3E3;
                background-color: #242424;
            }
            QPushButton:hover {
                background-color: #414956;
                color: white;
            }
            QPushButton:pressed {
                background-color: #1C1C1C;
            }
        """)
        icon1 = QIcon()
        icon1.addFile(u":/icons/emoji_objects_24dp_9D9D9D_FILL0_wght400_GRAD0_opsz24.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.request_a_new_feature_button.setIcon(icon1)
        self.request_a_new_feature_button.setIconSize(QSize(18, 18))
        self.horizontalLayout_3.addWidget(self.request_a_new_feature_button)

        self.close_button = QPushButton(self.frame_3)
        self.close_button.setObjectName(u"close_button")
        self.close_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_button.setStyleSheet(u"""
            QPushButton {
                font: 580 9pt "Segoe UI";
                border: 1px solid #505050;
                border-radius: 0px;
                padding: 4px 14px;
                color: #E3E3E3;
                background-color: #242424;
            }
            QPushButton:hover {
                background-color: #414956;
                color: white;
            }
            QPushButton:pressed {
                background-color: #1C1C1C;
            }
        """)
        self.horizontalLayout_3.addWidget(self.close_button)

        self.verticalLayout.addWidget(self.frame_3)

        self.retranslateUi(documentation_dialog)
        QMetaObject.connectSlotsByName(documentation_dialog)

    def retranslateUi(self, documentation_dialog):
        documentation_dialog.setWindowTitle(QCoreApplication.translate("documentation_dialog", u"About", None))
        self.label.setText("")
        self.version.setText(QCoreApplication.translate("documentation_dialog", u"Version: 1.0.0", None))
        
        self.video_title.setText(QCoreApplication.translate("documentation_dialog", u"CUSTOM LOADINGSCREEN - CS2 Mapping Tutorial", None))
        self.video_desc.setText(QCoreApplication.translate("documentation_dialog", u"In this video i'll show you how you can create a fully customized loadingscreen for your CounterStrike 2 map! Learn how to change the background, description and map icon of your custom CS2 map!\n\nTip: Setup the cameras in the early stages of your map so you can capture the history and progress of your map from start to finish!", None))
        self.watch_video_button.setText(QCoreApplication.translate("documentation_dialog", u"▶ Watch Tutorial on YouTube", None))

        self.guides_header.setText(QCoreApplication.translate("documentation_dialog", u"📚 Documentation & Guides", None))
        self.open_documentation_button.setText(QCoreApplication.translate("documentation_dialog", u"Documentation", None))
        self.open_radio_sound_guide_button.setText(QCoreApplication.translate("documentation_dialog", u"Radio Soundevent Guide", None))


        self.dont_show_button.setText(QCoreApplication.translate("documentation_dialog", u"Don't show on startup", None))
        self.request_a_new_feature_button.setText(QCoreApplication.translate("documentation_dialog", u"Feedback", None))
        self.close_button.setText(QCoreApplication.translate("documentation_dialog", u"Close", None))
