#!/usr/bin/env python3

import re
import gi
import os
import sys
import threading
import time
import json
from pathlib import Path
from typing import Optional

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Gtk, Adw, GLib, GObject, Gio, Pango
from picker_window import PickerWindow, PickerItem
from star_button import StarButton

APP_ID = "net.knoopx.music"

# Common audio file extensions
AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.ape', '.alac'
}

# Cache configuration
CACHE_DIR = Path.home() / ".cache" / "net.knoopx.music"
CACHE_FILE = CACHE_DIR / "releases_cache.json"
CACHE_VERSION = 1  # Increment when cache format changes

# Configuration directory for starred releases
CONFIG_DIR = Path.home() / ".config" / "net.knoopx.music"
STARRED_FILE = CONFIG_DIR / "starred.json"


class ReleaseItem(PickerItem):
    """Represents a music release (album/directory)."""
    __gtype_name__ = "ReleaseItem"

    title = GObject.Property(type=str, default="")
    path = GObject.Property(type=str, default="")
    track_count = GObject.Property(type=int, default=0)
    starred = GObject.Property(type=bool, default=False)

    def __init__(self, title: str, path: str, track_count: int = 0, starred: bool = False):
        super().__init__()
        self.title = title
        self.path = path
        self.track_count = track_count
        self.starred = starred


