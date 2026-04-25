import sys
import os
import argparse
import time
import ctypes

# ==========================================================================================
# VELOPACK / SQUIRREL HOOKS
# This MUST run before any other imports (especially Qt) to prevent the GUI from opening
# during installation, uninstallation, or updates.
# ==========================================================================================
def _handle_velopack_hook(argv):
    # Check if any argument contains 'velopack' or 'squirrel'
    # This is a broad check to catch any technical calls from the installer.
    if not any('velopack' in arg.lower() or 'squirrel' in arg.lower() for arg in argv):
        return

    import shutil
    from pathlib import Path

    uninstall_hooks = {
        '--velopack-uninstall', '--velopack-obsolete', '--velopack-obsoleted',
        '--squirrel-uninstall', '--squirrel-obsolete', '--squirrel-obsoleted',
    }
    install_hooks = {
        '--velopack-install', '--velopack-updated',
        '--squirrel-install', '--squirrel-updated',
    }

    active = set(argv) & (uninstall_hooks | install_hooks)
    if not active:
        # If it's a velopack flag but not a known hook, we still want to exit
        # to prevent the GUI from popping up during background operations.
        sys.exit(0)

    try:
        exe_path = Path(sys.executable).resolve()
        current_dir = exe_path.parent
        install_root = current_dir.parent
        userdata_path = install_root / "userdata"

        local_appdata = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
        backup_root = local_appdata / "Hammer5Tools.Backup"
        backup_userdata = backup_root / "userdata"
        backup_sentinel = backup_root / "USERDATA_BACKUP_VALID"

        def _log(msg):
            try:
                backup_root.mkdir(parents=True, exist_ok=True)
                with open(backup_root / "hook.log", "a", encoding="utf-8") as fh:
                    timestamp = time.strftime('%Y-%m-%dT%H:%M:%S')
                    fh.write(f"{timestamp} {' '.join(argv[1:])} :: {msg}\n")
            except Exception:
                pass

        if active & uninstall_hooks:
            _log(f"Starting backup from {userdata_path}")
            if userdata_path.is_dir():
                try:
                    if backup_userdata.exists():
                        shutil.rmtree(backup_userdata, ignore_errors=True)
                    backup_root.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(userdata_path, backup_userdata)
                    if backup_userdata.exists() and any(backup_userdata.iterdir()):
                        backup_sentinel.write_text("valid", encoding="utf-8")
                except Exception as e:
                    _log(f"BACKUP FAILED: {e}")

        if active & install_hooks:
            if backup_userdata.is_dir() and backup_sentinel.exists():
                try:
                    if userdata_path.exists():
                        shutil.rmtree(userdata_path, ignore_errors=True)
                    userdata_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(backup_userdata, userdata_path)
                    if userdata_path.exists() and any(userdata_path.iterdir()):
                        shutil.rmtree(backup_userdata, ignore_errors=True)
                        backup_sentinel.unlink(missing_ok=True)
                except Exception as e:
                    _log(f"RESTORE FAILED: {e}")
    except Exception:
        pass
    
    # ALWAYS exit after handling hooks
    sys.exit(0)

def allocate_console():
    if not ctypes.windll.kernel32.GetConsoleWindow():
        ctypes.windll.kernel32.AllocConsole()
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")

if __name__ == "__main__":
    # 1. Handle installer hooks IMMEDIATELY (no Qt loaded yet)
    _handle_velopack_hook(sys.argv)

    # 2. Parse arguments
    parser = argparse.ArgumentParser(description="Hammer 5 Tools Application")
    parser.add_argument('--dev', action='store_true', help='Enable development mode')
    parser.add_argument('--console', action='store_true', help='Enable console output')
    parser.add_argument('--create-vmdl', help='Create VMDL in folder')
    parser.add_argument('--quick-vmdl', help='Quick create VMDL from mesh')
    parser.add_argument('--quick-vmdl-dir', help='Quick create VMDL in folder')
    parser.add_argument('--quick-batch', help='Quick create batch in folder')
    parser.add_argument('--quick-process', help='Quick process folder')
    parser.add_argument('--quick-process-file', help='Quick process specific file')
    parser.add_argument('file', nargs='?', help='File to open')
    args, unknown = parser.parse_known_args()

    if args.console:
        allocate_console()

    # 3. Check for existing instance via IPC (loads QtNetwork ONLY)
    from PySide6.QtNetwork import QLocalSocket
    from src.ipc.protocol import IPCMessage, IPCCommand
    INSTANCE_KEY = "Hammer5ToolsIPC"

    existing_socket = QLocalSocket()
    existing_socket.connectToServer(INSTANCE_KEY)
    if existing_socket.waitForConnected(500):
        # Found existing instance, send command and exit
        if args.create_vmdl:
            message = IPCMessage.create_quick_action(IPCCommand.CREATE_VMDL, os.path.abspath(args.create_vmdl))
        elif args.quick_vmdl or args.quick_vmdl_dir:
            path = args.quick_vmdl or args.quick_vmdl_dir
            message = IPCMessage.create_quick_action(IPCCommand.QUICK_VMDL, os.path.abspath(path))
        elif args.quick_batch:
            message = IPCMessage.create_quick_action(IPCCommand.QUICK_BATCH, os.path.abspath(args.quick_batch))
        elif args.quick_process:
            message = IPCMessage.create_quick_action(IPCCommand.QUICK_PROCESS, os.path.abspath(args.quick_process))
        elif args.quick_process_file:
            message = IPCMessage.create_quick_action(IPCCommand.QUICK_PROCESS_FILE, os.path.abspath(args.quick_process_file))
        elif args.file:
            message = IPCMessage.create_open_file(os.path.abspath(args.file))
        else:
            message = IPCMessage.create_show()
        
        existing_socket.write(message.encode('utf-8'))
        existing_socket.flush()
        existing_socket.waitForBytesWritten(1000)
        sys.exit(0)

    # 4. No existing instance, load full app logic and start GUI
    from src.app_core import Widget, start_instance_server, QT_Stylesheet_global, check_dotnet_runtime
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer

    app = QApplication(sys.argv)
    app.setStyleSheet(QT_Stylesheet_global)
    
    # Check .NET runtime
    check_dotnet_runtime()
    
    # Create main window
    widget = Widget(dev_mode=args.dev)
    widget.show()
    
    # Start IPC server
    instance_server = start_instance_server(widget)

    # Handle initial arguments
    def handle_initial_args():
        if args.create_vmdl:
            widget.open_quick_create_dialog(os.path.abspath(args.create_vmdl), "vmdl")
        elif args.quick_vmdl or args.quick_vmdl_dir:
            path = args.quick_vmdl or args.quick_vmdl_dir
            widget.handle_quick_vmdl(os.path.abspath(path))
        elif args.quick_batch:
            widget.handle_quick_batch(os.path.abspath(args.quick_batch))
        elif args.quick_process:
            widget.handle_quick_process(os.path.abspath(args.quick_process))
        elif args.quick_process_file:
            widget.handle_quick_process_file(os.path.abspath(args.quick_process_file))
        elif args.file:
            file_path = os.path.abspath(args.file)
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ('.vsmart', '.vdata'):
                widget.open_file_in_smartprop(file_path)

    QTimer.singleShot(200, handle_initial_args)
    sys.exit(app.exec())