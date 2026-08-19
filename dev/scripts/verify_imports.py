"""Fail fast on imports that will not resolve in a release build.

PyInstaller only warns about modules it cannot find, so a stray import of a
package that is not in requirements.txt (e.g. an IDE-autocompleted
``win32comext``) builds fine and crashes on first launch. Run this after
``pip install -r requirements.txt`` and before the build.

Static only: it parses ``src/`` with ast and resolves each top-level import
root against the installed environment, without executing app code.
"""
import ast
import importlib.util
import os
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CUR_DIR = REPO_DIR
SRC_DIR = os.path.join(REPO_DIR, 'src')

# .NET assemblies pythonnet materialises at runtime after clr.AddReference().
# They never exist as Python packages, so no static check can resolve them.
CLR_ASSEMBLIES = {'System', 'Datamodel', 'SourcePorter', 'UnrealBridge', 'ValveResourceFormat'}


def local_names() -> set:
    """Top-level names importable from the repo itself.

    The spec builds with pathex=['.', 'src'], so both roots are on sys.path.
    """
    names = set()
    for root in (CUR_DIR, SRC_DIR):
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
    skip = local_names() | set(sys.stdlib_module_names) | CLR_ASSEMBLIES
    checked, missing = {}, []

    for dirpath, dirnames, filenames in os.walk(SRC_DIR):
        dirnames[:] = [d for d in dirnames if d not in ('__pycache__', 'net_core')]
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
                # A module sitting next to this file: importable both frozen
                # (its package dir lands on sys.path) and under pytest.
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
