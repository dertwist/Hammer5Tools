import sys

_ipc_server = None

def set_ipc_server(server):
    global _ipc_server
    _ipc_server = server

def stop_ipc_server():
    """
    Close the IPC server to prevent other instances from communicating with this one.
    Useful during updates to prevent the main window from being brought to front.
    """
    global _ipc_server
    if _ipc_server:
        print("[IPC] Stopping server...")
        try:
            _ipc_server.close()
        except Exception as e:
            print(f"[IPC] Error closing server: {e}")
        _ipc_server = None
