import time, psutil, subprocess
from PySide6.QtCore import QThread, Signal
from preferences import get_steam_path, get_cs2_path, get_addon_name

steam_path = get_steam_path()
counter_strikke_2_path = get_cs2_path()
addon_name = get_addon_name()

class SteamNoLogoFixThreadClass(QThread):
    any_signal = Signal(int)

    def launch_addon(self, addon_name, NCM_mode):
        cs2_launch_commands = counter_strikke_2_path + r"\game\bin\win64\cs2.exe" + " -addon " + addon_name + ' -tool hammer' + ' -asset maps/' + addon_name + '.vmap' + " -tools -steam -retail -gpuraytracing  -noinsecru +install_dlc_workshoptools_cvar 1"
        if NCM_mode:
            psutil.Popen(cs2_launch_commands + " -nocustomermachine")
        else:
            psutil.Popen(cs2_launch_commands)

    def is_steam_running(self):
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'] == 'steam.exe':
                return True
        return False

    def __init__(self, parent=None, addon_name="test", NCM_mode=True):
        super(SteamNoLogoFixThreadClass, self).__init__(parent)
        self.addon_name = addon_name
        self.NCM_mode = NCM_mode
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
        self.launch_addon(self.addon_name, self.NCM_mode)
    def stop(self):
        self.is_running = False