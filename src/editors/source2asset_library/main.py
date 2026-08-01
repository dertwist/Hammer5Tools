import os
import sys
import html
import json
import shutil
import hashlib
import zipfile
import urllib.request
import urllib.error
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QScrollArea, QFrame, QGridLayout,
    QMessageBox, QDialog, QTextEdit, QToolTip, QSplitter,
    QCheckBox, QTreeWidget, QTreeWidgetItem, QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl, QTimer, QEvent
from PySide6.QtGui import QPixmap, QIcon, QColor, QFont, QCursor, QDesktopServices, QUndoStack

from src.settings.main import get_addon_dir, get_addon_name, debug
from src.forms.asset_manager.move_worker import MoveWorker
from src.styles.common import apply_stylesheets, qt_stylesheet_button
from src.widgets.tree import HierarchyTreeWidget
from src.editors.smartprop_editor.property_tooltips import resolve_image_path
from src.forms.cleanup.common import format_size
import src.common as common

# Storage constants
USERDATA_DIR = os.path.join("userdata", "Source2AssetLibrary")
CACHE_DIR = os.path.join(USERDATA_DIR, "cache")
THUMB_DIR = os.path.join(USERDATA_DIR, "thumbnails")
DOWNLOAD_DIR = os.path.join(USERDATA_DIR, "downloads")
INSTALLED_DIR = os.path.join(USERDATA_DIR, "installed")

INDEX_URL = "https://raw.githubusercontent.com/dertwist/Source2AssetLibrary/main/index.json"
REPO_URL = "https://github.com/dertwist/Source2AssetLibrary"

# Valve Asset Type Icons Mapping
ASSET_TYPE_ICONS = {
    "vmdl": "model_sm.png", "models": "model_sm.png", "model": "model_sm.png",
    "vsmart": "smart_prop_sm.png", "smartprops": "smart_prop_sm.png", "smartprop": "smart_prop_sm.png",
    "vmat": "material_sm.png", "materials": "material_sm.png", "material": "material_sm.png",
    "vpcf": "particles_sm.png", "particles": "particles_sm.png",
    "vmap": "map_sm.png", "maps": "map_sm.png",
    "vsndevts": "vmix_sm.png", "sounds": "vmix_sm.png", "sound": "vmix_sm.png",
    "js": "javascript_sm.png", "ts": "typescript_sm.png", "scripts": "javascript_sm.png", "script": "javascript_sm.png"
}

LICENSE_COLORS = {
    "CC0": {"color": "#10b981", "bg": "rgba(16, 185, 129, 0.15)"},
    "CC BY": {"color": "#06b6d4", "bg": "rgba(6, 182, 212, 0.15)"},
    "CC BY-SA": {"color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.15)"},
    "CC BY-ND": {"color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.15)"},
    "CC BY-NC": {"color": "#f97316", "bg": "rgba(249, 115, 22, 0.15)"},
    "CC BY-NC-SA": {"color": "#ef4444", "bg": "rgba(239, 68, 68, 0.15)"},
    "CC BY-NC-ND": {"color": "#dc2626", "bg": "rgba(220, 38, 38, 0.15)"}
}

LICENSE_MATRIX = {
    "CC BY": {"attribution": True, "commercial": True, "derivatives": True, "desc": "Copy, share, adapt, and use in almost any way. Must give credit."},
    "CC BY-SA": {"attribution": True, "commercial": True, "derivatives": True, "desc": "Adaptations must be shared under the same license. Must give credit."},
    "CC BY-ND": {"attribution": True, "commercial": True, "derivatives": False, "desc": "Copy and share the work as-is. No changes or derivatives allowed. Must give credit."},
    "CC BY-NC": {"attribution": True, "commercial": False, "derivatives": True, "desc": "Copy, share, and adapt for noncommercial use only. Must give credit."},
    "CC BY-NC-SA": {"attribution": True, "commercial": False, "derivatives": True, "desc": "Noncommercial reuse and adaptations under same license. Must give credit."},
    "CC BY-NC-ND": {"attribution": True, "commercial": False, "derivatives": False, "desc": "Share work as-is for noncommercial use only. No changes allowed. Must give credit."},
    "CC0": {"attribution": False, "commercial": True, "derivatives": True, "desc": "Public Domain. No license conditions or credit required."}
}


def get_valve_asset_icon(ext_or_category: str) -> QIcon:
    ext_clean = ext_or_category.lower().lstrip(".")
    icon_fname = ASSET_TYPE_ICONS.get(ext_clean, "generic_sm.png")

    assettypes_dir = os.path.join(str(common.app_dir), "src", "icons", "tools", "assettypes")
    icon_path = os.path.join(assettypes_dir, icon_fname)
    if os.path.isfile(icon_path):
        return QIcon(icon_path)
    return QIcon(":/icons/description_16dp.svg")


