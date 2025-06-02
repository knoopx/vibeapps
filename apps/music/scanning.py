import os
import re
import threading
from pathlib import Path
from typing import Generator, Tuple, Union
import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib
from caching import ReleaseData, MusicLibrary
AUDIO_EXTENSIONS = {'.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.ape', '.alac'}

class MusicScanner:

    def __init__(self, music_dir: Path, starred_checker=None):
        self.music_dir = music_dir
        self.starred_checker = starred_checker
        self.cache = MusicLibrary(music_dir)
        self._scan_cancelled = False
        self._scan_total_estimated = 0
        self._scan_generator = None
        self._scan_progress = 0.0
        self._scan_current_count = 0

    def cancel_scan(self):
        self._scan_cancelled = True

    def initialize_scanning(self):
        self._scan_generator = None
        self._scan_cancelled = False
        self._scan_progress = 0.0
        self._scan_current_count = 0

    def start_incremental_scan(self):
        self._scan_generator = self.scan_music_directory()
        return self._scan_generator

    def continue_scanning(self):
        if not hasattr(self, '_scan_generator') or self._scan_generator is None or self._scan_cancelled:
            return (None, True)
        try:
            result = next(self._scan_generator)
            if isinstance(result, tuple) and len(result) == 2 and (result[0] == 'progress'):
                self._scan_progress = result[1]
                return (result, False)
            elif result is not None:
                self._scan_current_count += 1
                return (result, False)
            else:
                return (None, False)
        except StopIteration:
            return (None, True)

    def get_scan_progress(self) -> float:
        return self._scan_progress

    def scan_music_directory(self) -> Generator[Union[ReleaseData, Tuple[str, float], None], None, None]:
        try:
            found_releases = set()
            dirs_processed = 0
            releases_found = 0
            total_dirs_estimated = 0
            for root, dirs, files in os.walk(self.music_dir, followlinks=True):
                total_dirs_estimated += 1
                if total_dirs_estimated > 10000:
                    break
            self._scan_total_estimated = total_dirs_estimated
            for root, dirs, files in os.walk(self.music_dir, followlinks=True):
                if self._scan_cancelled:
                    return
                root_path = Path(root)
                if any((part.startswith('.') for part in root_path.parts)):
                    continue
                try:
                    relative_path = root_path.relative_to(self.music_dir)
                    if len(relative_path.parts) > 10:
                        continue
                except ValueError:
                    continue
                audio_files = [f for f in files if Path(f).suffix.lower() in AUDIO_EXTENSIONS]
                if audio_files:
                    release_path = root_path
                    release_title = self._clean_release_title(release_path.name)
                    if release_path == self.music_dir:
                        continue
                    path_str = str(release_path)
                    if path_str not in found_releases:
                        found_releases.add(path_str)
                        new_release = ReleaseData(title=release_title, path=path_str, track_count=len(audio_files))
                        releases_found += 1
                        yield new_release
                dirs_processed += 1
                if dirs_processed % 10 == 0:
                    if self._scan_total_estimated > 0:
                        progress = min(dirs_processed / self._scan_total_estimated, 1.0)
                        yield ('progress', progress)
                    yield None
        except Exception as e:
            raise e

    def _clean_release_title(self, title: str) -> str:
        title = re.sub('_', ' ', title)
        title = re.sub('\\-+', '-', title)
        title = re.sub('\\s+\\-\\s+', '-', title)
        return title.strip()

