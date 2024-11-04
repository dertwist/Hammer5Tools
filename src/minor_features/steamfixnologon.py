import time, psutil, subprocess
from PySide6.QtCore import QThread, Signal
from src.preferences import get_steam_path, get_cs2_path, get_addon_name, get_config_bool
from src.minor_features.addon_functions import launch_addon

steam_path = get_steam_path()
counter_strikke_2_path = get_cs2_path()
addon_name = get_addon_name()

class SteamNoLogoFixThreadClass(QThread):
    any_signal = Signal(int)


    def is_steam_running(self):
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'] == 'steam.exe':
                return True
        return False

    def __init__(self, parent=None):
        super(SteamNoLogoFixThreadClass, self).__init__(parent)
        self.is_running = True

    def run(self):
        terminate_process = psutil.Popen("taskkill /F /IM steam.exe", shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        terminate_process.communicate()  # Wait for the termination process to complete

        # Wait a moment to ensure the process is fully terminated
        time.sleep(2)
        psutil.Popen([steam_path + '\\steam.exe'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Wait until Steam is running
        while not self.is_steam_running():
            time.sleep(1)  # Sleep for a short period before checking again

        # Launch the addon
        try:
            launch_addon_after_nosteamlogon_fix = get_config_bool('OTHER', 'launch_addon_after_nosteamlogon_fix')
            print(launch_addon_after_nosteamlogon_fix)
            if launch_addon_after_nosteamlogon_fix:
                launch_addon()
        except:
            pass
    def stop(self):
        self.is_running = False