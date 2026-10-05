# -*- coding: utf-8 -*-

################################################################################
## Form generated for About dialog
################################################################################

import os
from PySide6.QtCore import (QCoreApplication, QMetaObject, QSize, Qt)
from PySide6.QtGui import (QFont, QIcon, QPixmap, QCursor)
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout)
from gui import resources_rc


class Ui_documentation_dialog(object):
    def setupUi(self, documentation_dialog):
        if not documentation_dialog.objectName():
            documentation_dialog.setObjectName(u"documentation_dialog")
        documentation_dialog.resize(680, 710)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(documentation_dialog.sizePolicy().hasHeightForWidth())
        documentation_dialog.setSizePolicy(sizePolicy)
        documentation_dialog.setMinimumSize(QSize(680, 710))
        documentation_dialog.setMaximumSize(QSize(680, 710))
        documentation_dialog.setFixedSize(QSize(680, 710))
        documentation_dialog.setProperty("h5Component", "aboutDialog")
        documentation_dialog.setSizeGripEnabled(False)
        documentation_dialog.setModal(False)

        self.verticalLayout = QVBoxLayout(documentation_dialog)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(16, 12, 16, 12)

        # Header Frame (Hammer 5 Tools Header Logo)
        self.frame = QFrame(documentation_dialog)
        self.frame.setObjectName(u"frame")
        self.frame.setProperty("h5Component", "aboutHeaderFrame")
        self.frame.setMinimumSize(QSize(0, 160))
        self.frame.setMaximumSize(QSize(16777215, 160))
        self.frame.setFrameShape(QFrame.Shape.NoFrame)
        self.frame.setFrameShadow(QFrame.Shadow.Plain)
        self.verticalLayout_3 = QVBoxLayout(self.frame)
        self.verticalLayout_3.setSpacing(6)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)

        # Original Logo Label
        self.label = QLabel(self.frame)
        self.label.setObjectName(u"label")
        self.label.setProperty("h5Component", "aboutLogoLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalLayout_3.addWidget(self.label)

        # Version Label
        self.version = QLabel(self.frame)
        self.version.setObjectName(u"version")
        self.version.setProperty("h5Component", "aboutVersionLabel")
        self.version.setMaximumSize(QSize(16777215, 20))
        font = QFont()
        font.setFamilies([u"Segoe UI Black", u"Segoe UI"])
        font.setPointSize(12)
        font.setBold(True)
        self.version.setFont(font)
        self.version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalLayout_3.addWidget(self.version)

        self.verticalLayout.addWidget(self.frame)

        # Main Content Frame
        self.content_frame = QFrame(documentation_dialog)
        self.content_frame.setObjectName(u"content_frame")
        self.content_frame.setProperty("h5Component", "aboutContentFrame")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(12, 12, 12, 12)

        # Video Card with YouTube Preview
        self.video_card = QFrame(self.content_frame)
        self.video_card.setObjectName(u"video_card")
        self.video_card.setProperty("h5Component", "aboutVideoCard")
        self.video_layout = QHBoxLayout(self.video_card)
        self.video_layout.setSpacing(12)
        self.video_layout.setContentsMargins(10, 10, 10, 10)

        # YouTube Thumbnail Preview Label
        self.yt_preview_label = QLabel(self.video_card)
        self.yt_preview_label.setObjectName(u"yt_preview_label")
        self.yt_preview_label.setProperty("h5Component", "aboutYtPreview")
        self.yt_preview_label.setFixedSize(QSize(264, 148))
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
        self.video_title.setProperty("h5Component", "aboutVideoTitle")
        font_vtitle = QFont()
        font_vtitle.setFamilies([u"Segoe UI"])
        font_vtitle.setPointSize(10.5)
        font_vtitle.setBold(True)
        self.video_title.setFont(font_vtitle)
        self.video_info_layout.addWidget(self.video_title)

        self.video_desc = QLabel(self.video_card)
        self.video_desc.setObjectName(u"video_desc")
        self.video_desc.setProperty("h5Component", "aboutVideoDesc")
        font_vdesc = QFont()
        font_vdesc.setFamilies([u"Segoe UI"])
        font_vdesc.setPointSize(8.5)
        self.video_desc.setFont(font_vdesc)
        self.video_desc.setWordWrap(True)
        self.video_info_layout.addWidget(self.video_desc)

        self.video_info_layout.addStretch()

        self.watch_video_button = QPushButton(self.video_card)
        self.watch_video_button.setObjectName(u"watch_video_button")
        self.watch_video_button.setProperty("h5Component", "aboutWatchVideoButton")
        self.watch_video_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon_play = QIcon()
        icon_play.addFile(u":/valve_common/icons/tools/common/control_play.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.watch_video_button.setIcon(icon_play)
        self.watch_video_button.setIconSize(QSize(18, 18))
        self.video_info_layout.addWidget(self.watch_video_button)

        self.video_layout.addLayout(self.video_info_layout)
        self.content_layout.addWidget(self.video_card)

        # Guides Section
        self.guides_card = QFrame(self.content_frame)
        self.guides_card.setObjectName(u"guides_card")
        self.guides_card.setProperty("h5Component", "aboutGuidesCard")
        self.guides_layout = QVBoxLayout(self.guides_card)
        self.guides_layout.setSpacing(8)
        self.guides_layout.setContentsMargins(10, 10, 10, 10)

        self.guides_header = QLabel(self.guides_card)
        self.guides_header.setObjectName(u"guides_header")
        self.guides_header.setProperty("h5Component", "aboutGuidesHeader")
        font_ghead = QFont()
        font_ghead.setFamilies([u"Segoe UI"])
        font_ghead.setPointSize(10.5)
        font_ghead.setBold(True)
        self.guides_header.setFont(font_ghead)
        self.guides_layout.addWidget(self.guides_header)

        # Buttons layout for documentation guides
        self.guides_btn_layout = QHBoxLayout()
        self.guides_btn_layout.setSpacing(8)

        icon_doc = QIcon()
        icon_doc.addFile(u":/icons/developer_guide_16dp.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)

        self.open_documentation_button = QPushButton(self.guides_card)
        self.open_documentation_button.setObjectName(u"open_documentation_button")
        self.open_documentation_button.setProperty("h5Component", "aboutGuideButton")
        self.open_documentation_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_documentation_button.setIcon(icon_doc)
        self.open_documentation_button.setIconSize(QSize(18, 18))
        self.guides_btn_layout.addWidget(self.open_documentation_button)

        self.open_radio_sound_guide_button = QPushButton(self.guides_card)
        self.open_radio_sound_guide_button.setObjectName(u"open_radio_sound_guide_button")
        self.open_radio_sound_guide_button.setProperty("h5Component", "aboutGuideButton")
        self.open_radio_sound_guide_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_radio_sound_guide_button.setIcon(icon_doc)
        self.open_radio_sound_guide_button.setIconSize(QSize(18, 18))
        self.guides_btn_layout.addWidget(self.open_radio_sound_guide_button)

        self.open_smart_props_guide_button = QPushButton(self.guides_card)
        self.open_smart_props_guide_button.setObjectName(u"open_smart_props_guide_button")
        self.open_smart_props_guide_button.setProperty("h5Component", "aboutGuideButton")
        self.open_smart_props_guide_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_smart_props_guide_button.setIcon(icon_doc)
        self.open_smart_props_guide_button.setIconSize(QSize(18, 18))
        self.guides_btn_layout.addWidget(self.open_smart_props_guide_button)

        self.guides_layout.addLayout(self.guides_btn_layout)
        self.content_layout.addWidget(self.guides_card)

        # Support Section
        self.support_card = QFrame(self.content_frame)
        self.support_card.setObjectName(u"support_card")
        self.support_card.setProperty("h5Component", "aboutSupportCard")
        self.support_layout = QHBoxLayout(self.support_card)
        self.support_layout.setSpacing(12)
        self.support_layout.setContentsMargins(10, 8, 10, 8)

        self.support_icon_label = QLabel(self.support_card)
        self.support_icon_label.setObjectName(u"support_icon_label")
        self.support_icon_label.setProperty("h5Component", "aboutSupportIcon")
        self.support_icon_label.setFixedSize(QSize(28, 28))
        self.support_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.support_icon_label.setPixmap(
            QPixmap(u":/icons/icons/blender_logo.png").scaled(
                28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        )
        self.support_layout.addWidget(self.support_icon_label)

        self.support_text_layout = QVBoxLayout()
        self.support_text_layout.setSpacing(2)

        self.support_header = QLabel(self.support_card)
        self.support_header.setObjectName(u"support_header")
        self.support_header.setProperty("h5Component", "aboutSupportHeader")
        font_shead = QFont()
        font_shead.setFamilies([u"Segoe UI"])
        font_shead.setPointSize(9.5)
        font_shead.setBold(True)
        self.support_header.setFont(font_shead)
        self.support_text_layout.addWidget(self.support_header)

        self.support_desc = QLabel(self.support_card)
        self.support_desc.setObjectName(u"support_desc")
        self.support_desc.setProperty("h5Component", "aboutSupportDesc")
        font_sdesc = QFont()
        font_sdesc.setFamilies([u"Segoe UI"])
        font_sdesc.setPointSize(8.5)
        self.support_desc.setFont(font_sdesc)
        self.support_desc.setWordWrap(True)
        self.support_text_layout.addWidget(self.support_desc)

        self.support_layout.addLayout(self.support_text_layout, 1)

        self.support_button = QPushButton(self.support_card)
        self.support_button.setObjectName(u"support_button")
        self.support_button.setProperty("h5Component", "aboutSupportButton")
        self.support_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon_gumroad = QIcon()
        icon_gumroad.addFile(u":/icons/icons/gumroad_logo.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.support_button.setIcon(icon_gumroad)
        self.support_button.setIconSize(QSize(18, 18))
        self.support_layout.addWidget(self.support_button)

        self.content_layout.addWidget(self.support_card)

        # Special Thanks Inline Mention
        self.special_thanks_label = QLabel(self.content_frame)
        self.special_thanks_label.setObjectName(u"special_thanks_label")
        self.special_thanks_label.setProperty("h5Component", "aboutSpecialThanks")
        font_thanks = QFont()
        font_thanks.setFamilies([u"Segoe UI"])
        font_thanks.setPointSize(9)
        self.special_thanks_label.setFont(font_thanks)
        self.special_thanks_label.setTextFormat(Qt.TextFormat.RichText)
        self.special_thanks_label.setOpenExternalLinks(True)
        self.special_thanks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.special_thanks_label)

        self.verticalLayout.addWidget(self.content_frame)

        # Bottom Frame
        self.frame_3 = QFrame(documentation_dialog)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setProperty("h5Component", "aboutBottomBar")
        self.frame_3.setMaximumSize(QSize(16777215, 44))
        self.frame_3.setFrameShape(QFrame.Shape.NoFrame)
        self.frame_3.setFrameShadow(QFrame.Shadow.Plain)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_3)
        self.horizontalLayout_3.setSpacing(8)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 4, 0, 0)

        # Small button to toggle don't show on startup
        self.dont_show_button = QPushButton(self.frame_3)
        self.dont_show_button.setObjectName(u"dont_show_button")
        self.dont_show_button.setProperty("h5Component", "aboutDontShowButton")
        self.dont_show_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.horizontalLayout_3.addWidget(self.dont_show_button)
        self.horizontalLayout_3.addStretch()

        self.request_a_new_feature_button = QPushButton(self.frame_3)
        self.request_a_new_feature_button.setObjectName(u"request_a_new_feature_button")
        self.request_a_new_feature_button.setProperty("h5Component", "aboutActionButton")
        self.request_a_new_feature_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/icons/emoji_objects_24dp.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.request_a_new_feature_button.setIcon(icon1)
        self.request_a_new_feature_button.setIconSize(QSize(18, 18))
        self.horizontalLayout_3.addWidget(self.request_a_new_feature_button)

        self.close_button = QPushButton(self.frame_3)
        self.close_button.setObjectName(u"close_button")
        self.close_button.setProperty("h5Component", "aboutActionButton")
        self.close_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.horizontalLayout_3.addWidget(self.close_button)

        self.verticalLayout.addWidget(self.frame_3)

        self.retranslateUi(documentation_dialog)
        QMetaObject.connectSlotsByName(documentation_dialog)

    def retranslateUi(self, documentation_dialog):
        documentation_dialog.setWindowTitle(QCoreApplication.translate("documentation_dialog", u"About", None))
        self.label.setText("")
        self.version.setText(QCoreApplication.translate("documentation_dialog", u"Version: 1.0.0", None))

        self.video_title.setText(QCoreApplication.translate("documentation_dialog", u"CUSTOM LOADINGSCREEN - CS2 Mapping Tutorial", None))
        self.video_desc.setText(QCoreApplication.translate("documentation_dialog", u"In this video i'll show you how you can create a fully customized loadingscreen for your CounterStrike 2 map! Learn how to change the background, description and map icon of your custom CS2 map!", None))
        self.watch_video_button.setText(QCoreApplication.translate("documentation_dialog", u"Watch Tutorial on YouTube", None))

        self.guides_header.setText(QCoreApplication.translate("documentation_dialog", u"\U0001f4da Documentation & Guides", None))
        self.open_documentation_button.setText(QCoreApplication.translate("documentation_dialog", u"Documentation", None))
        self.open_radio_sound_guide_button.setText(QCoreApplication.translate("documentation_dialog", u"Radio Soundevent Guide", None))
        self.open_smart_props_guide_button.setText(QCoreApplication.translate("documentation_dialog", u"Smart Props Guide", None))

        self.support_header.setText(QCoreApplication.translate("documentation_dialog", u"If You Want to Support the Project", None))
        self.support_desc.setText(QCoreApplication.translate("documentation_dialog", u"Mallet is a Blender addon that brings cool Hammer features to Blender, such as Hotspot UV, viewport camera, and more.\nBuying this addon will support Hammer5Tools development.", None))
        self.support_button.setText(QCoreApplication.translate("documentation_dialog", u"Mallet on Gumroad", None))

        self.special_thanks_label.setText(QCoreApplication.translate("documentation_dialog", u'Special thanks: <a href="https://github.com/LaplaceTor" style="color: #61AFEF; text-decoration: none;">LaplaceTor</a>, <a href="https://github.com/Andrew900460" style="color: #61AFEF; text-decoration: none;">Andrew900460</a>', None))

        self.dont_show_button.setText(QCoreApplication.translate("documentation_dialog", u"Don't show on startup", None))
        self.request_a_new_feature_button.setText(QCoreApplication.translate("documentation_dialog", u"Feedback", None))
        self.close_button.setText(QCoreApplication.translate("documentation_dialog", u"Close", None))
