import sys
import json
import webbrowser
import markdown2
import threading
import urllib.request
try:
    import velopack
    from velopack import UpdateManager
except ImportError:
    velopack = None
    UpdateManager = None
from src.common import get_channel, get_update_source, get_update_options
from src.updater.attachment_preview import (
    parse_release_segments,
    AttachmentThumbnailWidget,
    VideoAttachmentWidget,
    FileAttachmentWidget
)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QSpacerItem, QSizePolicy, QScrollArea, QWidget, QFrame, QMessageBox,
    QProgressDialog, QApplication, QProgressBar
)
from PySide6.QtCore import Qt, QUrl, QTimer, QObject, Signal
from PySide6.QtGui import QIcon

DIALOG_WIDTH = 600
DIALOG_HEIGHT = 700

class UpdateWorker(QObject):
    """Worker object to handle update checks and communicate with the main thread via signals."""
    finished = Signal(object, list, str, str, object)  # update, releases, owner, repo, mgr
    error = Signal(str)
    no_update = Signal(list, str, str, object)  # releases, owner, repo, mgr

    def __init__(self, repo_url, current_version, silent):
        super().__init__()
        self.repo_url = repo_url
        self.current_version = current_version
        self.silent = silent

    def run(self):
        try:
            print("Update thread started...")
            is_frozen = getattr(sys, 'frozen', False)
            mgr = None
            update = None
            
            # 1. Velopack check (only if frozen)
            if is_frozen and UpdateManager:
                try:
                    print(f"Checking Velopack updates on channel: {get_channel()}")
                    mgr = UpdateManager(get_update_source(), options=get_update_options())
                    update = mgr.check_for_updates()
                except Exception as ve:
                    print(f"Velopack check failed: {ve}")
            
            # 2. GitHub Releases check (for changelog)
            parts = self.repo_url.rstrip('/').split('/')
            owner = parts[-2]
            repo = parts[-1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            
            print(f"Fetching changelog from: {api_url}")
            data, fetch_error = self.fetch_data(api_url)
            releases = []
            if not fetch_error:
                try:
                    all_releases = json.loads(data.decode('utf-8'))
                    channel = get_channel()
                    if channel == 'dev':
                        # In dev channel, show all releases including pre-releases
                        releases = all_releases[:10]
                    else:
                        # Filter out pre-releases for stable channel
                        releases = [r for r in all_releases if not r.get('prerelease')][:10]
                except Exception as je:
                    print(f"Failed to parse releases JSON: {je}")
            
            # 3. Emit results
            if update:
                print("Update found via Velopack.")
                self.finished.emit(update, releases, owner, repo, mgr)
            elif not is_frozen:
                print("Running in dev mode, showing changelog if not silent.")
                if not self.silent:
                    self.no_update.emit(releases, owner, repo, mgr)
            else:
                print("No update found.")
                if not self.silent:
                    self.no_update.emit(releases, owner, repo, mgr)
                    
        except Exception as e:
            print(f"General update check error: {e}")
            if not self.silent:
                self.error.emit(str(e))

    def fetch_data(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Hammer5Tools-Updater'})
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.read(), None
        except Exception as e:
            return None, str(e)

# Global reference to prevent GC
_worker_thread = None
_worker = None

def check_updates(repo_url, current_version, silent):
    """
    Entry point for checking updates. 
    Creates a worker and a thread to avoid blocking the UI.
    """
    global _worker, _worker_thread
    
    if _worker_thread and _worker_thread.is_alive():
        return
    
    _worker = UpdateWorker(repo_url, current_version, silent)
    
    # Connect signals to UI functions with QueuedConnection to ensure they run on the main thread
    _worker.finished.connect(show_update_notification, Qt.QueuedConnection)
    _worker.no_update.connect(lambda r, o, re, m: show_latest_version_info(current_version, r, o, re, m), Qt.QueuedConnection)
    _worker.error.connect(lambda e: QMessageBox.critical(None, "Update Error", f"Failed to check for updates:\n{e}"), Qt.QueuedConnection)
    
    _worker_thread = threading.Thread(target=_worker.run, daemon=True)
    _worker_thread.start()

def show_latest_version_info(current_version, releases, owner, repo, mgr):
    print("Showing Latest Version dialog...")
    msg = QMessageBox()
    msg.setWindowTitle("Latest Version")
    msg.setText(f"You are already using the latest version ({current_version}).")
    msg.setIcon(QMessageBox.Information)
    show_changelog_btn = msg.addButton("Show Changelog", QMessageBox.ActionRole)
    msg.addButton(QMessageBox.Ok)
    msg.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    msg.exec()
    
    if msg.clickedButton() == show_changelog_btn:
        show_update_notification(None, releases, owner, repo, mgr)

def show_update_notification(update, releases, owner, repo, mgr):
    print("Showing Update Notification window...")
    dialog = QDialog()
    dialog.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    dialog.setWindowTitle("Updater")
    layout = QVBoxLayout(dialog)

    if update:
        latest_version = update.TargetFullRelease.Version
        header = QLabel(f"<h2>New version available: {latest_version}</h2>")
    else:
        header = QLabel(f"<h2>Changelog</h2>")
    
    header.setTextFormat(Qt.RichText)
    layout.addWidget(header)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    content_layout.setContentsMargins(10, 10, 10, 10)
    content_layout.setSpacing(10)

    if releases:
        for idx, release in enumerate(releases):
            rel_version = release.get('tag_name', 'unknown').lstrip('v')
            rel_notes = release.get('body') or ""

            # Version Header
            version_label = QLabel(f"<h3>Version: {rel_version}</h3>")
            version_label.setTextFormat(Qt.RichText)
            version_label.setStyleSheet("padding: 5px 5px 0px 5px;")
            content_layout.addWidget(version_label)

            # In-place release segments (rendered in original markdown order)
            segments = parse_release_segments(
                rel_notes,
                assets=release.get('assets', []),
                owner=owner,
                repo=repo,
                tag=release.get('tag_name', '')
            )

            for seg_type, seg_data in segments:
                if seg_type == 'text':
                    text_content = seg_data.strip()
                    if text_content:
                        formatted_notes = markdown2.markdown(
                            text_content,
                            extras=["fenced-code-blocks", "tables", "images", "strike", "target-blank-links"]
                        )
                        if formatted_notes.strip():
                            note_label = QLabel(f"<div>{formatted_notes}</div>")
                            note_label.setTextFormat(Qt.RichText)
                            note_label.setWordWrap(True)
                            note_label.setOpenExternalLinks(True)
                            note_label.setStyleSheet("padding: 0px 5px;")
                            content_layout.addWidget(note_label)
                elif seg_type == 'attachment':
                    att = seg_data
                    if att.media_type in ('image', 'gif'):
                        thumb = AttachmentThumbnailWidget(att, content_widget)
                        content_layout.addWidget(thumb)
                    elif att.media_type == 'video':
                        video_card = VideoAttachmentWidget(att, content_widget)
                        content_layout.addWidget(video_card)
                    else:
                        file_card = FileAttachmentWidget(att, content_widget)
                        content_layout.addWidget(file_card)

            if idx < len(releases) - 1:
                divider = QFrame()
                divider.setFrameShape(QFrame.HLine)
                divider.setFrameShadow(QFrame.Plain)
                divider.setLineWidth(2)
                divider.setFixedHeight(2)
                divider.setStyleSheet("background-color: #424242; border: none;")
                content_layout.addWidget(divider)
    else:
        content_layout.addWidget(QLabel("No release notes found."))

    scroll.setWidget(content_widget)
    layout.addWidget(scroll)

    button_layout = QHBoxLayout()
    button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

    download_button = QPushButton("Update")
    if update:
        download_button.clicked.connect(lambda: show_install_dialog(update, mgr, dialog))
    else:
        download_button.setEnabled(False)
        download_button.setToolTip("No update available.")
    button_layout.addWidget(download_button)

    change_log_button = QPushButton("ReleaseNotes")
    api_url = f"https://github.com/{owner}/{repo}/releases"
    change_log_button.clicked.connect(lambda: webbrowser.open(api_url))
    button_layout.addWidget(change_log_button)

    ok_button = QPushButton("OK")
    ok_button.clicked.connect(dialog.accept)
    button_layout.addWidget(ok_button)

    layout.addLayout(button_layout)
    dialog.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
    dialog.exec()

class DownloadProgressDialog(QDialog):
    """Custom modal dialog for update download progress using MapBuilder styling."""

    progress_signal = Signal(int)
    status_signal = Signal(str)

    def __init__(self, parent=None, title="Updating Hammer 5 Tools"):
        super().__init__(parent)
        self.setWindowTitle(title)
        try:
            self.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
        except Exception:
            pass
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setFixedWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.status_label = QLabel("Downloading update package...")
        self.status_label.setStyleSheet("color: #e5e5e5; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Downloading... 0%")
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #5e5e5e;
                border-radius: 2px;
                text-align: center;
                color: white;
                font-size: 10px;
                background-color: #2e2e2e;
            }
            QProgressBar::chunk {
                background-color: #1a528a;
                margin: 0px;
                width: 1px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.details_label = QLabel("Please wait while the update is downloaded...")
        self.details_label.setStyleSheet("color: #929292; font-size: 10px;")
        layout.addWidget(self.details_label)

        self.progress_signal.connect(self._set_progress)
        self.status_signal.connect(self._set_status)

    def update_progress(self, percent: int):
        self.progress_signal.emit(percent)

    def update_status(self, text: str):
        self.status_signal.emit(text)

    def _set_progress(self, percent: int):
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"Downloading... {percent}%")

    def _set_status(self, text: str):
        self.status_label.setText(text)


_active_download_dialog = None


def prepare_for_update():
    """
    Terminates child processes, other instances, stops IPC and flushes worker threads
    before Velopack applies an update to avoid sharing violations and locked file errors.
    """
    # 1. Stop IPC server
    try:
        from src.ipc.server_utils import stop_ipc_server
        stop_ipc_server()
    except Exception as e:
        print(f"Failed to stop IPC server: {e}")

    # 2. Terminate child processes and lingering helpers
    try:
        import os
        import psutil
        current_pid = os.getpid()
        current_proc = psutil.Process(current_pid)

        # Kill all direct and indirect children of the current process first (excluding CS2)
        try:
            children = [
                child for child in current_proc.children(recursive=True)
                if (child.name() or '').lower() != 'cs2.exe'
            ]
            for child in children:
                try:
                    child.terminate()
                except Exception:
                    pass
            gone, alive = psutil.wait_procs(children, timeout=2)
            for p in alive:
                try:
                    p.kill()
                except Exception:
                    pass
        except Exception as e:
            print(f"Error terminating child processes: {e}")

        # Kill any other background Hammer5Tools instances (e.g. tray instances) or specific locking tools
        target_names = {'hammer5tools.exe', 'hammer5tools_core.exe', 'resourcecompiler.exe', 'bspsrc.exe'}
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pid = proc.info['pid']
                if pid == current_pid:
                    continue
                pname = (proc.info['name'] or '').lower()
                if pname in target_names:
                    proc.terminate()
                elif pname == 'dotnet.exe':
                    cmdline = ' '.join(proc.info.get('cmdline') or []).lower()
                    if 'unrealbridge' in cmdline or 'sourceporter' in cmdline:
                        proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        print(f"Error during process cleanup: {e}")

    # 3. Flush / wait for global threadpool
    try:
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().waitForDone(500)
    except Exception:
        pass


def show_install_dialog(update, mgr, parent_dialog):
    reply = QMessageBox.question(None, "Installation Confirmation",
                                 "During update installation, Hammer5Tools will be closed.\n"
                                 "Do you wish to continue?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        handle_installation(update, mgr, parent_dialog)


def handle_installation(update, mgr, parent_dialog=None):
    global _active_download_dialog
    try:
        progress = DownloadProgressDialog(parent=parent_dialog)
        _active_download_dialog = progress
        progress.show()
        
        # Close the changelog dialog if it exists
        if parent_dialog:
            parent_dialog.accept()
            
        def on_progress(percent: int):
            # Velopack calls this from a native thread, emit signal to main thread
            progress.update_progress(percent)
            
        def run_update():
            global _active_download_dialog
            try:
                mgr.download_updates(update, on_progress)
                prepare_for_update()
                mgr.apply_updates_and_restart(update)
            except Exception as e:
                # Close progress dialog and show error on main thread
                error_msg = str(e)
                QTimer.singleShot(0, lambda err=error_msg: (
                    progress.close(),
                    QMessageBox.critical(None, "Update Error", f"Failed to apply update: {err}")
                ))
            finally:
                _active_download_dialog = None
                
        threading.Thread(target=run_update, daemon=True).start()
    except Exception as e:
        _active_download_dialog = None
        QMessageBox.critical(None, "Update Error", f"Failed to start update: {e}")


