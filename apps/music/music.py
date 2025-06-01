#!/usr/bin/env python3

import gi
import sys
import threading
from pathlib import Path
from typing import Optional

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")

from gi.repository import Gtk, Adw, GLib, GObject, Gio, Pango
from picker_window import PickerWindow, PickerItem
from star_button import StarButton
from circular_progress import CircularProgress
from scanner import MusicScanner
from caching import ReleaseData
from starring import StarringManager
from filtering import MusicFilter

APP_ID = "net.knoopx.music"


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
        self._current_query = ""  # Track current search query for sync

        # Initialize starring manager
        self._starring_manager = StarringManager()

        # Initialize scanner
        self._scanner = MusicScanner(self._music_dir, self._starring_manager.is_release_starred)

        # Initialize dconf settings
        self._settings = Gio.Settings.new("net.knoopx.music")

        # Create circular progress widget
        self._progress_widget = CircularProgress()
        self._progress_widget.set_visible(False)  # Initially hidden

        super().__init__(
            title="Music",
            search_placeholder="Search music...",
            **kwargs
        )

        # Initialize filter after window is created
        self._filter = MusicFilter(self)

        # Add CSS for star button styling
        self._setup_css()

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
        if not self._music_dir.exists():
            self._show_empty(
                title="Music Directory Not Found",
                description=f"Could not find music directory at {self._music_dir}"
            )
            return

        # Prevent duplicate loading
        if self._scanner.is_background_scan_running():
            return

        # Try to load from cache first
        cache_valid, cached_releases = self._scanner.cache.load_from_cache()
        if cache_valid and cached_releases:
            self._load_cache_in_background(cached_releases)
        else:
            # No valid cache, do a full scan
            self._initialize_scanning()
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()

    def _scan_music_directory(self):
        """Scan the music directory for audio files and create release items."""
        # Initialize and start the incremental scanning using the scanner
        self._scanner.initialize_scanning()
        self._scanner.start_incremental_scan()
        GLib.idle_add(self._continue_scanning)

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

    def _load_cache_in_background(self, releases_data):
        """Load large cache in background with batched UI updates."""
        try:
            # Process releases in batches
            batch_size = 1000
            all_releases = []

            for i in range(0, len(releases_data), batch_size):
                if self._scanner._scan_cancelled:
                    return

                batch = releases_data[i:i + batch_size]
                batch_releases = []

                for release_data in batch:
                    # Convert ReleaseData to ReleaseItem
                    release = ReleaseItem(
                        title=release_data.title,
                        path=release_data.path,
                        track_count=release_data.track_count,
                        starred=self._starring_manager.is_release_starred(release_data.path)
                    )
                    batch_releases.append(release)

                all_releases.extend(batch_releases)

                # Update UI with progress every few batches
                if i == 0 or (i // batch_size) % 5 == 0:
                    progress = len(all_releases) / len(releases_data)
                    GLib.idle_add(self._update_cache_loading_progress, len(all_releases), len(releases_data), progress)

            if all_releases:
                # Sort in background
                all_releases.sort(key=lambda r: r.title.lower())

                # Update main thread
                GLib.idle_add(self._finalize_cache_loading, all_releases)
            else:
                GLib.idle_add(self._handle_empty_cache)

        except Exception:
            GLib.idle_add(self._handle_cache_error)

    def _update_cache_loading_progress(self, loaded, total, progress):
        """Update UI with cache loading progress."""
        # Update the progress widget with actual progress
        self._update_progress(progress)
        return False

    def _finalize_cache_loading(self, all_releases):
        """Finalize cache loading on main thread."""
        # Ensure we don't duplicate if already loaded
        if self._all_releases:
            return False

        self._all_releases = all_releases
        self.set_loading(False)
        self._hide_progress()  # Hide progress when cache loading is complete

        # Clear any existing items to prevent duplicates
        self.remove_all_items()

        # Apply any active search or show all results
        current_query = self.get_search_text().strip()
        if current_query:
            self.on_search_changed(current_query)
        else:
            # Check if starred filter should be applied from settings
            starred_filter_active = self._settings.get_boolean("starred-filter-active")
            if starred_filter_active:
                # Apply starred filter to initial results
                starred_releases = [r for r in self._all_releases if r.starred]
                if starred_releases:
                    self._filter.start_batched_result_addition(starred_releases)
                else:
                    self._show_empty(
                        title="No Starred Releases",
                        description="Star some releases to see them here."
                    )
            else:
                # Use batched loading for UI updates too
                self._filter.start_batched_result_addition(self._all_releases)

        # After cache is successfully loaded and UI updated,
        # start a background scan for any updates since the cache was created.
        if not self._scanner.is_background_scan_running():
            # Convert ReleaseItems back to ReleaseData for the scanner
            current_releases = [
                ReleaseData(r.title, r.path, r.track_count)
                for r in self._all_releases
            ]
            self._scanner.start_background_cache_update(
                current_releases,
                self._on_cache_update_complete
            )

        # Ensure main scanning progress is hidden since cache loading is complete
        self._update_progress(0.0)
        self._hide_progress()

        return False # Important for GLib.idle_add to not re-schedule this handler

    def _on_cache_update_complete(self, updated_releases):
        """Handle completion of background cache update."""
        # Convert ReleaseData back to ReleaseItems
        self._all_releases = [
            ReleaseItem(
                title=rd.title,
                path=rd.path,
                track_count=rd.track_count,
                starred=self._starring_manager.is_release_starred(rd.path)
            )
            for rd in updated_releases
        ]

        # Refresh UI with updated releases
        self._refresh_ui_with_sorted_releases()
        return False

    def _handle_empty_cache(self):
        """Handle empty cache on main thread."""
        self.set_loading(False)
        self._hide_progress()
        self._show_empty(
            title="No Music Found",
            description=f"No audio files found in {self._music_dir}"
        )
        return False

    def _handle_cache_error(self):
        """Handle cache loading error on main thread."""
        self.set_loading(False)
        self._hide_progress()
        self._clear_all_operations()
        # Fall back to full scan
        if not self._scanner.is_background_scan_running():
            self._initialize_scanning()
            thread = threading.Thread(target=self._scan_music_directory)
            thread.daemon = True
            thread.start()
        return False

    def _save_to_cache(self):
        """Save current releases to cache using the scanner."""
        # Convert ReleaseItems to ReleaseData
        releases_data = [
            ReleaseData(r.title, r.path, r.track_count)
            for r in self._all_releases
        ]
        self._scanner.cache.save_to_cache(releases_data)

    def on_search_changed(self, query: str):
        """Filter releases based on search query."""
        self._filter.search_changed(query)



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
            except GLib.Error:
                # Fallback to xdg-open if amberol is not available
                try:
                    launcher.spawnv(["xdg-open", item.path])
                    # Keep the music browser open after fallback launch
                except GLib.Error:
                    pass

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
            "reveal": "on_reveal_action",
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
        menu_model.append("Reveal in Files", "context.reveal")
        menu_model.append("Move to Trash", "context.trash_release")
        return menu_model

    # Context menu action handlers
    def on_toggle_star_action(self, action, param):
        """Toggle star status for the selected release."""
        selected_item = self.get_selected_item()
        if selected_item:
            self._starring_manager.toggle_release_starred(selected_item.path)
            # Update the item's starred status
            selected_item.starred = self._starring_manager.is_release_starred(selected_item.path)
            # Refresh the UI to show the updated star
            self._refresh_single_item(selected_item)

    def on_open_release_action(self, action, param):
        """Open release with amberol (same as default action)."""
        selected_item = self.get_selected_item()
        if selected_item:
            self.on_item_activated(selected_item)

    def on_reveal_action(self, action, param):
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
            except GLib.Error:
                pass

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
        # Create star button for filtering and restore saved state
        starred_filter_active = self._settings.get_boolean("starred-filter-active")
        self._star_filter_button = StarButton(starred=starred_filter_active)
        self._star_filter_button.set_tooltip_text("Show only starred releases")
        self._star_filter_button.connect('star-toggled', self._on_star_filter_toggled)

        return [self._star_filter_button]

    def get_header_bar_right_widgets(self) -> list:
        """Return progress widget for the right side of header bar."""
        return [self._progress_widget]

    def _on_star_filter_toggled(self, star_button, starred):
        """Handle star filter button toggle."""
        self._filter.on_star_filter_toggled(starred)

    def _show_progress(self):
        """Show the circular progress widget."""
        self._progress_widget.set_visible(True)

    def _hide_progress(self):
        """Hide the circular progress widget."""
        self._progress_widget.set_visible(False)
        # Ensure the widget is properly reset
        self._progress_widget.set_fraction(0.0)

    def _update_progress(self, fraction):
        """Update the progress fraction (0.0 to 1.0)."""
        self._progress_widget.set_fraction(fraction)
        if fraction > 0:
            self._show_progress()
        else:
            self._hide_progress()

    def _initialize_scanning(self):
        """Initialize the UI for progressive scanning."""
        self._all_releases = []
        self._scan_generator = None
        self._scan_cancelled = False  # Reset cancellation flag
        self._cache_loaded = False   # Reset cache flag
        self._scan_progress = 0.0
        self._scan_current_count = 0
        self.remove_all_items()
        self.set_loading(True)
        self._update_progress(0.0)  # Start with 0 progress

    def _initialize_scanning(self):
        """Initialize the UI for progressive scanning."""
        self._all_releases = []
        self.remove_all_items()
        self.set_loading(True)
        self._update_progress(0.0)  # Start with 0 progress
        # Initialize scanner state
        self._scanner.initialize_scanning()

    def _continue_scanning(self):
        """Continue incremental scanning - called on idle to prevent blocking."""
        result, is_done = self._scanner.continue_scanning()

        if is_done:
            # Scanning complete
            self._finalize_scanning_complete()
            return False  # Stop the idle callback

        if result is not None:
            # Handle progress updates
            if isinstance(result, tuple) and len(result) == 2 and result[0] == 'progress':
                # Update progress in the UI (we're already in main thread)
                progress_fraction = result[1]
                self._update_progress(progress_fraction)
            elif hasattr(result, 'title'):  # ReleaseData object
                # If we got a new release, convert ReleaseData to ReleaseItem and add it
                release_item = ReleaseItem(
                    title=result.title,
                    path=result.path,
                    track_count=result.track_count,
                    starred=self._starring_manager.is_release_starred(result.path)
                )
                self._add_single_release(release_item)

        # Continue scanning on next idle
        return True

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
        # But keep the progress indicator visible during scanning
        if len(self._all_releases) == 1:
            self.set_loading(False)  # This switches from loading to results view
            # Keep progress visible during scanning with current fraction
            if hasattr(self, '_scan_progress') and self._scan_progress > 0:
                self._update_progress(self._scan_progress)
            else:
                # Show minimal progress to indicate scanning is ongoing
                self._update_progress(0.1)  # Small fraction to show activity

        # If this is the first item that matches search, make sure results are shown
        if should_show and self._item_store.get_n_items() == 1:
            self._show_results()

    def _refresh_ui_with_sorted_releases(self):
        """Refresh the UI with sorted releases."""
        self._filter.refresh_ui_with_sorted_releases()

    def _finalize_scanning_complete(self):
        """Called when scanning is completely finished."""
        # Ensure progress is completely hidden
        self._update_progress(0.0)  # Set fraction to 0 and hide
        self._hide_progress()       # Double ensure it's hidden

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
        self._scanner.cancel_scan()
        self._clear_all_operations()
        return False  # Allow window to close

    def _clear_all_operations(self):
        """Clear all ongoing operations to prevent race conditions."""
        # Cancel any pending search operations
        if hasattr(self, '_search_idle_id') and self._search_idle_id > 0:
            GLib.source_remove(self._search_idle_id)
            self._search_idle_id = 0

        # Clear filter operations
        if hasattr(self, '_filter'):
            self._filter.clear_all_operations()

        # Hide progress indicator
        self._update_progress(0.0)  # Reset fraction to 0
        self._hide_progress()       # Ensure it's hidden

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
        self._starring_manager.toggle_release_starred(item.path)
        # Update the item's starred property
        item.starred = self._starring_manager.is_release_starred(item.path)

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
