import os
import re

class ReferenceUpdater:
    SCANNABLE_EXTS = {'.vmdl', '.vsmart', '.vmat', '.vpcf', '.vsndevts', '.vsnd', '.vmap', '.vpost', '.vanim', '.vseq', '.vphys'}

    def __init__(self, addon_content_path: str):
        self.addon_content_path = addon_content_path

    @staticmethod
    def _compile(renames: dict):
        """One alternation over every old path, longest first.

        Longest-first so a path that is a prefix of another cannot shadow it, and
        a single pass rather than chained str.replace calls so a rename whose
        *output* matches another rename's input can't be applied twice.
        """
        keys = sorted(renames, key=len, reverse=True)
        if not keys:
            return None, {}
        return re.compile('|'.join(re.escape(k) for k in keys)), renames

    def _apply(self, text: str, pattern, renames: dict) -> str:
        return pattern.sub(lambda m: renames[m.group(0)], text)

    def _update_vmap_references(self, abs_path: str, renames: dict) -> bool:
        from hammer5tools_core.bridge import CoreBridge

        result = CoreBridge.instance().rewrite_vmap_references(abs_path, renames)
        for diagnostic in result.diagnostics:
            print(f"Warning: {diagnostic}")
        return result.changed

    def find_referencing(self, renames: dict) -> list[str]:
        """Dry run: which files hold any of the old paths, without touching them.

        A byte substring search, not a DMX load: the preview only has to name the
        files, and parsing every map here would cost as much as the move itself.
        """
        needles = [k.replace('\\', '/').encode('utf-8') for k in renames if k]
        if not needles:
            return []

        hits = []
        for root, _, files in os.walk(self.addon_content_path):
            for f in files:
                if os.path.splitext(f)[1].lower() not in self.SCANNABLE_EXTS:
                    continue
                abs_path = os.path.join(root, f)
                try:
                    with open(abs_path, 'rb') as file:
                        buf = file.read()
                except OSError:
                    continue
                if any(n in buf for n in needles):
                    hits.append(abs_path)
        return hits

    def update_references(self, old_rel: str, new_rel: str) -> list[str]:
        """Single rename. Prefer update_references_batch when moving more than one
        file: this walks the whole addon and reloads every vmap per call."""
        return self.update_references_batch({old_rel: new_rel})

    def update_references_batch(self, renames: dict) -> list[str]:
        """Apply many renames in one pass.

        A per-file loop costs one full addon walk and one DMX load/save of every
        map for each file moved, which does not finish on a real asset library -
        reorganising a few hundred props is thousands of reloads of a map that
        may be tens of MB. Here every path is rewritten in a single visit.
        """
        renames = {k.replace('\\', '/'): v.replace('\\', '/') for k, v in renames.items()}
        pattern, renames = self._compile(renames)
        if pattern is None:
            return []

        modified = []
        for root, _, files in os.walk(self.addon_content_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext not in self.SCANNABLE_EXTS:
                    continue
                abs_path = os.path.join(root, f)
                try:
                    if ext == '.vmap':
                        if self._update_vmap_references(abs_path, renames):
                            modified.append(abs_path)
                    else:
                        with open(abs_path, 'r', encoding='utf-8', errors='ignore', newline='') as file:
                            text = file.read()
                        new_text = self._apply(text, pattern, renames)
                        if new_text != text:
                            with open(abs_path, 'w', encoding='utf-8', newline='') as file:
                                file.write(new_text)
                            modified.append(abs_path)
                except Exception as e:
                    print(f"Error updating references in {abs_path}: {e}")
        return modified
