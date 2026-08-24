import os
import re
import sys
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple

import markdown2
from PySide6.QtCore import (
    Qt, QSize, QPoint, QRect, QUrl, Signal, Slot, QObject,
    QThreadPool, QRunnable, QTimer
)
from PySide6.QtGui import (
    QIcon, QPixmap, QImage, QMovie, QPainter, QColor, QFont,
    QCursor, QDesktopServices, QMouseEvent
)
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QMenu, QSizePolicy, QApplication
)

from hammer5tools_gui.common import user_data_dir

# Supported extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.svg', '.webp'}
ANIMATED_EXTENSIONS = {'.gif', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov', '.m4v', '.avi', '.mkv'}
EXCLUDED_RELEASE_ASSETS = {'.nupkg', '.exe', '.msi', '.pdb'}


@dataclass
class Attachment:
    """Represents a media or file attachment associated with a release."""
    url: str
    filename: str
    media_type: str  # 'image', 'gif', 'video', 'file'
    alt_text: str = ""
    size_bytes: int = 0
    source_tag: str = ""


def detect_media_type_from_url_or_name(url_or_name: str) -> str:
    """Infer media type from filename or URL extension."""
    parsed = urllib.parse.urlparse(url_or_name)
    path = parsed.path.lower()
    _, ext = os.path.splitext(path)

    if ext in ANIMATED_EXTENSIONS and ext == '.gif':
        return 'gif'
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    if ext in VIDEO_EXTENSIONS:
        return 'video'
    if 'user-attachments/assets' in url_or_name or 'user-images.githubusercontent.com' in url_or_name:
        # Default to image for github user attachments if no extension specified
        return 'image'
    return 'file'


def detect_media_type_from_bytes(data: bytes, fallback: str = 'image') -> Tuple[str, str]:
    """Detect media type and extension from file magic bytes."""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image', '.png'
    elif data.startswith(b'\xff\xd8\xff'):
        return 'image', '.jpg'
    elif data.startswith(b'GIF87a') or data.startswith(b'GIF89a'):
        return 'gif', '.gif'
    elif data.startswith(b'RIFF') and len(data) >= 12 and data[8:12] == b'WEBP':
        return 'image', '.webp'
    elif data.startswith(b'BM'):
        return 'image', '.bmp'
    elif len(data) >= 8 and (b'ftyp' in data[:16] or b'moov' in data[:32]):
        return 'video', '.mp4'
    elif data.lstrip().startswith(b'<svg') or (data.lstrip().startswith(b'<?xml') and b'<svg' in data[:500]):
        return 'image', '.svg'
    return fallback, ''


def parse_release_segments(
    body: str,
    assets: Optional[list] = None,
    owner: str = "",
    repo: str = "",
    tag: str = ""
) -> List[Tuple[str, object]]:
    """
    Parse release markdown body into sequential segments of ('text', text_content)
    and ('attachment', Attachment) preserving the exact placement of images and media.
    """
    if not body:
        body = ""

    # Strip git commit hashes e.g. (84c17b2c) or (2ca10f12)
    body = re.sub(r'\s*\([0-9a-f]{7,40}\)', '', body)

    # Master pattern for attachments in order
    pattern = re.compile(
        r'(!\[([^\]]*)\]\((https?://[^\s\)]+|\./[^\s\)]+|[^\s\)]+\.(?:png|jpg|jpeg|gif|webp|svg))\))|'
        r'(<img[^>]*src=["\']([^"\']+)["\'][^>]*\s*/?>)|'
        r'(<video[^>]*src=["\']([^"\']+)["\'][^>]*>(?:.*?</video>)?|<video[^>]*src=["\']([^"\']+)["\'][^>]*\s*/?>|</video>)|'
        r'(^\s*(?:https?://github\.com/user-attachments/assets/[a-f0-9-]+|https?://[^\s]+\.(?:png|jpg|jpeg|gif|webp|svg|mp4|webm|mov))\s*$)|'
        r'(\[([^\]]+)\]\((https?://github\.com/user-attachments/assets/[a-f0-9-]+|https?://[^\s]+\.(?:png|jpg|jpeg|gif|webp|svg|mp4|webm|mov))\))',
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )

    segments: List[Tuple[str, object]] = []
    last_idx = 0
    seen_urls = set()

    for match in pattern.finditer(body):
        start, end = match.span()
        text_before = body[last_idx:start]
        if text_before.strip():
            segments.append(('text', text_before))
        last_idx = end

        # Extract attachment info
        url = ""
        alt = ""
        mtype = ""

        if match.group(1):  # Markdown image: ![alt](url)
            alt = match.group(2).strip()
            url = match.group(3).strip()
            mtype = 'image'
        elif match.group(4):  # HTML img: <img src="url">
            url = match.group(5).strip()
            mtype = 'image'
        elif match.group(6):  # HTML video
            url = (match.group(7) or match.group(8) or "").strip()
            mtype = 'video'
        elif match.group(9):  # Bare user-attachment or media URL
            url = match.group(9).strip()
            mtype = detect_media_type_from_url_or_name(url)
        elif match.group(10):  # [title](url)
            alt = match.group(11).strip()
            url = match.group(12).strip()
            mtype = detect_media_type_from_url_or_name(url)

        if url and url not in seen_urls:
            # Resolve relative URLs
            if url.startswith('./') or url.startswith('../') or (not url.startswith('http://') and not url.startswith('https://') and not url.startswith('file://')):
                if owner and repo:
                    ref = tag if tag else 'main'
                    clean_path = url.lstrip('./')
                    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{clean_path}"

            if not mtype:
                mtype = detect_media_type_from_url_or_name(url)

            parsed = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed.path) or alt or "attachment"
            seen_urls.add(url)
            att = Attachment(
                url=url,
                filename=filename,
                media_type=mtype,
                alt_text=alt,
                source_tag=tag
            )
            segments.append(('attachment', att))

    text_after = body[last_idx:]
    if text_after.strip():
        segments.append(('text', text_after))

    # Add loose release assets (non-installers)
    if assets and isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = asset.get('name', '')
            download_url = asset.get('browser_download_url', '')
            size = asset.get('size', 0)
            _, ext = os.path.splitext(name.lower())

            if ext in EXCLUDED_RELEASE_ASSETS or name.lower().startswith('releases.'):
                continue

            if download_url not in seen_urls:
                seen_urls.add(download_url)
                att = Attachment(
                    url=download_url,
                    filename=name,
                    media_type=detect_media_type_from_url_or_name(name),
                    alt_text=name,
                    size_bytes=size,
                    source_tag=tag
                )
                segments.append(('attachment', att))

    return segments


