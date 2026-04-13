import os
from src.common import Kv3ToJson

class DependencyResolver:
    ASSET_DEPENDENCY_KEYS = [
        # vmdl / vsmart
        'm_refMeshes', 'm_refPhysicsData', 'model',
        # vmat
        'TextureColor', 'TextureNormal', 'TextureRoughness',
        'TextureMetalness', 'g_tColor', 'g_tNormal',
        # generic
        'material', 'mesh', 'texture', 'm_strPsd'
    ]

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
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # If it's pure binary or random data, kv3 parsing will fail, which is fine
            # We catch exceptions
            data = Kv3ToJson(content)
            if data:
                self._find_deps_in_dict(data)
        except Exception as e:
            print(f"DependencyResolver: Error parsing {path}: {e}")

    def _find_deps_in_dict(self, data):
        if isinstance(data, dict):
            for k, v in data.items():
                if k in self.ASSET_DEPENDENCY_KEYS and isinstance(v, str):
                    self._add_dep(v)
                else:
                    self._find_deps_in_dict(v)
        elif isinstance(data, list):
            for item in data:
                self._find_deps_in_dict(item)

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
