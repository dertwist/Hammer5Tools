import os
import shutil
import re
from PySide6.QtCore import Qt, QSize, QThreadPool, QRunnable, QObject, Signal, QFileSystemWatcher, QPointF, QRect, QRectF
from PySide6.QtGui import QPixmap, QIcon, QAction, QWheelEvent, QMouseEvent, QDragEnterEvent, QDropEvent, QColor, QPainter, QFont, QFontMetrics, QPen, QLinearGradient, QBrush, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTreeView,
    QFileSystemModel,
    QSplitter,
    QLabel,
    QScrollArea,
    QMenu,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QAbstractItemView,
    QPushButton,
    QFrame,
    QProgressBar,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsBlurEffect
)
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtSvg import QSvgRenderer
from src.settings.main import debug
import sys

class NoWheelScrollArea(QScrollArea):
    """
    Custom scroll area that ignores wheel events to delegate zooming to the main viewport instead.
    """
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

_fonts_loaded = False
_CS2_FONT_FILES = [
    "notosans-regular.ttf",
    "notosans-bold.ttf",
]
def ensure_cs2_fonts_loaded():
    global _fonts_loaded
    if _fonts_loaded:
        return
    fonts_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "fonts"))
    if os.path.exists(fonts_dir):
        for f in _CS2_FONT_FILES:
            font_path = os.path.join(fonts_dir, f)
            if os.path.exists(font_path):
                fid = QFontDatabase.addApplicationFont(font_path)
                if fid >= 0:
                    debug(f"Registered CS2 font: {f} -> {QFontDatabase.applicationFontFamilies(fid)}")
                else:
                    debug(f"Failed to register CS2 font: {f}")
    _fonts_loaded = True

def is_generic_camera_name(name: str) -> bool:
    if not name:
        return True
    return bool(re.match(r'^cam(?:era)?[\s_]*\d*$', name.strip(), re.IGNORECASE))

def extract_camera_name(filename: str, addon_name: str = None) -> str:
    """
    Extracts clean camera name from a filename (e.g. 'de_firewatch_Donut_0000.png' -> 'Donut').
    Returns empty string for generic camera names like cam0, cam1, cam3, camera1.
    """
    if not filename:
        return ""
    base = os.path.splitext(os.path.basename(filename))[0]
    base_no_seq = re.sub(r'_\d+$', '', base)

    # 1. Look for explicit camera keyword like cam3, camera2, cam_01, camera_3
    cam_match = re.search(r'(cam(?:era)?[\s_]*\d+)', base_no_seq, re.IGNORECASE)
    if cam_match:
        res = cam_match.group(1).replace('_', '')
        if is_generic_camera_name(res):
            return ""
        return res

    # 2. Strip map/addon prefix if present (e.g. 'de_firewatch_', 'firewatch_')
    curr = base_no_seq
    if addon_name:
        for prefix in [f"{addon_name}_", f"de_{addon_name}_", f"cs_{addon_name}_", f"ar_{addon_name}_"]:
            if curr.lower().startswith(prefix.lower()):
                curr = curr[len(prefix):]
                break

    # Strip generic map prefixes (e.g. 'de_dust2_', 'cs_office_')
    curr = re.sub(r'^(?:de|cs|ar|cp)_[a-zA-Z0-9]+_', '', curr, flags=re.IGNORECASE)

    if is_generic_camera_name(curr):
        return ""
    return curr