def extract_attachments(
    body: str,
    assets: Optional[list] = None,
    owner: str = "",
    repo: str = "",
    tag: str = ""
) -> Tuple[str, List[Attachment]]:
    """Legacy helper returning (cleaned_markdown, list_of_attachments)."""
    segments = parse_release_segments(body, assets, owner, repo, tag)
    text_chunks = []
    attachments = []
    for stype, sdata in segments:
        if stype == 'text':
            text_chunks.append(sdata)
        elif stype == 'attachment':
            attachments.append(sdata)
    return "\n\n".join(text_chunks), attachments


# ─────────────────────────────────────────────────────────────────────────────
# Cache & Async Downloader
# ─────────────────────────────────────────────────────────────────────────────

class AttachmentCache(QObject):
    """Singleton cache manager for downloaded attachments."""
    _instance = None

    download_finished = Signal(str, str, str)  # url, local_path, media_type
    download_failed = Signal(str, str)         # url, error_message

    @classmethod
    def instance(cls) -> 'AttachmentCache':
        if cls._instance is None:
            cls._instance = AttachmentCache()
        return cls._instance

    def __init__(self):
        super().__init__()
        self.cache_dir = user_data_dir / "cache" / "attachments"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thread_pool = QThreadPool.globalInstance()
        self._callbacks: dict = {}  # url -> {'success': [fn, ...], 'error': [fn, ...]}
        self._active_downloads: set = set()

        self.download_finished.connect(self._on_download_finished)
        self.download_failed.connect(self._on_download_failed)

    def get_cached_path(self, url: str) -> Optional[str]:
        """Check if URL has already been downloaded to cache."""
        url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
        for p in self.cache_dir.glob(f"{url_hash}.*"):
            if not p.name.endswith('.tmp') and p.is_file() and p.stat().st_size > 0:
                return str(p)
        return None

    def fetch_attachment(self, url: str, on_success, on_error=None, expected_type: str = 'image'):
        """Fetch attachment asynchronously. Calls on_success(local_path, media_type) on completion."""
        cached = self.get_cached_path(url)
        if cached:
            mtype = detect_media_type_from_url_or_name(cached)
            QTimer.singleShot(0, lambda: on_success(cached, mtype))
            return

        if url not in self._callbacks:
            self._callbacks[url] = {'success': [], 'error': []}
        
        self._callbacks[url]['success'].append(on_success)
        if on_error:
            self._callbacks[url]['error'].append(on_error)

        if url in self._active_downloads:
            return

        self._active_downloads.add(url)

        cache_dir = self.cache_dir
        cache_obj = self

        class Worker(QRunnable):
            def run(self):
                try:
                    url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    
                    req = urllib.request.Request(
                        url,
                        headers={'User-Agent': 'Hammer5Tools-Updater'}
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        data = resp.read()
                        content_type = resp.headers.get_content_type() or ""

                    mtype, ext = detect_media_type_from_bytes(data, fallback=expected_type)
                    if not ext:
                        if 'gif' in content_type:
                            ext = '.gif'; mtype = 'gif'
                        elif 'png' in content_type:
                            ext = '.png'; mtype = 'image'
                        elif 'jpeg' in content_type or 'jpg' in content_type:
                            ext = '.jpg'; mtype = 'image'
                        elif 'webp' in content_type:
                            ext = '.webp'; mtype = 'image'
                        elif 'mp4' in content_type:
                            ext = '.mp4'; mtype = 'video'
                        else:
                            ext = '.bin'

                    target_path = cache_dir / f"{url_hash}{ext}"
                    temp_path = cache_dir / f"{url_hash}.tmp"
                    
                    with open(temp_path, 'wb') as f:
                        f.write(data)
                    
                    if target_path.exists():
                        try:
                            target_path.unlink()
                        except Exception:
                            pass
                    temp_path.rename(target_path)

                    try:
                        cache_obj.download_finished.emit(url, str(target_path), mtype)
                    except RuntimeError:
                        pass
                except Exception as e:
                    try:
                        cache_obj.download_failed.emit(url, str(e))
                    except RuntimeError:
                        pass

        self.thread_pool.start(Worker())

    @Slot(str, str, str)
    def _on_download_finished(self, url: str, path: str, mtype: str):
        self._active_downloads.discard(url)
        cbs = self._callbacks.pop(url, {'success': [], 'error': []})
        for fn in cbs.get('success', []):
            try:
                fn(path, mtype)
            except Exception as e:
                print(f"Error in attachment callback: {e}")

    @Slot(str, str)
    def _on_download_failed(self, url: str, error: str):
        self._active_downloads.discard(url)
        cbs = self._callbacks.pop(url, {'success': [], 'error': []})
        for fn in cbs.get('error', []):
            try:
                fn(error)
            except Exception as e:
                print(f"Error in attachment error callback: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Attachment Preview UI Components
# ─────────────────────────────────────────────────────────────────────────────

class AttachmentThumbnailWidget(QFrame):
    """
    Thumbnail widget displaying a centered image or GIF preview.
    Clicking opens the generic SmartProp Editor HelpImageDialog.
    """
    clicked = Signal()

    def __init__(self, attachment: Attachment, parent=None):
        super().__init__(parent)
        self.attachment = attachment
        self.local_path: Optional[str] = None
        self.pixmap: Optional[QPixmap] = None
        self.movie: Optional[QMovie] = None
        self.is_movie = False

        self.setObjectName("AttachmentThumbnailCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.setStyleSheet("""
            QFrame#AttachmentThumbnailCard {
                background: transparent;
                border: none;
                padding: 4px 0px;
                margin: 0px;
            }
            QLabel {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
                qproperty-alignment: AlignCenter;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        # Image container label
        self.preview_label = QLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("Loading preview...")
        self.preview_label.setStyleSheet("color: #929292; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(self.preview_label)

        self.setToolTip("Click to view full image in viewer")
        self._load_attachment()

    def _load_attachment(self):
        AttachmentCache.instance().fetch_attachment(
            self.attachment.url,
            on_success=self._on_download_success,
            on_error=self._on_download_error,
            expected_type=self.attachment.media_type
        )

    def _on_download_success(self, path: str, media_type: str):
        self.local_path = path
        if not os.path.exists(path):
            self._on_download_error("File does not exist")
            return

        ext = os.path.splitext(path)[1].lower()
        if ext in ('.gif', '.webp') or media_type == 'gif':
            movie = QMovie(path)
            if movie.isValid() and movie.frameCount() > 1:
                self.is_movie = True
                self.movie = movie
                self.preview_label.setMovie(self.movie)
                self.preview_label.setAlignment(Qt.AlignCenter)
                self.movie.start()
                return

        pix = QPixmap(path)
        if not pix.isNull():
            self.pixmap = pix
            self._update_scaled_pixmap()
        else:
            self._on_download_error("Invalid image data")

    def _on_download_error(self, err_msg: str):
        self.preview_label.setText("Image preview unavailable")
        self.preview_label.setStyleSheet("color: #797979; font-size: 10px; font-style: italic;")

    def _update_scaled_pixmap(self):
        if self.pixmap is None or self.pixmap.isNull():
            return
        
        max_h = 360
        max_w = 560
        scaled = self.pixmap.scaled(
            max_w, max_h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setAlignment(Qt.AlignCenter)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._open_viewer()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _open_viewer(self):
        if not self.local_path or not os.path.exists(self.local_path):
            # Fallback to browser if local path not yet ready
            QDesktopServices.openUrl(QUrl(self.attachment.url))
            return

        from hammer5tools_gui.editors.smartprop_editor.props.help import HelpImageDialog
        title = self.attachment.alt_text or self.attachment.filename or "Image viewer"
        dialog = HelpImageDialog(
            image_path=self.local_path,
            title=f"Image viewer — {title}",
            parent=self.window()
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2e2e2e;
                color: #e5e5e5;
                border: 1px solid #464649;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #515965;
            }
        """)

        view_act = menu.addAction("View in Image Viewer")
        copy_img_act = menu.addAction("Copy Image")
        copy_url_act = menu.addAction("Copy Link")
        open_web_act = menu.addAction("Open in Browser")

        action = menu.exec(event.globalPos())
        if action == view_act:
            self._open_viewer()
        elif action == copy_img_act and self.pixmap:
            QApplication.clipboard().setPixmap(self.pixmap)
        elif action == copy_url_act:
            QApplication.clipboard().setText(self.attachment.url)
        elif action == open_web_act:
            QDesktopServices.openUrl(QUrl(self.attachment.url))


class VideoAttachmentWidget(QFrame):
    """
    Interactive card representing a video attachment or screen recording.
    """
    def __init__(self, attachment: Attachment, parent=None):
        super().__init__(parent)
        self.attachment = attachment
        self.setObjectName("VideoAttachmentCard")

        self.setStyleSheet("""
            QFrame#VideoAttachmentCard {
                background: transparent;
                border: none;
                padding: 2px 5px;
                margin: 0px;
            }
            QPushButton {
                background-color: #373737;
                color: #e5e5e5;
                border: 1px solid #464649;
                border-radius: 3px;
                padding: 3px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a83c9;
                color: white;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(10)

        # Video indicator
        icon_label = QLabel("▶", self)
        icon_label.setStyleSheet("color: #4a83c9; font-size: 14px; font-weight: bold;")
        layout.addWidget(icon_label)

        # Info text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = self.attachment.alt_text or self.attachment.filename or "Video Recording"
        title_label = QLabel(title, self)
        title_label.setStyleSheet("color: #e5e5e5; font-size: 11px; font-weight: bold;")
        text_layout.addWidget(title_label)

        sub_label = QLabel("Video Attachment", self)
        sub_label.setStyleSheet("color: #a5a5a5; font-size: 10px;")
        text_layout.addWidget(sub_label)

        layout.addLayout(text_layout, 1)

        play_btn = QPushButton("Play Video", self)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.attachment.url)))
        layout.addWidget(play_btn)


class FileAttachmentWidget(QFrame):
    """
    Card for downloadable file attachments (e.g. zip presets, documentation).
    """
    def __init__(self, attachment: Attachment, parent=None):
        super().__init__(parent)
        self.attachment = attachment
        self.setObjectName("FileAttachmentCard")

        self.setStyleSheet("""
            QFrame#FileAttachmentCard {
                background: transparent;
                border: none;
                padding: 2px 5px;
                margin: 0px;
            }
            QPushButton {
                background-color: #373737;
                color: #e5e5e5;
                border: 1px solid #464649;
                border-radius: 3px;
                padding: 3px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4a83c9;
                color: white;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 4)
        layout.setSpacing(10)

        icon_label = QLabel("📁", self)
        icon_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        name_label = QLabel(self.attachment.filename, self)
        name_label.setStyleSheet("color: #e5e5e5; font-size: 11px; font-weight: bold;")
        text_layout.addWidget(name_label)

        size_str = ""
        if self.attachment.size_bytes > 0:
            mb = self.attachment.size_bytes / (1024 * 1024)
            size_str = f"{mb:.1f} MB" if mb >= 1.0 else f"{self.attachment.size_bytes / 1024:.0f} KB"
            size_label = QLabel(size_str, self)
            size_label.setStyleSheet("color: #a5a5a5; font-size: 10px;")
            text_layout.addWidget(size_label)

        layout.addLayout(text_layout, 1)

        download_btn = QPushButton("Download", self)
        download_btn.setCursor(Qt.PointingHandCursor)
        download_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.attachment.url)))
        layout.addWidget(download_btn)
