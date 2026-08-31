import logging
import sys
import os
import argparse
import faulthandler
import ctypes

log = logging.getLogger(__name__)


if not getattr(sys, "frozen", False):
    from pathlib import Path

    repository_root = Path(__file__).resolve().parents[2]
    source = str(repository_root / "Hammer5ToolsGUI")
    if source not in sys.path:
        sys.path.insert(0, source)

# PyOpenGL wraps every GL call with a glGetError() round trip unless this is off.
# The 3D viewports issue tens of thousands of calls per frame on a loaded map, and
# each check is a driver round trip that can stall the pipeline. Must run before the
# first `import OpenGL.GL` anywhere, so it lives at the entry point.
try:
    import OpenGL
    OpenGL.ERROR_CHECKING = False
    OpenGL.ERROR_LOGGING = False
except ImportError:
    pass

# Initialize COM / OLE in STA apartment mode on Windows to support native OS dialogs
if sys.platform == "win32":
    try:
        ctypes.windll.ole32.OleInitialize(None)
    except Exception:
        pass

# Configure PySide6 DLL directory and library paths for Windows
if sys.platform == 'win32':
    try:
        import PySide6
        pyside_dir = os.path.dirname(PySide6.__file__)
        # Add to PATH so that plugin loader can find dependent Qt DLLs
        os.environ["PATH"] = pyside_dir + os.path.pathsep + os.environ.get("PATH", "")
        if hasattr(os, 'add_dll_directory'):
            os.add_dll_directory(pyside_dir)
            plugins_dir = os.path.join(pyside_dir, "plugins")
            if os.path.isdir(plugins_dir):
                os.add_dll_directory(plugins_dir)
                for sub in ["sceneparsers", "geometryloaders"]:
                    sub_dir = os.path.join(plugins_dir, sub)
                    if os.path.isdir(sub_dir):
                        os.add_dll_directory(sub_dir)
    except Exception as e:
        log.error(f"Error configuring PySide6 DLL paths: {e}")

# VELOPACK / SQUIRREL HOOKS
# This MUST run before any other imports (especially Qt) to prevent the GUI from opening
# during installation, uninstallation, or updates.
_INSTALLER_ARG_PREFIXES = ('--veloapp-', '--velopack-', '--squirrel-')


def _handle_velopack_hook(argv):
    """Exit immediately when the installer started us to run a hook.

    Velopack passes --veloapp-install/-updated/-obsolete/-uninstall. Matching the
    prefix rather than a fixed list means an unrecognised installer argument exits
    too, instead of opening a window the installer will later kill. User data lives
    outside the install tree now, so there is nothing to back up or restore here.
    """
    if any(argument.startswith(_INSTALLER_ARG_PREFIXES) for argument in argv[1:]):
        sys.exit(0)


def format_crash_report(exc_type, exc, tb, thread_name=None):
    """Format an unhandled exception into a crash report string."""
    import traceback
    import io
    from datetime import datetime
    try:
        from gui.common import app_version
    except Exception:
        app_version = 'unknown'

    lines = []
    lines.append(f"Hammer 5 Tools {app_version} crash report")
    lines.append(f"Time:    {datetime.now().isoformat(' ', 'seconds')}")
    lines.append(f"Thread:  {thread_name or 'MainThread'}")
    lines.append(f"Python:  {sys.version}")
    lines.append(f"Exe:     {sys.executable}")
    lines.append(f"Args:    {sys.argv}")
    lines.append("")
    lines.append("".join(traceback.format_exception(exc_type, exc, tb)))
    lines.append("--- All threads ---")
    try:
        sio = io.StringIO()
        faulthandler.dump_traceback(file=sio)
        lines.append(sio.getvalue())
    except Exception:
        pass
    return "\n".join(lines)


