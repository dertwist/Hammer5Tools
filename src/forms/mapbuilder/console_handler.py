from VConsoleLib.vconsole2_lib import VConsole2Lib

import time


initializated = False

def my_on_disconnected(vconsole):
    """
    :param vconsole: VConsole2Lib
    """


def my_on_adon_received(vconsole, name):
    print(f"Received adon: {name}")


def my_on_cvars_loaded(vconsole, cvars):
    vconsole.log('cvars loaded\n')
    vconsole.send_cmd("say Hello World from VConsole2Lib.python!")


def my_on_prnt_received(vconsole, channel_name, msg):
    global initializated
    # print(initializated)

    if initializated is True:
        pass
    #AddGameInputHandler - handle=3, flags=0xfd dbgContextName=TeamSelect, panelName=TeamSelectMenu
    else:
        if "AddGameInputHandler - handle=0, flags=0xfd dbgContextName=MainMenu, panelName=MainMenu" in msg:
            initializated = True
            print('Game Loaded')
        else:
            pass


def main():
    vconsole = VConsole2Lib()
    # vconsole.log_to_file = "vconsole.htm" # Changed to local path for safety
    vconsole.html_output = False
    vconsole.log_to_screen = True
    vconsole.channels_custom_color = {'VConComm': '009900', 'VScript': '3333CC'}
    vconsole.on_disconnected = my_on_disconnected
    vconsole.on_adon_received = my_on_adon_received
    vconsole.on_cvars_loaded = my_on_cvars_loaded
    vconsole.on_prnt_received = my_on_prnt_received

    vconsole.log("Trying connect...")
    while not vconsole.connect():
        time.sleep(1)

    vconsole.log("Connected...")
    for i in range(2):
        vconsole.send_cmd(f"say {i}")
        time.sleep(0.1)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
