import os
import re
import threading
from pathlib import Path
from typing import Generator, Tuple, Union

import gi
gi.require_version("GLib", "2.0")
from gi.repository import GLib

from caching import ReleaseData, MusicLibrary

# Common audio file extensions
AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.ape', '.alac'
}


class MusicScanner:
    """Music directory scanner."""

    def __init__(self, music_dir: Path, starred_checker=None):
        self.music_dir = music_dir
        self.starred_checker = starred_checker  # Function to check if path is starred
        self.cache = MusicLibrary(music_dir)

        # Scanning state
        self._scan_cancelled = False
        self._scan_total_estimated = 0
        self._scan_generator = None

        # Progress tracking
        self._scan_progress = 0.0
        self._scan_current_count = 0

    def cancel_scan(self):
        """Cancel any ongoing scanning operations."""
        self._scan_cancelled = True

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



    def _clean_release_title(self, title: str) -> str:
        """Clean up a release title by normalizing separators."""
        # Replace underscores with spaces
        title = re.sub(r'_', ' ', title)
        # Normalize multiple dashes
        title = re.sub(r'\-+', '-', title)
        # Normalize spaces around dashes
        title = re.sub(r'\s+\-\s+', '-', title)
        return title.strip()


class ScanningCoordinator:
    """Coordinates scanning operations with UI updates."""

    def __init__(self, window, scanner, progress_updater):
        self.window = window
        self.scanner = scanner
        self.progress_updater = progress_updater
        self._scan_cancelled = False

    def start_scanning(self):
        """Start the scanning process."""
        if not self.window._music_dir.exists():
            self.window._show_empty(
                title="Music Directory Not Found",
                description=f"Could not find music directory at {self.window._music_dir}",
            )
            return

        # Prevent duplicate loading
        if self.scanner.cache.is_background_scan_running():
            return

        # Try to load from cache first
        cache_loaded = self.scanner.cache.load_cache_in_background(
            progress_callback=self._update_cache_loading_progress,
            completion_callback=self._finalize_cache_loading,
            error_callback=self._handle_cache_error,
            converter_func=self.window._create_release_item_converter(),
            cancel_checker=lambda: self.scanner._scan_cancelled,
        )

        if not cache_loaded:
            # No valid cache, do a full scan
            self._initialize_scanning()
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()

    def _initialize_scanning(self):
        """Initialize the UI for progressive scanning."""
        self.window._all_releases = []
        self.window.remove_all_items()
        self.window.set_loading(True)
        self.progress_updater(0.0)  # Start with 0 progress
        # Initialize scanner state
        self.scanner.initialize_scanning()

    def _scan_music_directory(self):
        """Scan the music directory for audio files and create release items."""
        # Initialize and start the incremental scanning using the scanner
        self.scanner.initialize_scanning()
        self.scanner.start_incremental_scan()
        GLib.idle_add(self._continue_scanning)

    def _continue_scanning(self):
        """Continue incremental scanning - called on idle to prevent blocking."""
        result, is_done = self.scanner.continue_scanning()

        if is_done:
            # Scanning complete
            self._finalize_scanning_complete()
            return False  # Stop the idle callback

        if result is not None:
            # Handle progress updates
            if (
                isinstance(result, tuple)
                and len(result) == 2
                and result[0] == "progress"
            ):
                # Update progress in the UI (we're already in main thread)
                progress_fraction = result[1]
                self.progress_updater(progress_fraction)
            elif hasattr(result, "title"):  # ReleaseData object
                # If we got a new release, convert ReleaseData to ReleaseItem and add it
                converter = self.window._create_release_item_converter()
                release_item = converter(result)  # result is ReleaseData
                self._add_single_release(release_item)

        # Continue scanning on next idle
        return True

    def _add_single_release(self, release):
        """Add a single release to the UI immediately."""
        # Check if we already have this release path to prevent duplicates
        existing_paths = {r.path for r in self.window._all_releases}
        if release.path in existing_paths:
            return  # Skip duplicate

        # Add to our list (we'll sort later)
        self.window._all_releases.append(release)

        # Check if there's an active search query
        current_query = self.window.get_search_text().strip()

        # Check if star filter is active
        star_filter_active = (
            hasattr(self.window, "_star_filter_button")
            and self.window._star_filter_button.get_starred()
        )

        # Only add to UI if it matches current search (or no search active) and star filter
        should_show = (
            not current_query or current_query.lower() in release.title.lower()
        ) and (not star_filter_active or release.starred)
        if should_show:
            self.window.add_item(release)

        # Clear loading and show results on first item (regardless of search match)
        # This ensures we switch away from loading state once scanning finds anything
        # But keep the progress indicator visible during scanning
        if len(self.window._all_releases) == 1:
            self.window.set_loading(False)  # This switches from loading to results view
            # Keep progress visible during scanning with current fraction
            if hasattr(self.scanner, "_scan_progress") and self.scanner._scan_progress > 0:
                self.progress_updater(self.scanner._scan_progress)
            else:
                # Show minimal progress to indicate scanning is ongoing
                self.progress_updater(0.1)  # Small fraction to show activity

        # If this is the first item that matches search, make sure results are shown
        if should_show and self.window._item_store.get_n_items() == 1:
            self.window._show_results()

    def _update_cache_loading_progress(self, loaded, total, progress):
        """Update UI with cache loading progress."""
        # Update the progress widget with actual progress
        self.progress_updater(progress)
        return False

    def _finalize_cache_loading(self, all_releases):
        """Finalize cache loading on main thread."""
        # Ensure we don't duplicate if already loaded
        if self.window._all_releases:
            return False

        self.window._all_releases = all_releases
        self.window.set_loading(False)
        self.progress_updater(0.0)  # Hide progress when cache loading is complete

        # Clear any existing items to prevent duplicates
        self.window.remove_all_items()

        # Apply any active search or show all results
        current_query = self.window.get_search_text().strip()
        if current_query:
            self.window.on_search_changed(current_query)
        else:
            # Check if starred filter should be applied from settings
            starred_filter_active = self.window._settings.get_boolean("starred-filter-active")
            if starred_filter_active:
                # Apply starred filter to initial results
                starred_releases = [r for r in self.window._all_releases if r.starred]
                if starred_releases:
                    self.window._filter.start_batched_result_addition(starred_releases)
                else:
                    self.window._show_empty(
                        title="No Starred Releases",
                        description="Star some releases to see them here.",
                    )
            else:
                # Use batched loading for UI updates too
                self.window._filter.start_batched_result_addition(self.window._all_releases)

        # After cache is successfully loaded and UI updated,
        # start a background scan for any updates since the cache was created.
        if not self.scanner.cache.is_background_scan_running():
            # Convert ReleaseItems back to ReleaseData for the scanner
            def get_current_releases_data():
                from serialization import convert_release_items_to_data
                return convert_release_items_to_data(self.window._all_releases)

            current_releases = get_current_releases_data()
            self.scanner.cache.start_background_cache_update(
                current_releases, self._on_cache_update_complete
            )

        # Ensure main scanning progress is hidden since cache loading is complete
        self.progress_updater(0.0)

        return False  # Important for GLib.idle_add to not re-schedule this handler

    def _on_cache_update_complete(self, updated_releases):
        """Handle completion of background cache update."""
        # Convert ReleaseData back to ReleaseItems using the converter
        converter = self.window._create_release_item_converter()
        self.window._all_releases = [converter(rd) for rd in updated_releases]

        # Refresh UI with updated releases
        self.window._filter.refresh_ui_with_sorted_releases()
        return False

    def _handle_cache_error(self):
        """Handle cache loading error on main thread."""
        self.window.set_loading(False)
        self.progress_updater(0.0)
        self._clear_all_operations()
        # Fall back to full scan
        if not self.scanner.cache.is_background_scan_running():
            self._initialize_scanning()
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()
        return False

    def _finalize_scanning_complete(self):
        """Called when scanning is completely finished."""
        # Ensure progress is completely hidden
        self.progress_updater(0.0)  # Set fraction to 0 and hide

        # Only set loading to false if we have no releases yet
        # (it should already be false if we found any releases)
        if not self.window._all_releases:
            self.window.set_loading(False)
            self.window._show_empty(
                title="No Music Found",
                description=f"No audio files found in {self.window._music_dir}",
            )
        else:
            # Sort releases alphabetically and refresh the UI
            self.window._all_releases.sort(key=lambda r: r.title.lower())
            self.window._filter.refresh_ui_with_sorted_releases()

            # Save scan results to cache for faster next launch
            def save_cache():
                self.window.save_releases_to_cache()

            threading.Thread(target=save_cache, daemon=True).start()

    def _clear_all_operations(self):
        """Clear all ongoing operations to prevent race conditions."""
        self._scan_cancelled = True
        self.scanner.cancel_scan()
        self.progress_updater(0.0)

    def cancel_all_operations(self):
        """Cancel all scanning operations."""
        self._scan_cancelled = True
        self.scanner.cancel_scan()
        self._clear_all_operations()
