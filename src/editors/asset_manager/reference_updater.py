import os

class ReferenceUpdater:
    SCANNABLE_EXTS = {'.vmdl', '.vsmart', '.vmat', '.vpcf', '.vsndevts', '.vsnd'}

    def __init__(self, addon_content_path: str):
        self.addon_content_path = addon_content_path

    def update_references(self, old_rel: str, new_rel: str) -> list[str]:
        modified = []
        old_rel = old_rel.replace('\\', '/')
        new_rel = new_rel.replace('\\', '/')
        for root, _, files in os.walk(self.addon_content_path):
            for f in files:
                if os.path.splitext(f)[1].lower() not in self.SCANNABLE_EXTS:
                    continue
                abs_path = os.path.join(root, f)
                try:
                    with open(abs_path, 'r', encoding='utf-8', errors='ignore') as file:
                        text = file.read()
                    if old_rel in text:
                        new_text = text.replace(old_rel, new_rel)
                        with open(abs_path, 'w', encoding='utf-8') as file:
                            file.write(new_text)
                        modified.append(abs_path)
                except Exception as e:
                    print(f"Error updating references in {abs_path}: {e}")
        return modified
