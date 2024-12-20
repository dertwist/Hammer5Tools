import time
import psutil
import pygetwindow as gw
from pypresence import Presence
from src.preferences import get_config_value, get_config_bool
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client_id = '1265275649543897202'
try:
    RPC = Presence(client_id)
    RPC.connect()
except:
    print('Discord not running')
    pass

DISCORD_STATUS = 'DISCORD_STATUS'
CUSTOM_STATUS_KEY = 'custom_status'
SHOW_PROJECT_NAME_KEY = 'show_project_name'

start_time = time.time()

def update_rpc(display_name, custom_display_text, elapsed_time):
    if elapsed_time < 3600:
        minutes, seconds = divmod(elapsed_time, 60)
        elapsed_time_str = f"m {int(minutes):02}:{int(seconds):02}"
    else:
        hours, remainder = divmod(elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed_time_str = f"h {int(hours):02}:{int(minutes):02}"

    RPC.update(
        state=f"{display_name}",
        details=f"{custom_display_text} | Elapsed: {elapsed_time_str}",
        large_image="https://i.imgur.com/Zvsv8t5.png",
        buttons=[{"label": "Hammer5Tools", "url": "https://github.com/dertwist/Hammer5Tools"}]
    )
    # logging.info(f"Running {display_name}")


def update_discord_status():
    try:
        substring = "Hammer - ["
        global start_time
        custom_display_text = get_config_value(DISCORD_STATUS, CUSTOM_STATUS_KEY)
        hide_window_name = get_config_bool(DISCORD_STATUS, SHOW_PROJECT_NAME_KEY)
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if substring.lower() in proc.info['name'].lower():
                    display_name = "Hammer - Hidden Project" if hide_window_name else proc.info['name']
                    elapsed_time = time.time() - start_time
                    update_rpc(display_name, custom_display_text, elapsed_time)
                    return

            windows = gw.getAllTitles()
            for window in windows:
                if substring.lower() in window.lower():
                    display_name = "Hammer - Hidden Project" if hide_window_name else window
                    elapsed_time = time.time() - start_time
                    update_rpc(display_name, custom_display_text, elapsed_time)
                    return elapsed_time

            RPC.clear()
            start_time = time.time()
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            if "The pipe was closed" in str(e):
                logging.info("Attempting to reconnect...")
                RPC.connect()
                logging.info("Reconnected successfully")
    except:
        pass

def discord_status_clear():
    logging.info("Shutting down gracefully...")
    RPC.clear()