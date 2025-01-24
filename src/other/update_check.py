import requests, os, psutil
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QApplication, QHBoxLayout, QSpacerItem, QSizePolicy
import webbrowser
from PySide6.QtCore import Qt
from packaging import version
from PySide6.QtGui import QIcon
import markdown2
import sys

def check_updates(repo_url, current_version, silent):
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    response = requests.get(api_url)

    if response.status_code == 200:
        release_info = response.json()
        latest_version = release_info['tag_name'].lstrip('v')
        release_notes = release_info['body']

        if version.parse(current_version) < version.parse(latest_version):
            print(f"A new version is available: {latest_version}. You are using version: {current_version}.")
            show_update_notification(latest_version, release_notes, owner, repo)
        else:
            if not silent:
                show_update_check_result_notification(latest_version, release_notes, owner, repo)
    else:
        print(f"Failed to fetch releases. Status code: {response.status_code}")

def show_update_notification(latest_version, release_notes, owner, repo):
    dialog = QDialog()
    dialog.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    dialog.setWindowTitle("Updater")

    layout = QVBoxLayout(dialog)

    formatted_release_notes = markdown2.markdown(release_notes, extras=["fenced-code-blocks", "tables", "images", "strike", "target-blank-links"])
    label = QLabel(f"<h2>New version available: {latest_version}</h2>\n\n"
                   f"Release notes:<br>{formatted_release_notes}")
    label.setTextFormat(Qt.RichText)
    layout.addWidget(label)

    button_layout = QHBoxLayout()
    button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

    download_button = QPushButton("Update")
    download_button.clicked.connect(lambda: show_install_dialog())
    button_layout.addWidget(download_button)

    change_log_button = QPushButton("ReleaseNotes")
    api_url = f"https://github.com/{owner}/{repo}/releases/latest"
    change_log_button.clicked.connect(lambda: webbrowser.open(api_url))
    button_layout.addWidget(change_log_button)

    ok_button = QPushButton("OK")
    ok_button.clicked.connect(dialog.accept)
    button_layout.addWidget(ok_button)

    layout.addLayout(button_layout)
    dialog.adjustSize()
    dialog.setMinimumWidth(300)
    dialog.setMinimumHeight(200)  # Set a minimum height
    dialog.exec()

def show_update_check_result_notification(latest_version, release_notes, owner, repo):
    dialog = QDialog()
    dialog.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    dialog.setWindowTitle("Updater")

    layout = QVBoxLayout(dialog)

    formatted_release_notes = markdown2.markdown(release_notes, extras=["fenced-code-blocks", "tables", "images", "strike", "target-blank-links"])
    label = QLabel(f"<h2>You have the latest version: {latest_version}</h2>\n\n"
                   f"Release notes:<br>{formatted_release_notes}")
    label.setTextFormat(Qt.RichText)
    label.setWordWrap(True)
    layout.addWidget(label)

    button_layout = QHBoxLayout()
    button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

    change_log_button = QPushButton("ReleaseNotes")
    api_url = f"https://github.com/{owner}/{repo}/releases/latest"
    change_log_button.clicked.connect(lambda: webbrowser.open(api_url))
    button_layout.addWidget(change_log_button)

    ok_button = QPushButton("OK")
    ok_button.clicked.connect(dialog.accept)
    button_layout.addWidget(ok_button)

    layout.addLayout(button_layout)
    dialog.adjustSize()
    dialog.setMinimumWidth(300)
    dialog.setMinimumHeight(200)
    dialog.setMaximumWidth(1000)
    dialog.exec()

def show_install_dialog():
    dialog = QDialog()
    dialog.setWindowTitle("Installation Confirmation")

    layout = QVBoxLayout(dialog)

    label = QLabel("During update installation, Hammer5Tools will be closed. Are you ready?")
    layout.addWidget(label)

    button_layout = QHBoxLayout()
    button_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

    yes_button = QPushButton("Yes")
    yes_button.clicked.connect(lambda: handle_installation(dialog))
    button_layout.addWidget(yes_button)

    no_button = QPushButton("No")
    no_button.clicked.connect(dialog.reject)
    button_layout.addWidget(no_button)

    layout.addLayout(button_layout)
    dialog.adjustSize()
    dialog.exec()

def handle_installation(dialog):
    dialog.accept()
    psutil.Popen(['Hammer5Tools_Updater.exe'])
    QApplication.quit()
    QApplication.instance().quit()
    QApplication.exit(1)
    sys.exit(0)