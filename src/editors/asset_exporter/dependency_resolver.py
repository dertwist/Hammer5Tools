import os

class DependencyResolver:

    def __init__(self, addon_content_path: str):
        self.addon_content_path = addon_content_path
        self._visited: set[str] = set()
        self.missing_deps: set[str] = set()

    def resolve(self, asset_path: str) -> list[str]:
        self._visited.clear()
        self.missing_deps.clear()
        self._walk(asset_path)
        return sorted(list(self._visited))

    def _walk(self, path: str):
        path = os.path.normpath(path)
        if path in self._visited or not os.path.isfile(path):
            return
        self._visited.add(path)
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.vmdl', '.vsmart', '.vmat', '.vpcf', '.vsndevts', '.vtex', '.vsnd'):
            self._parse_kv3_deps(path)

    def _parse_kv3_deps(self, path: str):
        import re
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            pattern = r'"([^"]+\.(?:vmdl|vsmart|vmat|vpcf|vsndevts|vtex|vsnd|txt|kv3|vmap|vpost)(?:_c)?)"'
            matches = re.findall(pattern, content, re.IGNORECASE)
            for m in matches:
                self._add_dep(m)
        except Exception as e:
            print(f"DependencyResolver: Error parsing {path}: {e}")

    def _add_dep(self, rel_path: str):
        if not rel_path:
            return
            
        # Handle compiled asset path mapping
        if rel_path.endswith('_c'):
            rel_path = rel_path[:-2]

        rel_path = rel_path.replace('//', '/').replace('\\', '/')
        item_path = os.path.join(self.addon_content_path, rel_path)
        item_path = os.path.normpath(item_path)
        if os.path.exists(item_path):
            self._walk(item_path)
        else:
            self.missing_deps.add(rel_path)
