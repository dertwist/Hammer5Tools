import requests, os
from PySide6.QtWidgets import QMessageBox, QPushButton
import webbrowser
from PySide6.QtCore import Qt


def check_updates(repo_url, current_version):
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

        print(f"Latest version: {latest_version}")
        print(f"Release notes: {release_notes}")

        # Compare the current version with the latest version
        if current_version == latest_version:
            print("You are using the latest version.")
        else:
            print(f"A new version is available: {latest_version}. You are using version: {current_version}.")
            show_update_notification(latest_version, release_notes, owner, repo)
    else:
        print(f"Failed to fetch releases. Status code: {response.status_code}")


def show_update_notification(latest_version, release_notes, owner, repo):
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle("New Update Available")
    msg_box.setTextFormat(Qt.RichText)  # Ensure the text format is set to RichText

    # Replace newlines with HTML line breaks
    formatted_release_notes = release_notes.replace('\n', '<br>')

    msg_box.setText(f"<h2>Version: {latest_version}</h2>\n\n"
                    f"Release notes:<br>{formatted_release_notes}")

    download_button = QPushButton("Download")
    download_button.clicked.connect(lambda: show_install_dialog())
    msg_box.addButton(download_button, QMessageBox.ActionRole)

    change_log_button = QPushButton("Visit Change Log")
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
        # Run the updater executable
        os.startfile('Hammer5Tools_Updater.exe')