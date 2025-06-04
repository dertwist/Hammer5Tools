import sys
import json
import webbrowser
import markdown2
from packaging import version

from PySide6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QSpacerItem, QSizePolicy, QScrollArea, QWidget, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QUrl, QEventLoop
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from src.updater.script import perform_update

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
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"

    data, error = qt_get(api_url)
    if error:
        print(f"Failed to fetch releases. Error: {error}")
        return

    try:
        releases = json.loads(data.decode('utf-8'))[:10]
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return

    if not releases:
        print("No releases found.")
        return

    valid_releases = []
    for release in releases:
        try:
            if release.get("prerelease", False) or release.get("draft", False):
                continue
            _ = version.parse(release['tag_name'].lstrip('v'))
            valid_releases.append(release)
        except Exception:
            continue

    if not valid_releases:
        print("No valid releases found.")
        return

    latest_release = valid_releases[0]
    latest_version = latest_release['tag_name'].lstrip('v')

    if version.parse(current_version) < version.parse(latest_version):
        print(f"A new version is available: {latest_version}. You are using version: {current_version}.")
        show_update_notification(latest_release, valid_releases, owner, repo)
    else:
        if not silent:
            show_update_check_result_notification(latest_release, valid_releases, owner, repo)

def show_update_notification(latest_release, releases, owner, repo):
    dialog = QDialog()
    dialog.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    dialog.setWindowTitle("Updater")
    layout = QVBoxLayout(dialog)

    latest_version = latest_release['tag_name'].lstrip('v')
    header = QLabel(f"<h2>New version available: {latest_version}</h2>")
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
    download_button.clicked.connect(lambda: show_install_dialog())
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

def show_update_check_result_notification(latest_release, releases, owner, repo):
    dialog = QDialog()
    dialog.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    dialog.setWindowTitle("Updater")
    layout = QVBoxLayout(dialog)

    latest_version = latest_release['tag_name'].lstrip('v')
    header = QLabel(f"<h2>You have the latest version: {latest_version}</h2>")
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

    change_log_button = QPushButton("ReleaseNotes")
    api_url = f"https://github.com/{owner}/{repo}/releases"
    change_log_button.clicked.connect(lambda: webbrowser.open(api_url))
    button_layout.addWidget(change_log_button)

    force_update_button = QPushButton("Force Update")
    def handle_force_update():
        confirmation = QMessageBox.question(dialog, "Force Update Confirmation",
                                            "You are about to force update even though you have the latest version.\n"
                                            "This will reinstall the update. Proceed?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if confirmation == QMessageBox.Yes:
            show_install_dialog()
    force_update_button.clicked.connect(handle_force_update)
    button_layout.addWidget(force_update_button)

    ok_button = QPushButton("OK")
    ok_button.clicked.connect(dialog.accept)
    button_layout.addWidget(ok_button)

    layout.addLayout(button_layout)
    dialog.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
    dialog.exec()

def show_install_dialog():
    reply = QMessageBox.question(None, "Installation Confirmation",
                                 "During update installation, Hammer5Tools will be closed.\n"
                                 "Do you wish to continue?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        handle_installation()

def handle_installation():
    perform_update()