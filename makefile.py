import time
from datetime import datetime, timezone
import os
import shutil
import zipfile
import subprocess
import argparse
import glob
import json
from typing import List, Set
from tabulate import tabulate
import re
import sys
cur_dir = os.path.abspath(os.path.dirname(__file__))
build_root = os.path.join(cur_dir, 'build')
pyinstaller_root = os.path.join(build_root, 'pyinstaller')

with open(os.path.join(cur_dir, 'version.json'), encoding='utf-8') as version_file:
    app_version = json.load(version_file)['version']

gui_python_root = os.path.join(cur_dir, 'Hammer5ToolsGUI')
gui_root = os.path.join(gui_python_root, 'hammer5tools_gui')
core_python_root = os.path.join(cur_dir, 'Hammer5ToolsCore', 'Python')
core_csharp_root = os.path.join(cur_dir, 'Hammer5ToolsCore', 'CSharp')
external_root = os.path.join(core_csharp_root, 'external')
external = f"--add-data={external_root};external"
print(f"External path: {external}")


# Create a runtimeconfig.json for the bundled .NET runtime
def generate_runtime_config(target_dir):
    config = {
        "runtimeOptions": {
            "tfm": "net10.0",
            "frameworks": [
                {
                    "name": "Microsoft.NETCore.App",
                    "version": "10.0.0"
                }
            ]
        }
    }
    import json
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, 'Hammer5Tools.runtimeconfig.json'), 'w') as f:
        json.dump(config, f, indent=2)

def get_dotnet_runtime_data():
    """Finds .NET 10.0 runtime files on the system to bundle them."""
    import glob
    dotnet_root = os.environ.get("DOTNET_ROOT", r"C:\Program Files\dotnet")
    if not os.path.exists(dotnet_root):
        return []

    shared_path = os.path.join(dotnet_root, "shared")
    results = []

    # Find latest 10.0 version. Microsoft.WindowsDesktop.App is deliberately
    # excluded: nothing in this repo uses WPF/WinForms (no UseWPF/UseWindowsForms
    # in any .csproj), so bundling it just adds ~95MB of unused framework files.
    for framework in ["Microsoft.NETCore.App"]:
        fw_path = os.path.join(shared_path, framework)
        if os.path.exists(fw_path):
            versions = [v for v in os.listdir(fw_path) if v.startswith("10.0")]
            if versions:
                latest = sorted(versions, key=lambda x: [int(i) for i in x.split('.')])[-1]
                src = os.path.join(fw_path, latest)
                dst = f"dotnet/shared/{framework}/{latest}"
                results.append(f"--add-data={src};{dst}")

    # Find host fxr
    host_fxr_path = os.path.join(dotnet_root, "host", "fxr")
    if os.path.exists(host_fxr_path):
        versions = os.listdir(host_fxr_path)
        if versions:
            latest = sorted(versions, key=lambda x: [int(i) for i in x.split('.')])[-1]
            src = os.path.join(host_fxr_path, latest)
            dst = f"dotnet/host/fxr/{latest}"
            results.append(f"--add-data={src};{dst}")

    # Main host files
    for dll in ["hostfxr.dll", "hostpolicy.dll"]:
        dll_path = os.path.join(dotnet_root, dll)
        if os.path.exists(dll_path):
            results.append(f"--add-data={dll_path};dotnet")
            
    return results


# Path to your .NET DLLs


def print_elapsed_time(stage_name: str, start_time: float) -> None:
    """Prints the elapsed time for a given stage."""
    elapsed_time = time.time() - start_time
    print(f"{stage_name} took {elapsed_time:.2f} seconds")


