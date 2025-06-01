#!/usr/bin/env python3

from typing import List, Optional, Any
from gi.repository import GLib
from dataclasses import dataclass


@dataclass
class FilterState:
    """State for ongoing filter operations."""
    query_lower: str
    original_query: str
    star_filter_active: bool
    filtered_releases: List[Any]
    current_index: int
    batch_size: int


@dataclass
class ResultState:
    """State for ongoing result addition operations."""
    filtered_releases: List[Any]
    current_index: int
    batch_size: int


class MusicFilter:
    """Handles filtering and search operations for music releases."""

    def __init__(self, window):
        """Initialize the filter with a reference to the window."""
        self.window = window
        self._filter_idle_id = 0
        self._current_filter_state: Optional[FilterState] = None
        self._current_result_state: Optional[ResultState] = None
        self._current_query = ""

    def search_changed(self, query: str):
        """Filter releases based on search query."""
        # Cancel any pending operations and clear state
        self._cancel_pending_operations()

        # Track current query to validate results
        self._current_query = query.strip()

        # Clear UI immediately for responsive feel
        self.window.remove_all_items()

        # Get star filter state
        star_filter_active = self._get_star_filter_state()

        # Handle empty query quickly
        if not query:
            self._handle_empty_query(star_filter_active)
            return

        # For non-empty queries, filter efficiently
        query_lower = query.lower()

        # Simple filtering for small collections (< 100 items)
        if len(self.window._all_releases) < 100:
            filtered_releases = self._filter_small_collection(query_lower, star_filter_active)
            self._apply_search_results(filtered_releases, query)
        else:
            # Use batched filtering for large collections
            self._start_batched_filtering(query_lower, query, star_filter_active)

    def _cancel_pending_operations(self):
        """Cancel any pending filter operations."""
        if self._filter_idle_id > 0:
            GLib.source_remove(self._filter_idle_id)
            self._filter_idle_id = 0

        # Clear any ongoing filter state to prevent stale results
        self._current_filter_state = None
        self._current_result_state = None

    def _get_star_filter_state(self) -> bool:
        """Get the current star filter state."""
        return (hasattr(self.window, '_star_filter_button') and
                self.window._star_filter_button.get_starred())

    def _handle_empty_query(self, star_filter_active: bool):
        """Handle empty search query."""
        # Apply star filter if active
        releases_to_show = self.window._all_releases
        if star_filter_active:
            releases_to_show = [r for r in self.window._all_releases if r.starred]

        # For large collections, use batched addition even for "show all"
        if len(releases_to_show) > 100:
            self._start_batched_result_addition(releases_to_show)
        else:
            # For small collections, add all at once
            self._add_releases_immediately(releases_to_show, star_filter_active)

    def _add_releases_immediately(self, releases: List[Any], star_filter_active: bool):
        """Add releases immediately for small collections."""
        for release in releases:
            self.window.add_item(release)

        if releases:
            self.window._show_results()
        else:
            if star_filter_active:
                self.window._show_empty(
                    title="No Starred Music Found",
                    description="No starred releases match your criteria."
                )
            else:
                self.window._show_empty(
                    title="No Music Found",
                    description=f"No audio files found in {self.window._music_dir}"
                )

    def _filter_small_collection(self, query_lower: str, star_filter_active: bool) -> List[Any]:
        """Filter small collections directly."""
        return [
            release for release in self.window._all_releases
            if query_lower in release.title.lower() and
            (not star_filter_active or release.starred)
        ]

    def _start_batched_filtering(self, query_lower: str, original_query: str, star_filter_active: bool = False):
        """Start batched filtering for large collections."""
        self._current_filter_state = FilterState(
            query_lower=query_lower,
            original_query=original_query,
            star_filter_active=star_filter_active,
            filtered_releases=[],
            current_index=0,
            batch_size=100  # Smaller batches for better responsiveness
        )

        self._filter_idle_id = GLib.idle_add(self._filter_next_batch)

    def _filter_next_batch(self) -> bool:
        """Filter the next batch of releases."""
        # Check if filter state was cleared (search changed)
        if self._current_filter_state is None:
            self._filter_idle_id = 0
            return False

        state = self._current_filter_state

        # Validate that we haven't exceeded bounds
        if state.current_index >= len(self.window._all_releases):
            self._filter_idle_id = 0
            return False

        end_index = min(state.current_index + state.batch_size, len(self.window._all_releases))

        # Process this batch
        for i in range(state.current_index, end_index):
            release = self.window._all_releases[i]
            if (state.query_lower in release.title.lower() and
                (not state.star_filter_active or release.starred)):
                state.filtered_releases.append(release)

        state.current_index = end_index

        # Continue processing or finish
        if state.current_index < len(self.window._all_releases):
            return True  # Continue on next idle
        else:
            # Filtering complete - verify query hasn't changed
            if state.original_query == self._current_query:
                self._apply_search_results(state.filtered_releases, state.original_query)
            self._filter_idle_id = 0
            self._current_filter_state = None
            return False

    def _apply_search_results(self, filtered_releases: List[Any], query: str):
        """Apply search results to the UI efficiently."""
        # Handle empty results immediately
        if not filtered_releases:
            if query:
                self.window._show_empty(
                    title=f"No Results for '{query}'",
                    description="Try a different search term."
                )
            else:
                self.window._show_empty(
                    title="No Music Found",
                    description=f"No audio files found in {self.window._music_dir}"
                )
            return

        # For large result sets, add items in batches to prevent UI freezing
        if len(filtered_releases) > 100:
            self._start_batched_result_addition(filtered_releases)
        else:
            # For small result sets, add all at once
            for release in filtered_releases:
                self.window.add_item(release)
            self.window._show_results()

    def _start_batched_result_addition(self, filtered_releases: List[Any]):
        """Start batched addition of search results for large result sets."""
        self._current_result_state = ResultState(
            filtered_releases=filtered_releases,
            current_index=0,
            batch_size=50  # Add 50 items at a time
        )

        # Start adding results immediately
        self._add_result_batch()

    def _add_result_batch(self) -> bool:
        """Add the next batch of search results."""
        # Check if result state was cleared (search changed)
        if self._current_result_state is None:
            return False

        state = self._current_result_state

        # Validate bounds
        if state.current_index >= len(state.filtered_releases):
            self._current_result_state = None
            return False

        end_index = min(state.current_index + state.batch_size, len(state.filtered_releases))

        # Add this batch of items
        for i in range(state.current_index, end_index):
            self.window.add_item(state.filtered_releases[i])

        # Show results after first batch
        if state.current_index == 0:
            self.window._show_results()

        state.current_index = end_index

        # Continue processing or finish
        if state.current_index < len(state.filtered_releases):
            # Schedule next batch on idle
            GLib.idle_add(self._add_result_batch)
            return False  # Don't continue this idle callback
        else:
            # All results added
            self._current_result_state = None
            return False

    def refresh_ui_with_sorted_releases(self):
        """Refresh the UI with sorted releases."""
        # Clear current UI items
        self.window.remove_all_items()

        # Check if there's an active search query
        current_query = self.window.get_search_text().strip()

        # Check if star filter is active
        star_filter_active = self._get_star_filter_state()

        if not current_query:
            # No search active - add all releases (filtered by star if needed)
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
            # Search is active - filter and add matching releases
            query_lower = current_query.lower()
            if len(self.window._all_releases) < 100:
                # Small collection - filter directly
                filtered_releases = self._filter_small_collection(query_lower, star_filter_active)
                self._apply_search_results(filtered_releases, current_query)
            else:
                # Large collection - use batched filtering
                self._start_batched_filtering(query_lower, current_query, star_filter_active)

    def clear_all_operations(self):
        """Clear all ongoing filter operations."""
        self._cancel_pending_operations()
        self._current_query = ""

    def on_star_filter_toggled(self, starred: bool):
        """Handle star filter button toggle."""
        # Save the starred filter state to settings
        self.window._settings.set_boolean("starred-filter-active", starred)

        # Re-apply current search with star filter
        current_query = self.window.get_search_text()
        self.search_changed(current_query)

    def start_batched_result_addition(self, releases: List[Any]):
        """Public method to start batched result addition."""
        self._start_batched_result_addition(releases)
