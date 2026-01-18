"""
CS2RemoteConsole PTY Controller

Manages communication with CS2 via CS2RemoteConsole-client.exe using a PTY (pseudo-terminal).
Handles command sequencing, output parsing, and connection lifecycle.
"""
import os
import time
import re
import subprocess
from pathlib import Path
from typing import Optional, Callable


class CS2RemoteConsoleController:
    """
    Wraps CS2RemoteConsole-client.exe in a PTY for reliable command automation.
    
    Usage:
        controller = CS2RemoteConsoleController(
            cs2_remote_console_path="/path/to/CS2RemoteConsole-client.exe",
            log_callback=lambda msg: print(msg)
        )
        controller.connect()
        controller.send_command("map_workshop addon_name map_name")
        controller.send_command("buildcubemaps")
        controller.disconnect()
    """

    def __init__(
        self,
        cs2_remote_console_path: str,
        cs2_console_ip: str = "127.0.0.1",
        cs2_console_port: int = 29000,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize the controller.
        
        Args:
            cs2_remote_console_path: Full path to CS2RemoteConsole-client.exe
            cs2_console_ip: IP address of CS2 console (default: localhost)
            cs2_console_port: Port of CS2 console (default: 29000)
            log_callback: Optional callback for logging messages
        """
        self.cs2_remote_console_path = cs2_remote_console_path
        self.cs2_console_ip = cs2_console_ip
        self.cs2_console_port = cs2_console_port
        self.log_callback = log_callback or (lambda msg: None)
        
        self.pty = None
        self.connected = False
        self.output_buffer = ""

    def _log(self, message: str):
        """Log a message via callback"""
        self.log_callback(message)

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to CS2 via RemoteConsole.
        
        Args:
            timeout: Maximum time to wait for connection (seconds)
            
        Returns:
            True if connected, False otherwise
        """
        try:
            import winpty
        except ImportError:
            self._log("ERROR: pywinpty not installed. Install with: pip install pywinpty")
            return False

        if not Path(self.cs2_remote_console_path).exists():
            self._log(f"ERROR: CS2RemoteConsole not found at {self.cs2_remote_console_path}")
            return False

        try:
            self._log(f"Connecting to CS2 console at {self.cs2_console_ip}:{self.cs2_console_port}...")
            
            # Create PTY with RemoteConsole
            self.pty = winpty.PtyProcess.spawn(
                [self.cs2_remote_console_path],
                cwd=str(Path(self.cs2_remote_console_path).parent),
            )
            
            # Wait for connection prompt/response
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    output = self.pty.read()
                    if output:
                        self.output_buffer += output
                        self._log(f"[RemoteConsole] {output.strip()}")
                        
                        # Check for connection success indicators
                        if "connected" in output.lower() or "ready" in output.lower():
                            self.connected = True
                            self._log("✓ Connected to CS2 RemoteConsole")
                            return True
                except Exception:
                    pass
                
                time.sleep(0.1)
            
            # If we got here, assume connected (RemoteConsole may not always print "connected")
            self.connected = True
            self._log("✓ RemoteConsole PTY established (assuming connected)")
            return True
            
        except Exception as e:
            self._log(f"ERROR: Failed to connect: {e}")
            return False

    def send_command(self, command: str, wait_time: float = 2.0) -> str:
        """
        Send a command to CS2 via RemoteConsole.
        
        Args:
            command: Command to send (e.g., "map_workshop addon map")
            wait_time: Time to wait for response (seconds)
            
        Returns:
            Output from the command
        """
        if not self.connected or not self.pty:
            self._log(f"ERROR: Not connected to RemoteConsole")
            return ""

        try:
            self._log(f"Sending: {command}")
            
            # Send command with CRLF (Windows console expects this)
            self.pty.write(f"{command}\r\n")
            
            # Read response
            response = ""
            start_time = time.time()
            while time.time() - start_time < wait_time:
                try:
                    output = self.pty.read()
                    if output:
                        response += output
                        self._log(f"[Response] {output.strip()}")
                except Exception:
                    pass
                
                time.sleep(0.05)
            
            return response
            
        except Exception as e:
            self._log(f"ERROR: Failed to send command: {e}")
            return ""

    def send_command_and_wait_for_marker(
        self,
        command: str,
        marker: str,
        timeout: float = 30.0,
    ) -> bool:
        """
        Send a command and wait for a specific output marker (e.g., "cubemaps done").
        
        Args:
            command: Command to send
            marker: Text to wait for in output
            timeout: Maximum time to wait (seconds)
            
        Returns:
            True if marker found, False if timeout
        """
        if not self.connected or not self.pty:
            self._log(f"ERROR: Not connected to RemoteConsole")
            return False

        try:
            self._log(f"Sending: {command} (waiting for '{marker}')")
            
            # Send command
            self.pty.write(f"{command}\r\n")
            
            # Wait for marker
            start_time = time.time()
            accumulated = ""
            while time.time() - start_time < timeout:
                try:
                    output = self.pty.read()
                    if output:
                        accumulated += output
                        self._log(f"[Response] {output.strip()}")
                        
                        # Check for marker (case-insensitive)
                        if marker.lower() in accumulated.lower():
                            self._log(f"✓ Found marker: {marker}")
                            return True
                except Exception:
                    pass
                
                time.sleep(0.1)
            
            self._log(f"⚠ Timeout waiting for marker: {marker}")
            return False
            
        except Exception as e:
            self._log(f"ERROR: Failed to send command: {e}")
            return False

    def disconnect(self):
        """Disconnect from CS2 RemoteConsole"""
        try:
            if self.pty:
                self._log("Disconnecting from RemoteConsole...")
                self.pty.write("quit\r\n")
                time.sleep(0.5)
                self.pty.terminate()
                self.pty = None
            self.connected = False
            self._log("✓ Disconnected")
        except Exception as e:
            self._log(f"Warning: Error during disconnect: {e}")
            self.connected = False

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
