import os
import sys
import shutil
import tempfile
import threading
import psutil
import zipfile
import io

from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QUrl, QEventLoop, QProcess
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

DETACHED_PROCESS = 0x00000008


def perform_update(update_url="https://github.com/dertwist/Hammer5Tools/releases/latest/download/Hammer5Tools.zip"):
    program_path = os.getcwd()
    app_executable = os.path.join(program_path, "Hammer5tools.exe")
    update_path = tempfile.mkdtemp(prefix="hammer5tools_update_")

    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Download the archive update via QNetworkAccessManager.
        manager = QNetworkAccessManager()
        request = QNetworkRequest(QUrl(update_url))
        reply = manager.get(request)

        # Setup modal progress dialog.
        progress_dialog = QDialog()
        progress_dialog.setWindowTitle("Downloading Update")
        progress_dialog.setFixedSize(350, 120)
        layout = QVBoxLayout()
        label = QLabel("Downloading update... 0.00/0.00 MB")
        label.setAlignment(Qt.AlignCenter)
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        layout.addWidget(label)
        layout.addWidget(progress_bar)
        if progress_dialog.layout() is None:
            progress_dialog.setLayout(layout)
        progress_dialog.show()
        progress_dialog.raise_()

        # Wait for download to finish using an event loop.
        event_loop = QEventLoop()
        reply.finished.connect(event_loop.quit)

        def on_progress(bytes_received, bytes_total):
            if bytes_total > 0:
                progress_bar.setMaximum(bytes_total)
                progress_bar.setValue(bytes_received)
                label.setText(f"Downloading update... {bytes_received/1048576:.2f}/{bytes_total/1048576:.2f} MB")
                app.processEvents()

        reply.downloadProgress.connect(on_progress)
        event_loop.exec()

        if reply.error() != QNetworkReply.NetworkError.NoError:
            error_str = reply.errorString()
            progress_dialog.close()
            print(f"Error during update download: {error_str}")
            return

        data = reply.readAll()
        progress_dialog.close()

        # Extract downloaded zip archive.
        zip_data = io.BytesIO()
        zip_data.write(bytes(data))
        zip_data.seek(0)
        with zipfile.ZipFile(zip_data, "r") as zip_ref:
            zip_ref.extractall(update_path)
        print("Download and extraction successful.")

    except Exception as e:
        print(f"Error during update download/extraction: {e}")
        shutil.rmtree(update_path, ignore_errors=True)
        return

    try:
        # Create the PowerShell update script.
        ps1_path = os.path.join(tempfile.gettempdir(), "self_update.ps1")
        ps1_content = f"""$updatePath = "{update_path}"
$programPath = "{program_path}"
$appExecutable = Join-Path -Path $programPath -ChildPath "Hammer5tools.exe"

Write-Output "Killing Hammer5Tools.exe process if running..."
$runningProcess = Get-Process -Name "Hammer5Tools" -ErrorAction SilentlyContinue
if ($runningProcess) {{
    $runningProcess | ForEach-Object {{ $_.Kill() }}
    Write-Output "Process terminated."
}} else {{
    Write-Output "Process not running."
}}

Write-Output "Removing obsolete presets\\hammer5tools folder if exists..."
$obsoleteFolder = Join-Path -Path $programPath -ChildPath "presets\\hammer5tools"
if (Test-Path $obsoleteFolder) {{
    Remove-Item -Path $obsoleteFolder -Recurse -Force
}}

Write-Output "Updating application files..."
$filesToUpdate = @(
    "SoundEventEditor\\Presets\\SoundDebug.kv3",
    "SoundEventEditor\\Presets\\SoundGeneric.kv3",
    "SmartPropEditor\\Presets\\example_expressions.vsmart",
    "SmartPropEditor\\Presets\\example_fit_on_line.vsmart",
    "SmartPropEditor\\Presets\\example_trace_in_line.vsmart",
    "SmartPropEditor\\Presets\\example_variable_set.vsmart",
    "SmartPropEditor\\Presets\\Irregularity_single.vsmart"
)

foreach ($file in $filesToUpdate) {{
    $sourceFile = Join-Path -Path $updatePath -ChildPath $file
    $destFile = Join-Path -Path $programPath -ChildPath $file

    $destDir = Split-Path -Path $destFile -Parent
    if (!(Test-Path -Path $destDir)) {{
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    }}

    if (Test-Path -Path $sourceFile) {{
        if ((Resolve-Path $sourceFile).Path -ne (Resolve-Path $destFile 2>$null)) {{
            Copy-Item -Path $sourceFile -Destination $destFile -Force
            Write-Output "Updated: $file"
        }} else {{
            Write-Output "Skipping update for: $file (source equals destination)"
        }}
    }} else {{
        Write-Output "Source file not found: $file"
    }}
}}

Write-Output "Copying remaining updated files, excluding settings.ini..."
Get-ChildItem -Path $updatePath -Recurse | Where-Object {{ $_.FullName -notlike "*settings.ini" }} | ForEach-Object {{
    $source = $_.FullName
    $destination = $source.Replace($updatePath, $programPath)
    if ($_.PSIsContainer) {{
        if (!(Test-Path $destination)) {{
            New-Item -ItemType Directory -Force -Path $destination | Out-Null
            Write-Output "Created directory: $destination"
        }}
    }} else {{
        if ((Resolve-Path $source).Path -ne (Resolve-Path $destination 2>$null)) {{
            Copy-Item -Path $source -Destination $destination -Force
            Write-Output "Copied file: $destination"
        }} else {{
            Write-Output "Skipping copying same file: $destination"
        }}
    }}
}}

Write-Output "Cleaning up temporary files..."
Remove-Item -Path $updatePath -Recurse -Force

Write-Output "Restarting application..."
try {{
    $processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processStartInfo.FileName = $appExecutable
    $processStartInfo.WorkingDirectory = $programPath
    $processStartInfo.UseShellExecute = $true
    [System.Diagnostics.Process]::Start($processStartInfo) | Out-Null
    Write-Output "Application started successfully"
}} catch {{
    Write-Output "Error starting application: $($_.Exception.Message)"
}}

Start-Sleep -Seconds 2
Remove-Item -Path $MyInvocation.MyCommand.Definition -Force
"""
        with open(ps1_path, "w", encoding="utf-8") as f:
            f.write(ps1_content)

        # Launch PowerShell script bypassing the execution policy.
        if not QProcess.startDetached("powershell", ["-ExecutionPolicy", "Bypass", "-File", ps1_path]):
            print("Failed to launch the update PowerShell script.")
        else:
            print("Update PowerShell script launched successfully.")

    except Exception as e:
        print(f"Error during update installation: {e}")
        shutil.rmtree(update_path, ignore_errors=True)
        if os.path.exists(ps1_path):
            try:
                os.remove(ps1_path)
            except Exception:
                pass


if __name__ == "__main__":
    perform_update()