def _install_crash_handler():
    def hook(exc_type, exc, tb):
        try:
            details = format_crash_report(exc_type, exc, tb)
        except Exception:
            import traceback
            details = f"Fatal unhandled exception: {exc_type}: {exc}\n{''.join(traceback.format_exception(exc_type, exc, tb))}"

        # 1. Write to persistent crash log files
        try:
            from core.runtime_paths import resolve_runtime_paths
            paths = resolve_runtime_paths()
            logs_dir = paths.user_data_root / "logs"
        except Exception:
            from pathlib import Path
            logs_dir = Path.home() / "Hammer5Tools" / "logs"

        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            with open(logs_dir / "crash.log", "a", encoding="utf-8") as f:
                f.write(details + "\n\n" + "=" * 80 + "\n\n")
            with open(logs_dir / "last_crash.txt", "w", encoding="utf-8") as f:
                f.write(details)
        except Exception:
            pass

        # 2. Write to stderr (and flush) so the launcher or console stream captures it
        try:
            if sys.stderr is not None:
                sys.stderr.write(details + "\n")
                sys.stderr.flush()
        except Exception:
            pass

        # 3. Show dialog to user
        dialog_shown = False
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            if app is not None:
                from gui.widgets.common import ErrorInfo
                dialog = ErrorInfo(
                    text=f"An unhandled error occurred: {exc_type.__name__}: {exc}",
                    details=details,
                    title="Crash Report",
                )
                dialog.exec()
                dialog_shown = True
        except Exception:
            pass

        if not dialog_shown and sys.platform == "win32":
            try:
                import ctypes
                summary = f"Hammer 5 Tools encountered an unhandled error:\n\n{exc_type.__name__}: {exc}\n\n{details}"
                if len(summary) > 2048:
                    summary = summary[:2000] + "\n\n... [truncated, see crash.log for full details]"
                ctypes.windll.user32.MessageBoxW(None, summary, "Hammer 5 Tools Crash", 0x10)
            except Exception:
                pass

    sys.excepthook = hook

    import threading
    threading.excepthook = lambda a: hook(a.exc_type, a.exc_value, a.exc_traceback)



