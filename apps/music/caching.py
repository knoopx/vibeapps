import json
import time
import threading
from pathlib import Path
from typing import Optional, List, Tuple, Callable, Any
from serialization import APP_ID, ReleaseData
from gi.repository import GLib
import os

# Common audio file extensions
AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.ape', '.alac'
}

CACHE_DIR = Path.home() / ".cache" / APP_ID
CACHE_FILE = CACHE_DIR / "releases_cache.json"
CACHE_VERSION = 1  # Increment when cache format changes


class MusicLibrary:
    def __init__(self, music_dir: Path):
        self.music_dir = music_dir
        self._background_scan_running = False

    def load_from_cache(self) -> Tuple[bool, Optional[List[ReleaseData]]]:
        """
        Load releases from cache if available and valid.

        Returns:
            Tuple of (cache_valid, releases_data)
            - cache_valid: True if cache was loaded successfully
            - releases_data: List of release data if cache is valid, None otherwise
        """
        try:
            if not CACHE_FILE.exists():
                return False, None

            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Validate cache format and version
            if (
                cache_data.get("version") != CACHE_VERSION
                or "music_dir" not in cache_data
                or "releases" not in cache_data
                or "last_modified" not in cache_data
            ):
                return False, None

            # Check if cache is for the same music directory
            if cache_data["music_dir"] != str(self.music_dir):
                return False, None

            # Check if music directory has been modified since cache was created
            music_dir_mtime = self.music_dir.stat().st_mtime
            cache_mtime = cache_data["last_modified"]

            # If music dir is newer than cache, cache is stale
            if music_dir_mtime > cache_mtime:
                return False, None

            # Convert cache data to ReleaseData objects
            releases = [ReleaseData.from_dict(item) for item in cache_data["releases"]]

            return True, releases

        except (json.decoder.JSONDecodeError, KeyError, OSError, FileNotFoundError):
            # If cache is corrupted or unreadable, remove it
            try:
                CACHE_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            return False, None

    def save_to_cache(self, releases: List[ReleaseData]) -> None:
        """Save releases to cache."""
        try:
            # Ensure cache directory exists
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

            # Prepare cache data
            cache_data = {
                "version": CACHE_VERSION,
                "music_dir": str(self.music_dir),
                "last_modified": time.time(),
                "releases": [release.to_dict() for release in releases],
            }

            # Write cache atomically
            temp_file = CACHE_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(CACHE_FILE)

        except (OSError, json.decoder.JSONDecodeError):
            # If caching fails, just ignore it but don't crash
            pass

    def load_cache_in_background(
        self,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        completion_callback: Optional[Callable[[List[ReleaseData]], None]] = None,
        error_callback: Optional[Callable[[], None]] = None,
        converter_func: Optional[Callable[[ReleaseData], Any]] = None,
        cancel_checker: Optional[Callable[[], bool]] = None,
    ) -> bool:
        """
        Load cache in background with batched processing and progress updates.

        Args:
            progress_callback: Called with (loaded, total, progress) for progress updates
            completion_callback: Called with final list of converted items when complete
            error_callback: Called if an error occurs
            converter_func: Function to convert ReleaseData to desired item type
            cancel_checker: Function that returns True if operation should be cancelled

        Returns:
            True if background loading started, False if cache is invalid
        """
        cache_valid, cached_releases = self.load_from_cache()
        if not cache_valid or not cached_releases:
            return False

        def background_load():
            try:
                batch_size = 1000
                all_items = []

                for i in range(0, len(cached_releases), batch_size):
                    # Check for cancellation
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

                    # Update progress every few batches
                    if progress_callback and (i == 0 or (i // batch_size) % 5 == 0):
                        progress = len(all_items) / len(cached_releases)
                        GLib.idle_add(
                            progress_callback,
                            len(all_items),
                            len(cached_releases),
                            progress,
                        )

                if all_items:
                    # Sort in background if items have a title attribute
                    if hasattr(all_items[0], "title"):
                        all_items.sort(key=lambda r: r.title.lower())

                    # Call completion callback on main thread
                    if completion_callback:
                        GLib.idle_add(completion_callback, all_items)
                else:
                    if error_callback:
                        GLib.idle_add(error_callback)

            except Exception:
                if error_callback:
                    GLib.idle_add(error_callback)

        # Start background thread
        thread = threading.Thread(target=background_load, daemon=True)
        thread.start()
        return True

    def start_background_cache_update(self, current_releases: List[ReleaseData],
                                     update_callback=None) -> None:
        """
        Start a background scan to update cache with any new releases.

        Args:
            current_releases: Currently known releases
            update_callback: Function to call with updated releases if changes found
        """
        if self._background_scan_running:
            return

        self._background_scan_running = True

        def background_scan():
            try:
                new_releases = self._scan_for_cache_update()

                # Check if scan results differ from current
                new_paths = {r.path for r in new_releases}
                current_paths = {r.path for r in current_releases}

                if new_paths != current_paths:
                    # Results changed, sort and update
                    new_releases.sort(key=lambda r: r.title.lower())

                    # Save updated cache
                    self.save_to_cache(new_releases)

                    # Notify callback on main thread if provided
                    if update_callback:
                        GLib.idle_add(update_callback, new_releases)

            except Exception:
                pass
            finally:
                self._background_scan_running = False

        thread = threading.Thread(target=background_scan, daemon=True)
        thread.start()

    def _scan_for_cache_update(self) -> List[ReleaseData]:
        """
        Perform a full synchronous scan for cache update purposes.
        Returns a list of all found releases.
        """
        new_releases = []
        found_releases = set()

        try:
            for root, dirs, files in os.walk(self.music_dir, followlinks=True):
                root_path = Path(root)

                # Skip hidden directories and very deep nested paths
                if any(part.startswith('.') for part in root_path.parts):
                    continue

                # Skip paths that are too deep
                try:
                    relative_path = root_path.relative_to(self.music_dir)
                    if len(relative_path.parts) > 10:
                        continue
                except ValueError:
                    continue

                # Count audio files
                audio_files = [f for f in files if Path(f).suffix.lower() in AUDIO_EXTENSIONS]

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
                            track_count=len(audio_files)
                        )
                        new_releases.append(new_release)

        except Exception:
            # Return what we have so far
            pass

        return new_releases

    def _clean_release_title(self, title: str) -> str:
        """Clean up a release title by normalizing separators."""
        import re
        # Replace underscores with spaces
        title = re.sub(r'_', ' ', title)
        # Normalize multiple dashes
        title = re.sub(r'\-+', '-', title)
        # Normalize spaces around dashes
        title = re.sub(r'\s+\-\s+', '-', title)
        return title.strip()

    def is_background_scan_running(self) -> bool:
        """Check if background scan is running."""
        return self._background_scan_running
