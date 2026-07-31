import os
import json
import shutil
import zipfile
import tempfile
import urllib.request
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from src.common import user_data_dir

def get_plugins_dir() -> Path:
    """
    Returns the target installation directory:
    userdata/source2pluginloader/plugins/
    """
    plugins_dir = Path(user_data_dir) / "source2pluginloader" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    return plugins_dir

def get_metadata_file() -> Path:
    meta_dir = Path(user_data_dir) / "source2pluginloader"
    meta_dir.mkdir(parents=True, exist_ok=True)
    return meta_dir / "installed.json"

def get_installed_plugins_db() -> dict:
    meta_file = get_metadata_file()
    if meta_file.exists():
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_installed_plugins_db(db: dict):
    meta_file = get_metadata_file()
    try:
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        print(f"Failed to save installed plugins db: {e}")

def is_plugin_installed(repo_full_name: str) -> bool:
    db = get_installed_plugins_db()
    if repo_full_name in db:
        install_path = Path(db[repo_full_name].get("path", ""))
        if install_path.exists():
            return True
    # Fallback directory check
    safe_name = repo_full_name.replace("/", "_")
    target_dir = get_plugins_dir() / safe_name
    return target_dir.exists() and any(target_dir.iterdir())

def get_installed_plugin_path(repo_full_name: str) -> str:
    db = get_installed_plugins_db()
    if repo_full_name in db:
        return db[repo_full_name].get("path", "")
    safe_name = repo_full_name.replace("/", "_")
    return str(get_plugins_dir() / safe_name)

def uninstall_plugin(repo_full_name: str) -> bool:
    db = get_installed_plugins_db()
    safe_name = repo_full_name.replace("/", "_")
    target_dir = get_plugins_dir() / safe_name
    
    success = True
    if target_dir.exists():
        try:
            shutil.rmtree(target_dir)
        except Exception as e:
            print(f"Error removing plugin directory {target_dir}: {e}")
            success = False
            
    if repo_full_name in db:
        del db[repo_full_name]
        save_installed_plugins_db(db)
        
    return success


class PluginDownloadWorker(QThread):
    """
    Background worker thread to download a repository ZIP and extract it to
    userdata/source2pluginloader/plugins/<owner_repo>/
    """
    progress = Signal(int, str)  # (percent, status_message)
    finished = Signal(str, str)  # (repo_full_name, target_dir_path)
    failed = Signal(str, str)    # (repo_full_name, error_message)

    def __init__(self, repo_data: dict, token="", parent=None):
        super().__init__(parent)
        self.repo_data = repo_data
        self.full_name = repo_data.get("full_name", "")
        self.owner = repo_data.get("owner", {}).get("login", "")
        self.repo_name = repo_data.get("name", "")
        self.default_branch = repo_data.get("default_branch", "main")
        self.token = token.strip()

    def run(self):
        if not self.full_name or not self.owner or not self.repo_name:
            self.failed.emit(self.full_name, "Invalid repository metadata.")
            return

        self.progress.emit(10, f"Connecting to GitHub for {self.full_name}...")

        # Construct download URL (ZIP ball)
        zip_url = f"https://api.github.com/repos/{self.owner}/{self.repo_name}/zipball/{self.default_branch}"

        req = urllib.request.Request(zip_url)
        req.add_header("User-Agent", "Hammer5Tools-Source2PluginLoader")
        req.add_header("Accept", "application/vnd.github+json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")

        temp_zip_path = None
        try:
            self.progress.emit(30, "Downloading plugin archive...")
            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = response.headers.get('Content-Length')
                total_size = int(total_size) if total_size and total_size.isdigit() else 0

                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
                    temp_zip_path = tmp_file.name
                    downloaded = 0
                    block_size = 8192
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        tmp_file.write(buffer)
                        if total_size > 0:
                            pct = int(30 + (downloaded / total_size) * 40)
                            self.progress.emit(min(pct, 70), f"Downloading ({downloaded // 1024} KB)...")

            self.progress.emit(75, "Extracting repository files...")
            safe_folder_name = self.full_name.replace("/", "_")
            target_dir = get_plugins_dir() / safe_folder_name

            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            target_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                # GitHub zipballs extract into a single top-level directory (e.g. owner-repo-hash/)
                namelist = zip_ref.namelist()
                top_dirs = {name.split('/')[0] for name in namelist if '/' in name}

                if len(top_dirs) == 1:
                    top_prefix = list(top_dirs)[0] + '/'
                    for member in zip_ref.infolist():
                        if member.filename.startswith(top_prefix):
                            rel_path = member.filename[len(top_prefix):]
                            if not rel_path:
                                continue
                            dest = target_dir / rel_path
                            if member.is_dir():
                                dest.mkdir(parents=True, exist_ok=True)
                            else:
                                dest.parent.mkdir(parents=True, exist_ok=True)
                                with zip_ref.open(member) as source, open(dest, 'wb') as target:
                                    shutil.copyfileobj(source, target)
                else:
                    zip_ref.extractall(target_dir)

            self.progress.emit(95, "Updating installed plugins registry...")
            db = get_installed_plugins_db()
            db[self.full_name] = {
                "full_name": self.full_name,
                "owner": self.owner,
                "name": self.repo_name,
                "path": str(target_dir),
                "stargazers_count": self.repo_data.get("stargazers_count", 0),
                "description": self.repo_data.get("description", ""),
                "html_url": self.repo_data.get("html_url", ""),
                "installed_at": urllib.parse.quote(self.default_branch)
            }
            save_installed_plugins_db(db)

            self.progress.emit(100, f"Successfully installed {self.repo_name}!")
            self.finished.emit(self.full_name, str(target_dir))

        except Exception as e:
            self.failed.emit(self.full_name, f"Failed to download/install: {str(e)}")
        finally:
            if temp_zip_path and os.path.exists(temp_zip_path):
                try:
                    os.remove(temp_zip_path)
                except Exception:
                    pass
