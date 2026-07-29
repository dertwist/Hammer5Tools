"""
HelpPanel — Section 3 Help Pane for SmartProp property editor.

Design matches Hammer's Object Properties help strip:
  • Single QTextBrowser widget (read-only, no interaction) on the left
  • Bold title rendered in a distinct colour (cyan/teal like the reference)
  • Body text below in grey — word-wrapped
  • Optional borderless help picture on the right (auto-scaled, aspect-ratio preserved)
  • Clicking the picture opens a non-modal preview window using Loading Editor Viewport
  • Dark background, no visible border
"""

from __future__ import annotations

import os

from PySide6.QtCore import QModelIndex, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.editors.loading_editor.viewport import Viewport
from src.editors.smartprop_editor.property_tooltips import (
    get_tooltip_info,
    get_tooltip_info_multi,
    property_tooltips,
    resolve_image_path,
)
from src.editors.smartprop_editor.props.components import get_summary_hint, prettify_class_name
from src.editors.smartprop_editor.props.model import ComponentRef, FieldDefRole
from src.editors.smartprop_editor.props.schema import FieldDef

_PANEL_BG   = "#1E1E1E"
_TITLE_COL  = "#4EC9B0"   # cyan-teal — matches Hammer's category colour
_BODY_COL   = "#AAAAAA"
_FONT_FACE  = "Segoe UI"


def _render_html(title: str, body: str) -> str:
    """Return a minimal HTML snippet displayed in the QTextBrowser."""
    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<p style="margin:0 0 4px 0;">'
        f'<span style="font-family:{_FONT_FACE};font-size:12px;font-weight:bold;color:{_TITLE_COL};">'
        f'{_esc(title)}</span></p>'
        f'<p style="margin:0;">'
        f'<span style="font-family:{_FONT_FACE};font-size:11px;color:{_BODY_COL};">'
        f'{_esc(body)}</span></p>'
    )


