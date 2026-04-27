import threading
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QMessageBox, QProgressDialog
from velopack import UpdateManager
from src.common import get_channel, app_version

class VelopackManager:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.update_url = "https://github.com/dertwist/Hammer5Tools"

    def check_for_updates(self, interactive=False):
        """Checks for updates and prompts the user if one is found."""
        threading.Thread(target=self._update_thread, args=(interactive,), daemon=True).start()

    def _update_thread(self, interactive):
        try:
            channel = get_channel()
            import velopack
            opts = velopack.UpdateOptions(AllowVersionDowngrade=False, 
                                        MaximumDeltasBeforeFallback=0, 
                                        ExplicitChannel=channel)
            mgr = UpdateManager(self.update_url, options=opts)
            
            # Check for updates
            update = mgr.check_for_updates()
            
            if update:
                QTimer.singleShot(0, lambda: self._prompt_for_update(mgr, update))
            elif interactive:
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self.parent, "No Updates", 
                    f"You are already using the latest version ({app_version})."
                ))
        except Exception as e:
            print(f"Velopack update check failed: {e}")
            if interactive:
                QTimer.singleShot(0, lambda: QMessageBox.critical(
                    self.parent, "Update Error", 
                    f"Failed to check for updates:\n{str(e)}"
                ))

    def _prompt_for_update(self, mgr, update):
        msg = (f"A new version ({update.TargetFullRelease.Version}) is available.\n"
               "Would you like to download and install it now?")
        reply = QMessageBox.question(self.parent, "Update Available", msg,
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self._progress = QProgressDialog("Downloading update...", None, 0, 100, self.parent)
            self._progress.setWindowTitle("Updating")
            self._progress.setWindowModality(Qt.ApplicationModal)
            self._progress.setCancelButton(None)
            self._progress.setMinimumDuration(0)
            self._progress.show()
            threading.Thread(target=self._apply_update_thread, args=(mgr, update), daemon=True).start()

    def _apply_update_thread(self, mgr, update):
        def on_progress(percent: int):
            # Velopack calls this from a native thread, must dispatch to main thread
            QTimer.singleShot(0, lambda p=percent: self._progress.setValue(p))

        try:
            mgr.download_updates(update, on_progress)
            mgr.apply_updates_and_restart(update)
        except Exception as e:
            error_msg = str(e)
            QTimer.singleShot(0, lambda err=error_msg: (
                self._progress.close(),
                QMessageBox.critical(
                    self.parent, "Update Error", 
                    f"Failed to apply update:\n{err}"
                )
            ))
