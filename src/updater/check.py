import sys
import json
import webbrowser
import markdown2
import threading
import urllib.request
import velopack
from velopack import UpdateManager, UpdateOptions
from src.common import get_channel
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QSpacerItem, QSizePolicy, QScrollArea, QWidget, QFrame, QMessageBox
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
            if is_frozen:
                try:
                    channel = get_channel()
                    print(f"Checking Velopack updates on channel: {channel}")
                    
                    # Use UpdateOptions to specify the channel
                    opts = UpdateOptions(AllowVersionDowngrade=False, 
                                       MaximumDeltasBeforeFallback=0, 
                                       ExplicitChannel=channel)
                    mgr = UpdateManager("https://github.com/dertwist/Hammer5Tools", options=opts)
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
    
    _worker = UpdateWorker(repo_url, current_version, silent)
    
    # Connect signals to UI functions with QueuedConnection to ensure they run on the main thread
    _worker.finished.connect(show_update_notification, Qt.QueuedConnection)
    _worker.no_update.connect(lambda r, o, re, m: show_latest_version_info(current_version, r, o, re, m), Qt.QueuedConnection)
    _worker.error.connect(lambda e: QMessageBox.critical(None, "Update Error", f"Failed to check for updates:\n{e}"), Qt.QueuedConnection)
    
    # Run in a thread
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
            formatted_notes = markdown2.markdown(
                rel_notes,
                extras=["fenced-code-blocks", "tables", "images", "strike", "target-blank-links"]
            )
            note_label = QLabel(f"<h3>Version: {rel_version}</h3><div>{formatted_notes}</div>")
            note_label.setTextFormat(Qt.RichText)
            note_label.setWordWrap(True)
            note_label.setStyleSheet("padding: 5px;")
            content_layout.addWidget(note_label)
            if idx < len(releases) - 1:
                divider = QFrame()
                divider.setFrameShape(QFrame.HLine)
                divider.setFrameShadow(QFrame.Plain)
                divider.setLineWidth(2)
                divider.setFixedHeight(2)
                divider.setStyleSheet("background-color: #323232; border: none;")
                content_layout.addWidget(divider)
    else:
        content_layout.addWidget(QLabel("No release notes found."))

    scroll.setWidget(content_widget)
    layout.addWidget(scroll)

    button_layout = QHBoxLayout()
    button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

    download_button = QPushButton("Update")
    if update:
        download_button.clicked.connect(lambda: show_install_dialog(update, mgr))
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

def show_install_dialog(update, mgr):
    reply = QMessageBox.question(None, "Installation Confirmation",
                                 "During update installation, Hammer5Tools will be closed.\n"
                                 "Do you wish to continue?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        handle_installation(update, mgr)

def handle_installation(update, mgr):
    try:
        # Show a simple progress message
        msg = QMessageBox()
        msg.setWindowTitle("Updating")
        msg.setText("Downloading and applying update... The application will restart automatically.")
        msg.setStandardButtons(QMessageBox.NoButton)
        msg.show()
        
        def run_update():
            try:
                mgr.download_updates(update)
                # Before applying and restarting, we should close our own app properly
                # to avoid multiple instances or conflicts.
                QTimer.singleShot(0, QApplication.quit)
                mgr.apply_updates_and_restart(update)
            except Exception as e:
                # Use QTimer to show error on main thread
                QTimer.singleShot(0, lambda: QMessageBox.critical(None, "Update Error", f"Failed to apply update: {e}"))
                
        threading.Thread(target=run_update, daemon=True).start()
    except Exception as e:
        QMessageBox.critical(None, "Update Error", f"Failed to start update: {e}")