def compose_loading_screen_image(
    original_pixmap: QPixmap,
    icon_path: str = None,
    map_name: str = "Map Name",
    gamemode_text: str = "Competitive",
    description_text: str = "",
    camera_name: str = None
) -> QPixmap:
    """
    Composes the reconstructed CS2 loading screen widgets directly onto a copy of the
    screenshot pixmap, assembling exported PSD PNG assets (background fill, divider, cs2 icon)
    with high-quality smooth blur, exact map icon aspect-ratio scaling, and community author text replacement.
    """
    if not original_pixmap or original_pixmap.isNull():
        return original_pixmap

    ensure_cs2_fonts_loaded()

    composed = QPixmap(original_pixmap)
    W = composed.width()
    H = composed.height()
    if W <= 0 or H <= 0:
        return original_pixmap

    # Scale factor relative to 1080p reference from layout.psd
    scale = H / 1080.0

    assets_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "assets"))

    # widget_layout / background fill: bbox=(1599, 49, 1901, 1061), size=(302x1012)
    panel_w = int(302 * scale)
    panel_h = int(1012 * scale)
    panel_x = W - int((1920 - 1599) * scale)
    panel_y = int(49 * scale)
    panel_rect = QRect(panel_x, panel_y, panel_w, panel_h)

    # 1. Heavy High-Quality CS2 Gaussian Blur (Copy PSD Layer Stack)
    crop_rect = panel_rect.intersected(composed.rect())
    if not crop_rect.isEmpty():
        blur_radius = max(15, int(45 * scale))

        # Expand region by blur_radius to prevent edge fading artifacts during Gaussian blur
        margin = blur_radius
        exp_rect = crop_rect.adjusted(-margin, -margin, margin, margin).intersected(composed.rect())
        sub = original_pixmap.copy(exp_rect)

        # High-intensity smooth Gaussian blur via QGraphicsBlurEffect
        try:
            from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect
            scene = QGraphicsScene()
            item = QGraphicsPixmapItem(sub)
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(blur_radius)
            blur.setBlurHints(QGraphicsBlurEffect.QualityHint)
            item.setGraphicsEffect(blur)
            scene.addItem(item)
            
            res = QPixmap(sub.size())
            res.fill(Qt.transparent)
            painter = QPainter(res)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            scene.render(painter, QRectF(res.rect()), QRectF(sub.rect()))
            painter.end()

            # Crop out original crop_rect region from expanded blurred image
            offset_x = crop_rect.left() - exp_rect.left()
            offset_y = crop_rect.top() - exp_rect.top()
            blurred_sub = res.copy(offset_x, offset_y, crop_rect.width(), crop_rect.height())
        except Exception as e:
            debug(f"Blur effect fallback: {e}")
            sub_crop = original_pixmap.copy(crop_rect)
            pass1 = sub_crop.scaled(max(1, sub_crop.width() // 4), max(1, sub_crop.height() // 4), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pass2 = pass1.scaled(max(1, pass1.width() // 2), max(1, pass1.height() // 2), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            pass3 = pass2.scaled(max(1, pass1.width()), max(1, pass1.height()), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            blurred_sub = pass3.scaled(sub_crop.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        bp = QPainter(blurred_sub)
        bp.setRenderHint(QPainter.Antialiasing)
        bp.setRenderHint(QPainter.SmoothPixmapTransform)

        # Layer 1: background fill (PSD opacity=13, ~5% black overlay)
        bg_fill_file = os.path.join(assets_dir, "background_fill.png")
        if os.path.exists(bg_fill_file):
            bg_fill_pix = QPixmap(bg_fill_file)
            if not bg_fill_pix.isNull():
                bp.drawPixmap(blurred_sub.rect(), bg_fill_pix)
            else:
                bp.fillRect(blurred_sub.rect(), QColor(0, 0, 0, 13))
        else:
            bp.fillRect(blurred_sub.rect(), QColor(0, 0, 0, 13))

        # Layer 2: widget_layout (PSD opacity=51, 20% black overlay)
        bp.fillRect(blurred_sub.rect(), QColor(0, 0, 0, 51))

        bp.end()

        p = QPainter(composed)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(crop_rect.topLeft(), blurred_sub)
    else:
        p = QPainter(composed)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.fillRect(panel_rect, QColor(0, 0, 0, 64))

    # No border line drawn on panel

    # Helper function for font loading (Bahnschrift with fallback to Noto Sans)
    def get_cs2_font(size_px, bold=False, style_name=None):
        font = QFont("Bahnschrift")
        if style_name:
            font.setStyleName(style_name)
        if not font.exactMatch():
            if style_name:
                font = QFont(f"Bahnschrift {style_name}")
            if not font.exactMatch():
                font = QFont("Noto Sans")
        if not style_name:
            font.setBold(bold)
        font.setPixelSize(max(8, int(size_px * scale)))
        return font

    cs2_text_color = QColor(230, 231, 233)

    # 2. Camera Title (CameraNamePlaceholder: left=46, top=1010, height=42, font=42px, SemiCondensed)
    if camera_name and not is_generic_camera_name(camera_name):
        font_cam = get_cs2_font(42, style_name="SemiCondensed")
        p.setFont(font_cam)
        p.setPen(cs2_text_color)
        cam_x = int(46 * scale)
        cam_y = int(1010 * scale)
        cam_h = int(42 * scale)
        cam_rect = QRect(cam_x, cam_y, W // 2, cam_h)
        p.drawText(cam_rect, Qt.AlignLeft | Qt.AlignVCenter, camera_name)

    # 3. Inner Panel Layout (Divider width = 260px, centered in 302px panel: left=1620)
    content_x = panel_x + int(21 * scale)
    content_w = int(260 * scale)

    # a) Map Icon (map_icon_lobby_mapveto: size scaled 1.4x (166x203), top=48 to preserve center, preserving exact aspect ratio)
    if icon_path and os.path.exists(icon_path):
        box_w = int(119 * 1.4 * scale)
        box_h = int(145 * 1.4 * scale)
        box_x = panel_x + (panel_w - box_w) // 2
        box_y = int(48 * scale)

        if icon_path.lower().endswith(".svg"):
            renderer = QSvgRenderer(icon_path)
            if renderer.isValid():
                default_size = renderer.defaultSize()
                if default_size.width() > 0 and default_size.height() > 0:
                    aspect = default_size.width() / default_size.height()
                    if aspect >= (box_w / box_h):
                        render_w = box_w
                        render_h = int(box_w / aspect)
                    else:
                        render_h = box_h
                        render_w = int(box_h * aspect)
                else:
                    render_w, render_h = box_w, box_h
                render_x = box_x + (box_w - render_w) // 2
                render_y = box_y + (box_h - render_h) // 2
                renderer.render(p, QRectF(render_x, render_y, render_w, render_h))
        else:
            icon_pixmap = QPixmap(icon_path)
            if not icon_pixmap.isNull():
                scaled_icon = icon_pixmap.scaled(box_w, box_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                draw_x = box_x + (box_w - scaled_icon.width()) // 2
                draw_y = box_y + (box_h - scaled_icon.height()) // 2
                p.drawPixmap(draw_x, draw_y, scaled_icon)

    # b) Map Name (de_firewatch: top=244, height=36, font=36px SemiBold Condensed, centered)
    font_title = get_cs2_font(36, style_name="SemiBold Condensed")
    p.setFont(font_title)
    p.setPen(cs2_text_color)
    map_title_text = map_name or "de_map"
    title_rect = QRect(panel_x, int(244 * scale), panel_w, int(36 * scale))
    p.drawText(title_rect, Qt.AlignHCenter | Qt.AlignVCenter, map_title_text)

    # c) Gamemode Row (cs2_icon: size=(28x29), top=304; Competitive: size=(96x23), top=309, font=25px Light Condensed)
    gm_y = int(304 * scale)
    font_gm = get_cs2_font(25, style_name="Light Condensed")
    p.setFont(font_gm)
    metrics_gm = QFontMetrics(font_gm)

    gm_str = gamemode_text or "Competitive"
    gm_text_w = metrics_gm.horizontalAdvance(gm_str)
    badge_size = int(28 * scale)
    spacing = int(8 * scale)
    total_gm_w = badge_size + spacing + gm_text_w
    gm_start_x = panel_x + (panel_w - total_gm_w) // 2

    mode_icon_path = os.path.join(assets_dir, "cs2_icon.png")
    if not os.path.exists(mode_icon_path):
        mode_icon_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "icons", "cs2_icon.jpg"))
    badge_rect = QRect(gm_start_x, gm_y, badge_size, int(29 * scale))
    if os.path.exists(mode_icon_path):
        mode_pix = QPixmap(mode_icon_path)
        if not mode_pix.isNull():
            scaled_mode = mode_pix.scaled(badge_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(badge_rect.topLeft(), scaled_mode)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#e65100"))
            p.drawRoundedRect(badge_rect, int(4 * scale), int(4 * scale))
    else:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#e65100"))
        p.drawRoundedRect(badge_rect, int(4 * scale), int(4 * scale))

    p.setFont(font_gm)
    p.setPen(cs2_text_color)
    gm_text_rect = QRect(gm_start_x + badge_size + spacing, int(307 * scale), gm_text_w + 4, int(25 * scale))
    p.drawText(gm_text_rect, Qt.AlignVCenter | Qt.AlignLeft, gm_str)

    # d) Divider Line (divider: bbox=(1620, 357, 1880, 359), size=(260x2))
    div_y = int(357 * scale)
    divider_png = os.path.join(assets_dir, "divider.png")
    if os.path.exists(divider_png):
        div_pix = QPixmap(divider_png)
        if not div_pix.isNull():
            p.drawPixmap(QRect(content_x, div_y, content_w, int(2 * scale)), div_pix)
        else:
            p.setPen(QPen(cs2_text_color, max(1, int(2 * scale))))
            p.drawLine(content_x, div_y, content_x + content_w, div_y)
    else:
        p.setPen(QPen(cs2_text_color, max(1, int(2 * scale))))
        p.drawLine(content_x, div_y, content_x + content_w, div_y)

    # e) CS2 Standard Mission Text & Settings Block (Exact layout.psd coordinates)
    p.setPen(cs2_text_color)

    # "Bomb Scenario Mission" (left=1642, top=382, width=156, height=12, font=15px Light SemiCondensed)
    font_hdr = get_cs2_font(15, style_name="Light SemiCondensed")
    p.setFont(font_hdr)
    p.drawText(int(1642 * scale), int(382 * scale), int(226 * scale), int(18 * scale), Qt.AlignLeft | Qt.AlignTop, "Bomb Scenario Mission")

    # "Buy new weapons..." (left=1643, top=419, width=226, height=32, font=15px Light SemiCondensed)
    font_body = get_cs2_font(15, style_name="Light SemiCondensed")
    p.setFont(font_body)
    p.drawText(QRect(int(1643 * scale), int(419 * scale), int(226 * scale), int(45 * scale)),
               Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
               "Buy new weapons at the beginning\nof each round with money earned.")

    # "Settings:" (left=1644, top=475, width=50, height=15, font=15px Light SemiCondensed)
    font_set_hdr = get_cs2_font(15, style_name="Light SemiCondensed")
    p.setFont(font_set_hdr)
    p.drawText(int(1644 * scale), int(475 * scale), int(226 * scale), int(18 * scale), Qt.AlignLeft | Qt.AlignTop, "Settings:")

    # Settings list items (left=1647, top=492, 510, 529, font=15px Light SemiCondensed)
    p.setFont(font_body)
    p.drawText(int(1647 * scale), int(492 * scale), int(226 * scale), int(16 * scale), Qt.AlignLeft | Qt.AlignTop, "· Friendly fire is ON")
    p.drawText(int(1647 * scale), int(510 * scale), int(226 * scale), int(16 * scale), Qt.AlignLeft | Qt.AlignTop, "· Team collision is ON")
    p.drawText(QRect(int(1647 * scale), int(529 * scale), int(226 * scale), int(40 * scale)),
               Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop,
               "· Armor and defuse kits are\npurchasable")

    # "A community map created by:" (left=1642, top=584, width=149, height=13, font=13px Light SemiCondensed)
    font_author_hdr = get_cs2_font(13, style_name="Light SemiCondensed")
    p.setFont(font_author_hdr)
    p.setPen(cs2_text_color)
    p.drawText(int(1642 * scale), int(584 * scale), int(226 * scale), int(18 * scale), Qt.AlignLeft | Qt.AlignTop, "A community map created by:")

    # Custom Description / Author text: replaces "community placeholder text" at left=1643, top=606 (font=13px Light SemiCondensed)
    author_str = description_text.strip() if (description_text and description_text.strip()) else "community placeholder text"
    plain_author = author_str.replace("<br>", "\n").replace("<br/>", "\n").replace("<p>", "").replace("</p>", "\n")
    font_author_body = get_cs2_font(13, style_name="Light SemiCondensed")
    p.setFont(font_author_body)
    p.setPen(cs2_text_color)
    author_rect = QRect(int(1643 * scale), int(606 * scale), int(226 * scale), int(350 * scale))
    p.drawText(author_rect, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, plain_author)

    # f) Bottom Progress Section
    # Status text (Loading...: left=1620, top=998, width=61, height=17, font=17px Light SemiCondensed)
    status_y = int(998 * scale)
    font_prog = get_cs2_font(17, style_name="Light SemiCondensed")
    p.setFont(font_prog)
    p.setPen(cs2_text_color)
    p.drawText(int(1620 * scale), status_y, int(220 * scale), int(17 * scale), Qt.AlignLeft | Qt.AlignVCenter, "Making friends...")

    # Progress bar (loading_progress: bbox=(1620, 1036, 1880, 1044), size=(260x8))
    bar_y = int(1036 * scale)
    bar_h = max(4, int(8 * scale))
    bar_bg_rect = QRect(content_x, bar_y, content_w, bar_h)

    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 171))
    p.drawRect(bar_bg_rect)

    # 65% fill gradient (#134f87 -> #1ab8e0)
    fill_w = int(content_w * 0.65)
    bar_fill_rect = QRect(content_x, bar_y, fill_w, bar_h)
    gradient = QLinearGradient(content_x, bar_y, content_x + content_w, bar_y)
    gradient.setColorAt(0.0, QColor("#134f87"))
    gradient.setColorAt(1.0, QColor("#1ab8e0"))
    p.setBrush(QBrush(gradient))
    p.drawRect(bar_fill_rect)

    p.end()
    return composed


class Viewport(QMainWindow):
    """
    A QMainWindow subclass providing an image-viewing area with zoom, panning,
    and the ability to process images before displaying them.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.panning = False
        self.pan_start_point = QPointF(0, 0)
        self.current_pixmap = None
        self.zoom_level = 1.0
        self.image_files = []
        self.current_image_index = 0

        # Saved camera state - shared across all images
        self.saved_zoom_level = None
        self.saved_h_scroll = None
        self.saved_v_scroll = None
        self.current_image_path = None

        # LoadingShots preview overlay state
        self.loadingshots_dir = None
        self.preview_data_provider = None
        self._composed_pixmap_cache = None
        self._is_preview_active = False

        self.setupUI()

    def setupUI(self):
        self.container = QWidget(self)
        self.setCentralWidget(self.container)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.placeholder_label = QLabel(self.container)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setText("Select image in the screenshots")
        self.placeholder_label.setStyleSheet("color: gray; font-size: 13px;")

        self.image_label = QLabel(self.container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet("border: none; background: transparent; outline: none;")

        self.scroll_area = NoWheelScrollArea(self.container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.image_label)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; outline: none; }")

        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.scroll_area)

        self.placeholder_label.show()
        self.scroll_area.hide()

    def set_loadingshots_dir(self, directory: str):
        """
        Register the real LoadingShots directory. The preview button is only
        enabled while the displayed image lives directly inside this directory.
        """
        self.loadingshots_dir = os.path.normpath(directory) if directory else None

    def set_preview_data_provider(self, provider):
        """
        Register a callable() -> dict with keys icon_path, map_name,
        gamemode_text, description_html, used to populate the overlay.
        """
        self.preview_data_provider = provider

    def set_preview_visible(self, visible: bool):
        self._composed_pixmap_cache = None
        self.updateImageDisplay()

    def update_preview_content(self):
        self._composed_pixmap_cache = None
        self.updateImageDisplay()

    def _update_preview_availability(self, image_path):
        """
        Enable preview overlay for images living directly in the
        registered LoadingShots directory.
        """
        self._composed_pixmap_cache = None
        is_loadingshot = False
        if image_path:
            if self.loadingshots_dir:
                norm_img_dir = os.path.normpath(os.path.dirname(image_path)).lower()
                norm_shots_dir = os.path.normpath(self.loadingshots_dir).lower()
                is_loadingshot = (norm_img_dir == norm_shots_dir)
            else:
                is_loadingshot = True

        self._is_preview_active = is_loadingshot
        self.updateImageDisplay()

    def set_placeholder_text(self):
        """
        Show a placeholder label and hide the scroll area when no valid image is loaded.
        """
        self.placeholder_label.setText("Select image in the screenshots")
        self.placeholder_label.setStyleSheet("color: gray; font-size: 16px;")
        self.placeholder_label.show()
        self.scroll_area.hide()
        self.image_label.clear()
        self._is_preview_active = False

    def clear_placeholder_text(self):
        """
        Clear placeholder text and reveal the scroll area when a valid image is displayed.
        """
        self.placeholder_label.hide()
        self.placeholder_label.clear()
        self.placeholder_label.setStyleSheet("")
        self.scroll_area.show()

    def loadImagesFromDirectory(self, directory):
        """
        Load all valid images from the specified directory into a list
        and display the first image if available.
        """
        valid_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga"]
        try:
            self.image_files = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if os.path.splitext(f)[1].lower() in valid_extensions
            ]
            if self.image_files:
                self.current_image_index = 0
                self.showImage(self.image_files[self.current_image_index])
            else:
                self.set_placeholder_text()
        except Exception as e:
            debug(f"Error loading images from directory '{directory}': {e}")
            self.set_placeholder_text()

    def showImage(self, image_path):
        """
        Load a QPixmap from the given path and display it in the label.
        Maintains the current camera position when switching images.
        """
        try:
            self._composed_pixmap_cache = None
            # Save current camera position before switching
            if self.current_pixmap:
                self.saveCameraPosition()
            
            # Store the current zoom and scroll positions
            current_zoom = self.zoom_level
            current_h_scroll = self.scroll_area.horizontalScrollBar().value() if self.current_pixmap else None
            current_v_scroll = self.scroll_area.verticalScrollBar().value() if self.current_pixmap else None
            
            self.current_pixmap = QPixmap(image_path)
            if not self.current_pixmap.isNull():
                self.clear_placeholder_text()
                self.current_image_path = image_path
                self.updateWindowTitle(image_path)
                
                # If we had a previous image, maintain the camera position
                if current_h_scroll is not None:
                    # Restore the zoom level
                    self.zoom_level = current_zoom
                    self.updateImageDisplay(save_position=False)
                    self.scroll_area.horizontalScrollBar().setValue(current_h_scroll)
                    self.scroll_area.verticalScrollBar().setValue(current_v_scroll)
                else:
                    # First image, check if we have a saved position
                    if self.saved_zoom_level is not None:
                        self.zoom_level = self.saved_zoom_level
                        self.updateImageDisplay(save_position=False)
                        if self.saved_h_scroll is not None:
                            self.scroll_area.horizontalScrollBar().setValue(self.saved_h_scroll)
                        if self.saved_v_scroll is not None:
                            self.scroll_area.verticalScrollBar().setValue(self.saved_v_scroll)
                    else:
                        # No saved position, fit to window
                        self.zoom_level = 1.0
                        self.fitToWindow()
                self._update_preview_availability(image_path)
            else:
                self.set_placeholder_text()
        except Exception as e:
            debug(f"Error displaying image '{image_path}': {e}")
            self.set_placeholder_text()

    def updateWindowTitle(self, image_path):
        """
        Update the main window title bar with the base name of the displayed image.
        """
        self.setWindowTitle(f"Advanced Image Viewer - {os.path.basename(image_path)}")

    def zoomIn(self, mouse_pos=None):
        """
        Zoom in by 20%. Optionally keep the zoom focus around a specific mouse position.
        Limited to 500% zoom.
        """
        if self.current_pixmap:
            new_zoom = self.zoom_level * 1.2
            if new_zoom <= 5:  # Limit to 1000%
                self.zoom_level = new_zoom
                self.updateImageDisplay(mouse_pos)

    def zoomOut(self, mouse_pos=None):
        """
        Zoom out by 20%. Optionally keep the zoom focus around a specific mouse position.
        Limited between 10% and 1000%.
        """
        if self.current_pixmap:
            self.zoom_level /= 1.2
            if self.zoom_level < 0.1:  # Minimum 10% zoom
                self.zoom_level = 0.1
            self.updateImageDisplay(mouse_pos)

    def fitToWindow(self):
        """
        Fit the current image to the window for a convenient view.
        """
        if self.current_pixmap:
            try:
                w_ratio = self.scroll_area.viewport().width() / self.current_pixmap.width()
                h_ratio = self.scroll_area.viewport().height() / self.current_pixmap.height()
                self.zoom_level = min(w_ratio, h_ratio)
                # Slight offset to avoid accidental scrollbars.
                self.zoom_level = self.zoom_level - 0.025 if self.zoom_level > 0.025 else self.zoom_level
                self.updateImageDisplay()
            except Exception as e:
                debug(f"Error fitting image to window: {e}")

    def updateImageDisplay(self, mouse_pos=None, save_position=True):
        """
        Scale the displayed pixmap according to the current zoom_level.
        If preview is toggled on, composes the CS2 loading widgets directly onto the pixmap.
        If a mouse_pos is provided, keep the scroll offset around that position.
        """
        if getattr(self, '_is_updating_display', False):
            return
        self._is_updating_display = True
        try:
            if self.current_pixmap:
                old_size = self.image_label.size()

                if self._is_preview_active:
                    if self._composed_pixmap_cache is None or self._composed_pixmap_cache.isNull():
                        data = {}
                        if self.preview_data_provider:
                            try:
                                data = self.preview_data_provider() or {}
                            except Exception as e:
                                debug(f"Error retrieving loading screen preview data: {e}")
                        
                        camera_name = None
                        if data.get("show_camera_name", False):
                            camera_name = data.get("camera_name")
                            if not camera_name and self.current_image_path:
                                camera_name = extract_camera_name(self.current_image_path, data.get("map_name"))
                            if is_generic_camera_name(camera_name):
                                camera_name = None

                        self._composed_pixmap_cache = compose_loading_screen_image(
                            self.current_pixmap,
                            icon_path=data.get("icon_path"),
                            map_name=data.get("map_name"),
                            gamemode_text=data.get("gamemode_text", "Competitive"),
                            description_text=data.get("description_html"),
                            camera_name=camera_name
                        )
                    pixmap_to_render = self._composed_pixmap_cache
                else:
                    pixmap_to_render = self.current_pixmap

                scaled_pixmap = pixmap_to_render.scaled(
                    pixmap_to_render.size() * self.zoom_level,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.adjustSize()

                if mouse_pos:
                    new_size = self.image_label.size()
                    delta_size = new_size - old_size
                    scroll_bar_h = self.scroll_area.horizontalScrollBar()
                    scroll_bar_v = self.scroll_area.verticalScrollBar()
                    scroll_bar_h.setValue(
                        scroll_bar_h.value() + delta_size.width() * mouse_pos.x() / old_size.width()
                    )
                    scroll_bar_v.setValue(
                        scroll_bar_v.value() + delta_size.height() * mouse_pos.y() / old_size.height()
                    )
                
                # Auto-save camera position after zoom (if enabled)
                if save_position:
                    self.saveCameraPosition()
        except Exception as e:
            debug(f"Error updating image display: {e}")
        finally:
            self._is_updating_display = False

    def wheelEvent(self, event: QWheelEvent):
        """
        Override the main window wheel event to provide zooming
        using the wheel, based on scroll direction.
        """
        mouse_pos = self.image_label.mapFromGlobal(event.globalPosition().toPoint())
        if event.angleDelta().y() > 0:
            self.zoomIn(mouse_pos)
        else:
            self.zoomOut(mouse_pos)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        """
        Activate panning when the user right-clicks inside the viewer.
        """
        if event.button() == Qt.RightButton:
            self.panning = True
            self.pan_start_point = event.position()
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        On mouse move, shift the scrollbars to implement manual panning.
        """
        if self.panning:
            delta = event.position() - self.pan_start_point
            self.scroll_area.horizontalScrollBar().setValue(
                self.scroll_area.horizontalScrollBar().value() - delta.x()
            )
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().value() - delta.y()
            )
            self.pan_start_point = event.position()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Disable panning when the user releases the right mouse button.
        """
        if event.button() == Qt.RightButton:
            self.panning = False
            QApplication.restoreOverrideCursor()
            # Save camera position after panning
            self.saveCameraPosition()
    
    def saveCameraPosition(self):
        """
        Save the current camera position (shared across all images).
        """
        if self.current_pixmap:
            self.saved_zoom_level = self.zoom_level
            self.saved_h_scroll = self.scroll_area.horizontalScrollBar().value()
            self.saved_v_scroll = self.scroll_area.verticalScrollBar().value()
            debug(f"Saved shared camera position - Zoom: {self.saved_zoom_level}, H: {self.saved_h_scroll}, V: {self.saved_v_scroll}")
    
    def restoreCameraPosition(self):
        """
        Restore the saved camera position (shared across all images).
        """
        if self.current_pixmap and self.saved_zoom_level is not None:
            # Restore zoom level without saving position again
            self.zoom_level = self.saved_zoom_level
            self.updateImageDisplay(save_position=False)
            
            # Restore scroll positions after processing events
            QApplication.processEvents()
            
            if self.saved_h_scroll is not None:
                self.scroll_area.horizontalScrollBar().setValue(self.saved_h_scroll)
            if self.saved_v_scroll is not None:
                self.scroll_area.verticalScrollBar().setValue(self.saved_v_scroll)
                
            debug(f"Restored shared camera position - Zoom: {self.saved_zoom_level}, H: {self.saved_h_scroll}, V: {self.saved_v_scroll}")

VALID_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tga")


class SectionHeader(QWidget):
    """Custom, hand-built collapsible-section header: a disclosure arrow plus a
    bold title, clickable across its whole width.  Built from plain widgets so
    the explorer does not rely on QToolBox / stylesheet shortcuts."""
    clicked = Signal()

    ARROW_EXPANDED = "▾"   # ▾
    ARROW_COLLAPSED = "▸"  # ▸

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setAutoFillBackground(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self.arrow_label = QLabel(self.ARROW_EXPANDED, self)
        self.title_label = QLabel(title, self)
        font = self.title_label.font()
        font.setBold(True)
        self.title_label.setFont(font)

        self.count_label = QLabel("", self)
        self.count_label.setStyleSheet("color: gray;")

        layout.addWidget(self.arrow_label)
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.count_label)

    def set_expanded(self, expanded: bool):
        self.arrow_label.setText(self.ARROW_EXPANDED if expanded else self.ARROW_COLLAPSED)

    def set_count(self, count: int):
        self.count_label.setText(f"{count} image{'s' if count != 1 else ''}")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class CollapsibleSection(QWidget):
    """A custom collapsible container: a SectionHeader stacked above a body
    widget whose visibility is toggled by clicking the header."""
    def __init__(self, title: str, body: QWidget, expanded: bool = True, parent=None):
        super().__init__(parent)
        self._body = body
        self._expanded = expanded

        self.header = SectionHeader(title, self)
        self.header.clicked.connect(self.toggle)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self._body)

        self._apply_state()

    def toggle(self):
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._apply_state()

    def set_count(self, count: int):
        self.header.set_count(count)

    def _apply_state(self):
        self._body.setVisible(self._expanded)
        self.header.set_expanded(self._expanded)
        # When collapsed the section should shrink to just its header height so
        # the sibling section can claim the freed vertical space.
        if self._expanded:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)


class ImageTreeView(QTreeView):
    """A QTreeView bound to a single real directory that accepts image files
    dropped from outside and copies them into that directory."""
    images_dropped = Signal(list)   # list[str] of destination paths
    file_activated = Signal(str)    # image file path clicked

    FILE_ICON_SIZE = QSize(32, 32)
    FOLDER_ICON_SIZE = QSize(32, 32)

    def __init__(self, root_dir: str, parent=None):
        super().__init__(parent)
        self.root_dir = root_dir
        self.setIconSize(self.FILE_ICON_SIZE)
        self.setUniformRowHeights(False)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setStyleSheet("QTreeView { outline: none; }")

        self.file_model = QFileSystemModelWithThumbnails(self)
        self.file_model.setRootPath(root_dir)
        self.file_model.setNameFilters([f"*{ext}" for ext in VALID_IMAGE_EXTENSIONS])
        self.file_model.setNameFilterDisables(False)

        self.setModel(self.file_model)
        self.setRootIndex(self.file_model.index(root_dir))

        self.header().setDefaultSectionSize(120)
        self.header().resizeSection(0, 160)
        self.header().hideSection(1)
        self.header().hideSection(2)
        self.header().hideSection(3)

        self.setItemDelegate(
            FolderIconSizeDelegate(self.file_model, self.FOLDER_ICON_SIZE, self.FILE_ICON_SIZE, self)
        )

        self.clicked.connect(self._on_clicked)

    def _on_clicked(self, index):
        if not self.file_model.isDir(index):
            self.file_activated.emit(self.file_model.filePath(index))

    def _has_valid_urls(self, event) -> bool:
        if not event.mimeData().hasUrls():
            return False
        for url in event.mimeData().urls():
            if url.isLocalFile() and os.path.splitext(url.toLocalFile())[1].lower() in VALID_IMAGE_EXTENSIONS:
                return True
        return False

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self._has_valid_urls(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent):
        if self._has_valid_urls(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if not self._has_valid_urls(event):
            event.ignore()
            return
        copied_files = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            source_file = url.toLocalFile()
            if os.path.splitext(source_file)[1].lower() not in VALID_IMAGE_EXTENSIONS:
                continue
            destination_file = os.path.join(self.root_dir, os.path.basename(source_file))
            try:
                shutil.copy(source_file, destination_file)
                copied_files.append(destination_file)
                debug(f"Copied file {source_file} to {destination_file}")
            except Exception as e:
                debug(f"Error copying file '{source_file}': {e}")
        if copied_files:
            self.images_dropped.emit(copied_files)
            event.acceptProposedAction()
        else:
            event.ignore()


class ImageExplorer(QWidget):
    """
    A file explorer that shows two real directories as separate collapsible,
    thumbnailed groups (History and LoadingShots) alongside an embedded
    Viewport.  No filesystem junction "shortcuts" are used — each group's tree
    is rooted directly at its real directory.
    """

    def __init__(self, history_dir: str = "", loadingshots_dir: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Explorer")

        self.image_viewer = Viewport()
        if loadingshots_dir:
            self.image_viewer.set_loadingshots_dir(loadingshots_dir)

        # One collapsible section per real directory.
        self.sections = []  # list[tuple[CollapsibleSection, ImageTreeView]]

        panel = QWidget(self)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        for title, directory in (("LoadingShots", loadingshots_dir), ("History", history_dir)):
            if not directory:
                continue
            os.makedirs(directory, exist_ok=True)
            tree = ImageTreeView(directory, self)
            tree.setContextMenuPolicy(Qt.CustomContextMenu)
            tree.customContextMenuRequested.connect(
                lambda pos, t=tree: self.openContextMenu(t, pos)
            )
            tree.file_activated.connect(self.image_viewer.showImage)
            tree.images_dropped.connect(self.on_images_dropped)

            section = CollapsibleSection(title, tree, expanded=True, parent=panel)
            panel_layout.addWidget(section)
            self.sections.append((section, tree))

        if not self.sections:
            panel_layout.addStretch(1)

        splitter = QSplitter(self)
        splitter.addWidget(panel)
        splitter.addWidget(self.image_viewer)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(splitter)

    def on_images_dropped(self, copied_files):
        # QFileSystemModel auto-refreshes on directory change; just surface the
        # first dropped image in the viewport.
        if copied_files:
            self.image_viewer.showImage(copied_files[0])

    def openContextMenu(self, tree: "ImageTreeView", position):
        model = tree.file_model
        index = tree.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        if model.isDir(index):
            open_folder_action = QAction("Open Folder", self)
            open_folder_action.triggered.connect(lambda: os.startfile(model.filePath(index)))
            menu.addAction(open_folder_action)
            remove_action = QAction("Remove Folder", self)
            remove_action.triggered.connect(lambda: self.removeSelectedFolder(tree, index))
            menu.addAction(remove_action)
        else:
            open_folder_action = QAction("Open Folder", self)
            file_path = model.filePath(index)
            open_folder_action.triggered.connect(lambda: os.startfile(os.path.dirname(file_path)))
            menu.addAction(open_folder_action)
            remove_action = QAction("Remove Image", self)
            remove_action.triggered.connect(lambda: self.removeSelectedImage(tree, index))
            menu.addAction(remove_action)

        menu.exec(tree.viewport().mapToGlobal(position))

    def removeSelectedImage(self, tree: "ImageTreeView", index):
        model = tree.file_model
        file_path = model.filePath(index)
        if not model.isDir(index):
            try:
                os.remove(file_path)
                model.remove(index)
                self.image_viewer.set_placeholder_text()
                debug(f"Removed image: {file_path}")
            except Exception as e:
                debug(f"Error removing file '{file_path}': {e}")

    def removeSelectedFolder(self, tree: "ImageTreeView", index):
        model = tree.file_model
        folder_path = model.filePath(index)
        if model.isDir(index):
            try:
                shutil.rmtree(folder_path)
                model.remove(index)
                self.image_viewer.set_placeholder_text()
                debug(f"Removed folder: {folder_path}")
            except Exception as e:
                debug(f"Error removing folder '{folder_path}': {e}")

from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtCore import QSize

class FolderIconSizeDelegate(QStyledItemDelegate):
    """
    Custom delegate to set a smaller icon size for folders in the tree view.
    """
    def __init__(self, model, folder_icon_size, file_icon_size, parent=None):
        super().__init__(parent)
        self.model = model
        self.folder_icon_size = folder_icon_size
        self.file_icon_size = file_icon_size

    def sizeHint(self, option, index):
        if self.model.isDir(index):
            return self.folder_icon_size
        return self.file_icon_size

class ThumbnailWorkerSignals(QObject):
    result = Signal(str, QIcon)

class ThumbnailWorker(QRunnable):
    """
    Worker thread that loads and scales a thumbnail off the main thread.
    """
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.signals = ThumbnailWorkerSignals()

    def run(self):
        try:
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(
                    128,
                    128,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                icon = QIcon(thumbnail)
                self.signals.result.emit(self.file_path, icon)
            else:
                debug(f"Failed to generate thumbnail for: {self.file_path}")
        except Exception as e:
            debug(f"Error generating thumbnail for '{self.file_path}': {e}")

class QFileSystemModelWithThumbnails(QFileSystemModel):
    """
    Custom QFileSystemModel that loads thumbnails asynchronously and updates the model.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnail_cache = {}
        self.thread_pool = QThreadPool()
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self.on_file_changed)

    def data(self, index, role=Qt.DisplayRole):
        if index.column() == 0 and role == Qt.DecorationRole:
            file_path = self.filePath(index)
            if not self.isDir(index):
                if file_path not in self.watcher.files():
                    self.watcher.addPath(file_path)
                    debug(f"Added watcher for file: {file_path}")

                if file_path in self.thumbnail_cache:
                    return self.thumbnail_cache[file_path]
                else:
                    self.load_thumbnail_async(file_path)
        return super().data(index, role)

    def load_thumbnail_async(self, file_path):
        worker = ThumbnailWorker(file_path)
        worker.signals.result.connect(self.on_thumbnail_loaded)
        self.thread_pool.start(worker)

    def on_thumbnail_loaded(self, file_path, icon):
        self.thumbnail_cache[file_path] = icon
        index = self.index(file_path)
        self.dataChanged.emit(index, index, [Qt.DecorationRole])
        debug(f"Loaded thumbnail for: {file_path}")

    def on_file_changed(self, file_path):
        if file_path in self.thumbnail_cache:
            del self.thumbnail_cache[file_path]
            self.load_thumbnail_async(file_path)
            index = self.index(file_path)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])
            debug(f"Updated thumbnail for changed file: {file_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    explorer = ImageExplorer()
    explorer.show()
    sys.exit(app.exec())