"""
HelpPanel — Section 3 Help & Note Pane for SmartProp property editor.

Design matches Hammer's Object Properties help strip:
  • Single QTextBrowser widget (read-only, no interaction) on the left
  • Bold title rendered in a distinct colour (cyan/teal like the reference)
  • Body text below in grey — word-wrapped
  • Optional borderless help picture on the right (auto-scaled, aspect-ratio preserved)
  • Clicking the picture opens a non-modal preview window using Loading Editor Viewport
  • Swappable Note editor with toggle button in top-left corner
  • Smooth 60+ FPS splitter resizing with zero layout fight or rubber-banding
"""

from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from hammer5tools_gui.editors.loading_editor.viewport import Viewport
from hammer5tools_gui.editors.smartprop_editor.note_utils import get_note, has_note
from hammer5tools_gui.editors.smartprop_editor.props.note import NoteEditorWidget
from hammer5tools_gui.editors.smartprop_editor.property_tooltips import (
    get_tooltip_info,
    get_tooltip_info_multi,
    property_tooltips,
    resolve_image_path,
)
from hammer5tools_gui.editors.smartprop_editor.props.components import get_summary_hint, prettify_class_name
from hammer5tools_gui.editors.smartprop_editor.props.model import ComponentRef
from hammer5tools_gui.styles.property_icons import IconCache

_PANEL_BG   = "#303030"
_TITLE_COL  = "#4EC9B0"   # cyan-teal — matches Hammer's category colour
_BODY_COL   = "#b1b1b1"
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