class HelpImageDialog(Viewport):
    """Image preview window inheriting loading_editor's Viewport directly for full zoom/pan support."""

    MIN_ZOOM = 0.03  # 3% minimum zoom limit
    MAX_ZOOM = 10.0  # 1000% maximum zoom limit

    def __init__(self, image_path: str, title: str = "Image viewer", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(960, 640)

        # Disable CS2 loading screen overlay generation
        self.set_loadingshots_dir("C:/nonexistent_dummy_dir")
        self._is_preview_active = False
        self._image_path = image_path
        self._title_override = title

    def updateWindowTitle(self, image_path):
        title = self._title_override or (f"Image viewer — {os.path.basename(image_path)}" if image_path else "Image viewer")
        self.setWindowTitle(title)

    def show_image(self, image_path: str, title: str | None = None):
        self._image_path = image_path
        if title:
            self._title_override = title
            self.setWindowTitle(title)
        self._apply_image()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_image()
        QTimer.singleShot(50, self._apply_image)

    def _apply_image(self):
        if not self._image_path or not os.path.exists(self._image_path):
            return

        self._is_preview_active = False
        self.showImage(self._image_path)
        self._is_preview_active = False

        # Fit image to window so it's clearly visible and centered
        self.fitToWindow()

    def fitToWindow(self):
        super().fitToWindow()
        if self.zoom_level < self.MIN_ZOOM:
            self.zoom_level = self.MIN_ZOOM
            self.updateImageDisplay()
        elif self.zoom_level > self.MAX_ZOOM:
            self.zoom_level = self.MAX_ZOOM
            self.updateImageDisplay()

    def zoomIn(self, mouse_pos=None):
        if self.current_pixmap:
            new_zoom = self.zoom_level * 1.2
            if new_zoom > self.MAX_ZOOM:
                new_zoom = self.MAX_ZOOM
            self.zoom_level = new_zoom
            self.updateImageDisplay(mouse_pos)

    def zoomOut(self, mouse_pos=None):
        if self.current_pixmap:
            new_zoom = self.zoom_level / 1.2
            if new_zoom < self.MIN_ZOOM:
                new_zoom = self.MIN_ZOOM
            self.zoom_level = new_zoom
            self.updateImageDisplay(mouse_pos)


class _ClickableLabel(QLabel):
    """QLabel emitting clicked signal on left-click."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class HelpPanel(QFrame):
    """Section 3 Help Pane — text widget on left, borderless clickable image preview on right."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            HelpPanel {{
                background-color: {_PANEL_BG};
                border-top: 1px solid #2D2D2D;
            }}
        """)

        self._current_pixmap: QPixmap | None = None
        self._current_image_path: str | None = None
        self._current_title: str = ""
        self._image_dialog: HelpImageDialog | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Text Browser (left) ──────────────────────────────────────────────
        self.browser = QTextBrowser(self)
        self.browser.setOpenLinks(False)
        self.browser.setReadOnly(True)
        self.browser.setFocusPolicy(Qt.NoFocus)
        self.browser.setFrameShape(QFrame.NoFrame)
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {_PANEL_BG};
                color: {_BODY_COL};
                border: none;
                padding: 8px 10px;
                font-family: {_FONT_FACE};
                font-size: 11px;
            }}
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: #444;
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.browser, 1)

        # ── Image Frame (right, borderless) ──────────────────────────────────
        self.image_frame = QFrame(self)
        self.image_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        img_layout = QVBoxLayout(self.image_frame)
        img_layout.setContentsMargins(0, 0, 0, 0)
        img_layout.setSpacing(0)

        self.image_label = _ClickableLabel(self.image_frame)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: none; background: transparent;")
        self.image_label.setToolTip("Click to view full image in viewer")
        self.image_label.clicked.connect(self._on_image_clicked)
        img_layout.addWidget(self.image_label)

        # Outer layout for padding around image frame
        self.image_container = QWidget(self)
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(4, 4, 8, 4)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.image_frame)

        layout.addWidget(self.image_container, 0)
        self.image_container.hide()

        self.clear_help()

    # ── Internal Image Display Scaling & Click Handler ──────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_pixmap and not self._current_pixmap.isNull():
            self._update_image_display()

    def _update_image_display(self):
        if self._current_pixmap is None or self._current_pixmap.isNull():
            self.image_container.hide()
            return

        panel_h = self.height()
        panel_w = self.width()

        max_w = max(40, int(panel_w * 0.45) - 16)
        max_h = max(30, panel_h - 16)

        scaled = self._current_pixmap.scaled(
            QSize(max_w, max_h),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.image_container.show()

    def _on_image_clicked(self):
        """Open full-size view in a non-modal (non-blocking) window using loading_editor Viewport."""
        if not self._current_image_path or not os.path.exists(self._current_image_path):
            return

        title_str = f"Image viewer — {self._current_title}" if self._current_title else "Image viewer"
        if self._image_dialog is None or not self._image_dialog.isVisible():
            self._image_dialog = HelpImageDialog(
                image_path=self._current_image_path,
                title=title_str,
                parent=self.window()
            )
            self._image_dialog.show()
        else:
            self._image_dialog.show_image(self._current_image_path, title_str)

        self._image_dialog.raise_()
        self._image_dialog.activateWindow()

    # ── Public API ──────────────────────────────────────────────────────────

    def set_help(self, title: str, body: str, image_path: str | None = None):
        """Set help text and optional right-side image."""
        self._current_title = title
        self.browser.setHtml(_render_html(title, body))

        resolved = resolve_image_path(image_path)
        if resolved:
            pix = QPixmap(resolved)
            if not pix.isNull():
                self._current_pixmap = pix
                self._current_image_path = resolved
                self._update_image_display()
                return

        self._current_pixmap = None
        self._current_image_path = None
        self.image_label.clear()
        self.image_container.hide()

    def clear_help(self):
        """Show neutral empty state."""
        self.set_help(
            "Help",
            "Select a component or property to view a detailed description.",
            None
        )

    def set_field_help(self, index: QModelIndex):
        """Set help text from focused property tree index."""
        if not index.isValid():
            self.clear_help()
            return
        fd: FieldDef = index.data(FieldDefRole)
        if not fd:
            self.clear_help()
            return

        desc, img = get_tooltip_info(fd.field, f"Property '{fd.field}' ({fd.control}).")
        self.set_help(fd.label, desc, img)

    def set_component_help(self, ref: ComponentRef | None):
        """Set help text for selected component ref (no focused property)."""
        if not ref:
            self.clear_help()
            return

        prop_cls = ref.prop_class()
        pretty   = prettify_class_name(prop_cls)

        keys_to_try = [
            prop_cls,
            f"CSmartProp{prop_cls}",
            f"CSmartProp_{prop_cls}",
            f"m_{prop_cls}",
            pretty,
        ]

        desc, img = get_tooltip_info_multi(
            keys_to_try,
            default_desc=f"SmartProp component of class '{prop_cls}'."
        )
        self.set_help(pretty, desc, img)
