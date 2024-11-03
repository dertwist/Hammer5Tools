import requests, os, psutil
from PySide6.QtWidgets import QMessageBox, QPushButton, QApplication
import webbrowser
from PySide6.QtCore import Qt
from packaging import version
from PySide6.QtGui import QIcon
import markdown2
import sys

def check_updates(repo_url, current_version, silent):
    # Extract the owner and repo name from the URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]

    # GitHub API URL for releases
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

    # Make a request to the GitHub API
    response = requests.get(api_url)

    if response.status_code == 200:
        release_info = response.json()
        latest_version = release_info['tag_name'].lstrip('v')  # Remove 'v' from the version
        release_notes = release_info['body']

        print(f"GitHub version: {latest_version}")

        # Compare the current version with the latest version using packaging.version
        if version.parse(current_version) < version.parse(latest_version):
            print(f"A new version is available: {latest_version}. You are using version: {current_version}.")
            show_update_notification(latest_version, release_notes, owner, repo)
        else:
            print("You are using the latest version.")
            if not silent:
                show_update_check_result_notification(latest_version, release_notes, owner, repo)
    else:
        print(f"Failed to fetch releases. Status code: {response.status_code}")

def show_update_notification(latest_version, release_notes, owner, repo):
    msg_box = QMessageBox()
    msg_box.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle("Updater")
    msg_box.setTextFormat(Qt.RichText)  # Ensure the text format is set to RichText

    # Replace newlines with HTML line breaks
    formatted_release_notes = markdown2.markdown(release_notes)

    msg_box.setText(f"<h2>New version available: {latest_version}</h2>\n\n"
                    f"Release notes:{formatted_release_notes}")

    download_button = QPushButton("Update")
    download_button.clicked.connect(lambda: show_install_dialog())
    msg_box.addButton(download_button, QMessageBox.ActionRole)

    change_log_button = QPushButton("ReleaseNotes")
    api_url = f"https://github.com/{owner}/{repo}/releases/latest"
    change_log_button.clicked.connect(lambda: os.startfile(api_url))
    msg_box.addButton(change_log_button, QMessageBox.ActionRole)

    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()

def show_update_check_result_notification(latest_version, release_notes, owner, repo):
    msg_box = QMessageBox()
    msg_box.setWindowIcon(QIcon.fromTheme(":/icons/appicon.ico"))
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle("Updater")
    msg_box.setTextFormat(Qt.RichText)  # Ensure the text format is set to RichText

    # Convert Markdown to HTML
    formatted_release_notes = markdown2.markdown(release_notes)
    msg_box.setText(f"<h2>You have the latest version: {latest_version}</h2>\n\n"
                    f"Release notes:{formatted_release_notes}")
    change_log_button = QPushButton("ReleaseNotes")
    api_url = f"https://github.com/{owner}/{repo}/releases/latest"
    change_log_button.clicked.connect(lambda: os.startfile(api_url))
    msg_box.addButton(change_log_button, QMessageBox.ActionRole)

    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.exec()

def show_install_dialog():
    install_msg_box = QMessageBox()
    install_msg_box.setIcon(QMessageBox.Question)
    install_msg_box.setWindowTitle("Installation Confirmation")
    install_msg_box.setText("During update installation, Hammer5Tools will be closed. Are you ready?")
    install_msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

    response = install_msg_box.exec()

    if response == QMessageBox.Yes:
        psutil.Popen(['Hammer5Tools_Updater.exe'])
        QApplication.quit()
        QApplication.instance().quit()
        QApplication.exit(1)
        sys.exit(0)
        # os.system('Hammer5Tools_Updater.exe')