def placeholder_pixmap(width: int, height: int) -> QPixmap:
    """Stand-in thumbnail shown until the asset's own thumb.png arrives."""
    pix = QPixmap(resolve_image_path("images/placeholder.png") or "")
    if pix.isNull():
        return pix
    return pix.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def author_html(asset: dict) -> str:
    """'By <name>', hyperlinked when the index entry carries an author url."""
    author = asset.get("author") or {}
    name = html.escape(author.get("name") or "Community")
    url = author.get("url") or ""
    if url.startswith("http"):
        return f"By <a href='{html.escape(url, quote=True)}' style='color: #4f98a3; text-decoration: none;'>{name}</a>"
    return f"By {name}"


def http_fetch_bytes(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Hammer5Tools/1.0 (Windows)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def build_license_tooltip(license_name: str) -> str:
    info = LICENSE_MATRIX.get(license_name.upper(), LICENSE_MATRIX.get(license_name, None))
    if info:
        attr_str = "YES" if info["attribution"] else "NO"
        comm_str = "YES" if info["commercial"] else "NO"
        deriv_str = "YES" if info["derivatives"] else "NO"
        desc_str = info["desc"]
        return (
            f"License: {license_name}\n"
            f"----------------------------------------\n"
            f"• Attribution required: {attr_str}\n"
            f"• Commercial use allowed: {comm_str}\n"
            f"• Derivatives allowed: {deriv_str}\n"
            f"----------------------------------------\n"
            f"{desc_str}"
        )
    return f"License: {license_name}"


class IndexFetcherThread(QThread):
    fetched_signal = Signal(list, str)

    def run(self):
        local_cache = os.path.join(CACHE_DIR, "index_cache.json")
        repo_local = os.path.normpath("../Source2AssetLibrary/index.json")

        assets = []
        error_msg = ""

        try:
            raw_bytes = http_fetch_bytes(INDEX_URL, timeout=8)
            data = json.loads(raw_bytes.decode("utf-8"))
            assets = data.get("assets", [])
            with open(local_cache, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.fetched_signal.emit(assets, "")
            return
        except Exception as e:
            error_msg = f"Network fetch failed: {e}"
            debug(f"Source2AssetLibrary network fetch error: {e}")

        if os.path.isfile(local_cache):
            try:
                with open(local_cache, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    assets = data.get("assets", [])
                    self.fetched_signal.emit(assets, "Loaded from local cache.")
                    return
            except Exception as le:
                debug(f"Local cache read error: {le}")

        if os.path.isfile(repo_local):
            try:
                with open(repo_local, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    assets = data.get("assets", [])
                    shutil.copyfile(repo_local, local_cache)
                    self.fetched_signal.emit(assets, "Loaded from repository folder.")
                    return
            except Exception as re_err:
                debug(f"Repo local read error: {re_err}")

        self.fetched_signal.emit([], f"Could not load asset index. {error_msg}")


class ThumbnailFetcherThread(QThread):
    thumb_fetched = Signal(str, str)

    def __init__(self, asset_id: str, thumb_url: str, category: str):
        super().__init__()
        self.asset_id = asset_id
        self.thumb_url = thumb_url
        self.category = category

    def run(self):
        dest_path = os.path.join(THUMB_DIR, f"{self.asset_id}.png")
        if os.path.isfile(dest_path):
            self.thumb_fetched.emit(self.asset_id, dest_path)
            return

        if self.thumb_url.startswith("http"):
            try:
                img_data = http_fetch_bytes(self.thumb_url, timeout=10)
                with open(dest_path, "wb") as f:
                    f.write(img_data)
                self.thumb_fetched.emit(self.asset_id, dest_path)
                return
            except Exception as e:
                debug(f"Failed to fetch thumb for {self.asset_id}: {e}")

        local_repo_thumb = os.path.normpath(f"../Source2AssetLibrary/assets/{self.category}/{self.asset_id}/thumb.png")
        if os.path.isfile(local_repo_thumb):
            shutil.copyfile(local_repo_thumb, dest_path)
            self.thumb_fetched.emit(self.asset_id, dest_path)


class ArchiveDownloaderThread(QThread):
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, str, str)

    def __init__(self, asset_data: dict):
        super().__init__()
        self.asset = asset_data

    def run(self):
        try:
            asset_id = self.asset["id"]
            download_info = self.asset.get("download", {})
            files_list = download_info.get("files", [])
            if not files_list:
                raise ValueError("No download files specified for asset.")

            temp_asset_dir = os.path.join(DOWNLOAD_DIR, asset_id)
            os.makedirs(temp_asset_dir, exist_ok=True)
            chunk_paths = []
            total_files = len(files_list)

            for idx, file_info in enumerate(files_list):
                fname = file_info["name"]
                furl = file_info.get("url", "")
                expected_sha = file_info.get("sha256", "")
                dest_file = os.path.join(temp_asset_dir, fname)

                pct = int(((idx + 0.1) / total_files) * 80)
                self.progress_signal.emit(pct, f"Part {idx+1}/{total_files}")

                if furl.startswith("http"):
                    part_bytes = http_fetch_bytes(furl, timeout=30)
                    with open(dest_file, "wb") as f:
                        f.write(part_bytes)
                else:
                    local_fallback = os.path.normpath(f"../Source2AssetLibrary/assets/{self.asset.get('category', 'smartprops')}/{asset_id}/{fname}")
                    if os.path.isfile(local_fallback):
                        shutil.copyfile(local_fallback, dest_file)
                    else:
                        raise ValueError(f"Cannot resolve download source for {fname}")

                if expected_sha and not self.verify_sha256(dest_file, expected_sha):
                    raise ValueError(f"Checksum mismatch for part {fname}")

                chunk_paths.append(dest_file)

            combined_zip_path = os.path.join(temp_asset_dir, "asset.zip")
            self.progress_signal.emit(90, "Combining parts...")

            if len(chunk_paths) == 1 and chunk_paths[0].endswith(".zip"):
                if chunk_paths[0] != combined_zip_path:
                    shutil.copyfile(chunk_paths[0], combined_zip_path)
            else:
                with open(combined_zip_path, "wb") as out_zip:
                    for cp in chunk_paths:
                        with open(cp, "rb") as in_part:
                            shutil.copyfileobj(in_part, out_zip)

            self.progress_signal.emit(100, "Done")
            self.finished_signal.emit(True, asset_id, combined_zip_path)

        except Exception as e:
            self.finished_signal.emit(False, self.asset.get("id", ""), str(e))

    @staticmethod
    def verify_sha256(file_path: str, expected_sha: str) -> bool:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
        return hasher.hexdigest().lower() == expected_sha.lower()


class GridScrollArea(QScrollArea):
    resized = Signal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


class AssetCardWidget(QFrame):
    card_selected = Signal(dict)

    def __init__(self, asset_data: dict, parent_tab=None):
        super().__init__()
        self.asset = asset_data
        self.parent_tab = parent_tab
        self.asset_id = asset_data["id"]

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e20;
                border-radius: 0px;
                border: 1px solid #333336;
            }
            QFrame:hover {
                border: 1px solid #4f98a3;
            }
        """)
        self.setFixedWidth(230)
        self.setFixedHeight(260)

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(3)

        # 1. Sharp Top Thumbnail Label
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(214, 120)
        self.thumb_label.setStyleSheet("background-color: #121214; border-radius: 0px; border: 1px solid #2a2a2d;")
        self.thumb_label.setAlignment(Qt.AlignCenter)

        self.load_thumbnail()
        card_layout.addWidget(self.thumb_label)

        # 2. Title
        title_label = QLabel(self.asset.get("name", self.asset_id))
        title_font = QFont("Segoe UI", 9)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #E3E3E3; border: none; background: transparent;")
        title_label.setWordWrap(True)
        card_layout.addWidget(title_label)

        # 3. Author Subtitle
        author_label = QLabel(author_html(self.asset))
        author_label.setFont(QFont("Segoe UI", 8))
        author_label.setTextFormat(Qt.RichText)
        author_label.setOpenExternalLinks(True)
        author_label.setStyleSheet("color: #8E8E93; border: none; background: transparent;")
        card_layout.addWidget(author_label)

        # 4. License Badge Only
        license_str = self.asset.get("license", "CC BY")
        c_style = LICENSE_COLORS.get(license_str.upper(), {"color": "#4f98a3", "bg": "rgba(79, 152, 163, 0.15)"})

        license_badge = QLabel(f" {license_str} ")
        lic_font = QFont("Segoe UI", 7)
        lic_font.setBold(True)
        license_badge.setFont(lic_font)
        license_badge.setStyleSheet(
            f"background-color: {c_style['bg']}; "
            f"color: {c_style['color']}; "
            f"border-radius: 0px; "
            f"padding: 1px 4px; "
            f"border: 1px solid {c_style['color']};"
        )
        license_badge.setToolTip(build_license_tooltip(license_str))
        license_badge.setCursor(QCursor(Qt.WhatsThisCursor))

        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(4)
        badges_layout.setContentsMargins(0, 1, 0, 1)
        badges_layout.addWidget(license_badge)
        badges_layout.addStretch()
        card_layout.addLayout(badges_layout)

        # 5. Tags Row (#tag1 #tag2)
        tags_list = self.asset.get("tags", [])
        if tags_list:
            formatted_tags = " ".join([f"#{t}" for t in tags_list])
            tags_label = QLabel(formatted_tags)
            tags_font = QFont("Segoe UI", 7)
            tags_font.setItalic(True)
            tags_label.setFont(tags_font)
            tags_label.setStyleSheet("color: #71717a; border: none; background: transparent;")
            tags_label.setWordWrap(False)
            card_layout.addWidget(tags_label)

        card_layout.addStretch(1)

        # 6. Action Button at VERY BOTTOM
        self.action_btn = QPushButton("Download Asset")
        self.action_btn.setStyleSheet(qt_stylesheet_button)
        self.action_btn.setFixedHeight(26)
        self.action_btn.clicked.connect(self.on_action_click)
        card_layout.addWidget(self.action_btn)

        self.update_status()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.card_selected.emit(self.asset)

    def load_thumbnail(self):
        dest_path = os.path.join(THUMB_DIR, f"{self.asset_id}.png")
        if os.path.isfile(dest_path):
            pixmap = QPixmap(dest_path)
            self.thumb_label.setPixmap(pixmap.scaled(214, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.thumb_label.setPixmap(placeholder_pixmap(214, 120))
            thumb_url = self.asset.get("thumb_url", "")
            cat = self.asset.get("category", "smartprops")

            self.thumb_worker = ThumbnailFetcherThread(self.asset_id, thumb_url, cat)
            def on_thumb_done(aid, path):
                if aid == self.asset_id and os.path.isfile(path):
                    pix = QPixmap(path)
                    self.thumb_label.setPixmap(pix.scaled(214, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            self.thumb_worker.thumb_fetched.connect(on_thumb_done)
            self.thumb_worker.start()

    def update_status(self):
        manifest_path = os.path.join(INSTALLED_DIR, self.asset_id, "manifest.json")
        downloaded_zip = os.path.join(DOWNLOAD_DIR, self.asset_id, "asset.zip")

        if os.path.isfile(manifest_path):
            self.action_btn.setEnabled(True)
            self.action_btn.setText("Imported (Options)")
            self.action_btn.setStyleSheet(qt_stylesheet_button)
        elif os.path.isfile(downloaded_zip):
            self.action_btn.setEnabled(True)
            self.action_btn.setText("Import to Addon")
            self.action_btn.setStyleSheet(qt_stylesheet_button)
        else:
            self.action_btn.setEnabled(True)
            self.action_btn.setText("Download Asset")
            self.action_btn.setStyleSheet(qt_stylesheet_button)

    def on_action_click(self):
        manifest_path = os.path.join(INSTALLED_DIR, self.asset_id, "manifest.json")
        downloaded_zip = os.path.join(DOWNLOAD_DIR, self.asset_id, "asset.zip")

        if os.path.isfile(manifest_path):
            if self.parent_tab:
                self.parent_tab.select_asset_for_panel(self.asset)
        elif os.path.isfile(downloaded_zip):
            if self.parent_tab:
                self.parent_tab.select_asset_for_panel(self.asset)
                self.parent_tab.import_asset_to_project(self.asset)
        else:
            self.start_in_button_download()

    def start_in_button_download(self):
        self.action_btn.setEnabled(False)
        self.action_btn.setText("Downloading 0%...")
        self.action_btn.setStyleSheet(qt_stylesheet_button)

        self.dl_thread = ArchiveDownloaderThread(self.asset)

        def on_prog(pct, msg):
            self.action_btn.setText(f"Downloading {pct}%...")

        def on_finished(success, aid, result):
            if success:
                self.update_status()
                if self.parent_tab:
                    self.parent_tab.filter_assets()
                    self.parent_tab.select_asset_for_panel(self.asset)
            else:
                self.action_btn.setEnabled(True)
                self.action_btn.setText("Download Failed")
                QMessageBox.critical(self, "Download Error", f"Error downloading asset: {result}")
                self.update_status()

        self.dl_thread.progress_signal.connect(on_prog)
        self.dl_thread.finished_signal.connect(on_finished)
        self.dl_thread.start()

    def uninstall_asset(self):
        manifest_path = os.path.join(INSTALLED_DIR, self.asset_id, "manifest.json")
        if not os.path.isfile(manifest_path):
            return

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        target_dir = manifest.get("target_addon_dir", "")
        installed_files = manifest.get("installed_files", [])

        for rel_file in installed_files:
            full_p = os.path.join(target_dir, rel_file)
            if os.path.isfile(full_p):
                try:
                    os.remove(full_p)
                except Exception as e:
                    debug(f"Failed to remove {full_p}: {e}")

        shutil.rmtree(os.path.dirname(manifest_path), ignore_errors=True)
        QMessageBox.information(self, "Removed", f"Removed asset '{self.asset_id}' from addon.")
        self.update_status()

    def reposition_asset(self):
        addon_dir = get_addon_dir()
        if not addon_dir:
            QMessageBox.warning(self, "No Addon", "Please select an active addon first.")
            return

        manifest_path = os.path.join(INSTALLED_DIR, self.asset_id, "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        installed_files = manifest.get("installed_files", [])
        if not installed_files:
            QMessageBox.information(self, "No Files", "No files found to reposition.")
            return

        from PySide6.QtWidgets import QFileDialog
        new_dir = QFileDialog.getExistingDirectory(self, "Select New Destination Directory in Addon", addon_dir)
        if not new_dir:
            return

        move_pairs = []
        new_installed_files = []
        for rel_p in installed_files:
            old_p = os.path.join(addon_dir, rel_p)
            bname = os.path.basename(rel_p)
            new_p = os.path.join(new_dir, bname)
            if os.path.exists(old_p):
                move_pairs.append((old_p, new_p))
                new_installed_files.append(os.path.relpath(new_p, addon_dir).replace("\\", "/"))

        if move_pairs:
            progress = QProgressDialog("Repositioning asset and updating references...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            apply_stylesheets(progress)
            progress.show()

            self.worker = MoveWorker(move_pairs, addon_dir)

            def on_done():
                progress.close()
                manifest["installed_files"] = new_installed_files
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)
                QMessageBox.information(self, "Reposition Complete", "Asset repositioned and references updated successfully!")

            self.worker.finished_move.connect(on_done)
            self.worker.start()


class ImportOptionsPanel(QFrame):
    def __init__(self, parent_tab=None):
        super().__init__()
        self.parent_tab = parent_tab
        self.current_asset = None

        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame#ImportOptionsPanel {
                background-color: #18181a;
                border-left: 1px solid #2d2d30;
            }
            QLabel { color: #e3e3e3; font-size: 9pt; background: transparent; }
            QLineEdit {
                background-color: #1e1e20; color: #e3e3e3;
                border: 1px solid #333336; padding: 3px 6px; font-size: 8.5pt;
            }
            QCheckBox { color: #e3e3e3; font-size: 8.5pt; background: transparent; }
        """)
        self.setObjectName("ImportOptionsPanel")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 1. Package Details Header
        details_header = QLabel("Package Details")
        d_font = QFont("Segoe UI", 10)
        d_font.setBold(True)
        details_header.setFont(d_font)
        layout.addWidget(details_header)

        # Side-by-Side Thumbnail + Full Info Layout
        details_row = QHBoxLayout()
        details_row.setSpacing(10)

        self.thumb_preview_label = QLabel("No Preview")
        self.thumb_preview_label.setFixedSize(125, 95)
        self.thumb_preview_label.setStyleSheet("background-color: #121214; border: 1px solid #2a2a2d; color: #666666;")
        self.thumb_preview_label.setAlignment(Qt.AlignCenter)
        details_row.addWidget(self.thumb_preview_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        self.asset_name_label = QLabel("No asset selected")
        a_font = QFont("Segoe UI", 9)
        a_font.setBold(True)
        self.asset_name_label.setFont(a_font)
        self.asset_name_label.setStyleSheet("color: #4f98a3; background: transparent;")
        self.asset_name_label.setWordWrap(True)
        info_col.addWidget(self.asset_name_label)

        self.author_meta_label = QLabel("")
        self.author_meta_label.setTextFormat(Qt.RichText)
        self.author_meta_label.setOpenExternalLinks(True)
        self.author_meta_label.setStyleSheet("color: #94a3b8; background: transparent; font-size: 8.5pt;")
        info_col.addWidget(self.author_meta_label)

        # Category displayed in LOWERCASE
        self.cat_meta_label = QLabel("")
        self.cat_meta_label.setStyleSheet("color: #a1a1aa; background: transparent; font-size: 8.5pt;")
        info_col.addWidget(self.cat_meta_label)

        self.license_meta_label = QLabel("")
        self.license_meta_label.setStyleSheet("color: #4f98a3; background: transparent; font-weight: bold; font-size: 8.5pt;")
        info_col.addWidget(self.license_meta_label)

        self.size_meta_label = QLabel("")
        self.size_meta_label.setStyleSheet("color: #a1a1aa; background: transparent; font-size: 8.5pt;")
        info_col.addWidget(self.size_meta_label)

        self.tags_meta_label = QLabel("")
        self.tags_meta_label.setStyleSheet("color: #71717a; background: transparent; font-style: italic; font-size: 8pt;")
        info_col.addWidget(self.tags_meta_label)

        info_col.addStretch(1)
        details_row.addLayout(info_col, stretch=1)
        layout.addLayout(details_row)

        self.asset_desc_label = QLabel("")
        self.asset_desc_label.setStyleSheet("color: #b0b0b8; background: transparent; font-size: 8.5pt;")
        self.asset_desc_label.setWordWrap(True)
        layout.addWidget(self.asset_desc_label)

        # 2. Import Options Header
        import_header = QLabel("Import Options")
        i_font = QFont("Segoe UI", 10)
        i_font.setBold(True)
        import_header.setFont(i_font)
        layout.addWidget(import_header)

        # Subfolder & Overwrite in single row
        opt_row = QHBoxLayout()
        opt_row.setSpacing(6)

        sub_lbl = QLabel("Subfolder:")
        opt_row.addWidget(sub_lbl)

        self.subfolder_edit = QLineEdit("s2library")
        self.subfolder_edit.setPlaceholderText("s2library")
        opt_row.addWidget(self.subfolder_edit, stretch=1)

        self.overwrite_check = QCheckBox("Overwrite existing")
        self.overwrite_check.setChecked(True)
        opt_row.addWidget(self.overwrite_check)

        layout.addLayout(opt_row)

        self.addon_name_label = QLabel(f"Target Addon: {get_addon_name() or 'None Selected'}")
        self.addon_name_label.setStyleSheet("color: #10b981; font-weight: bold; background: transparent;")
        layout.addWidget(self.addon_name_label)

        # 3. Package File Contents (SmartProp Editor Hierarchy Tree Widget)
        tree_header = QLabel("Package File Contents:")
        t_font = QFont("Segoe UI", 9)
        t_font.setBold(True)
        tree_header.setFont(t_font)
        layout.addWidget(tree_header)

        self.undo_stack = QUndoStack(self)
        self.tree_widget = HierarchyTreeWidget(undo_stack=self.undo_stack, list_mode=False)
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.setDragEnabled(False)
        self.tree_widget.setAcceptDrops(False)
        self.tree_widget.setContextMenuPolicy(Qt.NoContextMenu)
        self.tree_widget.setEditTriggers(QTreeWidget.NoEditTriggers)

        layout.addWidget(self.tree_widget, stretch=1)

        # Single Row Action Buttons Layout (Import to Addon, Reposition, Remove from Addon)
        btn_row_layout = QHBoxLayout()
        btn_row_layout.setSpacing(4)

        self.import_btn = QPushButton("Import to Addon")
        self.import_btn.setStyleSheet(qt_stylesheet_button)
        self.import_btn.clicked.connect(self.on_panel_import_click)

        self.reposition_btn = QPushButton("Reposition")
        self.reposition_btn.setStyleSheet(qt_stylesheet_button)
        self.reposition_btn.clicked.connect(self.on_panel_reposition_click)

        self.remove_btn = QPushButton("Remove from Addon")
        self.remove_btn.setStyleSheet(qt_stylesheet_button)
        self.remove_btn.clicked.connect(self.on_panel_remove_click)

        btn_row_layout.addWidget(self.import_btn, stretch=1)
        btn_row_layout.addWidget(self.reposition_btn, stretch=1)
        btn_row_layout.addWidget(self.remove_btn, stretch=1)

        layout.addLayout(btn_row_layout)

        apply_stylesheets(self)
        self.set_asset(None)

    def set_asset(self, asset: dict):
        self.current_asset = asset
        self.tree_widget.clear()

        if not asset:
            self.asset_name_label.setText("No asset selected")
            self.author_meta_label.setText("")
            self.cat_meta_label.setText("")
            self.license_meta_label.setText("")
            self.size_meta_label.setText("")
            self.tags_meta_label.setText("")
            self.asset_desc_label.setText("")
            self.thumb_preview_label.clear()
            self.thumb_preview_label.setText("No Preview")
            self.import_btn.setEnabled(False)
            self.reposition_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            return

        aid = asset["id"]
        self.asset_name_label.setText(f"{asset.get('name', aid)}")
        self.author_meta_label.setText(author_html(asset))
        self.cat_meta_label.setText(f"Category: {asset.get('category', 'asset').lower()}")
        self.license_meta_label.setText(f"License: {asset.get('license', 'CC BY')}")

        total_bytes = asset.get("download", {}).get("total_size_bytes", 0)
        self.size_meta_label.setText(f"Size: {format_size(total_bytes)}" if total_bytes else "")

        tags_list = asset.get("tags", [])
        if tags_list:
            self.tags_meta_label.setText(f"Tags: {' '.join([f'#{t}' for t in tags_list])}")
        else:
            self.tags_meta_label.setText("")

        self.asset_desc_label.setText(asset.get("description", ""))
        self.addon_name_label.setText(f"Target Addon: {get_addon_name() or 'None Selected'}")

        # Load Thumbnail
        dest_path = os.path.join(THUMB_DIR, f"{aid}.png")
        if os.path.isfile(dest_path):
            pix = QPixmap(dest_path)
            self.thumb_preview_label.setPixmap(pix.scaled(125, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.thumb_preview_label.setPixmap(placeholder_pixmap(125, 90))
            thumb_url = asset.get("thumb_url", "")
            cat = asset.get("category", "smartprops")

            self.thumb_worker = ThumbnailFetcherThread(aid, thumb_url, cat)
            def on_thumb_done(t_aid, path):
                if self.current_asset and self.current_asset.get("id") == t_aid and os.path.isfile(path):
                    pix = QPixmap(path)
                    self.thumb_preview_label.setPixmap(pix.scaled(125, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            self.thumb_worker.thumb_fetched.connect(on_thumb_done)
            self.thumb_worker.start()

        # Build Hierarchy Tree checking all fallbacks
        downloaded_zip = os.path.join(DOWNLOAD_DIR, aid, "asset.zip")
        manifest_path = os.path.join(INSTALLED_DIR, aid, "manifest.json")

        file_paths = []
        if os.path.isfile(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    m_data = json.load(mf)
                    file_paths = m_data.get("installed_files", [])
            except Exception as e:
                debug(f"Manifest read error: {e}")

        if not file_paths and os.path.isfile(downloaded_zip):
            try:
                with zipfile.ZipFile(downloaded_zip, "r") as z:
                    file_paths = [f for f in z.namelist() if not f.endswith("/")]
            except Exception as e:
                debug(f"Zip read error: {e}")

        if not file_paths:
            local_repo_zip = os.path.normpath(f"../Source2AssetLibrary/assets/{asset.get('category', 'smartprops')}/{aid}/asset.zip")
            if os.path.isfile(local_repo_zip):
                try:
                    with zipfile.ZipFile(local_repo_zip, "r") as z:
                        file_paths = [f for f in z.namelist() if not f.endswith("/")]
                except Exception as e:
                    debug(f"Local repo zip read error: {e}")

        if file_paths:
            self.populate_hierarchy_tree(file_paths, asset.get("category", ""))
        else:
            self.tree_widget.clear()

        if os.path.isfile(manifest_path):
            self.import_btn.setEnabled(False)
            self.reposition_btn.setEnabled(True)
            self.remove_btn.setEnabled(True)
        elif os.path.isfile(downloaded_zip):
            self.import_btn.setEnabled(True)
            self.reposition_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
        else:
            self.import_btn.setEnabled(False)
            self.reposition_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)

    def populate_hierarchy_tree(self, paths: list, category: str = ""):
        self.tree_widget.clear()
        node_map = {}
        folder_icon = QIcon(":/icons/folder_16dp.svg")

        for raw_path in sorted(paths):
            path = raw_path.replace("\\", "/").strip("/")
            if not path:
                continue

            parts = path.split("/")
            curr_path = ""
            parent_item = None

            for idx, part in enumerate(parts):
                curr_path = f"{curr_path}/{part}" if curr_path else part
                is_file = (idx == len(parts) - 1)

                if curr_path in node_map:
                    parent_item = node_map[curr_path]
                else:
                    if parent_item is None:
                        item = QTreeWidgetItem(self.tree_widget)
                    else:
                        item = QTreeWidgetItem(parent_item)

                    item.setText(0, part)
                    if is_file:
                        ext = os.path.splitext(part)[1].lstrip(".") or category
                        item.setIcon(0, get_valve_asset_icon(ext))
                    else:
                        item.setIcon(0, folder_icon)

                    node_map[curr_path] = item
                    parent_item = item

        self.tree_widget.expandAll()

    def on_panel_import_click(self):
        if self.current_asset and self.parent_tab:
            downloaded_zip = os.path.join(DOWNLOAD_DIR, self.current_asset["id"], "asset.zip")
            if os.path.isfile(downloaded_zip):
                subfolder = self.subfolder_edit.text().strip() or "s2library"
                self.parent_tab.import_asset_to_project(self.current_asset, subfolder)

    def on_panel_reposition_click(self):
        if self.current_asset and self.parent_tab:
            card = self.parent_tab.find_card_for_asset(self.current_asset["id"])
            if card:
                card.reposition_asset()

    def on_panel_remove_click(self):
        if self.current_asset and self.parent_tab:
            card = self.parent_tab.find_card_for_asset(self.current_asset["id"])
            if card:
                card.uninstall_asset()
                self.set_asset(self.current_asset)


class Source2AssetLibraryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.assets_list = []
        self.cards = []
        self.has_loaded = False
        self.init_dirs()
        self.setup_ui()
        # Set global tooltip stylesheet to neutral dark background and light gray text
        self.setStyleSheet("QToolTip { background-color: #1c1c1e; color: #e3e3e3; border: 1px solid #38383c; }")
        apply_stylesheets(self)

    def ensure_loaded(self):
        if not self.has_loaded:
            self.has_loaded = True
            self.load_index()

    def init_dirs(self):
        for d in [USERDATA_DIR, CACHE_DIR, THUMB_DIR, DOWNLOAD_DIR, INSTALLED_DIR]:
            os.makedirs(d, exist_ok=True)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Header Filter Bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search assets by name, tag, or description...")
        self.search_input.textChanged.connect(self.filter_assets)
        filter_layout.addWidget(self.search_input, stretch=2)

        self.cat_combo = QComboBox()
        self.cat_combo.addItems([
            "All Categories", "models", "particles", "materials", "smartprops",
            "maps", "sounds", "scripts"
        ])
        self.cat_combo.currentIndexChanged.connect(self.filter_assets)
        filter_layout.addWidget(self.cat_combo)

        self.license_combo = QComboBox()
        self.license_combo.addItems(["All Licenses", "CC0 Only", "CC BY", "Commercial Allowed"])
        self.license_combo.currentIndexChanged.connect(self.filter_assets)
        filter_layout.addWidget(self.license_combo)

        # Downloaded Filter Checkbox
        self.downloaded_combo = QComboBox()
        self.downloaded_combo.addItems(["All Assets", "Downloaded Only", "Imported Only"])
        self.downloaded_combo.currentIndexChanged.connect(self.filter_assets)
        filter_layout.addWidget(self.downloaded_combo)

        self.refresh_btn = QPushButton("Refresh Index")
        self.refresh_btn.setStyleSheet(qt_stylesheet_button)
        self.refresh_btn.clicked.connect(self.load_index)
        filter_layout.addWidget(self.refresh_btn)

        self.upload_btn = QPushButton("Upload Asset")
        self.upload_btn.setStyleSheet(qt_stylesheet_button)
        self.upload_btn.clicked.connect(self.open_upload_github)
        filter_layout.addWidget(self.upload_btn)

        main_layout.addLayout(filter_layout)

        # Splitter Layout (Left Grid + Right Import Options Panel)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(4)

        self.scroll_area = GridScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #2d2d30; background-color: #141416; }")
        self.scroll_area.resized.connect(lambda: QTimer.singleShot(10, self.relayout_cards))

        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(6)
        self.grid_layout.setContentsMargins(6, 6, 6, 6)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.scroll_content)
        self.splitter.addWidget(self.scroll_area)

        # Right Import Options Panel
        self.import_panel = ImportOptionsPanel(parent_tab=self)
        self.splitter.addWidget(self.import_panel)

        # Default ratio: Left ~75% (5-6 cols), Right ~25%
        self.splitter.setSizes([1000, 320])
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)

        self.splitter.splitterMoved.connect(lambda pos, idx: QTimer.singleShot(10, self.relayout_cards))

        main_layout.addWidget(self.splitter, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(20, self.relayout_cards)

    def open_upload_github(self):
        QDesktopServices.openUrl(QUrl(REPO_URL))

    def load_index(self):
        self.refresh_btn.setEnabled(False)

        self.index_thread = IndexFetcherThread()

        def on_index_ready(assets, msg):
            self.refresh_btn.setEnabled(True)
            self.assets_list = assets
            self.filter_assets()

        self.index_thread.fetched_signal.connect(on_index_ready)
        self.index_thread.start()

    def filter_assets(self):
        query = self.search_input.text().lower().strip()
        cat_filter = self.cat_combo.currentText()
        lic_filter = self.license_combo.currentText()
        dl_filter = self.downloaded_combo.currentText()

        filtered = []
        for a in self.assets_list:
            aid = a.get("id", "")
            dl_zip = os.path.join(DOWNLOAD_DIR, aid, "asset.zip")
            inst_manifest = os.path.join(INSTALLED_DIR, aid, "manifest.json")

            if dl_filter == "Downloaded Only" and not os.path.isfile(dl_zip):
                continue
            elif dl_filter == "Imported Only" and not os.path.isfile(inst_manifest):
                continue

            if cat_filter != "All Categories" and a.get("category") != cat_filter:
                continue

            lic = a.get("license", "")
            if lic_filter == "CC0 Only" and lic != "CC0":
                continue
            elif lic_filter == "CC BY" and "CC BY" not in lic:
                continue
            elif lic_filter == "Commercial Allowed":
                info = LICENSE_MATRIX.get(lic.upper(), LICENSE_MATRIX.get(lic, {}))
                if info and not info.get("commercial", True):
                    continue

            name = a.get("name", "").lower()
            tags = " ".join(a.get("tags", [])).lower()
            desc = a.get("description", "").lower()
            if query and query not in name and query not in tags and query not in desc:
                continue

            filtered.append(a)

        self.render_assets(filtered)

    def render_assets(self, assets: list):
        self.cards.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for asset in assets:
            card = AssetCardWidget(asset, parent_tab=self)
            card.card_selected.connect(self.select_asset_for_panel)
            self.cards.append(card)

        self.relayout_cards()

    def relayout_cards(self):
        if not self.cards:
            return

        viewport_w = self.scroll_area.viewport().width() - 8
        card_w = 230
        cols = max(1, (viewport_w + 4) // (card_w + 6))

        for idx, card in enumerate(self.cards):
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)

    def select_asset_for_panel(self, asset: dict):
        self.import_panel.set_asset(asset)

    def find_card_for_asset(self, asset_id: str):
        for c in self.cards:
            if c.asset_id == asset_id:
                return c
        return None

    def import_asset_to_project(self, asset: dict, subfolder_target: str = "s2library"):
        addon_dir = get_addon_dir()
        if not addon_dir:
            QMessageBox.warning(self, "No Addon Selected", "Please select an active CS2 addon before importing assets.")
            return

        subfolder = subfolder_target.strip() if subfolder_target else "s2library"
        target_base = os.path.join(addon_dir, subfolder)
        os.makedirs(target_base, exist_ok=True)
        aid = asset["id"]
        downloaded_zip = os.path.join(DOWNLOAD_DIR, aid, "asset.zip")

        if not os.path.isfile(downloaded_zip):
            QMessageBox.warning(self, "Not Downloaded", f"Asset package for '{aid}' is not downloaded yet.")
            return

        try:
            installed_files = []
            with zipfile.ZipFile(downloaded_zip, "r") as z:
                for member in z.infolist():
                    target_path = os.path.normpath(os.path.join(target_base, member.filename))
                    if not target_path.startswith(os.path.abspath(addon_dir)):
                        raise ValueError(f"Security error: Zip path traversal detected ({member.filename})")

                    z.extract(member, target_base)
                    if not member.is_dir():
                        rel_inst = os.path.relpath(target_path, addon_dir).replace("\\", "/")
                        installed_files.append(rel_inst)

            manifest_dir = os.path.join(INSTALLED_DIR, aid)
            os.makedirs(manifest_dir, exist_ok=True)
            manifest_data = {
                "asset_id": aid,
                "version": asset.get("version", "1.0.0"),
                "name": asset.get("name", aid),
                "target_addon_dir": addon_dir,
                "installed_files": installed_files
            }
            with open(os.path.join(manifest_dir, "manifest.json"), "w", encoding="utf-8") as mf:
                json.dump(manifest_data, mf, indent=2)

            QMessageBox.information(self, "Imported", f"Successfully imported '{asset.get('name')}' to addon {get_addon_name()}!")

            card = self.find_card_for_asset(aid)
            if card:
                card.update_status()
            self.import_panel.set_asset(asset)

        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to import asset: {e}")
