from VConsoleLib.vconsole2_lib import VConsole2Lib
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

initialized = False


def my_on_connected(vconsole):
    """
    Called when successfully connected to CS2 VConsole
    :param vconsole: VConsole2Lib
    """
    vconsole.log("Successfully connected to CS2!")


def my_on_disconnected(vconsole):
    """
    Called when disconnected from CS2 VConsole
    :param vconsole: VConsole2Lib
    """
    vconsole.log("Disconnected from CS2")


def my_on_reconnecting(vconsole, attempt):
    """
    Called when attempting to reconnect
    :param vconsole: VConsole2Lib
    :param attempt: Reconnection attempt number
    """
    vconsole.log(f"Reconnecting... (attempt {attempt})")


def my_on_adon_received(vconsole, name):
    """
    Called when ADON packet is received
    :param vconsole: VConsole2Lib
    :param name: Addon name
    """
    vconsole.log(f"Received addon: {name}")


def my_on_cvars_loaded(vconsole, cvars):
    """
    Called when all CVARs have been loaded
    :param vconsole: VConsole2Lib
    :param cvars: List of cvars
    """
    vconsole.log(f'CVARs loaded: {len(cvars)} total')
    # Send a test command
    vconsole.send_cmd("echo VConsole2Lib.python connected!")


def my_on_prnt_received(vconsole, channel_name, msg):
    """
    Called when a PRNT (print) packet is received
    :param vconsole: VConsole2Lib
    :param channel_name: Channel name
    :param msg: Message content
    """
    global initialized
    
    # Detect when game has fully loaded
    if not initialized:
        if "AddGameInputHandler - handle=0, flags=0xfd dbgContextName=MainMenu, panelName=MainMenu" in msg:
            initialized = True
            vconsole.log('Game fully loaded!')
            # Can send commands here when game is ready
            vconsole.send_cmd("echo Game is ready!")


def main():
    vconsole = VConsole2Lib()
    
    # Configuration
    vconsole.html_output = False
    vconsole.log_to_screen = True
    # vconsole.log_to_file = "vconsole_log.txt"  # Uncomment to enable file logging
    
    # Custom channel colors (hex RGB)
    vconsole.channels_custom_color = {
        'VConComm': '009900',
        'VScript': '3333CC',
        'Console': 'FFFFFF'
    }
    
    # Reconnection settings
    vconsole.auto_reconnect = True
    vconsole.reconnect_delay = 5.0  # seconds between reconnection attempts
    vconsole.socket_timeout = 30.0  # socket read timeout
    vconsole.max_reconnect_attempts = 0  # 0 = infinite reconnection attempts
    
    # Set up callbacks
    vconsole.on_connected = my_on_connected
    vconsole.on_disconnected = my_on_disconnected
    vconsole.on_reconnecting = my_on_reconnecting
    vconsole.on_adon_received = my_on_adon_received
    vconsole.on_cvars_loaded = my_on_cvars_loaded
    vconsole.on_prnt_received = my_on_prnt_received
    
    # Optional: ignore certain channels
    # vconsole.ignore_channels = ['SomeChannel', 'AnotherChannel']
    
    vconsole.log("Connecting to CS2 VConsole...")
    vconsole.connect(ip='127.0.0.1', port=29000)
    
    # Keep the program running
    try:
        while True:
            time.sleep(0.1)
            
            # Example: Send periodic commands
            # if vconsole.is_connected:
            #     vconsole.send_cmd("status")
            #     time.sleep(5)
            
    except KeyboardInterrupt:
        vconsole.log("Shutting down...")
        vconsole.disconnect()


if __name__ == "__main__":
    main()
