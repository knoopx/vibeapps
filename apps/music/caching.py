import json
import threading
from pathlib import Path
from typing import Optional, List, Tuple, Callable, Any
from serialization import APP_ID, ReleaseData
from gi.repository import GLib
import os

AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wma",
    ".ape",
    ".alac",
}
CACHE_DIR = Path.home() / ".cache" / APP_ID
CACHE_FILE = CACHE_DIR / "releases.json"


class MusicLibrary:

    def __init__(self, music_dir: Path):
        self.music_dir = music_dir
        self._background_scan_running = False

    def load_from_cache(self) -> Tuple[bool, Optional[List[ReleaseData]]]:
        try:
            if not CACHE_FILE.exists():
                return (False, None)
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                releases_data = json.load(f)
            releases = [ReleaseData.from_dict(item) for item in releases_data]
            return (True, releases)
        except (json.decoder.JSONDecodeError, KeyError, OSError, FileNotFoundError):
            try:
                CACHE_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            return (False, None)

    def save_to_cache(self, releases: List[ReleaseData]) -> None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            releases_data = [release.to_dict() for release in releases]
            temp_file = CACHE_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(releases_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(CACHE_FILE)
        except (OSError, json.decoder.JSONDecodeError):
            pass

    def load_cache_in_background(
        self,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        completion_callback: Optional[Callable[[List[ReleaseData]], None]] = None,
        error_callback: Optional[Callable[[], None]] = None,
        converter_func: Optional[Callable[[ReleaseData], Any]] = None,
        cancel_checker: Optional[Callable[[], bool]] = None,
    ) -> bool:
        cache_valid, cached_releases = self.load_from_cache()
        if not cache_valid or not cached_releases:
            return False

        def background_load():
            try:
                batch_size = 1000
                all_items = []
                for i in range(0, len(cached_releases), batch_size):
                    if cancel_checker and cancel_checker():
                        return
                    batch = cached_releases[i : i + batch_size]
                    batch_items = []
                    for release_data in batch:
                        if converter_func:
                            item = converter_func(release_data)
                        else:
                            item = release_data
                        batch_items.append(item)
                    all_items.extend(batch_items)
                    if progress_callback and (i == 0 or i // batch_size % 5 == 0):
                        progress = len(all_items) / len(cached_releases)
                        GLib.idle_add(
                            progress_callback,
                            len(all_items),
                            len(cached_releases),
                            progress,
                        )
                if all_items:
                    if hasattr(all_items[0], "title"):
                        all_items.sort(key=lambda r: r.title.lower())
                    if completion_callback:
                        GLib.idle_add(completion_callback, all_items)
                elif error_callback:
                    GLib.idle_add(error_callback)
            except Exception:
                if error_callback:
                    GLib.idle_add(error_callback)

        thread = threading.Thread(target=background_load, daemon=True)
        thread.start()
        return True

    def start_background_cache_update(
        self, current_releases: List[ReleaseData], update_callback=None
    ) -> None:
        if self._background_scan_running:
            return
        self._background_scan_running = True

        def background_scan():
            try:
                new_releases = self._scan_for_cache_update()
                new_paths = {r.path for r in new_releases}
                current_paths = {r.path for r in current_releases}
                if new_paths != current_paths:
                    new_releases.sort(key=lambda r: r.title.lower())
                    self.save_to_cache(new_releases)
                    if update_callback:
                        GLib.idle_add(update_callback, new_releases)
            except Exception:
                pass
            finally:
                self._background_scan_running = False

        thread = threading.Thread(target=background_scan, daemon=True)
        thread.start()

    def _scan_for_cache_update(self) -> List[ReleaseData]:
        new_releases = []
        found_releases = set()
        try:
            for root, dirs, files in os.walk(self.music_dir, followlinks=True):
                root_path = Path(root)
                if any((part.startswith(".") for part in root_path.parts)):
                    continue
                try:
                    relative_path = root_path.relative_to(self.music_dir)
                    if len(relative_path.parts) > 10:
                        continue
                except ValueError:
                    continue
                audio_files = [
                    f for f in files if Path(f).suffix.lower() in AUDIO_EXTENSIONS
                ]
                if audio_files:
                    if root_path == self.music_dir:
                        continue
                    path_str = str(root_path)
                    if path_str not in found_releases:
                        found_releases.add(path_str)
                        release_title = self._clean_release_title(root_path.name)
                        new_release = ReleaseData(
                            title=release_title,
                            path=path_str,
                            track_count=len(audio_files),
                        )
                        new_releases.append(new_release)
        except Exception:
            pass
        return new_releases

    def _clean_release_title(self, title: str) -> str:
        import re

        title = re.sub("_", " ", title)
        title = re.sub("\\-+", "-", title)
        title = re.sub("\\s+\\-\\s+", "-", title)
        return title.strip()

    def is_background_scan_running(self) -> bool:
        return self._background_scan_running
