#!/usr/bin/env python3

import os
import re
import threading
from pathlib import Path
from typing import List, Generator, Tuple, Union

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from caching import ReleaseData, MusicCache

# Common audio file extensions
AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.ape', '.alac'
}


class MusicScanner:
    """Music directory scanner."""

    def __init__(self, music_dir: Path, starred_checker=None):
        self.music_dir = music_dir
        self.starred_checker = starred_checker  # Function to check if path is starred
        self.cache = MusicCache(music_dir)

        # Scanning state
        self._scan_cancelled = False
        self._scan_total_estimated = 0
        self._background_scan_running = False
        self._scan_generator = None

        # Progress tracking
        self._scan_progress = 0.0
        self._scan_current_count = 0

    def cancel_scan(self):
        """Cancel any ongoing scanning operations."""
        self._scan_cancelled = True

    def is_background_scan_running(self) -> bool:
        """Check if background scan is running."""
        return self._background_scan_running

    def initialize_scanning(self):
        """Initialize scanning state."""
        self._scan_generator = None
        self._scan_cancelled = False
        self._scan_progress = 0.0
        self._scan_current_count = 0

    def start_incremental_scan(self):
        """Start incremental scanning and return the generator."""
        self._scan_generator = self.scan_music_directory()
        return self._scan_generator

    def continue_scanning(self):
        """Continue incremental scanning - returns next result or None if done."""
        if (not hasattr(self, '_scan_generator') or
            self._scan_generator is None or
            self._scan_cancelled):
            return None, True  # None result, scanning done

        try:
            result = next(self._scan_generator)

            # Handle progress updates
            if isinstance(result, tuple) and len(result) == 2 and result[0] == 'progress':
                self._scan_progress = result[1]
                return result, False  # Progress update, continue scanning
            elif result is not None:
                self._scan_current_count += 1
                return result, False  # Release found, continue scanning
            else:
                return None, False  # Control yield, continue scanning

        except StopIteration:
            # Scanning complete
            return None, True  # None result, scanning done

    def get_scan_progress(self) -> float:
        """Get current scan progress (0.0 to 1.0)."""
        return self._scan_progress

    def scan_music_directory(self) -> Generator[Union[ReleaseData, Tuple[str, float], None], None, None]:
        """
        Scan the music directory for audio files and yield release items.

        Yields:
            - ReleaseData objects for found releases
            - Tuple ('progress', float) for progress updates (0.0 to 1.0)
            - None for yielding control without new data
        """
        try:
            found_releases = set()  # Track paths we've already processed
            dirs_processed = 0
            releases_found = 0

            # Estimate total directories (rough estimation for progress)
            total_dirs_estimated = 0
            for root, dirs, files in os.walk(self.music_dir, followlinks=True):
                total_dirs_estimated += 1
                if total_dirs_estimated > 10000:  # Cap estimation to prevent long delays
                    break

            # Reset walk for actual processing
            self._scan_total_estimated = total_dirs_estimated

            # Walk through all directories in Music folder, following symlinks
            for root, dirs, files in os.walk(self.music_dir, followlinks=True):
                # Check for cancellation
                if self._scan_cancelled:
                    return

                root_path = Path(root)

                # Skip hidden directories and very deep nested paths
                if any(part.startswith('.') for part in root_path.parts):
                    continue

                # Skip paths that are too deep (> 10 levels from music dir) to avoid infinite recursion
                try:
                    relative_path = root_path.relative_to(self.music_dir)
                    if len(relative_path.parts) > 10:
                        continue
                except ValueError:
                    # Not relative to music dir, skip
                    continue

                # Count audio files in this directory
                audio_files = [f for f in files if Path(f).suffix.lower() in AUDIO_EXTENSIONS]

                if audio_files:
                    # Use the immediate parent directory as the release
                    release_path = root_path
                    release_title = self._clean_release_title(release_path.name)

                    # Skip if it's the root Music directory itself
                    if release_path == self.music_dir:
                        continue

                    # Only yield new releases we haven't seen before
                    path_str = str(release_path)
                    if path_str not in found_releases:
                        found_releases.add(path_str)
                        new_release = ReleaseData(
                            title=release_title,
                            path=path_str,
                            track_count=len(audio_files)
                        )
                        releases_found += 1
                        yield new_release

                dirs_processed += 1

                # Update progress and yield control every 10 directories
                if dirs_processed % 10 == 0:
                    # Update progress based on directories processed
                    if self._scan_total_estimated > 0:
                        progress = min(dirs_processed / self._scan_total_estimated, 1.0)
                        yield ('progress', progress)
                    yield None  # Just yield control, no new release

        except Exception as e:
            # Let the caller handle the error
            raise e

    def scan_for_cache_update(self) -> List[ReleaseData]:
        """
        Perform a full synchronous scan for cache update purposes.
        Returns a list of all found releases.
        """
        new_releases = []
        found_releases = set()

        try:
            for root, dirs, files in os.walk(self.music_dir, followlinks=True):
                if self._scan_cancelled:
                    break

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
                new_releases = self.scan_for_cache_update()

                # Check if scan results differ from current
                new_paths = {r.path for r in new_releases}
                current_paths = {r.path for r in current_releases}

                if new_paths != current_paths:
                    # Results changed, sort and update
                    new_releases.sort(key=lambda r: r.title.lower())

                    # Save updated cache
                    self.cache.save_to_cache(new_releases)

                    # Notify callback on main thread if provided
                    if update_callback:
                        GLib.idle_add(update_callback, new_releases)

            except Exception:
                pass
            finally:
                self._background_scan_running = False

        thread = threading.Thread(target=background_scan, daemon=True)
        thread.start()

    def _clean_release_title(self, title: str) -> str:
        """Clean up a release title by normalizing separators."""
        # Replace underscores with spaces
        title = re.sub(r'_', ' ', title)
        # Normalize multiple dashes
        title = re.sub(r'\-+', '-', title)
        # Normalize spaces around dashes
        title = re.sub(r'\s+\-\s+', '-', title)
        return title.strip()
