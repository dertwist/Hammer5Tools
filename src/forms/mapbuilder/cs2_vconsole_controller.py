"""
CS2 VConsole Controller

Manages communication with CS2 via VConsole2Lib (direct socket connection).
Handles command sequencing, output parsing, and connection lifecycle.

Replaces the legacy PTY-based RemoteConsole implementation.
"""
import socket
import time
import ctypes
from typing import Optional, Callable
from VConsoleLib.vconsole2_lib import VConsole2Lib


class CS2VConsoleController:
    """
    Wraps VConsole2Lib for reliable CS2 console automation.
    
    Usage:
        controller = CS2VConsoleController(
            log_callback=lambda msg: print(msg)
        )
        if controller.connect():
            controller.send_command("map_workshop addon_name map_name")
            controller.send_command("buildcubemaps")
            controller.disconnect()
    """

    def __init__(
        self,
        cs2_console_ip: str = "127.0.0.1",
        cs2_console_port: int = 29000,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the controller.
        
        Args:
            cs2_console_ip: IP address of CS2 console (default: localhost)
            cs2_console_port: Port of CS2 console (default: 29000)
            log_callback: Optional callback for logging messages
        """
        self.cs2_console_ip = cs2_console_ip
        self.cs2_console_port = cs2_console_port
        self.log_callback = log_callback or (lambda msg: None)
        
        self.vconsole = None
        self.connected = False
        self.last_messages = []

    def _log(self, message: str):
        """Log a message via callback"""
        self.log_callback(message)

    def _on_prnt_received(self, vconsole: VConsole2Lib, channel_name: str, msg: str):
        """
        Callback when console message is received.
        
        Args:
            vconsole: VConsole2Lib instance
            channel_name: Channel name (e.g., 'Console', 'VScript')
            msg: Message text
        """
        # Store recent messages for potential parsing
        self.last_messages.append((channel_name, msg))
        if len(self.last_messages) > 100:
            self.last_messages.pop(0)
        
        # Clean up channel name presentation
        # VConsole2Lib often returns 'Unknown:<hash>' if channel isn't mapped
        if channel_name.startswith("Unknown:"):
            # If it's unknown, just print the message cleanly (Valve style)
            # This avoids the ugly [Unknown:12345] prefix
            self._log(f"{msg}")
        else:
            # If we have a known channel name, show it
            self._log(f"[{channel_name}] {msg}")

    def _on_disconnected(self, vconsole: VConsole2Lib):
        """
        Callback when disconnected from CS2.
        
        Args:
            vconsole: VConsole2Lib instance
        """
        self.connected = False
        self._log("Disconnected from CS2 console")

    def _on_cvars_loaded(self, vconsole: VConsole2Lib, cvars: list):
        """
        Callback when CVARs are loaded.
        
        Args:
            vconsole: VConsole2Lib instance
            cvars: List of loaded CVARs
        """
        self._log(f"Loaded {len(cvars)} CVARs from CS2")

    def check_port_ready(self, timeout: float = 30.0) -> bool:
        """
        Check if CS2 console port is ready to accept connections.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if port is listening, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.cs2_console_ip, self.cs2_console_port))
                sock.close()
                if result == 0:
                    self._log(f"✓ CS2 console port {self.cs2_console_port} is ready")
                    return True
            except Exception:
                pass
            time.sleep(1)
        
        self._log(f"✗ CS2 console port {self.cs2_console_port} not ready after {timeout}s")
        return False

    def connect(self, timeout: float = 30.0, retry_count: int = 3) -> bool:
        """
        Connect to CS2 VConsole.
        
        Args:
            timeout: Maximum time to wait for port readiness (seconds)
            retry_count: Number of connection attempts
            
        Returns:
            True if connected, False otherwise
        """
        # First check if port is ready
        self._log(f"Checking if CS2 console port {self.cs2_console_port} is ready...")
        if not self.check_port_ready(timeout):
            self._log("ERROR: CS2 console port is not accessible")
            self._log("Make sure CS2 is running with -console parameter")
            return False

        # Create VConsole instance
        self.vconsole = VConsole2Lib()
        self.vconsole.log_to_screen = False  # We handle logging ourselves
        self.vconsole.on_prnt_received = self._on_prnt_received
        self.vconsole.on_disconnected = self._on_disconnected
        self.vconsole.on_cvars_loaded = self._on_cvars_loaded

        # Attempt connection with retries
        for attempt in range(1, retry_count + 1):
            self._log(f"Connecting to CS2 console (attempt {attempt}/{retry_count})...")
            
            if self.vconsole.connect(self.cs2_console_ip, self.cs2_console_port):
                self.connected = True
                self._log("✓ Connected to CS2 VConsole")
                # Give it a moment to receive initial packets
                time.sleep(0.5)
                return True
            
            if attempt < retry_count:
                self._log(f"Connection failed, retrying in 2 seconds...")
                time.sleep(2)
        
        self._log("ERROR: Failed to connect to CS2 console after all attempts")
        return False

    def send_command(self, command: str) -> bool:
        """
        Send a command to CS2 console.
        
        Args:
            command: Command to send (e.g., "map_workshop addon map")
            
        Returns:
            True if command was sent, False otherwise
        """
        # Auto-reconnect logic
        if not self.connected or not self.vconsole:
            self._log("Connection lost, attempting to reconnect...")
            if not self.connect(timeout=5.0, retry_count=2):
                self._log(f"ERROR: Could not reconnect to send command: {command}")
                return False

        try:
            self._log(f"Sending: {command}")
            self.vconsole.send_cmd(command)
            return True
        except Exception as e:
            self._log(f"ERROR: Failed to send command: {e}")
            self.connected = False # Mark as disconnected on error
            return False

    def bring_cs2_to_front(self):
        """
        Attempt to find the CS2 window and bring it to the foreground.
        Uses ctypes to call Windows API directly.
        """
        try:
            # CS2 window title is usually "Counter-Strike 2"
            hwnd = ctypes.windll.user32.FindWindowW(None, "Counter-Strike 2")
            if hwnd:
                # Restore if minimized
                if ctypes.windll.user32.IsIconic(hwnd):
                    ctypes.windll.user32.ShowWindow(hwnd, 9) # SW_RESTORE
                
                # Bring to front
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                self._log("Focused CS2 window")
            else:
                self._log("Could not find CS2 window to focus")
        except Exception as e:
            self._log(f"Failed to focus CS2 window: {e}")

    def disconnect(self):
        """
        Disconnect from CS2 VConsole.
        """
        if self.vconsole and self.connected:
            self._log("Disconnecting from CS2 console...")
            try:
                # VConsole2Lib doesn't have explicit disconnect,
                # connection closes when socket is closed
                if self.vconsole.client_socket:
                    self.vconsole.client_socket.close()
                self.connected = False
                self._log("✓ Disconnected")
            except Exception as e:
                self._log(f"Note: Disconnect error: {e}")
                self.connected = False
        
        self.vconsole = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