class ScanningCoordinator:

    def __init__(self, window, scanner, progress_updater):
        self.window = window
        self.scanner = scanner
        self.progress_updater = progress_updater
        self._scan_cancelled = False

    def start_scanning(self):
        if not self.window._music_dir.exists():
            self.window._show_empty(title='Music Directory Not Found', description=f'Could not find music directory at {self.window._music_dir}')
            return
        if self.scanner.cache.is_background_scan_running():
            return
        cache_loaded = self.scanner.cache.load_cache_in_background(progress_callback=self._update_cache_loading_progress, completion_callback=self._finalize_cache_loading, error_callback=self._handle_cache_error, converter_func=self.window._create_release_item_converter(), cancel_checker=lambda: self.scanner._scan_cancelled)
        if not cache_loaded:
            self._initialize_scanning()
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()

    def _initialize_scanning(self):
        self.window._all_releases = []
        self.window.remove_all_items()
        self.window.set_loading(True)
        self.progress_updater(0.0)
        self.scanner.initialize_scanning()

    def _scan_music_directory(self):
        self.scanner.initialize_scanning()
        self.scanner.start_incremental_scan()
        GLib.idle_add(self._continue_scanning)

    def _continue_scanning(self):
        result, is_done = self.scanner.continue_scanning()
        if is_done:
            self._finalize_scanning_complete()
            return False
        if result is not None:
            if isinstance(result, tuple) and len(result) == 2 and (result[0] == 'progress'):
                progress_fraction = result[1]
                self.progress_updater(progress_fraction)
            elif hasattr(result, 'title'):
                converter = self.window._create_release_item_converter()
                release_item = converter(result)
                self._add_single_release(release_item)
        return True

    def _add_single_release(self, release):
        existing_paths = {r.path for r in self.window._all_releases}
        if release.path in existing_paths:
            return
        self.window._all_releases.append(release)
        current_query = self.window.get_search_text().strip()
        star_filter_active = hasattr(self.window, '_star_filter_button') and self.window._star_filter_button.get_starred()
        should_show = (not current_query or current_query.lower() in release.title.lower()) and (not star_filter_active or release.starred)
        if should_show:
            self.window.add_item(release)
        if len(self.window._all_releases) == 1:
            self.window.set_loading(False)
            if hasattr(self.scanner, '_scan_progress') and self.scanner._scan_progress > 0:
                self.progress_updater(self.scanner._scan_progress)
            else:
                self.progress_updater(0.1)
        if should_show and self.window._item_store.get_n_items() == 1:
            self.window._show_results()

    def _update_cache_loading_progress(self, loaded, total, progress):
        self.progress_updater(progress)
        return False

    def _finalize_cache_loading(self, all_releases):
        if self.window._all_releases:
            return False
        self.window._all_releases = all_releases
        self.window.set_loading(False)
        self.progress_updater(0.0)
        self.window.remove_all_items()
        current_query = self.window.get_search_text().strip()
        if current_query:
            self.window.on_search_changed(current_query)
        else:
            starred_filter_active = self.window._settings.get_boolean('starred-filter-active')
            if starred_filter_active:
                starred_releases = [r for r in self.window._all_releases if r.starred]
                if starred_releases:
                    self.window._filter.start_batched_result_addition(starred_releases)
                else:
                    self.window._show_empty(title='No Starred Releases', description='Star some releases to see them here.')
            else:
                self.window._filter.start_batched_result_addition(self.window._all_releases)
        if not self.scanner.cache.is_background_scan_running():

            def get_current_releases_data():
                from serialization import convert_release_items_to_data
                return convert_release_items_to_data(self.window._all_releases)
            current_releases = get_current_releases_data()
            self.scanner.cache.start_background_cache_update(current_releases, self._on_cache_update_complete)
        self.progress_updater(0.0)
        return False

    def _on_cache_update_complete(self, updated_releases):
        converter = self.window._create_release_item_converter()
        self.window._all_releases = [converter(rd) for rd in updated_releases]
        self.window._filter.refresh_ui_with_sorted_releases()
        return False

    def _handle_cache_error(self):
        self.window.set_loading(False)
        self.progress_updater(0.0)
        self._clear_all_operations()
        if not self.scanner.cache.is_background_scan_running():
            self._initialize_scanning()
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()
        return False

    def _finalize_scanning_complete(self):
        self.progress_updater(0.0)
        if not self.window._all_releases:
            self.window.set_loading(False)
            self.window._show_empty(title='No Music Found', description=f'No audio files found in {self.window._music_dir}')
        else:
            self.window._all_releases.sort(key=lambda r: r.title.lower())
            self.window._filter.refresh_ui_with_sorted_releases()

            def save_cache():
                self.window.save_releases_to_cache()
            threading.Thread(target=save_cache, daemon=True).start()

    def _clear_all_operations(self):
        self._scan_cancelled = True
        self.scanner.cancel_scan()
        self.progress_updater(0.0)

    def cancel_all_operations(self):
        self._scan_cancelled = True
        self.scanner.cancel_scan()
        self._clear_all_operations()