if __name__ == "__main__":
    # Add the 'src' directory to sys.path so that 'import resources_rc' and other
    # top-level imports within the 'src' package work correctly.
    # This handles both direct package startup and the frozen entry point.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) == 'src':
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
    else:
        src_dir = os.path.join(current_dir, 'src')
        if os.path.isdir(src_dir) and src_dir not in sys.path:
            sys.path.insert(0, src_dir)

    from gui.logs import setup_logging
    setup_logging()

    _install_crash_handler()

    # Windows Job Object initialization (ensures all child processes terminate on exit)
    if sys.platform == 'win32':
        try:
            from gui.job_object import install_job_object
            install_job_object()
        except Exception as e:
            log.error(f"Error installing job object: {e}")

    # 1. Handle installer hooks IMMEDIATELY (no Qt loaded yet)
    _handle_velopack_hook(sys.argv)

    from gui.lifecycle import require_launcher_for_frozen_build
    try:
        require_launcher_for_frozen_build()
    except RuntimeError as error:
        from gui.lifecycle import relaunch_through_launcher
        if relaunch_through_launcher(sys.argv[1:]):
            sys.exit(0)
        if sys.platform == "win32":
            ctypes.windll.user32.MessageBoxW(None, str(error), "Hammer 5 Tools", 0x10)
        sys.exit(2)

    parser = argparse.ArgumentParser(description="Hammer 5 Tools Application")
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
        from gui.other.console import allocate_console
        allocate_console()

    # Must run before anything spawns a child process.
    from gui.no_console import install as _install_no_console
    _install_no_console()

    # 3. Check for existing instance via IPC (loads QtNetwork ONLY)
    from PySide6.QtNetwork import QLocalSocket
    from gui.shell.ipc_protocol import IPCMessage, IPCCommand
    INSTANCE_KEY = "Hammer5ToolsIPC"

    from gui.lifecycle import launcher_supervises_process
    launcher_owns_instance = launcher_supervises_process()
    existing_socket = QLocalSocket()
    existing_socket.connectToServer(INSTANCE_KEY)
    if not launcher_owns_instance and existing_socket.waitForConnected(500):
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
            file_path = os.path.abspath(args.file)
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.vsndevts':
                message = IPCMessage.create_open_file(file_path, "soundevent")
            elif ext == '.vsnap':
                message = IPCMessage.create_open_file(file_path, "vsnap")
            else:
                message = IPCMessage.create_open_file(file_path)
        else:
            message = IPCMessage.create_show()
        
        existing_socket.write(message.encode('utf-8'))
        existing_socket.flush()
        existing_socket.waitForBytesWritten(1000)
        sys.exit(0)

    from gui.app_core import MainWindow, start_instance_server
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer, Qt, QCoreApplication

    app = QApplication(sys.argv)
    # The global stylesheet's layout assumptions (tab alignment, control padding,
    # etc.) are tuned against Qt's Fusion style. Native styles lay widgets out
    # differently per platform (e.g. QMacStyle centers QTabBar tabs), which QSS
    # color/border rules can't override, so pin one style everywhere.
    app.setStyle('Fusion')

    # Explicitly add PySide6 plugins to library path to ensure scene importers (assimp, gltf) are resolved
    import PySide6
    plugins_dir = os.path.join(os.path.dirname(PySide6.__file__), "plugins")
    if os.path.isdir(plugins_dir):
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.addLibraryPath(plugins_dir)
        
    # Select the theme before widgets are constructed so custom-painted
    # controls and the global stylesheet read the same active Theme.
    from gui.styles import theme
    from gui.settings.common import get_settings_value
    try:
        level = int(get_settings_value('APP', 'theme_level', 0))
    except (TypeError, ValueError):
        level = 0
    theme.set_level(level)

    from gui.styles import manager as style_manager
    style_manager.apply(app, theme.get_theme())

    # "System" follows the OS scheme for as long as it stays selected.
    def _on_system_scheme_changed(_scheme):
        if theme.selected() != theme.LEVEL_SYSTEM:
            return
        theme.set_level(theme.LEVEL_SYSTEM)
        style_manager.reapply(theme.get_theme())
        from gui.common import refresh_title_bars
        refresh_title_bars()

    app.styleHints().colorSchemeChanged.connect(_on_system_scheme_changed)

    widget = MainWindow()
    # Adding the first QOpenGLWidget to a visible window makes Qt switch the
    # top level to an RHI-backed backing store, which destroys and recreates the
    # native window -- the app looks like it closed and reopened when a 3D
    # viewport tab is first opened. A throwaway GL child forces that switch here,
    # while nothing is on screen yet; the window stays RHI-backed after it goes.
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    _rhi_primer = QOpenGLWidget(widget)
    _rhi_primer.hide()
    from gui.other.taskbar_identity import apply_taskbar_identity
    apply_taskbar_identity(widget)
    widget.show()
    _rhi_primer.setParent(None)
    _rhi_primer.deleteLater()
    
    instance_server = start_instance_server(widget)

    def handle_initial_args():
        if args.create_vmdl:
            widget.quick_actions.open_quick_create_dialog(os.path.abspath(args.create_vmdl), "vmdl")
        elif args.quick_vmdl or args.quick_vmdl_dir:
            path = args.quick_vmdl or args.quick_vmdl_dir
            widget.quick_actions.create_vmdl(os.path.abspath(path))
        elif args.quick_batch:
            widget.quick_actions.create_compile_batch(os.path.abspath(args.quick_batch))
        elif args.quick_process:
            widget.quick_actions.compile_folder(os.path.abspath(args.quick_process))
        elif args.quick_process_file:
            widget.quick_actions.compile_file(os.path.abspath(args.quick_process_file))
        elif args.file:
            file_path = os.path.abspath(args.file)
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ('.vsmart', '.vdata'):
                widget.open_file_in_smartprop(file_path)
            elif ext == '.vsndevts':
                widget.open_file_in_soundevent(file_path)
            elif ext == '.vsnap':
                widget.open_file_in_vsnap(file_path)

    QTimer.singleShot(200, handle_initial_args)
    sys.exit(app.exec())
