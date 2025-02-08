import time
import psutil
import pygetwindow as gw
from pypresence import Presence
from src.settings.main import get_settings_value, get_settings_bool
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client_id = '1265275649543897202'
RPC = None

DISCORD_STATUS = 'DISCORD_STATUS'
CUSTOM_STATUS_KEY = 'custom_status'
SHOW_PROJECT_NAME_KEY = 'show_project_name'

start_time = time.time()

def initialize_rpc():
    global RPC
    try:
        RPC = Presence(client_id)
        RPC.connect()
        logging.info("Connected to Discord RPC.")
    except Exception as e:
        logging.error(f"Failed to connect to Discord RPC: {e}")
        RPC = None

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

def update_discord_status():
    global RPC, start_time
    if RPC is None:
        initialize_rpc()

    if RPC is not None:
        try:
            substring = "Hammer - ["
            custom_display_text = get_settings_value(DISCORD_STATUS, CUSTOM_STATUS_KEY)
            hide_window_name = get_settings_bool(DISCORD_STATUS, SHOW_PROJECT_NAME_KEY)

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
                    return

            RPC.clear()
            start_time = time.time()
        except Exception as e:
            logging.error(f"An error occurred during RPC update: {e}")
            if "The pipe was closed" in str(e):
                logging.info("Connection to Discord RPC lost. Attempting to reconnect...")
                RPC = None
    else:
        logging.info("Discord RPC is not connected. Will retry on the next update.")

def discord_status_clear():
    logging.info("Shutting down gracefully...")
    if RPC is not None:
        RPC.clear()