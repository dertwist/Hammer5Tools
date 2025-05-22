import os
import sys
import tempfile
import random

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import (
    QImage,
    QPixmap,
    QPainter,
    QColor,
    QFont,
    QFontMetrics,
    QPen,
    QBrush,
    QLinearGradient
)
from PySide6.QtSvg import QSvgRenderer


def blur_qimage_region(image, rect, radius=5):
    # Validate rectangle dimensions and boundaries
    left, top, width_rect, height_rect = rect
    if (width_rect <= 0 or height_rect <= 0 or
            left + width_rect > image.width() or
            top + height_rect > image.height()):
        return image

    # Extract the region to blur as a QPixmap
    region_pixmap = QPixmap.fromImage(image.copy(left, top, width_rect, height_rect))

    # Create a scaled-down size for the blur effect
    scaled_down_size = QSize(region_pixmap.width() // 10, region_pixmap.height() // 10)
    # Scale down and then up to simulate a blur
    blurred = region_pixmap.scaled(scaled_down_size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    blurred = blurred.scaled(region_pixmap.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    # Paste the blurred region back onto the original image
    painter = QPainter(image)
    painter.drawPixmap(left, top, blurred)
    painter.end()

    return image


def load_svg_as_qpixmap(svg_path, target_width):
    if not svg_path or not os.path.isfile(svg_path):
        return None

    renderer = QSvgRenderer(svg_path)
    if not renderer.isValid():
        return None

    original_size = renderer.defaultSize()
    if original_size.width() == 0 or original_size.height() == 0:
        return None

    scale_factor = target_width / original_size.width()
    scaled_width = int(original_size.width() * scale_factor)
    scaled_height = int(original_size.height() * scale_factor)

    pixmap = QPixmap(scaled_width, scaled_height)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return pixmap


def preview_image(image_path, svg_icon_path, description_text, output_path, viewport_size=(1280, 720)):
    if not os.path.exists(image_path):
        print(f"Input image not found: {image_path}")
        return

    # Load image and scale while preserving aspect ratio
    image = QImage(image_path)
    if image.isNull():
        print(f"Error: unable to load {image_path}")
        return
    image = image.scaled(viewport_size[0], viewport_size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)

    width = image.width()
    height = image.height()

    # Define rectangular region on the right side for the blur overlay.
    rect_left = int(width * 0.70)
    rect_top = int(height * 0.05)
    rect_right = int(width * 0.98)
    rect_bottom = int(height * 0.95)
    region_width = rect_right - rect_left
    region_height = rect_bottom - rect_top

    # Apply blur on the defined region if dimensions are valid
    if region_width > 0 and region_height > 0:
        image = blur_qimage_region(image, (rect_left, rect_top, region_width, region_height), radius=5)

    # Convert the QImage to QPixmap for overlay drawing
    pixmap = QPixmap.fromImage(image)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw semi-transparent overlay on the blurred region
    overlay_rect = QRectF(rect_left, rect_top, region_width, region_height)
    overlay_color = QColor(0, 0, 0, 120)
    painter.fillRect(overlay_rect, overlay_color)

    # Setup for UI overlay elements
    padding = 10
    current_y = rect_top + padding

    # 1. Draw random status text
    status_text_options = ["Accepting", "Checking", "Testing"]
    status_text = random.choice(status_text_options)
    status_font = QFont("Arial", 12)
    painter.setFont(status_font)
    painter.setPen(Qt.white)
    fm_status = QFontMetrics(status_font)
    text_width = fm_status.horizontalAdvance(status_text)
    text_height = fm_status.height()
    status_x = rect_left + (region_width - text_width) // 2
    painter.drawText(status_x, current_y + text_height, status_text)
    current_y += text_height + padding

    # 2. Draw optional SVG icon if provided
    if svg_icon_path:
        max_icon_width = int(region_width * 0.8)
        icon_pix = load_svg_as_qpixmap(svg_icon_path, max_icon_width)
        if icon_pix:
            icon_x = rect_left + (region_width - icon_pix.width()) // 2
            painter.drawPixmap(icon_x, current_y, icon_pix)
            current_y += icon_pix.height() + padding
        else:
            current_y += padding
    else:
        current_y += padding

    # 3. Draw add-on name ("Addon Name")
    addon_font = QFont("Arial", 20, QFont.Bold)
    painter.setFont(addon_font)
    addon_text = "Addon Name"
    fm_addon = QFontMetrics(addon_font)
    addon_text_width = fm_addon.horizontalAdvance(addon_text)
    addon_text_height = fm_addon.height()
    addon_x = rect_left + (region_width - addon_text_width) // 2
    painter.drawText(addon_x, current_y + addon_text_height, addon_text)
    current_y += addon_text_height + padding

    # 4. Draw game mode ("Game Mode")
    gamemode_font = QFont("Arial", 16)
    painter.setFont(gamemode_font)
    game_mode_text = "Game Mode"
    fm_gamemode = QFontMetrics(gamemode_font)
    gamemode_text_width = fm_gamemode.horizontalAdvance(game_mode_text)
    gamemode_text_height = fm_gamemode.height()
    gamemode_x = rect_left + (region_width - gamemode_text_width) // 2
    painter.drawText(gamemode_x, current_y + gamemode_text_height, game_mode_text)
    current_y += gamemode_text_height + padding

    # 5. Draw divider line
    divider_y = current_y + padding // 2
    pen = QPen(QColor("gray"))
    pen.setWidth(2)
    painter.setPen(pen)
    painter.drawLine(rect_left + padding, divider_y, rect_left + region_width - padding, divider_y)
    current_y = divider_y + padding

    # 6. Draw game mode description text
    desc_font = QFont("Arial", 14)
    painter.setFont(desc_font)
    painter.setPen(Qt.white)
    fm_desc = QFontMetrics(desc_font)
    desc_text = description_text
    desc_text_width = fm_desc.horizontalAdvance(desc_text)
    desc_x = rect_left + (region_width - desc_text_width) // 2
    painter.drawText(desc_x, current_y + fm_desc.height(), desc_text)
    current_y += fm_desc.height() + padding

    # 7. Draw loading gradient line at the bottom of the overlay
    gradient_height = 8
    gradient_rect_top = rect_bottom - gradient_height - padding
    gradient_rect = QRectF(rect_left + padding, gradient_rect_top, region_width - 2 * padding, gradient_height)
    gradient = QLinearGradient(gradient_rect.topLeft(), gradient_rect.topRight())
    gradient.setColorAt(0.0, QColor(0, 255, 0, 150))
    gradient.setColorAt(0.5, QColor(255, 255, 0, 150))
    gradient.setColorAt(1.0, QColor(255, 0, 0, 150))
    painter.fillRect(gradient_rect, QBrush(gradient))

    painter.end()

    # Save the processed image
    final_image = pixmap.toImage()
    if not final_image.save(output_path):
        print(f"Failed to save processed image to {output_path}")
    else:
        print(f"Processed image saved to: {output_path}")