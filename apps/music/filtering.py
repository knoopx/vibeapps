from typing import TYPE_CHECKING, List, Optional, Any
from gi.repository import GLib
from dataclasses import dataclass

if TYPE_CHECKING:
    from music import MusicWindow


@dataclass
class FilterState:
    query_lower: str
    original_query: str
    star_filter_active: bool
    collection_filter_active: str  # Empty string means no collection filter
    filtered_releases: List[Any]
    current_index: int
    batch_size: int


@dataclass
class ResultState:
    filtered_releases: List[Any]
    current_index: int
    batch_size: int


class MusicFilter:
    def __init__(self, window: "MusicWindow") -> None:
        self.window = window
        self._filter_idle_id = 0
        self._current_filter_state: Optional[FilterState] = None
        self._current_result_state: Optional[ResultState] = None
        self._current_query = ""

    def search_changed(self, query: str) -> None:
        self._cancel_pending_operations()
        self._current_query = query.strip()
        self.window.remove_all_items()
        star_filter_active = self._get_star_filter_state()
        collection_filter = self._get_collection_filter_state()
        if not query:
            self._handle_empty_query(star_filter_active, collection_filter)
            return
        query_lower = query.lower()
        self._start_batched_filtering(
            query_lower, query, star_filter_active, collection_filter
        )

    def _cancel_pending_operations(self) -> None:
        if self._filter_idle_id > 0:
            GLib.source_remove(self._filter_idle_id)
            self._filter_idle_id = 0
        self._current_filter_state = None
        self._current_result_state = None

    def _get_star_filter_state(self) -> bool:
        return (
            hasattr(self.window, "_star_filter_button")
            and self.window._star_filter_button.get_starred()
        )

    def _get_collection_filter_state(self) -> str:
        return (
            getattr(self.window, "_selected_collection", "")
            if hasattr(self.window, "_selected_collection")
            else ""
        )

    def _handle_empty_query(
        self, star_filter_active: bool, collection_filter: str
    ) -> None:
        releases_to_show = self.window._all_releases
        if star_filter_active:
            releases_to_show = [r for r in releases_to_show if r.starred]
        if collection_filter:
            collection = self.window._collections.get(collection_filter)
            if collection:
                releases_to_show = [
                    r for r in releases_to_show if collection.contains(r.path)
                ]
        self._start_batched_result_addition_with_empty_check(
            releases_to_show, star_filter_active, collection_filter
        )

    def _start_batched_result_addition_with_empty_check(
        self,
        releases: List[Any],
        star_filter_active: bool = False,
        collection_filter: str = "",
    ) -> None:
        if not releases:
            if collection_filter:
                self.window._show_empty(
                    title=f"No Music in '{collection_filter}'",
                    description="This collection is empty or no releases match your criteria.",
                )
            elif star_filter_active:
                self.window._show_empty(
                    title="No Starred Music Found",
                    description="No starred releases match your criteria.",
                )
            else:
                self.window._show_empty(
                    title="No Music Found",
                    description=f"No audio files found in {self.window._music_dir}",
                )
        else:
            self._start_batched_result_addition(releases)

    def _start_batched_filtering(
        self,
        query_lower: str,
        original_query: str,
        star_filter_active: bool = False,
        collection_filter: str = "",
    ) -> None:
        self._current_filter_state = FilterState(
            query_lower=query_lower,
            original_query=original_query,
            star_filter_active=star_filter_active,
            collection_filter_active=collection_filter,
            filtered_releases=[],
            current_index=0,
            batch_size=100,
        )
        self._filter_idle_id = GLib.idle_add(self._filter_next_batch)

    def _filter_next_batch(self) -> bool:
        if self._current_filter_state is None:
            self._filter_idle_id = 0
            return False
        state = self._current_filter_state
        if state.current_index >= len(self.window._all_releases):
            self._filter_idle_id = 0
            return False
        end_index = min(
            state.current_index + state.batch_size, len(self.window._all_releases)
        )
        collection = None
        if state.collection_filter_active:
            collection = self.window._collections.get(state.collection_filter_active)

        for i in range(state.current_index, end_index):
            release = self.window._all_releases[i]
            if state.query_lower not in release.title.lower():
                continue
            if state.star_filter_active and not release.starred:
                continue
            if (
                state.collection_filter_active
                and collection
                and not collection.contains(release.path)
            ):
                continue
            state.filtered_releases.append(release)
        state.current_index = end_index
        if state.current_index < len(self.window._all_releases):
            return True
        else:
            if state.original_query == self._current_query:
                self._apply_search_results(
                    state.filtered_releases, state.original_query
                )
            self._filter_idle_id = 0
            self._current_filter_state = None
            return False

    def _apply_search_results(self, filtered_releases: List[Any], query: str) -> None:
        if not filtered_releases:
            if query:
                self.window._show_empty(
                    title=f"No Results for '{query}'",
                    description="Try a different search term.",
                )
            else:
                self.window._show_empty(
                    title="No Music Found",
                    description=f"No audio files found in {self.window._music_dir}",
                )
            return
        self._start_batched_result_addition(filtered_releases)

    def _start_batched_result_addition(self, filtered_releases: List[Any]) -> None:
        self._current_result_state = ResultState(
            filtered_releases=filtered_releases, current_index=0, batch_size=50
        )
        self._add_result_batch()

    def _add_result_batch(self) -> bool:
        if self._current_result_state is None:
            return False
        state = self._current_result_state
        if state.current_index >= len(state.filtered_releases):
            self._current_result_state = None
            return False
        end_index = min(
            state.current_index + state.batch_size, len(state.filtered_releases)
        )
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

    def refresh_ui_with_sorted_releases(self) -> None:
        self.window.remove_all_items()
        current_query = self.window.get_search_text().strip()
        star_filter_active = self._get_star_filter_state()
        collection_filter = self._get_collection_filter_state()
        if not current_query:
            releases_to_show = self.window._all_releases
            if star_filter_active:
                releases_to_show = [r for r in releases_to_show if r.starred]
            if collection_filter:
                collection = self.window._collections.get(collection_filter)
                if collection:
                    releases_to_show = [
                        r for r in releases_to_show if collection.contains(r.path)
                    ]
            self._start_batched_result_addition_with_empty_check(releases_to_show)
        else:
            query_lower = current_query.lower()
            self._start_batched_filtering(
                query_lower, current_query, star_filter_active, collection_filter
            )

    def clear_all_operations(self) -> None:
        self._cancel_pending_operations()
        self._current_query = ""

    def on_star_filter_toggled(self, starred: bool) -> None:
        self.window._settings.set_boolean("starred-filter-active", starred)
        current_query = self.window.get_search_text()
        self.search_changed(current_query)

    def on_collection_filter_changed(self, collection_name: str) -> None:
        self.window._selected_collection = collection_name
        current_query = self.window.get_search_text()
        self.search_changed(current_query)

    def start_batched_result_addition(self, releases: List[Any]) -> None:
        self._start_batched_result_addition(releases)


class OperationsCoordinator:
    def __init__(self, window, filter_manager, scanning_coordinator) -> None:
        self.window = window
        self.filter_manager = filter_manager
        self.scanning_coordinator = scanning_coordinator

    def clear_all_operations(self) -> None:
        if self.filter_manager:
            self.filter_manager.clear_all_operations()
        if self.scanning_coordinator:
            self.scanning_coordinator.cancel_all_operations()
        self.window._update_progress(0.0)
