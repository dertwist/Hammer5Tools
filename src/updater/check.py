import sys
import json
import webbrowser
import markdown2
import threading
from velopack import UpdateManager
from src.common import get_channel
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QSpacerItem, QSizePolicy, QScrollArea, QWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QUrl, QEventLoop, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

DIALOG_WIDTH = 600
DIALOG_HEIGHT = 700

def qt_get(url):
    """
    Performs a synchronous HTTP GET request using QNetworkAccessManager.
    Returns a tuple (data, error_string). Data is returned as bytes if successful.
    """
    manager = QNetworkAccessManager()
    request = QNetworkRequest(QUrl(url))
    reply = manager.get(request)

    # Create a local event loop to wait for reply to finish
    loop = QEventLoop()
    reply.finished.connect(loop.quit)
    loop.exec()

    if reply.error() != QNetworkReply.NetworkError.NoError:
        error_str = reply.errorString()
        reply.deleteLater()
        return None, error_str

    data = reply.readAll().data()  # bytes data
    reply.deleteLater()
    return data, None

def check_updates(repo_url, current_version, silent):
    """
    Checks for updates using Velopack and shows the release notes window if found.
    """
    threading.Thread(target=_check_thread, args=(repo_url, current_version, silent), daemon=True).start()

def _check_thread(repo_url, current_version, silent):
    try:
        is_frozen = getattr(sys, 'frozen', False)
        mgr = None
        update = None
        
        if is_frozen:
            channel = get_channel()
            mgr = UpdateManager("https://github.com/dertwist/Hammer5Tools")
            # Check for updates via Velopack
            update = mgr.check_for_updates(prerelease=(channel == 'dev'))
        
        if update or not is_frozen:
            # Fetch release notes from GitHub
            parts = repo_url.rstrip('/').split('/')
            owner = parts[-2]
            repo = parts[-1]
            api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            
            data, error = qt_get(api_url)
            releases = []
            if not error:
                try:
                    releases = json.loads(data.decode('utf-8'))[:10]
                except Exception:
                    pass
            
            # Show the notification window on the main thread
            if update or not silent:
                QTimer.singleShot(0, lambda: show_update_notification(update, releases, owner, repo, mgr))
        elif not silent:
            # If no update and not silent, show info dialog
            QTimer.singleShot(0, lambda: QMessageBox.information(
                None, "No Updates", 
                f"You are already using the latest version ({current_version})."
            ))
            
    except Exception as e:
        print(f"Update check failed: {e}")
        if not silent:
            QTimer.singleShot(0, lambda: QMessageBox.critical(
                None, "Update Error", 
                f"Failed to check for updates:\n{str(e)}"
            ))

def show_update_notification(update, releases, owner, repo, mgr):
    dialog = QDialog()
    dialog.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    dialog.setWindowTitle("Updater")
    layout = QVBoxLayout(dialog)

    if update:
        latest_version = update.TargetFullRelease.Version
        header = QLabel(f"<h2>New version available: {latest_version}</h2>")
    else:
        header = QLabel(f"<h2>Release Notes (Dev Mode)</h2>")
    
    header.setTextFormat(Qt.RichText)
    layout.addWidget(header)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content_widget = QWidget()
    content_layout = QVBoxLayout(content_widget)
    content_layout.setContentsMargins(10, 10, 10, 10)
    content_layout.setSpacing(10)

    for idx, release in enumerate(releases):
        rel_version = release['tag_name'].lstrip('v')
        rel_notes = release.get('body', '')
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

    scroll.setWidget(content_widget)
    layout.addWidget(scroll)

    button_layout = QHBoxLayout()
    button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

    download_button = QPushButton("Update")
    if update:
        download_button.clicked.connect(lambda: show_install_dialog(update, mgr))
    else:
        download_button.setEnabled(False)
        download_button.setToolTip("Updating is disabled in development mode.")
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
                mgr.apply_updates_and_restart(update)
            except Exception as e:
                QTimer.singleShot(0, lambda: QMessageBox.critical(None, "Update Error", f"Failed to apply update: {e}"))
                
        threading.Thread(target=run_update, daemon=True).start()
    except Exception as e:
        QMessageBox.critical(None, "Update Error", f"Failed to start update: {e}")