def kill_process(process_name: str) -> None:
    """Kills a process by its name."""
    subprocess.run(
        ["taskkill", "/F", "/IM", process_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def find_pycparser_tables():
    """
    Return (lextab_path, yacctab_path) if the pre-generated pycparser parser
    tables exist, or None if they are absent (pycparser >= 3.0 generates them
    lazily at runtime, so absence is normal).

    Search order:
      1. Local .venv / venv
      2. pycparser's own package directory (global installs, CI)
      3. The generated parser-table directory under build/
    """
    try:
        import pycparser as _pycparser
        pycparser_pkg_dir = os.path.dirname(_pycparser.__file__)
    except ImportError:
        pycparser_pkg_dir = None

    candidates = [
        os.path.join(cur_dir, '.venv', 'Lib', 'site-packages', 'pycparser'),
        os.path.join(cur_dir, 'venv', 'Lib', 'site-packages', 'pycparser'),
    ]
    if pycparser_pkg_dir:
        candidates.append(pycparser_pkg_dir)
    candidates.append(os.path.join(build_root, 'pycparser'))

    for base in candidates:
        lextab = os.path.join(base, 'lextab.py')
        yacctab = os.path.join(base, 'yacctab.py')
        if os.path.isfile(lextab) and os.path.isfile(yacctab):
            return lextab, yacctab
    return None


def _generate_pycparser_tables():
    """
    Force pycparser to generate lextab.py and yacctab.py by instantiating
    its C parser with outputdir under build/ so the files land somewhere
    predictable regardless of whether the package dir is writable.
    """
    try:
        try:
            import pycparser.ply.lex as lex
            import pycparser.ply.yacc as yacc
        except ImportError:
            import ply.lex as lex
            import ply.yacc as yacc
        table_dir = os.path.join(build_root, 'pycparser')
        os.makedirs(table_dir, exist_ok=True)

        # Monkey-patch outputdir so generated tables stay with build artifacts.
        _orig_lex = lex.lex
        _orig_yacc = yacc.yacc

        def _lex(*a, **kw):
            kw.setdefault('outputdir', table_dir)
            return _orig_lex(*a, **kw)

        def _yacc(*a, **kw):
            kw.setdefault('outputdir', table_dir)
            return _orig_yacc(*a, **kw)

        lex.lex = _lex
        yacc.yacc = _yacc
        try:
            from pycparser import c_parser
            c_parser.CParser()
            print("pycparser tables generated.")
        finally:
            lex.lex = _orig_lex
            yacc.yacc = _orig_yacc
    except Exception as e:
        print(f"Warning: could not pre-generate pycparser tables: {e}")



def build_cpp(project: str, src_dir: str, output_name: str) -> None:
    """Builds a C++ project using CMake."""
    build_dir = os.path.join(build_root, 'native', project)
    os.makedirs(build_dir, exist_ok=True)
    try:
        # Let CMake choose the best generator for the system
        subprocess.run(["cmake", "-S", src_dir, "-B", build_dir,
                        "-DCMAKE_BUILD_TYPE=Release"], check=True)
        subprocess.run(["cmake", "--build", build_dir, "--config", "Release"], check=True)
        
        # Copy exe to hammer5tools/
        # CMake might put the exe in build_dir or build_dir/Release (for MSVC)
        src_exe = os.path.join(build_dir, f"{output_name}.exe")
        if not os.path.exists(src_exe):
            src_exe = os.path.join(build_dir, "Release", f"{output_name}.exe")
            
        if not os.path.exists(src_exe):
            raise FileNotFoundError(f"Could not find built executable at {src_exe}")

        dst_exe = os.path.join(cur_dir, "Hammer5Tools", f"{output_name}.exe")


        os.makedirs(os.path.dirname(dst_exe), exist_ok=True)
        import shutil
        shutil.copy2(src_exe, dst_exe)
        print(f"Successfully built and copied {output_name}.exe")
    except subprocess.CalledProcessError as e:
        print(f"Error building C++ project {project}: {e}")
        raise


def build_libraries() -> None:
    """Builds and publishes all Windows x64 .NET and native libraries."""
    smartprop_native_project = os.path.join(core_csharp_root, 'Hammer5Tools.Native', 'Hammer5Tools.Native.csproj')
    smartprop_native_publish = os.path.join(core_csharp_root, 'Hammer5Tools.Native', 'publish')
    if os.path.exists(smartprop_native_project):
        print("Building Hammer5Tools.Native (win-x64 NativeAOT)...")
        subprocess.run([
            'dotnet', 'publish', smartprop_native_project,
            '--configuration', 'Release',
            '--runtime', 'win-x64',
            '--self-contained', 'true',
            '--output', smartprop_native_publish,
        ], check=True)

    core_project = os.path.join(core_csharp_root, 'Hammer5Tools.Core', 'Hammer5Tools.Core.csproj')
    core_publish = os.path.join(core_csharp_root, 'Hammer5Tools.Core', 'publish')
    if os.path.exists(core_project):
        print("Building Hammer5Tools.Core...")
        subprocess.run([
            'dotnet', 'publish', core_project,
            '--configuration', 'Release',
            '--output', core_publish,
        ], check=True)

    source_porter_project = os.path.join(core_csharp_root, 'SourcePorter.Core', 'SourcePorter.Core.csproj')
    source_porter_publish = os.path.join(core_csharp_root, 'SourcePorter.Core', 'publish')
    if os.path.exists(source_porter_project):
        print("Building SourcePorter.Core...")
        # Incremental publish does not prune stale per-RID native asset folders
        # (e.g. runtimes/win-x86, runtimes/linux-x64) left behind by a prior
        # publish without --runtime; wipe the output first so only win-x64 lands.
        if os.path.exists(source_porter_publish):
            shutil.rmtree(source_porter_publish)
        subprocess.run([
            'dotnet', 'publish', source_porter_project,
            '--configuration', 'Release',
            '--runtime', 'win-x64',
            '--output', source_porter_publish,
            '--no-self-contained',
        ], check=True)

    unreal_bridge_project = os.path.join(core_csharp_root, 'UnrealBridge', 'UnrealBridge.csproj')
    unreal_bridge_publish = os.path.join(core_csharp_root, 'UnrealBridge', 'publish')
    if os.path.exists(unreal_bridge_project):
        print("Building UnrealBridge...")
        subprocess.run([
            'dotnet', 'publish', unreal_bridge_project,
            '--configuration', 'Release',
            '--output', unreal_bridge_publish,
            '--no-self-contained',
        ], check=True)


def build_app_pyinstaller(fast=False, channel='stable') -> None:
    """Builds the Python application using PyInstaller."""
    # Try to locate pre-generated pycparser tables; generate them if absent.
    tables = find_pycparser_tables()
    if tables is None:
        _generate_pycparser_tables()
        tables = find_pycparser_tables()

    runtime_config_dir = os.path.join(external_root, 'dotnet')
    runtime_config_path = os.path.join(runtime_config_dir, 'Hammer5Tools.runtimeconfig.json')
    if channel == 'stable':
        generate_runtime_config(runtime_config_dir)

    build_libraries()

    smartprop_native_publish = os.path.join(core_csharp_root, 'Hammer5Tools.Native', 'publish')
    smartprop_native_dlls = [
        path for path in glob.glob(os.path.join(smartprop_native_publish, '*.dll'))
        if os.path.isfile(path)
    ]

    unreal_bridge_publish = os.path.join(core_csharp_root, 'UnrealBridge', 'publish')
    ue_scripts_dir = os.path.join(cur_dir, 'tools', 'ue_scripts')
    source_porter_publish = os.path.join(core_csharp_root, 'SourcePorter.Core', 'publish')
    bspsrc_dir = os.path.join(cur_dir, 'tools', 'bspsrc')
    import_scripts_dir = os.path.join(cur_dir, 'tools', 'import_scripts')

    pyinstaller_dist = os.path.join(pyinstaller_root, 'dist')
    pyinstaller_work = os.path.join(pyinstaller_root, 'work')
    pyinstaller_spec = os.path.join(pyinstaller_root, 'spec')
    os.makedirs(pyinstaller_spec, exist_ok=True)

    pyinstaller_cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=Hammer5ToolsGUI',
        '--contents-directory=runtime',
        '--noupx',
        f'--distpath={pyinstaller_dist}',
        f'--workpath={pyinstaller_work}',
        f'--specpath={pyinstaller_spec}',

        '--hidden-import=vpk',
        '--collect-all=velopack',
        # Only win32com.client.Dispatch("Shell.Application") is used (addon_functions.py);
        # collect-all pulled in unrelated Pythonwin/pywin32 payload for nothing.
        '--hidden-import=win32com.client',
        '--exclude-module=win32ui',
        '--exclude-module=Pythonwin',
        # pyqtgraph.colormap has an optional try/except matplotlib import for a
        # colormap-listing feature we never call; PyInstaller's static scan still
        # follows it into the full matplotlib package otherwise.
        '--exclude-module=matplotlib',

        '--noconfirm',

        '--onedir',
        '--windowed',

        f'--paths={gui_python_root}',
        f'--paths={core_python_root}',
        '--hidden-import=hammer5tools_gui.resources_rc',
        '--collect-all=hammer5tools_gui',
        '--collect-all=hammer5tools_core',
        '--collect-all=keyvalues3',
        # Only OpenGL.GL is imported anywhere; collect-submodules (no data/binaries)
        # still catches PyOpenGL's lazy per-extension submodule loading.
        '--collect-submodules=OpenGL',
        '--collect-submodules=pycparser',

        '--hidden-import=PySide6.QtNetwork',
        '--hidden-import=PySide6.QtMultimedia',
        '--hidden-import=PySide6.QtMultimediaWidgets',
        '--hidden-import=cffi',
        '--collect-submodules=cffi',
        '--hidden-import=clr_loader',
        '--collect-submodules=clr_loader',
        '--optimize=0',
        f'--icon={os.path.join(gui_root, "appicon.ico")}',
        f'--add-data={os.path.join(gui_root, "appicon.ico")};.',
        f'--add-data={os.path.join(gui_root, "images")};images/',
        f'--add-data={os.path.join(gui_root, "styles")};styles/',
        f'--add-data={os.path.join(cur_dir, "version.json")};.',
        *[
            f'--add-data={os.path.join(cur_dir, "Hammer5Tools", folder)};defaults/{folder}'
            for folder in ('Hotkeys', 'Presets', 'SmartPropEditor', 'SoundEventEditor')
            if os.path.isdir(os.path.join(cur_dir, 'Hammer5Tools', folder))
        ],
        '--exclude-module=PyQt5',
        '--exclude-module=numba',
        '--exclude-module=scipy',
        '--exclude-module=pandas',
        '--exclude-module=tabulate',
        # Unused Qt addon modules (nothing in the codebase imports these); PySide6's
        # PyInstaller hook otherwise bundles Qt6Quick/Qml/Pdf regardless of usage.
        '--exclude-module=PySide6.QtQml',
        '--exclude-module=PySide6.QtQuick',
        '--exclude-module=PySide6.QtQuickWidgets',
        '--exclude-module=PySide6.QtQuick3D',
        '--exclude-module=PySide6.QtPdf',
        '--exclude-module=PySide6.QtPdfWidgets',
        '--exclude-module=PySide6.QtBluetooth',
        '--exclude-module=PySide6.QtNfc',
        '--exclude-module=PySide6.QtSensors',
        '--exclude-module=PySide6.QtSerialPort',
        '--exclude-module=PySide6.QtSerialBus',
        '--exclude-module=PySide6.QtPositioning',
        '--exclude-module=PySide6.QtLocation',
        '--exclude-module=PySide6.QtTextToSpeech',
        '--exclude-module=PySide6.QtWebEngineCore',
        '--exclude-module=PySide6.QtWebEngineWidgets',
        '--exclude-module=PySide6.QtWebEngineQuick',
        '--exclude-module=PySide6.QtWebSockets',
        '--exclude-module=PySide6.QtWebChannel',
        '--exclude-module=PySide6.QtCharts',
        '--exclude-module=PySide6.QtDataVisualization',
        '--exclude-module=PySide6.QtRemoteObjects',
        '--exclude-module=PySide6.QtDesigner',
        '--exclude-module=PySide6.QtHelp',
        '--exclude-module=PySide6.QtSql',
        '--exclude-module=PySide6.QtSpatialAudio',
        '--exclude-module=PySide6.QtScxml',
        '--exclude-module=PySide6.QtStateMachine',
        '--exclude-module=PySide6.QtHttpServer',
        '--exclude-module=PySide6.Qt3DCore',
        '--exclude-module=PySide6.Qt3DRender',
        '--exclude-module=PySide6.Qt3DAnimation',
        '--exclude-module=PySide6.Qt3DExtras',
        '--exclude-module=PySide6.Qt3DInput',
        '--exclude-module=PySide6.Qt3DLogic',
        external,
        *[
            f'--add-binary={path};smartprop_native'
            for path in smartprop_native_dlls
        ],
        f'--add-data={unreal_bridge_publish};unreal_bridge' if os.path.exists(unreal_bridge_publish) else '',
        f'--add-data={source_porter_publish};source_porter' if os.path.exists(source_porter_publish) else '',
        f'--add-data={bspsrc_dir};tools/bspsrc' if os.path.exists(bspsrc_dir) else '',
        f'--add-data={import_scripts_dir};tools/import_scripts' if os.path.exists(import_scripts_dir) else '',
        f'--add-data={ue_scripts_dir};tools/ue_scripts' if os.path.exists(ue_scripts_dir) else '',
        *( get_dotnet_runtime_data() if channel == 'stable' else [] ),
        f'--add-data={runtime_config_path};dotnet' if channel == 'stable' and os.path.exists(runtime_config_path) else '',
        os.path.join(gui_root, 'main.py')
    ]
    pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]

    if tables:
        lextab_path, yacctab_path = tables
        pyinstaller_cmd += [
            f'--add-data={lextab_path};pycparser',
            f'--add-data={yacctab_path};pycparser',
        ]
    
    build_environment = os.environ.copy()
    existing_python_path = build_environment.get('PYTHONPATH')
    python_roots = os.pathsep.join((gui_python_root, core_python_root))
    build_environment['PYTHONPATH'] = (
        python_roots + os.pathsep + existing_python_path
        if existing_python_path
        else python_roots
    )
    subprocess.run(pyinstaller_cmd, check=True, env=build_environment)


