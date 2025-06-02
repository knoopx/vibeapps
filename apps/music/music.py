#!/usr/bin/env python3

import gi
import sys
from pathlib import Path
from typing import Optional

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gtk, Adw, GLib, Gio, Pango
from picker_window import PickerWindow
from star_button import StarButton
from circular_progress import CircularProgress
from scanning import MusicScanner, ScanningCoordinator
from starring import StarringManager
from filtering import MusicFilter, OperationsCoordinator
from serialization import APP_ID, ReleaseItem

class MusicWindow(PickerWindow):
    """Music launcher window that shows releases/albums."""

    def __init__(self, **kwargs):
        # Initialize attributes before calling super().__init__
        self._all_releases = []
        self._music_dir = Path.home() / "Music"

        # Initialize starring manager
        self._starring_manager = StarringManager()

        # Initialize scanner
        self._scanner = MusicScanner(
            self._music_dir, self._starring_manager.is_release_starred
        )

        # Initialize dconf settings
        self._settings = Gio.Settings.new("net.knoopx.music")

        # Create circular progress widget
        self._progress_widget = CircularProgress()
        self._progress_widget.set_visible(False)  # Initially hidden

        # Initialize filter before window creation (needs to be available early)
        self._filter = None  # Will be initialized after super().__init__

        # Initialize scanning coordinator early (needed for load_initial_data)
        self._scanning_coordinator = ScanningCoordinator(
            self, self._scanner, self._update_progress
        )

        super().__init__(title="Music", search_placeholder="Search music...", **kwargs)

        # Initialize filter after window is created
        self._filter = MusicFilter(self)

        # Update operations coordinator now that filter is ready
        self._operations_coordinator = OperationsCoordinator(
            self, self._filter, self._scanning_coordinator
        )

        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()

        # Add CSS for star button styling
        self._setup_css()

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for the application."""
        # Create action for toggling starred filter
        toggle_starred_action = Gio.SimpleAction.new("toggle-starred-filter", None)
        toggle_starred_action.connect("activate", self._on_toggle_starred_filter_shortcut)
        self.add_action(toggle_starred_action)

        # Create action for refreshing filter list
        refresh_filter_action = Gio.SimpleAction.new("refresh-filter", None)
        refresh_filter_action.connect("activate", self._on_refresh_filter_shortcut)
        self.add_action(refresh_filter_action)

        # Set up accelerators
        app = self.get_application()
        if app:
            app.set_accels_for_action("win.toggle-starred-filter", ["<Control>s"])
            app.set_accels_for_action("win.refresh-filter", ["<Control>r"])

    def _on_toggle_starred_filter_shortcut(self, action, param):
        """Handle Ctrl+S keyboard shortcut to toggle starred filter."""
        if hasattr(self, "_star_filter_button"):
            # Get current state and toggle it
            current_state = self._star_filter_button.get_starred()
            new_state = not current_state

            # Set the button state (this will update the visual state)
            self._star_filter_button.set_starred(new_state)

            # Manually trigger the filter toggle since set_starred doesn't emit the signal
            self._on_star_filter_toggled(self._star_filter_button, new_state)

    def _on_refresh_filter_shortcut(self, action, param):
        """Handle Ctrl+R keyboard shortcut to refresh the filter list."""
        # Reapply current search and filters
        current_query = self.get_search_text().strip()
        self.on_search_changed(current_query)

    def _setup_css(self):
        """Setup CSS styling for the music window."""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(StarButton.get_css_style().encode())

        # Apply to the current display
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
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
        self._scanning_coordinator.start_scanning()

    def _scan_music_directory(self):
        """Delegate to scanning coordinator."""
        self._scanning_coordinator._scan_music_directory()

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
                description=f"No audio files found in {self._music_dir}",
            )

    def _create_release_item_converter(self):
        """Create a converter function for ReleaseData to ReleaseItem."""
        from serialization import create_release_item_converter

        return create_release_item_converter(self._starring_manager)

    def on_search_changed(self, query: str):
        """Filter releases based on search query."""
        if self._filter:
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
            margin_end=12,
        )

        # Star button
        star_button = StarButton(starred=False)
        star_button.connect("star-toggled", self._on_star_button_toggled)
        main_box.append(star_button)

        # Content box for title and info
        content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True
        )

        # Release title
        title_label = Gtk.Label(
            halign=Gtk.Align.START,
            xalign=0,
            wrap=False,
            single_line_mode=True,
            ellipsize=Pango.EllipsizeMode.END,
        )
        title_label.add_css_class("heading")

        # Track count and path info
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        track_count_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
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
            "trash_release": "on_trash_release_action",
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
            selected_item.starred = self._starring_manager.is_release_starred(
                selected_item.path
            )
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
        dialog = Adw.MessageDialog.new(self, f"Move '{selected_item.title}' to Trash?")
        dialog.set_body(
            f"This will move the entire directory and all its contents to trash.\n\nPath: {selected_item.path}"
        )
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
                self._all_releases = [
                    r for r in self._all_releases if r.path != item.path
                ]
                self.on_search_changed(self.get_search_text())

            except Exception as e:
                error_dialog = Adw.MessageDialog.new(self, "Error Moving to Trash")
                error_dialog.set_body(
                    f"Could not move '{item.title}' to trash:\n{str(e)}"
                )
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
        self._star_filter_button.connect("star-toggled", self._on_star_filter_toggled)

        return [self._star_filter_button]

    def get_header_bar_right_widgets(self) -> list:
        """Return progress widget for the right side of header bar."""
        return [self._progress_widget]

    def _on_star_filter_toggled(self, star_button, starred):
        """Handle star filter button toggle."""
        if self._filter:
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

    def _refresh_ui_with_sorted_releases(self):
        """Refresh the UI with sorted releases."""
        if self._filter:
            self._filter.refresh_ui_with_sorted_releases()

    def on_close_request(self):
        """Handle window close request - cancel any ongoing scanning."""
        self._operations_coordinator.clear_all_operations()
        return False  # Allow window to close

    def _on_star_button_toggled(self, star_button, starred):
        """Handle star button toggle events from the UI."""
        # Get the item reference stored on the button
        item = getattr(star_button, "item", None)
        if not item:
            return

        # Toggle the release starred status
        self._starring_manager.toggle_release_starred(item.path)
        # Update the item's starred property
        item.starred = self._starring_manager.is_release_starred(item.path)

        # Ensure button state matches the actual starred state
        # (in case there was any discrepancy)
        star_button.set_starred(item.starred)

    def save_releases_to_cache(self):
        """Save current releases to cache."""
        from serialization import convert_release_items_to_data
        releases_data = convert_release_items_to_data(self._all_releases)
        self._scanner.cache.save_to_cache(releases_data)


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
