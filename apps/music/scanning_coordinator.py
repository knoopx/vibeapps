import threading
import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music import MusicWindow


class ScanningCoordinator:
    def __init__(self, window: "MusicWindow") -> None:
        self.window = window
        self._scan_cancelled = False

    def start_scanning(self) -> None:
        if not self.window._music_dir.exists():
            self.window._show_empty(
                title="Music Directory Not Found",
                description=f"Could not find music directory at {self.window._music_dir}",
            )
            return
        if self.window._scanner.cache.is_background_scan_running():
            return
        cache_loaded = self.window._scanner.cache.load_cache_in_background(
            progress_callback=self._update_cache_loading_progress,
            completion_callback=self._finalize_cache_loading,
            error_callback=self._handle_cache_error,
            converter_func=self.window._create_release_item_converter(),
            cancel_checker=lambda: self.window._scanner._scan_cancelled,
        )
        if not cache_loaded:
            self._initialize_scanning()
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()

    def _initialize_scanning(self) -> None:
        self.window._all_releases = []
        self.window.remove_all_items()
        self.window.set_loading(True)
        self.window._update_progress(0.0)
        self.window._scanner.initialize_scanning()

    def _scan_music_directory(self) -> None:
        self.window._scanner.initialize_scanning()
        self.window._scanner.start_incremental_scan()
        GLib.idle_add(self._continue_scanning)

    def _continue_scanning(self) -> bool:
        result, is_done = self.window._scanner.continue_scanning()
        if is_done:
            self._finalize_scanning_complete()
            return False
        if result is not None:
            if (
                isinstance(result, tuple)
                and len(result) == 2
                and (result[0] == "progress")
            ):
                progress_fraction = result[1]
                self.window._update_progress(progress_fraction)
            elif hasattr(result, "title"):
                converter = self.window._create_release_item_converter()
                release_item = converter(result)
                self._add_single_release(release_item)
        return True

    def _add_single_release(self, release) -> None:
        existing_paths = {r.path for r in self.window._all_releases}
        if release.path in existing_paths:
            return
        self.window._all_releases.append(release)
        current_query = self.window.get_search_text().strip()
        star_filter_active = (
            hasattr(self.window, "_star_filter_button")
            and self.window._star_filter_button.get_starred()
        )
        should_show = (
            not current_query or current_query.lower() in release.title.lower()
        ) and (not star_filter_active or release.starred)
        if should_show:
            self.window.add_item(release)
        if len(self.window._all_releases) == 1:
            self.window.set_loading(False)
            if (
                hasattr(self.window._scanner, "_scan_progress")
                and self.window._scanner._scan_progress > 0
            ):
                self.window._update_progress(self.window._scanner._scan_progress)
            else:
                self.window._update_progress(0.1)
        if should_show and self.window._item_store.get_n_items() == 1:
            self.window._show_results()

    def _update_cache_loading_progress(self, loaded, total, progress) -> bool:
        self.window._update_progress(progress)
        return False

    def _finalize_cache_loading(self, all_releases) -> bool:
        if self.window._all_releases:
            return False
        self.window._all_releases = all_releases
        self.window.set_loading(False)
        self.window._update_progress(0.0)
        self.window.remove_all_items()
        current_query = self.window.get_search_text().strip()
        if current_query:
            self.window.on_search_changed(current_query)
        else:
            starred_filter_active = self.window._settings.get_boolean(
                "starred-filter-active"
            )
            if starred_filter_active:
                starred_releases = [r for r in self.window._all_releases if r.starred]
                if starred_releases:
                    self.window._filter.start_batched_result_addition(starred_releases)
                else:
                    self.window._show_empty(
                        title="No Starred Releases",
                        description="Star some releases to see them here.",
                    )
            else:
                self.window._filter.start_batched_result_addition(
                    self.window._all_releases
                )
        if not self.window._scanner.cache.is_background_scan_running():

            def get_current_releases_data():
                from serialization import convert_release_items_to_data

                return convert_release_items_to_data(self.window._all_releases)

            current_releases = get_current_releases_data()
            self.window._scanner.cache.start_background_cache_update(
                current_releases, self._on_cache_update_complete
            )
        self.window._update_progress(0.0)
        return False

    def _on_cache_update_complete(self, updated_releases) -> bool:
        converter = self.window._create_release_item_converter()
        self.window._all_releases = [converter(rd) for rd in updated_releases]
        self.window._filter.refresh_ui_with_sorted_releases()
        return False

    def _handle_cache_error(self) -> bool:
        self.window.set_loading(False)
        self.window._update_progress(0.0)
        self._clear_all_operations()
        if not self.window._scanner.cache.is_background_scan_running():
            self._initialize_scanning()
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()
        return False

    def _finalize_scanning_complete(self) -> None:
        self.window._update_progress(0.0)
        if not self.window._all_releases:
            self.window.set_loading(False)
            self.window._show_empty(
                title="No Music Found",
                description=f"No audio files found in {self.window._music_dir}",
            )
        else:
            self.window._hide_progress()
            self.window._all_releases.sort(key=lambda r: r.title.lower())
            self.window._filter.refresh_ui_with_sorted_releases()

            def save_cache():
                self.window.save_releases_to_cache()

            threading.Thread(target=save_cache, daemon=True).start()

    def _clear_all_operations(self) -> None:
        self._scan_cancelled = True
        self.window._scanner.cancel_scan()
        self.window._update_progress(0.0)

    def cancel_all_operations(self) -> None:
        self._scan_cancelled = True
        self.window._scanner.cancel_scan()
        self._clear_all_operations()