def stage_three_root_bundle(pyi_output: str, bundle_root: str) -> None:
    """Stage a PyInstaller onedir output under the immutable application root."""
    source = os.path.realpath(pyi_output)
    destination_root = os.path.realpath(bundle_root)
    if not os.path.isdir(source):
        raise FileNotFoundError(f"PyInstaller output is missing: {source}")
    if source == destination_root or destination_root.startswith(source + os.sep):
        raise ValueError("Bundle root must not be inside the PyInstaller output")
    os.makedirs(destination_root, exist_ok=True)
    app_root = os.path.join(destination_root, 'app')
    if os.path.exists(app_root):
        shutil.rmtree(app_root)
    try:
        shutil.move(source, app_root)
    except Exception:
        shutil.copytree(source, app_root)
    executable = os.path.join(app_root, 'Hammer5ToolsGUI.exe')
    runtime = os.path.join(app_root, 'runtime')
    if not os.path.isfile(executable) or not os.path.isdir(runtime):
        raise RuntimeError("Staged bundle does not contain app/Hammer5ToolsGUI.exe and app/runtime")



def build_hammer5_tools(fast=False, channel='stable') -> None:
    # Phase 0: cleanup moved to main() for thread safety
    build_app_pyinstaller(fast=fast, channel=channel)

    def _safe_rmtree(p):
        import stat
        def _onerror(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass
        for attempt in range(5):
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p, onerror=_onerror)
                elif os.path.exists(p):
                    os.remove(p)
                break
            except Exception:
                time.sleep(0.5)
        else:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)

    # Final distribution folder
    bundle_root = os.path.join(cur_dir, 'Hammer5Tools')
    # Safe cleanup: only remove build artifacts, keep data folders
    for item in ['app', '_internal']:
        path = os.path.join(bundle_root, item)
        if os.path.exists(path):
            _safe_rmtree(path)
    if not os.path.exists(bundle_root):
        os.makedirs(bundle_root)

    # Three-root layout: immutable app payload, bundled runtime, mutable userdata.
    # PyInstaller places its dependency payload under app/runtime.
    pyinstaller_dist = os.path.join(pyinstaller_root, 'dist')
    pyi_output = os.path.join(pyinstaller_dist, 'Hammer5ToolsGUI')
    if os.path.exists(pyi_output):
        stage_three_root_bundle(pyi_output, bundle_root)
        _safe_rmtree(pyinstaller_dist)

    # Ensure data folders are present in bundle_root (they should be if it's the source folder)
    template_dir = os.path.join(cur_dir, 'Hammer5Tools')
    data_folders = ['Hotkeys', 'Presets', 'SmartPropEditor', 'SoundEventEditor']
    for folder in data_folders:
        src = os.path.join(template_dir, folder)
        dst = os.path.join(bundle_root, folder)
        if os.path.exists(src) and src != dst:
            if os.path.exists(dst): shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"Copied data folder {folder} to bundle root")
        elif not os.path.exists(src):
            print(f"Warning: data folder {folder} missing from template")


