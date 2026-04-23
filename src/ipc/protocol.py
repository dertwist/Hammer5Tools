"""Inter-process communication protocol for file operations.

Messages are JSON-encoded for extensibility and support:
- Show/focus window commands
- Open file commands with editor routing
- Focus existing document commands
"""
import json
from enum import Enum


class IPCCommand(Enum):
    """Available IPC commands."""
    SHOW_WINDOW = "show"
    OPEN_FILE = "open_file"
    FOCUS_FILE = "focus_file"
    CREATE_VMDL = "create_vmdl"
    QUICK_VMDL = "quick_vmdl"
    QUICK_BATCH = "quick_batch"
    QUICK_PROCESS = "quick_process"
    QUICK_PROCESS_FILE = "quick_process_file"


class IPCMessage:
    """Factory for creating and parsing IPC messages."""
    
    @staticmethod
    def create_show():
        """Create a message to show/focus the main window."""
        return json.dumps({"command": IPCCommand.SHOW_WINDOW.value})
    
    @staticmethod
    def create_open_file(file_path, editor_type="smartprop"):
        """Create a message to open a file in the specified editor.
        
        Args:
            file_path: Absolute path to the file to open
            editor_type: Type of editor (smartprop, soundevent, etc.)
        """
        return json.dumps({
            "command": IPCCommand.OPEN_FILE.value,
            "file_path": file_path,
            "editor_type": editor_type
        })
    
    @staticmethod
    def create_focus_file(file_path, editor_type="smartprop"):
        """Create a message to focus an already-open file.
        
        Args:
            file_path: Absolute path to the file to focus
            editor_type: Type of editor where the file is open
        """
        return json.dumps({
            "command": IPCCommand.FOCUS_FILE.value,
            "file_path": file_path,
            "editor_type": editor_type
        })

    @staticmethod
    def create_quick_action(command, file_path, addon_hint=None):
        """Create a message for a quick action (VMDL, Batch, Process).
        
        Args:
            command: The IPCCommand to execute
            file_path: Target file or directory
            addon_hint: Optional addon name hint extracted from path
        """
        msg = {
            "command": command.value,
            "file_path": file_path
        }
        if addon_hint:
            msg["addon_hint"] = addon_hint
        return json.dumps(msg)
    
    @staticmethod
    def parse(message_bytes):
        """Parse incoming message bytes into a command dictionary.
        
        Args:
            message_bytes: Raw bytes from QLocalSocket
            
        Returns:
            Dictionary with command and parameters, or None if invalid
        """
        try:
            return json.loads(message_bytes.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback for legacy "show" message (backward compatibility)
            try:
                msg = message_bytes.decode('utf-8').strip()
                if msg == "show":
                    return {"command": IPCCommand.SHOW_WINDOW.value}
            except:
                pass
            return None
    
    @staticmethod
    def encode(message_dict):
        """Encode a message dictionary to JSON bytes.
        
        Args:
            message_dict: Dictionary with command and parameters
            
        Returns:
            UTF-8 encoded JSON bytes
        """
        return json.dumps(message_dict).encode('utf-8')
