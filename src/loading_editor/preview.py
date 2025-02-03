import sys
import os
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImage, QPixmap, QPainter, QFont, QColor
from PySide6.QtWidgets import (QApplication, QGraphicsScene, QGraphicsPixmapItem,
                               QGraphicsBlurEffect)
from PySide6.QtSvg import QSvgRenderer

def apply_blur_to_pixmap(pixmap, blur_radius=5):
    """
    Apply a blur effect to a QPixmap using QGraphicsBlurEffect.
    """
    # Create a scene and add the pixmap item with a blur effect.
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(pixmap)
    blur = QGraphicsBlurEffect()
    blur.setBlurRadius(blur_radius)
    item.setGraphicsEffect(blur)
    scene.addItem(item)

    # Render the scene to a new QPixmap.
    result = QPixmap(pixmap.size())
    result.fill(Qt.transparent)
    painter = QPainter(result)
    scene.render(painter, QRectF(0, 0, pixmap.width(), pixmap.height()),
                 QRectF(0, 0, pixmap.width(), pixmap.height()))
    painter.end()
    return result

def load_svg_as_pixmap(svg_path, target_width):
    """
    Load an SVG file and render it to a QPixmap with the specified target width,
    maintaining its aspect ratio.
    """
    if not os.path.exists(svg_path):
        print(f"SVG icon not found: {svg_path}")
        return None

    renderer = QSvgRenderer(svg_path)
    # Calculate target height using the viewBox size of the SVG.
    default_size = renderer.defaultSize()
    if default_size.width() == 0:
        default_size.setWidth(target_width)
    scale_factor = target_width / default_size.width()
    target_height = int(default_size.height() * scale_factor)

    pixmap = QPixmap(target_width, target_height)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap

def preview_image(image_path, svg_icon_path, description_text, output_path, viewport_size=(1280, 720)):
    """
    Processes the image by resizing to a 16:9 viewport, creating a blurred overlay area,
    and overlaying an SVG icon with accompanying text using Qt APIs.

    Steps:
      0. Rescale the image to a 16:9 viewport.
      1. Create a blurred rectangle area within the image with specific offsets:
           - left: 87% of width, right: 4% from the right, top: 5% of height, bottom: 5% from the bottom.
      2. Overlay on top of this blurred rectangle:
           - the SVG icon (converted to pixmap)
           - below the icon, draw the label "Casual"
      3. Draw a gray divider below the icon and text.
      4. Write the text "test" below the divider.
      5. Write the text "A community map created by:" followed by the provided description.
    """
    # Step 0: Load and resize the image to the viewport size.
    if not os.path.exists(image_path):
        print(f"Input image not found: {image_path}")
        return
    image = QImage(image_path)
    if image.isNull():
        print(f"Failed to load image: {image_path}")
        return
    image = image.scaled(QSize(*viewport_size), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pixmap = QPixmap.fromImage(image)
    width, height = pixmap.width(), pixmap.height()

    # Step 1: Define the blurred rectangle area using percentage offsets.
    rect_left   = int(width * 0.87)
    rect_top    = int(height * 0.05)
    rect_right  = int(width * (1 - 0.04))   # 4% from right edge => width * 0.96
    rect_bottom = int(height * (1 - 0.05))    # 5% from bottom edge => height * 0.95
    region_width = rect_right - rect_left
    region_height = rect_bottom - rect_top

    if region_width <= 0 or region_height <= 0:
        print("Invalid rectangle dimensions calculated.")
        return

    # Crop the rectangle region
    region_pixmap = pixmap.copy(rect_left, rect_top, region_width, region_height)
    # Apply blur to the rectangle region
    blurred_pixmap = apply_blur_to_pixmap(region_pixmap, blur_radius=5)

    # Draw the blurred region back onto the main pixmap.
    painter = QPainter(pixmap)
    painter.drawPixmap(rect_left, rect_top, blurred_pixmap)

    # Step 2: Load the SVG icon as a pixmap.
    # Set maximum icon width to 80% of the blurred region's width.
    max_icon_width = int(region_width * 0.8)
    icon_pixmap = load_svg_as_pixmap(svg_icon_path, max_icon_width)
    if icon_pixmap is None:
        painter.end()
        return

    # Calculate position: center horizontally within the blurred rectangle.
    icon_x = rect_left + (region_width - icon_pixmap.width()) // 2
    icon_padding_top = 10
    icon_y = rect_top + icon_padding_top
    painter.drawPixmap(icon_x, icon_y, icon_pixmap)

    # Set up fonts for drawing text.
    try:
        # Attempt to load a nice sans-serif font.
        font = QFont("Arial", 20)
        font_small = QFont("Arial", 16)
    except Exception:
        font = painter.font()
        font_small = painter.font()

    # Step 2.2: Draw label "Casual" under the icon.
    label_text = "Casual"
    painter.setFont(font)
    painter.setPen(QColor("white"))
    metrics = painter.fontMetrics()
    text_width = metrics.horizontalAdvance(label_text)
    text_height = metrics.height()
    label_x = rect_left + (region_width - text_width) // 2
    label_y = icon_y + icon_pixmap.height() + 5  # slight padding below icon
    painter.drawText(label_x, label_y + text_height, label_text)

    # Step 3: Draw a gray divider below the label text.
    divider_padding = 10
    divider_y = label_y + text_height + divider_padding
    divider_thickness = 2
    painter.setPen(QColor("gray"))
    painter.drawLine(rect_left + 5, divider_y, rect_right - 5, divider_y)

    # Step 4: Draw the text "test" below the divider.
    test_padding = 10
    test_y = divider_y + test_padding + text_height
    painter.setPen(QColor("white"))
    painter.drawText(rect_left + 10, test_y, "test")

    # Step 5: Draw "A community map created by:" and the description.
    base_text = "A community map created by:"
    combined_text = f"{base_text} {description_text}"
    desc_padding = 10
    desc_y = test_y + text_height + desc_padding
    painter.setFont(font_small)
    painter.drawText(rect_left + 10, desc_y, combined_text)

    painter.end()

    # Save the processed image.
    if not pixmap.save(output_path):
        print(f"Error saving processed image to: {output_path}")
    else:
        print(f"Processed image saved to: {output_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Example usage:
    input_image = "input_image.jpg"  # Path to the input image file
    svg_icon = "icon.svg"            # Path to the SVG icon file
    description = "Your Organization Name"
    output_image = "processed_image_qt.png"

    if not os.path.exists(input_image):
        print(f"Input image not found: {input_image}")
        sys.exit(1)
    if not os.path.exists(svg_icon):
        print(f"SVG icon not found: {svg_icon}")
        sys.exit(1)

    preview_image(input_image, svg_icon, description, output_image)
    sys.exit(0)