class MusicWindow(PickerWindow):
    """Music launcher window that shows releases/albums."""

    def __init__(self, **kwargs):
        # Initialize attributes before calling super().__init__
        self._all_releases = []
        self._music_dir = Path.home() / "Music"
        self._search_idle_id = 0  # For non-blocking search operations
        self._filter_idle_id = 0  # For non-blocking filtering operations
        self._scan_generator = None  # Track current scan generator
        self._scan_cancelled = False  # Flag to cancel scanning
        self._cache_loaded = False  # Flag to prevent duplicate loading
        self._background_scan_running = False  # Flag to prevent concurrent scans
        self._current_query = ""  # Track current search query for sync
        self._current_filter_state = None  # Track filter operation state
        self._current_result_state = None  # Track result addition state
        self._starred_releases = set()  # Store starred release basenames

        super().__init__(
            title="Music",
            search_placeholder="Search music...",
            **kwargs
        )

        # Add CSS for star button styling
        self._setup_css()

        # Load starred releases
        self._load_starred_releases()

    def _setup_css(self):
        """Setup CSS styling for the music window."""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(StarButton.get_css_style().encode())

        # Apply to the current display
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # Required abstract method implementations
    def get_item_type(self):
        return ReleaseItem

    def use_list_view(self):
        return True  # Use modern ListView

    def _load_starred_releases(self):
        """Load starred releases from starred.json."""
        try:
            if STARRED_FILE.exists():
                with open(STARRED_FILE, 'r', encoding='utf-8') as f:
                    starred_data = json.load(f)
                    self._starred_releases = set(starred_data.get('starred', []))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load starred releases: {e}")
            self._starred_releases = set()

    def _save_starred_releases(self):
        """Save starred releases to starred.json."""
        try:
            # Ensure config directory exists
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            starred_data = {
                'starred': sorted(list(self._starred_releases))
            }

            # Write starred file atomically
            temp_file = STARRED_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(starred_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(STARRED_FILE)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Failed to save starred releases: {e}")

    def _get_release_basename(self, release_path: str) -> str:
        """Get the basename of a release path."""
        return Path(release_path).name

    def _is_release_starred(self, release_path: str) -> bool:
        """Check if a release is starred."""
        basename = self._get_release_basename(release_path)
        return basename in self._starred_releases

    def _toggle_release_starred(self, release_path: str):
        """Toggle the starred status of a release."""
        basename = self._get_release_basename(release_path)
        if basename in self._starred_releases:
            self._starred_releases.remove(basename)
        else:
            self._starred_releases.add(basename)
        self._save_starred_releases()

    def _update_release_starred_status(self, release):
        """Update the starred status of a release item."""
        release.starred = self._is_release_starred(release.path)

    def _refresh_single_item(self, item):
        """Refresh a single item in the UI by triggering a rebind."""
        if not self.use_list_view():
            return  # Only implemented for ListView

        # Find the item's position in the store
        for i in range(self._item_store.get_n_items()):
            store_item = self._item_store.get_item(i)
            if store_item and store_item.path == item.path:
                # Notify the model that this item changed
                self._item_store.items_changed(i, 1, 1)
                break

    def load_initial_data(self):
        """Scan music directory for releases, using cache if available."""
        print("MusicWindow: load_initial_data called")
        if not self._music_dir.exists():
            self._show_empty(
                title="Music Directory Not Found",
                description=f"Could not find music directory at {self._music_dir}"
            )
            return

        # Prevent duplicate loading
        if self._cache_loaded or self._background_scan_running:
            return

        # Mark that we're starting to prevent concurrent loads
        self._cache_loaded = True
        print("MusicWindow: Attempting to load from cache...")
        # Try to load from cache first
        if self._load_from_cache():
            # Cache loading started successfully - background scan will be started
            # after cache loading completes in _finalize_cache_loading
            print("MusicWindow: Cache load initiated.")
            pass
        else:
            # No valid cache, reset flag and do a full scan
            print("MusicWindow: No valid cache found or cache load failed. Starting full scan.")
            self._cache_loaded = False
            self._initialize_scanning()
            self._background_scan_running = True
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()
        print("MusicWindow: load_initial_data finished")

    def _scan_music_directory(self):
        """Scan the music directory for audio files and create release items."""
        print("MusicWindow: _scan_music_directory started")
        def scan_generator():
            """Generator that yields each new release as it's found."""
            try:
                found_releases = set()  # Track paths we've already processed
                dirs_processed = 0
                releases_found = 0
                start_time = time.time()
                last_yield_time = start_time

                # Walk through all directories in Music folder, following symlinks
                for root, dirs, files in os.walk(self._music_dir, followlinks=True):
                    # Check for cancellation
                    if self._scan_cancelled:
                        return

                    root_path = Path(root)

                    # Skip hidden directories and very deep nested paths
                    if any(part.startswith('.') for part in root_path.parts):
                        continue

                    # Skip paths that are too deep (> 10 levels from music dir) to avoid infinite recursion
                    try:
                        relative_path = root_path.relative_to(self._music_dir)
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
                        release_title = release_path.name
                        release_title = re.sub(r'_', ' ', release_title)
                        release_title = re.sub(r'\-+', '-', release_title)
                        release_title = re.sub(r'\s+\-\s+', '-', release_title)
                        release_title = release_title.strip()

                        # Skip if it's the root Music directory itself
                        if release_path == self._music_dir:
                            continue

                        # Only yield new releases we haven't seen before
                        path_str = str(release_path)
                        if path_str not in found_releases:
                            found_releases.add(path_str)
                            new_release = ReleaseItem(
                                title=release_title,
                                path=path_str,
                                track_count=len(audio_files),
                                starred=self._is_release_starred(path_str)
                            )
                            releases_found += 1
                            yield new_release

                    dirs_processed += 1
                    current_time = time.time()

                    # Yield control every 10 directories OR every 100ms to prevent overwhelming
                    if dirs_processed % 10 == 0 or (current_time - last_yield_time) > 0.1:
                        last_yield_time = current_time
                        yield None  # Just yield control, no new release

            except Exception as e:
                GLib.idle_add(self._show_error, f"Error scanning music directory: {str(e)}")
                print(f"MusicWindow: Error in scan_generator: {e}")
                return

        # Start the incremental scanning directly
        self._scan_generator = scan_generator()
        GLib.idle_add(self._continue_scanning)
        print("MusicWindow: _scan_music_directory finished, incremental scan scheduled")

    def _update_releases(self, releases):
        """Update the UI with scanned releases."""
        self._all_releases = releases
        self.remove_all_items()

        for release in self._all_releases:
            self.add_item(release)

        if self._all_releases:
            self._show_results()
        else:
            self._show_empty(
                title="No Music Found",
                description=f"No audio files found in {self._music_dir}"
            )

    def _load_from_cache(self) -> bool:
        """Load releases from cache if available and valid."""
        print("MusicWindow: _load_from_cache called")
        try:
            if not CACHE_FILE.exists():
                print("MusicWindow: Cache file does not exist.")
                return False

            # Check file size first - if it's huge, we know it'll be slow
            file_size = CACHE_FILE.stat().st_size

            # Quick validation of cache file before loading
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                # For very large files (>50MB), start async loading immediately
                # The json.load() call below (or in _load_large_cache_async)
                # will handle actual JSON validation.
                if file_size > 50 * 1024 * 1024:  # 50MB
                    print("MusicWindow: Large cache file detected, starting async load.")
                    self.set_loading(True)
                    threading.Thread(
                        target=self._load_large_cache_async,
                        args=(str(CACHE_FILE),),
                        daemon=True
                    ).start()
                    return True

                print("MusicWindow: Loading cache data from file.")
                cache_data = json.load(f)

            # Validate cache format and version
            if (cache_data.get('version') != CACHE_VERSION or
                'music_dir' not in cache_data or
                'releases' not in cache_data or
                'last_modified' not in cache_data):
                print("MusicWindow: Cache data validation failed (version, keys).")
                return False

            # Check if cache is for the same music directory
            if cache_data['music_dir'] != str(self._music_dir):
                print("MusicWindow: Cache is for a different music directory.")
                return False

            # Check if music directory has been modified since cache was created
            music_dir_mtime = self._music_dir.stat().st_mtime
            cache_mtime = cache_data['last_modified']

            # If music dir is newer than cache, cache is stale
            if music_dir_mtime > cache_mtime:
                print("MusicWindow: Music directory modified since cache creation, cache is stale.")
                return False

            # Always load asynchronously for consistency and performance
            print("MusicWindow: Cache is valid, starting background load.")
            self.set_loading(True)
            # Start background loading
            threading.Thread(
                target=self._load_cache_in_background,
                args=(cache_data['releases'],),
                daemon=True
            ).start()
            return True

        except (json.decoder.JSONDecodeError, KeyError, OSError, FileNotFoundError) as e:
            print(f"MusicWindow: Error loading from cache: {e}")
            # If cache is corrupted or unreadable, remove it
            try:
                CACHE_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def _load_large_cache_async(self, cache_file_path):
        """Load very large cache files completely asynchronously."""
        print(f"MusicWindow: _load_large_cache_async started for {cache_file_path}")
        try:
            with open(cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            print("MusicWindow: Large cache file read.")
            # Basic validation
            if (cache_data.get('version') != CACHE_VERSION or
                'music_dir' not in cache_data or
                'releases' not in cache_data):
                print("MusicWindow: Large cache data validation failed.")
                GLib.idle_add(self._handle_cache_error)
                return

            # Check music directory
            if cache_data['music_dir'] != str(self._music_dir):
                print("MusicWindow: Large cache is for a different music directory.")
                GLib.idle_add(self._handle_cache_error)
                return

            # Check if stale
            music_dir_mtime = self._music_dir.stat().st_mtime
            cache_mtime = cache_data.get('last_modified', 0)
            if music_dir_mtime > cache_mtime:
                print("MusicWindow: Large cache is stale.")
                GLib.idle_add(self._handle_cache_error)
                return

            # Process in background
            print("MusicWindow: Processing large cache in background.")
            self._load_cache_in_background(cache_data['releases'])

        except Exception as e:
            print(f"MusicWindow: Error loading large cache async: {e}")
            GLib.idle_add(self._handle_cache_error)
        print("MusicWindow: _load_large_cache_async finished.")

    def _load_cache_in_background(self, releases_data):
        """Load large cache in background with batched UI updates."""
        print(f"MusicWindow: _load_cache_in_background started with {len(releases_data)} items.")
        try:
            # Process releases in batches
            batch_size = 1000
            all_releases = []

            for i in range(0, len(releases_data), batch_size):
                if self._scan_cancelled:
                    return

                batch = releases_data[i:i + batch_size]
                batch_releases = []

                for release_data in batch:
                    # Cache validity, including directory mtime, is checked before this function.
                    # We assume cached paths are valid; _scan_and_update_cache will reconcile later.
                    release = ReleaseItem(
                        title=release_data['title'],
                        path=release_data['path'],
                        track_count=release_data['track_count'],
                        starred=self._is_release_starred(release_data['path'])
                    )
                    batch_releases.append(release)

                all_releases.extend(batch_releases)

                # Update UI with progress every few batches
                if i == 0 or (i // batch_size) % 5 == 0:
                    GLib.idle_add(self._update_cache_loading_progress, len(all_releases), len(releases_data))
                    print(f"MusicWindow: Cache loading progress: {len(all_releases)}/{len(releases_data)}")

            if all_releases:
                # Sort in background
                print("MusicWindow: Sorting cached releases.")
                all_releases.sort(key=lambda r: r.title.lower())

                # Update main thread
                print("MusicWindow: Scheduling finalization of cache loading.")
                GLib.idle_add(self._finalize_cache_loading, all_releases)
            else:
                print("MusicWindow: No releases found in cache data, handling empty cache.")
                GLib.idle_add(self._handle_empty_cache)

        except Exception as e:
            print(f"MusicWindow: Error in _load_cache_in_background: {e}")
            GLib.idle_add(self._handle_cache_error)
        print("MusicWindow: _load_cache_in_background finished.")

    def _update_cache_loading_progress(self, loaded, total):
        """Update UI with cache loading progress."""
        # Could show progress in status or title
        # For now, just ensure we stay in loading state
        self.set_loading(True)
        return False

    def _finalize_cache_loading(self, all_releases):
        """Finalize cache loading on main thread."""
        print(f"MusicWindow: _finalize_cache_loading called with {len(all_releases)} releases.")
        # Ensure we don't duplicate if already loaded
        if self._all_releases:
            print("MusicWindow: Releases already loaded, skipping finalize.")
            return False

        self._all_releases = all_releases
        self.set_loading(False)

        # Clear any existing items to prevent duplicates
        self.remove_all_items()

        # Apply any active search or show all results
        current_query = self.get_search_text().strip()
        if current_query:
            self.on_search_changed(current_query)
        else:
            # Use batched loading for UI updates too
            self._start_batched_result_addition(self._all_releases)

        # After cache is successfully loaded and UI updated,
        # start a background scan for any updates since the cache was created.
        # This fulfills the comment in load_initial_data.
        if not self._background_scan_running:
            self._background_scan_running = True
            print("MusicWindow: Starting background scan for cache updates after initial load.")
            thread = threading.Thread(target=self._scan_and_update_cache)
            thread.daemon = True
            thread.start()
        else:
            print("MusicWindow: Background scan already running or not needed.")

        print("MusicWindow: _finalize_cache_loading finished.")
        return False # Important for GLib.idle_add to not re-schedule this handler

    def _handle_empty_cache(self):
        """Handle empty cache on main thread."""
        self.set_loading(False)
        self._show_empty(
            title="No Music Found",
            description=f"No audio files found in {self._music_dir}"
        )
        return False

    def _handle_cache_error(self):
        """Handle cache loading error on main thread."""
        print("MusicWindow: _handle_cache_error called.")
        self.set_loading(False)
        self._cache_loaded = False  # Reset flag so we can try full scan
        self._clear_all_operations()
        # Fall back to full scan
        if not self._background_scan_running:
            self._initialize_scanning()
            self._background_scan_running = True
            print("MusicWindow: Cache error, falling back to full scan.")
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()
        return False

    def _save_to_cache(self):
        """Save current releases to cache."""
        try:
            # Ensure cache directory exists
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

            # Prepare cache data
            cache_data = {
                'version': CACHE_VERSION,
                'music_dir': str(self._music_dir),
                'last_modified': time.time(),
                'releases': []
            }

            # Add release data
            for release in self._all_releases:
                cache_data['releases'].append({
                    'title': release.title,
                    'path': release.path,
                    'track_count': release.track_count
                })

            # Write cache atomically
            temp_file = CACHE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(CACHE_FILE)

        except (OSError, json.decoder.JSONDecodeError) as e:
            # If caching fails, just log it but don't crash
            print(f"Warning: Failed to save cache: {e}")

    def _scan_and_update_cache(self):
        """Scan music directory and update cache in background."""
        print("MusicWindow: _scan_and_update_cache started.")
        # Perform scan to check for new/removed releases
        new_releases = []
        found_releases = set()

        try:
            for root, dirs, files in os.walk(self._music_dir, followlinks=True):
                if self._scan_cancelled:
                    return

                root_path = Path(root)

                # Skip hidden directories and very deep nested paths
                if any(part.startswith('.') for part in root_path.parts):
                    continue

                # Skip paths that are too deep
                try:
                    relative_path = root_path.relative_to(self._music_dir)
                    if len(relative_path.parts) > 10:
                        continue
                except ValueError:
                    continue

                # Count audio files
                audio_files = [f for f in files if Path(f).suffix.lower() in AUDIO_EXTENSIONS]

                if audio_files:
                    if root_path == self._music_dir:
                        continue

                    path_str = str(root_path)
                    if path_str not in found_releases:
                        found_releases.add(path_str)

                        release_title = root_path.name
                        release_title = re.sub(r'_', ' ', release_title)
                        release_title = re.sub(r'\-+', '-', release_title)
                        release_title = re.sub(r'\s+\-\s+', '-', release_title)

                        new_release = ReleaseItem(
                            title=release_title,
                            path=path_str,
                            track_count=len(audio_files),
                            starred=self._is_release_starred(path_str)
                        )
                        new_releases.append(new_release)

            # Check if scan results differ from cache
            new_paths = {r.path for r in new_releases}
            cached_paths = {r.path for r in self._all_releases}

            if new_paths != cached_paths:
                # Results changed, update UI and cache
                print(f"MusicWindow: Cache changed. Old: {len(cached_paths)}, New: {len(new_paths)}. Updating UI and saving cache.")
                self._all_releases = new_releases
                self._all_releases.sort(key=lambda r: r.title.lower())

                # Update UI on main thread
                GLib.idle_add(self._refresh_ui_with_sorted_releases)

                # Save updated cache
                self._save_to_cache()
                print("MusicWindow: Cache updated and saved.")
            else:
                print("MusicWindow: No changes found during background scan.")

        except Exception as e:
            print(f"MusicWindow: Warning: Background scan failed: {e}")
        finally:
            # Reset the background scan flag
            print("MusicWindow: _scan_and_update_cache finished.")
            self._background_scan_running = False

    def on_search_changed(self, query: str):
        """Filter releases based on search query."""
        # Cancel any pending operations and clear state
        if hasattr(self, '_search_idle_id') and self._search_idle_id > 0:
            GLib.source_remove(self._search_idle_id)
            self._search_idle_id = 0
        if hasattr(self, '_filter_idle_id') and self._filter_idle_id > 0:
            GLib.source_remove(self._filter_idle_id)
            self._filter_idle_id = 0

        # Clear any ongoing filter state to prevent stale results
        if hasattr(self, '_current_filter_state'):
            self._current_filter_state = None
        if hasattr(self, '_current_result_state'):
            self._current_result_state = None

        # Track current query to validate results
        self._current_query = query.strip()

        # Clear UI immediately for responsive feel
        self.remove_all_items()

        # Get star filter state
        star_filter_active = hasattr(self, '_star_filter_button') and self._star_filter_button.get_starred()

        # Handle empty query quickly
        if not query:
            # Apply star filter if active
            releases_to_show = self._all_releases
            if star_filter_active:
                releases_to_show = [r for r in self._all_releases if r.starred]

            # For large collections, use batched addition even for "show all"
            if len(releases_to_show) > 100:
                self._start_batched_result_addition(releases_to_show)
            else:
                # For small collections, add all at once
                for release in releases_to_show:
                    self.add_item(release)
                if releases_to_show:
                    self._show_results()
                else:
                    if star_filter_active:
                        self._show_empty(
                            title="No Starred Music Found",
                            description="No starred releases match your criteria."
                        )
                    else:
                        self._show_empty(
                            title="No Music Found",
                            description=f"No audio files found in {self._music_dir}"
                        )
            return

        # For non-empty queries, filter efficiently
        query_lower = query.lower()

        # Simple filtering for small collections (< 100 items)
        if len(self._all_releases) < 100:
            filtered_releases = [
                release for release in self._all_releases
                if query_lower in release.title.lower() and
                (not star_filter_active or release.starred)
            ]
            self._apply_search_results(filtered_releases, query)
        else:
            # Use batched filtering for large collections
            self._start_batched_filtering(query_lower, query, star_filter_active)

    def _start_batched_filtering(self, query_lower, original_query, star_filter_active=False):
        """Start batched filtering for large collections."""
        self._current_filter_state = {
            'query_lower': query_lower,
            'original_query': original_query,
            'star_filter_active': star_filter_active,
            'filtered_releases': [],
            'current_index': 0,
            'batch_size': 100  # Smaller batches for better responsiveness
        }

        self._filter_idle_id = GLib.idle_add(self._filter_next_batch)

    def _filter_next_batch(self):
        """Filter the next batch of releases."""
        # Check if filter state was cleared (search changed)
        if not hasattr(self, '_current_filter_state') or self._current_filter_state is None:
            self._filter_idle_id = 0
            return False

        state = self._current_filter_state

        # Validate that we haven't exceeded bounds
        if state['current_index'] >= len(self._all_releases):
            self._filter_idle_id = 0
            return False

        end_index = min(state['current_index'] + state['batch_size'], len(self._all_releases))

        # Process this batch
        for i in range(state['current_index'], end_index):
            release = self._all_releases[i]
            if (state['query_lower'] in release.title.lower() and
                (not state.get('star_filter_active', False) or release.starred)):
                state['filtered_releases'].append(release)

        state['current_index'] = end_index

        # Continue processing or finish
        if state['current_index'] < len(self._all_releases):
            return True  # Continue on next idle
        else:
            # Filtering complete - verify query hasn't changed
            if hasattr(self, '_current_query') and state['original_query'] == self._current_query:
                self._apply_search_results(state['filtered_releases'], state['original_query'])
            self._filter_idle_id = 0
            self._current_filter_state = None
            return False

    def _apply_search_results(self, filtered_releases, query):
        """Apply search results to the UI efficiently."""
        # Handle empty results immediately
        if not filtered_releases:
            if query:
                self._show_empty(
                    title=f"No Results for '{query}'",
                    description="Try a different search term."
                )
            else:
                self._show_empty(
                    title="No Music Found",
                    description=f"No audio files found in {self._music_dir}"
                )
            return

        # For large result sets, add items in batches to prevent UI freezing
        if len(filtered_releases) > 100:
            self._start_batched_result_addition(filtered_releases)
        else:
            # For small result sets, add all at once
            for release in filtered_releases:
                self.add_item(release)
            self._show_results()

    def _start_batched_result_addition(self, filtered_releases):
        """Start batched addition of search results for large result sets."""
        self._current_result_state = {
            'filtered_releases': filtered_releases,
            'current_index': 0,
            'batch_size': 50  # Add 50 items at a time
        }

        # Start adding results immediately
        self._add_result_batch()

    def _add_result_batch(self):
        """Add the next batch of search results."""
        # Check if result state was cleared (search changed)
        if not hasattr(self, '_current_result_state') or self._current_result_state is None:
            return False

        state = self._current_result_state

        # Validate bounds
        if state['current_index'] >= len(state['filtered_releases']):
            self._current_result_state = None
            return False

        end_index = min(state['current_index'] + state['batch_size'], len(state['filtered_releases']))

        # Add this batch of items
        for i in range(state['current_index'], end_index):
            self.add_item(state['filtered_releases'][i])

        # Show results after first batch
        if state['current_index'] == 0:
            self._show_results()

        state['current_index'] = end_index

        # Continue processing or finish
        if state['current_index'] < len(state['filtered_releases']):
            # Schedule next batch on idle
            GLib.idle_add(self._add_result_batch)
            return False  # Don't continue this idle callback
        else:
            # All results added
            self._current_result_state = None
            return False

    def on_item_activated(self, item):
        """Open release directory with amberol."""
        if item and item.path:
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.SEARCH_PATH_FROM_ENVP
                | Gio.SubprocessFlags.STDERR_PIPE
                | Gio.SubprocessFlags.STDOUT_PIPE
            )
            # Launch process detached from our window
            try:
                launcher.spawnv(["amberol", item.path])
                # Keep the music browser open after launching Amberol
            except GLib.Error as e:
                print(f"Failed to launch Amberol: {e.message}")
                # Fallback to xdg-open if amberol is not available
                try:
                    launcher.spawnv(["xdg-open", item.path])
                    # Keep the music browser open after fallback launch
                except GLib.Error as e:
                    print(f"Error opening music directory: {e.message}")

    # ListView methods
    def setup_list_item(self, list_item):
        """Setup UI for each release item."""
        # Create main container
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12
        )

        # Star button
        star_button = StarButton(starred=False)
        star_button.connect('star-toggled', self._on_star_button_toggled)
        main_box.append(star_button)

        # Content box for title and info
        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            hexpand=True
        )

        # Release title
        title_label = Gtk.Label(
            halign=Gtk.Align.START,
            xalign=0,
            wrap=False,
            single_line_mode=True,
            ellipsize=Pango.EllipsizeMode.END
        )
        title_label.add_css_class("heading")

        # Track count and path info
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        track_count_label = Gtk.Label(
            halign=Gtk.Align.START,
            xalign=0
        )
        track_count_label.add_css_class("dim-label")
        track_count_label.add_css_class("caption")

        info_box.append(track_count_label)

        content_box.append(title_label)
        content_box.append(info_box)
        main_box.append(content_box)

        list_item.set_child(main_box)

    def bind_list_item(self, list_item, item):
        """Bind release data to list item."""
        if not item:
            return

        main_box = list_item.get_child()
        if not main_box:
            return

        # Get star button (first child)
        star_button = main_box.get_first_child()
        if not star_button:
            return

        # Get content box (second child)
        content_box = star_button.get_next_sibling()
        if not content_box:
            return

        # Get title label (first child of content box)
        title_label = content_box.get_first_child()
        if not title_label:
            return

        # Get info box (second child of content box)
        info_box = title_label.get_next_sibling()
        if not info_box:
            return

        # Get track count label (first child of info box)
        track_count_label = info_box.get_first_child()
        if not track_count_label:
            return

        # Update star button state and connect to item
        star_button.set_starred(item.starred)
        # Store item reference on the button for the toggle handler
        star_button.item = item

        # Set content efficiently
        title_label.set_markup(f"<b>{GLib.markup_escape_text(item.title)}</b>")
        track_text = f"{item.track_count} track{'s' if item.track_count != 1 else ''}"
        track_count_label.set_text(track_text)

    # Context menu support
    def get_context_menu_actions(self) -> dict:
        """Return context menu actions for releases."""
        return {
            "toggle_star": "on_toggle_star_action",
            "open_release": "on_open_release_action",
            "reveal_in_files": "on_reveal_in_files_action",
            "trash_release": "on_trash_release_action"
        }

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        """Return context menu model for releases."""
        if not item:
            return None

        menu_model = Gio.Menu.new()

        # Star/Unstar action
        star_label = "Unstar" if item.starred else "Star"
        menu_model.append(star_label, "context.toggle_star")

        menu_model.append("Open with Amberol", "context.open_release")
        menu_model.append("Reveal in Files", "context.reveal_in_files")
        menu_model.append("Move to Trash", "context.trash_release")
        return menu_model

    # Context menu action handlers
    def on_toggle_star_action(self, action, param):
        """Toggle star status for the selected release."""
        selected_item = self.get_selected_item()
        if selected_item:
            self._toggle_release_starred(selected_item.path)
            # Update the item's starred status
            selected_item.starred = self._is_release_starred(selected_item.path)
            # Refresh the UI to show the updated star
            self._refresh_single_item(selected_item)

    def on_open_release_action(self, action, param):
        """Open release with amberol (same as default action)."""
        selected_item = self.get_selected_item()
        if selected_item:
            self.on_item_activated(selected_item)

    def on_reveal_in_files_action(self, action, param):
        """Reveal release directory in file manager."""
        selected_item = self.get_selected_item()
        if selected_item and selected_item.path:
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.SEARCH_PATH_FROM_ENVP
                | Gio.SubprocessFlags.STDERR_PIPE
                | Gio.SubprocessFlags.STDOUT_PIPE
            )
            try:
                # Use xdg-open to open the directory in the file manager
                launcher.spawnv(["xdg-open", selected_item.path])
            except GLib.Error as e:
                print(f"Error revealing directory: {e.message}")

    def on_trash_release_action(self, action, param):
        """Move release directory to trash."""
        selected_item = self.get_selected_item()
        if not selected_item or not selected_item.path:
            return

        # Create confirmation dialog
        dialog = Adw.MessageDialog.new(
            self,
            f"Move '{selected_item.title}' to Trash?"
        )
        dialog.set_body(f"This will move the entire directory and all its contents to trash.\n\nPath: {selected_item.path}")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("trash", "Move to Trash")
        dialog.set_response_appearance("trash", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        dialog.connect("response", self._on_trash_dialog_response, selected_item)
        dialog.present()

    def _on_trash_dialog_response(self, dialog, response, item):
        """Handle trash confirmation dialog response."""
        if response == "trash":
            try:
                # Use gio trash command to move to trash
                file = Gio.File.new_for_path(item.path)
                file.trash(None)

                # Remove from our list and refresh
                self._all_releases = [r for r in self._all_releases if r.path != item.path]
                self.on_search_changed(self.get_search_text())

            except Exception as e:
                error_dialog = Adw.MessageDialog.new(
                    self,
                    "Error Moving to Trash"
                )
                error_dialog.set_body(f"Could not move '{item.title}' to trash:\n{str(e)}")
                error_dialog.add_response("ok", "OK")
                error_dialog.set_default_response("ok")
                error_dialog.present()

    # Status page customization
    def get_empty_icon(self) -> str:
        return "multimedia-player-symbolic"

    def get_loading_icon(self) -> str:
        return "multimedia-player-symbolic"

    def get_empty_title(self) -> str:
        return "No Music Found"

    def get_empty_description(self) -> str:
        return "Add some music to your Music directory and search for it here."

    # Header bar customization
    def get_header_bar_left_widgets(self) -> list:
        """Return star filter button for the left side of header bar."""
        # Create star button for filtering
        self._star_filter_button = StarButton(starred=False)
        self._star_filter_button.set_tooltip_text("Show only starred releases")
        self._star_filter_button.connect('star-toggled', self._on_star_filter_toggled)

        return [self._star_filter_button]

    def _on_star_filter_toggled(self, star_button, starred):
        """Handle star filter button toggle."""
        # Re-apply current search with star filter
        current_query = self.get_search_text()
        self.on_search_changed(current_query)

    def _initialize_scanning(self):
        """Initialize the UI for progressive scanning."""
        self._all_releases = []
        self._scan_generator = None
        self._scan_cancelled = False  # Reset cancellation flag
        self._cache_loaded = False   # Reset cache flag
        self.remove_all_items()
        self.set_loading(True)

    def _continue_scanning(self):
        """Continue incremental scanning - called on idle to prevent blocking."""
        if (not hasattr(self, '_scan_generator') or
            self._scan_generator is None or
            self._scan_cancelled):
            return False  # Stop the idle callback

        try:
            # Get next release or control yield
            result = next(self._scan_generator)

            # If we got a new release, add it immediately
            if result is not None:
                self._add_single_release(result)

            # Continue scanning on next idle
            return True

        except StopIteration:
            # Scanning complete
            self._finalize_scanning_complete()
            return False  # Stop the idle callback

    def _add_single_release(self, release):
        """Add a single release to the UI immediately."""
        # Check if we already have this release path to prevent duplicates
        existing_paths = {r.path for r in self._all_releases}
        if release.path in existing_paths:
            return  # Skip duplicate

        # Add to our list (we'll sort later)
        self._all_releases.append(release)

        # Check if there's an active search query
        current_query = self.get_search_text().strip()

        # Check if star filter is active
        star_filter_active = hasattr(self, '_star_filter_button') and self._star_filter_button.get_starred()

        # Only add to UI if it matches current search (or no search active) and star filter
        should_show = (not current_query or current_query.lower() in release.title.lower()) and \
                      (not star_filter_active or release.starred)
        if should_show:
            self.add_item(release)

        # Clear loading and show results on first item (regardless of search match)
        # This ensures we switch away from loading state once scanning finds anything
        if len(self._all_releases) == 1:
            self.set_loading(False)  # This switches from loading to results view

        # If this is the first item that matches search, make sure results are shown
        if should_show and self._item_store.get_n_items() == 1:
            self._show_results()

    def _refresh_ui_with_sorted_releases(self):
        """Refresh the UI with sorted releases."""
        # Clear current UI items
        self.remove_all_items()

        # Check if there's an active search query
        current_query = self.get_search_text().strip()

        # Check if star filter is active
        star_filter_active = hasattr(self, '_star_filter_button') and self._star_filter_button.get_starred()

        if not current_query:
            # No search active - add all releases (filtered by star if needed)
            releases_to_show = self._all_releases
            if star_filter_active:
                releases_to_show = [r for r in self._all_releases if r.starred]

            if len(releases_to_show) > 100:
                self._start_batched_result_addition(releases_to_show)
            else:
                for release in releases_to_show:
                    self.add_item(release)
                if releases_to_show:
                    self._show_results()
        else:
            # Search is active - filter and add matching releases
            query_lower = current_query.lower()
            if len(self._all_releases) < 100:
                # Small collection - filter directly
                filtered_releases = [
                    release for release in self._all_releases
                    if query_lower in release.title.lower() and
                    (not star_filter_active or release.starred)
                ]
                self._apply_search_results(filtered_releases, current_query)
            else:
                # Large collection - use batched filtering
                self._start_batched_filtering(query_lower, current_query, star_filter_active)

    def _finalize_scanning_complete(self):
        """Called when scanning is completely finished."""
        # Only set loading to false if we have no releases yet
        # (it should already be false if we found any releases)
        if not self._all_releases:
            self.set_loading(False)
            self._show_empty(
                title="No Music Found",
                description=f"No audio files found in {self._music_dir}"
            )
        else:
            # Sort releases alphabetically and refresh the UI
            self._all_releases.sort(key=lambda r: r.title.lower())
            self._refresh_ui_with_sorted_releases()

            # Save scan results to cache for faster next launch
            threading.Thread(target=self._save_to_cache, daemon=True).start()

    def on_close_request(self):
        """Handle window close request - cancel any ongoing scanning."""
        self._scan_cancelled = True
        self._clear_all_operations()
        return False  # Allow window to close

    def _clear_all_operations(self):
        """Clear all ongoing operations to prevent race conditions."""
        # Cancel any pending search operations
        if hasattr(self, '_search_idle_id') and self._search_idle_id > 0:
            GLib.source_remove(self._search_idle_id)
            self._search_idle_id = 0
        if hasattr(self, '_filter_idle_id') and self._filter_idle_id > 0:
            GLib.source_remove(self._filter_idle_id)
            self._filter_idle_id = 0

        # Clear filter and result states to prevent stale operations
        self._current_filter_state = None
        self._current_result_state = None
        self._current_query = ""

        # Reset flags
        self._scan_cancelled = True
        self._cache_loaded = False
        self._background_scan_running = False

    def _on_star_button_toggled(self, star_button, starred):
        """Handle star button toggle events from the UI."""
        # Get the item reference stored on the button
        item = getattr(star_button, 'item', None)
        if not item:
            return

        # Toggle the release starred status
        self._toggle_release_starred(item.path)
        # Update the item's starred property
        item.starred = self._is_release_starred(item.path)

        # Ensure button state matches the actual starred state
        # (in case there was any discrepancy)
        star_button.set_starred(item.starred)

class MusicApplication(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        """Activate the application."""
        window = MusicWindow(application=self)
        window.present()


def main():
    """Entry point."""
    app = MusicApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
