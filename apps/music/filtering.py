from typing import List, Optional, Any
from gi.repository import GLib
from dataclasses import dataclass

@dataclass
class FilterState:
    query_lower: str
    original_query: str
    star_filter_active: bool
    filtered_releases: List[Any]
    current_index: int
    batch_size: int

@dataclass
class ResultState:
    filtered_releases: List[Any]
    current_index: int
    batch_size: int

class MusicFilter:

    def __init__(self, window):
        self.window = window
        self._filter_idle_id = 0
        self._current_filter_state: Optional[FilterState] = None
        self._current_result_state: Optional[ResultState] = None
        self._current_query = ''

    def search_changed(self, query: str):
        self._cancel_pending_operations()
        self._current_query = query.strip()
        self.window.remove_all_items()
        star_filter_active = self._get_star_filter_state()
        if not query:
            self._handle_empty_query(star_filter_active)
            return
        query_lower = query.lower()
        if len(self.window._all_releases) < 100:
            filtered_releases = self._filter_small_collection(query_lower, star_filter_active)
            self._apply_search_results(filtered_releases, query)
        else:
            self._start_batched_filtering(query_lower, query, star_filter_active)

    def _cancel_pending_operations(self):
        if self._filter_idle_id > 0:
            GLib.source_remove(self._filter_idle_id)
            self._filter_idle_id = 0
        self._current_filter_state = None
        self._current_result_state = None

    def _get_star_filter_state(self) -> bool:
        return hasattr(self.window, '_star_filter_button') and self.window._star_filter_button.get_starred()

    def _handle_empty_query(self, star_filter_active: bool):
        releases_to_show = self.window._all_releases
        if star_filter_active:
            releases_to_show = [r for r in self.window._all_releases if r.starred]
        if len(releases_to_show) > 100:
            self._start_batched_result_addition(releases_to_show)
        else:
            self._add_releases_immediately(releases_to_show, star_filter_active)

    def _add_releases_immediately(self, releases: List[Any], star_filter_active: bool):
        for release in releases:
            self.window.add_item(release)
        if releases:
            self.window._show_results()
        elif star_filter_active:
            self.window._show_empty(title='No Starred Music Found', description='No starred releases match your criteria.')
        else:
            self.window._show_empty(title='No Music Found', description=f'No audio files found in {self.window._music_dir}')

    def _filter_small_collection(self, query_lower: str, star_filter_active: bool) -> List[Any]:
        return [release for release in self.window._all_releases if query_lower in release.title.lower() and (not star_filter_active or release.starred)]

    def _start_batched_filtering(self, query_lower: str, original_query: str, star_filter_active: bool=False):
        self._current_filter_state = FilterState(query_lower=query_lower, original_query=original_query, star_filter_active=star_filter_active, filtered_releases=[], current_index=0, batch_size=100)
        self._filter_idle_id = GLib.idle_add(self._filter_next_batch)

    def _filter_next_batch(self) -> bool:
        if self._current_filter_state is None:
            self._filter_idle_id = 0
            return False
        state = self._current_filter_state
        if state.current_index >= len(self.window._all_releases):
            self._filter_idle_id = 0
            return False
        end_index = min(state.current_index + state.batch_size, len(self.window._all_releases))
        for i in range(state.current_index, end_index):
            release = self.window._all_releases[i]
            if state.query_lower in release.title.lower() and (not state.star_filter_active or release.starred):
                state.filtered_releases.append(release)
        state.current_index = end_index
        if state.current_index < len(self.window._all_releases):
            return True
        else:
            if state.original_query == self._current_query:
                self._apply_search_results(state.filtered_releases, state.original_query)
            self._filter_idle_id = 0
            self._current_filter_state = None
            return False

    def _apply_search_results(self, filtered_releases: List[Any], query: str):
        if not filtered_releases:
            if query:
                self.window._show_empty(title=f"No Results for '{query}'", description='Try a different search term.')
            else:
                self.window._show_empty(title='No Music Found', description=f'No audio files found in {self.window._music_dir}')
            return
        if len(filtered_releases) > 100:
            self._start_batched_result_addition(filtered_releases)
        else:
            for release in filtered_releases:
                self.window.add_item(release)
            self.window._show_results()

    def _start_batched_result_addition(self, filtered_releases: List[Any]):
        self._current_result_state = ResultState(filtered_releases=filtered_releases, current_index=0, batch_size=50)
        self._add_result_batch()

    def _add_result_batch(self) -> bool:
        if self._current_result_state is None:
            return False
        state = self._current_result_state
        if state.current_index >= len(state.filtered_releases):
            self._current_result_state = None
            return False
        end_index = min(state.current_index + state.batch_size, len(state.filtered_releases))
        for i in range(state.current_index, end_index):
            self.window.add_item(state.filtered_releases[i])
        if state.current_index == 0:
            self.window._show_results()
        state.current_index = end_index
        if state.current_index < len(state.filtered_releases):
            GLib.idle_add(self._add_result_batch)
            return False
        else:
            self._current_result_state = None
            return False

    def refresh_ui_with_sorted_releases(self):
        self.window.remove_all_items()
        current_query = self.window.get_search_text().strip()
        star_filter_active = self._get_star_filter_state()
        if not current_query:
            releases_to_show = self.window._all_releases
            if star_filter_active:
                releases_to_show = [r for r in self.window._all_releases if r.starred]
            if len(releases_to_show) > 100:
                self._start_batched_result_addition(releases_to_show)
            else:
                for release in releases_to_show:
                    self.window.add_item(release)
                if releases_to_show:
                    self.window._show_results()
        else:
            query_lower = current_query.lower()
            if len(self.window._all_releases) < 100:
                filtered_releases = self._filter_small_collection(query_lower, star_filter_active)
                self._apply_search_results(filtered_releases, current_query)
            else:
                self._start_batched_filtering(query_lower, current_query, star_filter_active)

    def clear_all_operations(self):
        self._cancel_pending_operations()
        self._current_query = ''

    def on_star_filter_toggled(self, starred: bool):
        self.window._settings.set_boolean('starred-filter-active', starred)
        current_query = self.window.get_search_text()
        self.search_changed(current_query)

    def start_batched_result_addition(self, releases: List[Any]):
        self._start_batched_result_addition(releases)

class OperationsCoordinator:

    def __init__(self, window, filter_manager, scanning_coordinator):
        self.window = window
        self.filter_manager = filter_manager
        self.scanning_coordinator = scanning_coordinator

    def clear_all_operations(self):
        if self.filter_manager:
            self.filter_manager.clear_all_operations()
        if self.scanning_coordinator:
            self.scanning_coordinator.cancel_all_operations()
        self.window._update_progress(0.0)