def package_velopack(channel: str) -> str:
    """Create a local Velopack distribution using the release workflow contract."""
    bundle_root = os.path.join(cur_dir, 'Hammer5Tools')
    required_paths = [
        os.path.join(bundle_root, 'Hammer5Tools.exe'),
        os.path.join(bundle_root, 'app', 'Hammer5ToolsGUI.exe'),
        os.path.join(bundle_root, 'app', 'runtime'),
    ]
    missing = [path for path in required_paths if not os.path.exists(path)]
    if missing:
        raise FileNotFoundError(f"Cannot package incomplete bundle: {', '.join(missing)}")

    if channel == 'dev':
        build_number = os.environ.get('H5T_DEV_BUILD_NUMBER')
        if not build_number:
            build_number = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
        package_version = f"{app_version}-dev.{build_number}"
    else:
        package_version = app_version

    with open(os.path.join(bundle_root, 'version.txt'), 'w', encoding='utf-8', newline='\n') as version_file:
        version_file.write(f"{package_version}\n{channel}\n")

    packaging_root = os.path.join(build_root, 'packaging')
    os.makedirs(packaging_root, exist_ok=True)
    release_notes = os.path.join(packaging_root, f'{channel}-release-notes.md')
    if channel == 'dev':
        commits = subprocess.run(
            ['git', 'log', '-n', '5', '--pretty=format:* %s (%h)'],
            cwd=cur_dir,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        notes = f"### Recent Changes (Dev Build):\n\n{commits}\n"
    else:
        source_notes = os.path.join(cur_dir, 'RELEASE_NOTES.md')
        if os.path.isfile(source_notes):
            with open(source_notes, encoding='utf-8') as notes_file:
                notes = notes_file.read()
        else:
            notes = f"## Hammer5Tools {package_version}\n\nRelease {package_version}.\n"
    with open(release_notes, 'w', encoding='utf-8', newline='\n') as notes_file:
        notes_file.write(notes)

    tool_root = os.path.join(build_root, 'tools', 'velopack')
    velopack = os.path.join(tool_root, 'vpk.exe')
    if not os.path.isfile(velopack):
        os.makedirs(tool_root, exist_ok=True)
        subprocess.run(
            ['dotnet', 'tool', 'install', 'vpk', '--tool-path', tool_root],
            cwd=cur_dir,
            check=True,
        )

    output_root = os.path.join(build_root, 'dist')
    os.makedirs(output_root, exist_ok=True)
    command = [
        velopack,
        'pack',
        '--outputDir', output_root,
        '--packId', 'Hammer5Tools',
        '--packVersion', package_version,
        '--packDir', bundle_root,
        '--mainExe', 'Hammer5Tools.exe',
        '--icon', os.path.join(gui_root, 'appicon.ico'),
        '--channel', channel,
        '--noPortable',
        '--releaseNotes', release_notes,
    ]
    if channel == 'stable':
        command.extend(['--framework', 'net10.0-x64-desktop'])
    subprocess.run(command, cwd=cur_dir, check=True)
    print(f"Velopack {channel} distribution created in {output_root}")
    return output_root






def main() -> None:
    """Main function to parse arguments and execute build and packaging tasks."""
    parser = argparse.ArgumentParser(description="Build Hammer 5 Tools for Velopack.")
    parser.add_argument('--build-all', action='store_true', help="Build Hammer 5 Tools.")
    parser.add_argument('--build-app', action='store_true', help="Build only Hammer 5 Tools.")
    parser.add_argument('--build-libs', action='store_true', help="Build only Windows x64 .NET and native libraries.")
    parser.add_argument('--package', action='store_true', help="Create a Velopack distribution after a full build.")
    parser.add_argument('--fast', action='store_true', help="Use 0 level optimization.")
    channel_group = parser.add_mutually_exclusive_group()
    channel_group.add_argument('--stable', action='store_true', help="Build stable release (default).")
    channel_group.add_argument('--dev', action='store_true', help="Build dev release.")
    args = parser.parse_args()
    if args.package and not args.build_all:
        parser.error('--package requires --build-all')
    channel = 'dev' if args.dev else 'stable'


    overall_start_time = time.time()

    # ui_*.py and resources_rc.py are generated, not tracked in git.
    if args.build_all or args.build_app:
        stage_start_time = time.time()
        import compile_ui
        compile_ui.main(cur_dir)
        print_elapsed_time("Compile UI/resources", stage_start_time)

    stage_start_time = time.time()
    # Kill processes
    for p in ["Hammer5Tools.exe", "fileedit.exe"]:
        kill_process(p)



    print_elapsed_time("Kill processes", stage_start_time)

    results = []

    try:
        if args.build_all:
            stage_start_time = time.time()
            
            # Phase 0: Cleanup
            bundle_root = os.path.join(cur_dir, 'Hammer5Tools')
            if os.path.exists(bundle_root):
                for item in ['app', 'runtime', 'Hammer5Tools.exe', 'Hammer5ToolsGUI.exe', 'fileedit.exe', '_internal']:
                    path = os.path.join(bundle_root, item)
                    if os.path.exists(path):
                        if os.path.isdir(path): shutil.rmtree(path)
                        else: os.remove(path)

            # 1. Build Python Core
            build_hammer5_tools(fast=args.fast, channel=channel)
            
            # 2. Build C++ Launcher
            build_cpp("Hammer5ToolsLauncher", os.path.join(cur_dir, "Hammer5ToolsLauncher"), "Hammer5Tools")
            
            # Verify Launcher exists
            launcher_path = os.path.join(bundle_root, "Hammer5Tools.exe")
            if not os.path.exists(launcher_path):
                print(f"FATAL ERROR: Launcher was not found at {launcher_path}")
                sys.exit(1)
            
            elapsed_time = time.time() - stage_start_time
            results.append(["Sequential Build (Core + Launcher)", f"{elapsed_time:.2f} seconds"])

            if args.package:
                stage_start_time = time.time()
                output_root = package_velopack(channel)
                elapsed_time = time.time() - stage_start_time
                results.append([f"Velopack {channel} Distribution", f"{elapsed_time:.2f} seconds"])
                results.append(["Distribution Output", output_root])
            
        elif args.build_app:
            stage_start_time = time.time()
            build_hammer5_tools(fast=args.fast, channel=channel)
            elapsed_time = time.time() - stage_start_time
            results.append(["Hammer 5 Tools Build (Python)", f"{elapsed_time:.2f} seconds"])

        elif args.build_libs:
            stage_start_time = time.time()
            build_libraries()
            elapsed_time = time.time() - stage_start_time
            results.append(["Build Windows x64 Libraries (.NET / NativeAOT)", f"{elapsed_time:.2f} seconds"])

    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        raise

    overall_elapsed_time = time.time() - overall_start_time
    results.append(["Overall process", f"{overall_elapsed_time:.2f} seconds"])

    print(tabulate(results, headers=["Stage", "Elapsed Time"], tablefmt="grid"))



if __name__ == "__main__":
    main()
