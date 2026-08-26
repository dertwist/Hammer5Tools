"""Fail fast on imports that will not resolve in a release build.

PyInstaller only warns about modules it cannot find, so a stray import of a
package that is not in requirements.txt (e.g. an IDE-autocompleted
``win32comext``) builds fine and crashes on first launch. Run this after
``pip install -r requirements.txt`` and before the build.

Static only: it parses the GUI and Python Core roots with ast and resolves each
top-level import root against the installed environment, without executing app code.
"""
import ast
import importlib.util
import os
import sys

REPO_DIR = os.path.abspath(os.path.dirname(__file__))
CUR_DIR = REPO_DIR
SOURCE_DIRS = (
    os.path.join(REPO_DIR, 'Hammer5ToolsGUI', 'gui'),
    os.path.join(REPO_DIR, 'Hammer5ToolsGUI', 'core'),
)
IMPORT_ROOTS = (
    os.path.join(REPO_DIR, 'Hammer5ToolsGUI'),
)

# .NET assemblies pythonnet materialises at runtime after clr.AddReference().
# They never exist as Python packages, so no static check can resolve them.
CLR_ASSEMBLIES = {'System', 'Datamodel', 'SourcePorter', 'UnrealBridge', 'ValveResourceFormat'}

# Only importable inside the Unreal Editor's embedded Python interpreter —
# gui/tools/ue_scripts run there, never inside this app's own process.
RUNTIME_ONLY_MODULES = {'unreal'}


def local_names() -> set:
    """Top-level names importable from the repo itself.

    The release build adds the Hammer5ToolsGUI root to ``sys.path``.
    """
    names = set()
    for root in (CUR_DIR, *IMPORT_ROOTS):
        for entry in os.listdir(root):
            if entry.endswith('.py'):
                names.add(entry[:-3])
            elif os.path.isdir(os.path.join(root, entry)):
                names.add(entry)
    return names


CATCHES_IMPORT_ERROR = {'ImportError', 'ModuleNotFoundError', 'Exception', 'BaseException'}


def handles_import_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:  # bare `except:`
        return True
    caught = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(isinstance(e, ast.Name) and e.id in CATCHES_IMPORT_ERROR for e in caught)


def import_roots(tree: ast.AST):
    """Yield (root_module, lineno, guarded) for every absolute import.

    An import inside a try block with an ImportError-catching handler is a
    deliberate fallback, not a missing dependency.
    """
    guarded = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(map(handles_import_error, node.handlers)):
            # The fallback in the except body is as deliberate as the try body.
            bodies = [node.body] + [h.body for h in node.handlers] + [node.orelse]
            for child in [stmt for body in bodies for stmt in body]:
                for sub in ast.walk(child):
                    guarded.add(id(sub))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split('.')[0], node.lineno, id(node) in guarded
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split('.')[0], node.lineno, id(node) in guarded


def resolvable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def self_test() -> None:
    """Guard the parser itself: it must flag bare imports and skip fallbacks."""
    found = set(import_roots(ast.parse(
        'import os.path\n'
        'from win32comext.shell.shellcon import X\n'
        'try:\n'
        '    from .commands import Y\n'
        'except ImportError:\n'
        '    from commands import Y\n'
        'try:\n'
        '    import optional_pkg\n'
        'except:\n'
        '    optional_pkg = None\n'
    )))
    flagged = {root for root, _, guarded in found if not guarded}
    assert flagged == {'os', 'win32comext'}, flagged


def main() -> int:
    self_test()
    skip = local_names() | set(sys.stdlib_module_names) | CLR_ASSEMBLIES | RUNTIME_ONLY_MODULES
    checked, missing = {}, []

    for source_dir in SOURCE_DIRS:
        for dirpath, dirnames, filenames in os.walk(source_dir):
            dirnames[:] = [d for d in dirnames if d != '__pycache__']
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                path = os.path.join(dirpath, filename)
                with open(path, encoding='utf-8-sig') as f:
                    source = f.read()
                try:
                    tree = ast.parse(source, filename=path)
                except SyntaxError as e:
                    missing.append(f"{os.path.relpath(path, CUR_DIR)}:{e.lineno}: syntax error: {e.msg}")
                    continue
                for root, lineno, guarded in import_roots(tree):
                    if root in skip or guarded:
                        continue
                    if os.path.exists(os.path.join(dirpath, root + '.py')) or os.path.isdir(
                        os.path.join(dirpath, root)
                    ):
                        continue
                    if checked.setdefault(root, resolvable(root)):
                        continue
                    missing.append(
                        f"{os.path.relpath(path, CUR_DIR)}:{lineno}: cannot resolve '{root}'"
                    )

    if missing:
        print(f"Unresolvable imports ({len(missing)}):", file=sys.stderr)
        for line in missing:
            print(f"  {line}", file=sys.stderr)
        print(
            "\nAdd the package to requirements.txt or remove the import.",
            file=sys.stderr,
        )
        return 1

    print(f"OK: {len(checked)} third-party import roots resolve.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