class _ClickableLabel(QWidget):
    """Clickable image preview widget with smooth aspect-ratio scaling and zero layout fight."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._pixmap: QPixmap | None = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(0, 0)

    def setPixmap(self, pixmap: QPixmap | None):
        self._pixmap = pixmap
        self.update()

    def clear(self):
        self._pixmap = None
        self.update()

    def sizeHint(self):
        return QSize(0, 0)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def paintEvent(self, event):
        if self._pixmap and not self._pixmap.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            rect_w = self.width()
            rect_h = self.height()
            if rect_w > 4 and rect_h > 4:
                scaled = self._pixmap.scaled(
                    QSize(rect_w, rect_h),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                x = (rect_w - scaled.width()) // 2
                y = (rect_h - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class HelpPanel(QFrame):
    """Section 3 Help & Note Pane — toggles between Help strip and Note widget with top-left button."""

    noteEdited = Signal(object, str)  # forwarded from NoteEditorWidget

    MODE_HELP = "help"
    MODE_NOTE = "note"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet(f"""
            HelpPanel {{
                background-color: {_PANEL_BG};
                border-top: 1px solid #3e3e3e;
            }}
        """)

        self._current_mode = self.MODE_HELP
        self._current_ref: ComponentRef | None = None
        self._current_pixmap: QPixmap | None = None
        self._current_image_path: str | None = None
        self._current_title: str = ""
        self._image_dialog: HelpImageDialog | None = None

        main_vbox = QVBoxLayout(self)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # ── Top toolbar strip with Toggle button in top-left corner ──────────
        self.toolbar_frame = QFrame(self)
        self.toolbar_frame.setFixedHeight(22)
        self.toolbar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #272727;
                border-bottom: 1px solid #383838;
            }}
        """)
        tb_layout = QHBoxLayout(self.toolbar_frame)
        tb_layout.setContentsMargins(4, 0, 4, 0)
        tb_layout.setSpacing(6)

        self.btn_toggle_mode = QToolButton(self.toolbar_frame)
        self.btn_toggle_mode.setFixedSize(18, 18)
        self.btn_toggle_mode.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 2px;
                padding: 1px;
            }
            QToolButton:hover {
                background-color: #4a4a4a;
                border-color: #666666;
            }
            QToolButton:pressed {
                background-color: #383838;
            }
        """)
        self.btn_toggle_mode.clicked.connect(self.toggle_mode)
        tb_layout.addWidget(self.btn_toggle_mode)

        self.lbl_mode_title = QLabel("Description", self.toolbar_frame)
        self.lbl_mode_title.setStyleSheet("""
            QLabel {
                color: #8E8E8E;
                font-family: "Segoe UI";
                font-size: 10px;
                font-weight: bold;
                background: transparent;
            }
        """)
        tb_layout.addWidget(self.lbl_mode_title)
        tb_layout.addStretch(1)

        main_vbox.addWidget(self.toolbar_frame)

        # ── Stacked widget for Help content vs Note Editor ──────────────────
        self.stacked = QStackedWidget(self)
        self.stacked.setMinimumHeight(0)
        self.stacked.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # View 0: Help content
        self.help_widget = QWidget(self.stacked)
        self.help_widget.setMinimumHeight(0)
        help_layout = QHBoxLayout(self.help_widget)
        help_layout.setContentsMargins(0, 0, 0, 0)
        help_layout.setSpacing(0)

        self.browser = QTextBrowser(self.help_widget)
        self.browser.setOpenLinks(False)
        self.browser.setReadOnly(True)
        self.browser.setFocusPolicy(Qt.NoFocus)
        self.browser.setFrameShape(QFrame.NoFrame)
        self.browser.setMinimumHeight(0)
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {_PANEL_BG};
                color: {_BODY_COL};
                border: none;
                padding: 6px 10px;
                font-family: {_FONT_FACE};
                font-size: 11px;
            }}
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: #555;
                border-radius: 0px;
            }}
        """)
        help_layout.addWidget(self.browser, 1)

        self.image_frame = QFrame(self.help_widget)
        self.image_frame.setMinimumHeight(0)
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
        self.image_label.setToolTip("Click to view full image in viewer")
        self.image_label.clicked.connect(self._on_image_clicked)
        img_layout.addWidget(self.image_label)

        self.image_container = QWidget(self.help_widget)
        self.image_container.setMinimumSize(0, 0)
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(4, 4, 8, 4)
        container_layout.setSpacing(0)
        container_layout.addWidget(self.image_frame)

        help_layout.addWidget(self.image_container, 0)
        self.image_container.hide()

        self.stacked.addWidget(self.help_widget)

        # View 1: Note Editor
        self.note_editor = NoteEditorWidget(self.stacked)
        self.note_editor.setMinimumHeight(0)
        self.note_editor.noteEdited.connect(self.noteEdited)
        self.stacked.addWidget(self.note_editor)

        main_vbox.addWidget(self.stacked, 1)

        self._update_mode_ui()
        self.clear_help()

    def sizeHint(self) -> QSize:
        return QSize(200, 110)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)

    # ── Mode switching (Help vs Note) ───────────────────────────────────────

    def _update_mode_ui(self):
        if self._current_mode == self.MODE_NOTE:
            self.stacked.setCurrentWidget(self.note_editor)
            help_icon = QIcon(":/icons/help_24dp.svg")
            if help_icon.isNull():
                help_icon = IconCache.get_property_icon("legacy")
            self.btn_toggle_mode.setIcon(help_icon)
            self.btn_toggle_mode.setToolTip("Switch to Description / Help")
            self.lbl_mode_title.setText("Note")
        else:
            self.stacked.setCurrentWidget(self.help_widget)
            note_icon = IconCache.get_note_icon()
            self.btn_toggle_mode.setIcon(note_icon)
            self.btn_toggle_mode.setToolTip("Switch to Note")
            self.lbl_mode_title.setText("Description")

    def set_mode(self, mode: str):
        """Set active mode: 'help' or 'note'."""
        if mode in (self.MODE_HELP, self.MODE_NOTE):
            self._current_mode = mode
            self._update_mode_ui()

    def toggle_mode(self):
        """Toggle between Help view and Note view."""
        new_mode = self.MODE_HELP if self._current_mode == self.MODE_NOTE else self.MODE_NOTE
        self.set_mode(new_mode)
        if new_mode == self.MODE_NOTE:
            self.note_editor.focus_editor()

    def open_note(self, ref: ComponentRef | None = None):
        """Activate the note editor and set focus to it."""
        if ref is not None:
            self._current_ref = ref
            self.note_editor.set_component(ref)
        self.set_mode(self.MODE_NOTE)
        self.note_editor.focus_editor()

    # ── Internal Image Display Scaling & Click Handler ──────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_pixmap and not self._current_pixmap.isNull():
            self._update_image_display()

    def _update_image_display(self):
        if self._current_pixmap is None or self._current_pixmap.isNull():
            self.image_container.hide()
            return

        panel_w = self.width()
        panel_h = self.height()

        if panel_h < 20 or panel_w < 60:
            self.image_container.hide()
            return

        target_w = max(40, min(320, int(panel_w * 0.36)))
        self.image_container.setFixedWidth(target_w)
        self.image_label.setPixmap(self._current_pixmap)
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
        self._current_ref = None
        self.note_editor.set_component(None)
        self.set_help(
            "Help",
            "Select a component or property to view a detailed description.",
            None
        )
        self.set_mode(self.MODE_HELP)

    def set_property_help(self, value_class: str, label: str = ""):
        """Set help text for a property selected in the legacy (form) backend."""
        if not value_class:
            self.clear_help()
            return
        desc, img = get_tooltip_info(value_class, f"Property '{value_class}'.")
        self.set_help(label or value_class, desc, img)

    def set_component_help(self, ref: ComponentRef | None):
        """Set help text and note content for selected component ref."""
        self._current_ref = ref
        if not ref or ref.item is None:
            self.clear_help()
            return

        # Bind component to NoteEditorWidget
        self.note_editor.set_component(ref)

        # Check if component has an existing note
        data = ref.item.data(0, Qt.UserRole)
        target = ref.target(data) if isinstance(data, dict) else None
        item_has_note = has_note(target) if isinstance(target, dict) else False

        prop_cls = ref.prop_class()
        pretty   = prettify_class_name(prop_cls)

        keys_to_try = [
            prop_cls,
            f"CSmartPropElement_{prop_cls}",
            f"CSmartPropOperation_{prop_cls}",
            f"CSmartPropFilter_{prop_cls}",
            f"CSmartPropSelectionCriteria_{prop_cls}",
            f"CSmartPropVariable_{prop_cls}",
            f"CSmartPropPulse_{prop_cls}",
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

        # If component has a note, switch to Note view automatically
        if item_has_note:
            self.set_mode(self.MODE_NOTE)
        else:
            self.set_mode(self.MODE_HELP)
