import json
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap
from src.common import user_data_dir

def get_cache_dir() -> Path:
    cache_dir = Path(user_data_dir) / "source2pluginloader"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def get_cache_file_path() -> Path:
    return get_cache_dir() / "cache.json"

def load_disk_cache() -> dict:
    cache_file = get_cache_file_path()
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading disk cache: {e}")
    return {}

def save_disk_cache(data: dict):
    cache_file = get_cache_file_path()
    try:
        data["_cached_at"] = time.time()
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving disk cache: {e}")

class GitHubSearchWorker(QThread):
    """
    Asynchronous worker thread to query the GitHub Search Repositories API.
    Saves and reads persistent cache to conserve GitHub API quota.
    """
    search_finished = Signal(dict)
    search_failed = Signal(str)

    def __init__(self, topic="blender-addon", query="", sort_by="stars", page=1, token="", force_refresh=False, parent=None):
        super().__init__(parent)
        self.topic = topic.strip()
        self.query = query.strip()
        self.sort_by = sort_by
        self.page = page
        self.token = token.strip()
        self.force_refresh = force_refresh

    def run(self):
        # Build search query string
        q_parts = []
        if self.topic:
            q_parts.append(f"topic:{self.topic}")
        if self.query:
            q_parts.append(self.query)
        
        q_str = " ".join(q_parts) if q_parts else "blender-addon"
        sort_param = self.sort_by if self.sort_by in ("stars", "forks", "updated") else "stars"
        url = (
            f"https://api.github.com/search/repositories"
            f"?q={urllib.parse.quote(q_str)}&sort={sort_param}&order=desc&per_page=30&page={self.page}"
        )

        # Check persistent disk cache unless force_refresh is requested
        if not self.force_refresh:
            disk_cache = load_disk_cache()
            cached_query_data = disk_cache.get(url)
            if cached_query_data:
                cached_query_data["_is_from_cache"] = True
                self.search_finished.emit(cached_query_data)
                return

        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "Hammer5Tools-Source2PluginLoader")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                body = response.read().decode('utf-8')
                data = json.loads(body)

                data["_rate_limit_remaining"] = response.headers.get("X-RateLimit-Remaining", "N/A")
                data["_rate_limit_reset"] = response.headers.get("X-RateLimit-Reset", "N/A")
                data["_is_from_cache"] = False

                # Save to disk cache
                disk_cache = load_disk_cache()
                disk_cache[url] = data
                save_disk_cache(disk_cache)

                self.search_finished.emit(data)
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            if e.code == 403:
                error_msg += " (GitHub API rate limit exceeded. Set a GitHub token in settings)."
            
            # If rate limited, fallback to disk cache if available
            disk_cache = load_disk_cache()
            cached_query_data = disk_cache.get(url)
            if cached_query_data:
                cached_query_data["_is_from_cache"] = True
                cached_query_data["_rate_limit_error"] = error_msg
                self.search_finished.emit(cached_query_data)
            else:
                self.search_failed.emit(error_msg)
        except urllib.error.URLError as e:
            # Fallback to cache on network offline
            disk_cache = load_disk_cache()
            cached_query_data = disk_cache.get(url)
            if cached_query_data:
                cached_query_data["_is_from_cache"] = True
                self.search_finished.emit(cached_query_data)
            else:
                self.search_failed.emit(f"Network Error: {e.reason}")
        except Exception as e:
            self.search_failed.emit(f"Error fetching data: {str(e)}")


class GitHubReadmeWorker(QThread):
    """
    Asynchronous worker thread to fetch raw README content for a repository.
    """
    readme_finished = Signal(str)
    readme_failed = Signal(str)

    def __init__(self, owner, repo, token="", parent=None):
        super().__init__(parent)
        self.owner = owner
        self.repo = repo
        self.token = token.strip()

    def run(self):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/readme"
        req = urllib.request.Request(url)
        req.add_header("Accept", "application/vnd.github.raw+json")
        req.add_header("User-Agent", "Hammer5Tools-Source2PluginLoader")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8', errors='replace')
                self.readme_finished.emit(content)
        except Exception as e:
            self.readme_failed.emit(f"Could not load README: {str(e)}")


class ImageLoaderWorker(QThread):
    """
    Asynchronous worker thread to load remote image assets (avatars/thumbnails).
    """
    image_loaded = Signal(str, QPixmap)  # (url, pixmap)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        if not self.url:
            return
        try:
            req = urllib.request.Request(self.url)
            req.add_header("User-Agent", "Hammer5Tools-Source2PluginLoader")
            with urllib.request.urlopen(req, timeout=8) as response:
                data = response.read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    self.image_loaded.emit(self.url, pixmap)
        except Exception:
            pass
