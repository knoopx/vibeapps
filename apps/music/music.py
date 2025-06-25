#!/usr/bin/env python3
import gi
import sys
from pathlib import Path
from typing import Optional, List, Any

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

from picker_window import PickerWindow
from star_button import StarButton
from circular_progress import CircularProgress
from music_scanner import MusicScanner
from scanning_coordinator import ScanningCoordinator
from collection import Collection
from collection_manager import CollectionManager
from filtering import MusicFilter, OperationsCoordinator
from serialization import APP_ID, ReleaseItem
from release_list_item import ReleaseListItem
from release_context_menu import ReleaseContextMenu
from collection_picker_window import CollectionPickerWindow
from badge import Badge


class MusicWindow(PickerWindow):

    def __init__(self, **kwargs) -> None:
        self._all_releases = []
        self._music_dir = Path.home() / "Music"
        self._selected_collection = ""
        self._starred = Collection(
            Path.home() / ".config" / APP_ID / "starred.json"
        )
        self._collections = CollectionManager(
            Path.home() / ".config" / APP_ID / "collections"
        )
        self._scanner = MusicScanner(self._music_dir)
        self._settings = Gio.Settings.new("net.knoopx.music")
        self._progress_widget = CircularProgress()
        self._progress_widget.set_visible(False)
        self._scanning_coordinator = ScanningCoordinator(self)
        self._filter = MusicFilter(self)
        self._operations_coordinator = OperationsCoordinator(
            self, self._filter, self._scanning_coordinator
        )
        self._context_menu_widget = ReleaseContextMenu(self)
        super().__init__(title="Music", search_placeholder="Search music...", **kwargs)
        self._setup_keyboard_shortcuts()
        self._setup_css()

    def _setup_keyboard_shortcuts(self) -> None:
        toggle_starred_action = Gio.SimpleAction.new("toggle-starred-filter", None)
        toggle_starred_action.connect(
            "activate", self._on_toggle_starred_filter_shortcut
        )
        self.add_action(toggle_starred_action)
        refresh_filter_action = Gio.SimpleAction.new("refresh-filter", None)
        refresh_filter_action.connect("activate", self._on_refresh_filter_shortcut)
        self.add_action(refresh_filter_action)
        app = self.get_application()
        if app:
            app.set_accels_for_action("win.toggle-starred-filter", ["<Control>s"])
            app.set_accels_for_action("win.refresh-filter", ["<Control>r"])

    def _on_toggle_starred_filter_shortcut(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        current_state = self._star_filter_button.get_starred()
        new_state = not current_state
        self._star_filter_button.set_starred(new_state)
        self._on_star_filter_toggled(self._star_filter_button, new_state)

    def _on_refresh_filter_shortcut(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        current_query = self.get_search_text().strip()
        self.on_search_changed(current_query)

    def _setup_css(self) -> None:
        css_provider = Gtk.CssProvider()
        css_content = StarButton.get_css_style() + Badge.get_css_style()
        css_provider.load_from_data(css_content.encode())
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def get_item_type(self) -> type:
        return ReleaseItem

    def load_initial_data(self) -> None:
        self._scanning_coordinator.start_scanning()

    def _scan_music_directory(self) -> None:
        self._scanning_coordinator._scan_music_directory()

    def _create_release_item_converter(self):
        from serialization import create_release_item_converter

        return create_release_item_converter(self._starred)

    def on_search_changed(self, query: str) -> None:
        self._filter.search_changed(query)

    def on_search_cleared(self) -> None:
        self._filter.search_changed("")

    def on_item_activated(self, item: ReleaseItem) -> None:
        if item and item.path:
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.SEARCH_PATH_FROM_ENVP
                | Gio.SubprocessFlags.STDERR_PIPE
                | Gio.SubprocessFlags.STDOUT_PIPE
            )
            try:
                launcher.spawnv(["amberol", item.path])
            except GLib.Error:
                try:
                    launcher.spawnv(["xdg-open", item.path])
                except GLib.Error:
                    pass

    def setup_list_item(self, list_item: Gtk.ListItem) -> None:

        def _on_star_item(star_button, starred):
            item = list_item.get_item()
            if item:
                self.set_starred(item, starred)

        widget = ReleaseListItem(on_star_toggled=_on_star_item)
        list_item.set_child(widget)

    def bind_list_item(self, list_item: Gtk.ListItem, item: ReleaseItem) -> None:
        if not item:
            return
        widget = list_item.get_child()
        assert isinstance(widget, ReleaseListItem)

        # Get collections that contain this release
        collections = self._collections.lookup(item.path)

        widget.bind_to_item(item, [c.name for c in collections])

    def get_context_menu_model(self, item: Optional[ReleaseItem]) -> Optional[Gio.Menu]:
        return self._context_menu_widget.get_context_menu_model(item)

    def on_toggle_star_action(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        selected_item = self.get_selected_item()
        if selected_item:
            self.toggle_starred(selected_item)

    def on_open_release_action(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        selected_item = self.get_selected_item()
        if selected_item:
            self.on_item_activated(selected_item)

    def on_reveal_action(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        selected_item = self.get_selected_item()
        if selected_item and selected_item.path:
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.SEARCH_PATH_FROM_ENVP
                | Gio.SubprocessFlags.STDERR_PIPE
                | Gio.SubprocessFlags.STDOUT_PIPE
            )
            try:
                launcher.spawnv(["xdg-open", selected_item.path])
            except GLib.Error:
                pass

    def on_trash_release_action(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        selected_item = self.get_selected_item()
        if not selected_item or not selected_item.path:
            return
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

    def _on_trash_dialog_response(
        self, dialog: Adw.MessageDialog, response: str, item: ReleaseItem
    ) -> None:
        if response == "trash":
            try:
                file = Gio.File.new_for_path(item.path)
                file.trash(None)
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

    def on_add_to_collection_action(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        selected_item = self.get_selected_item()
        if not selected_item or not selected_item.path:
            return

        def on_collection_selected(collection_name: str):
            collection = self._collections[collection_name]
            collection.add(selected_item.path)
            self._refresh_collection_dropdown()

        picker = CollectionPickerWindow(
            parent_window=self,
            collection_manager=self._collections,
            on_collection_selected=on_collection_selected,
        )
        picker.present()

    def __getattr__(self, name: str):
        """Handle dynamic remove from collection actions"""
        if name.startswith("on_remove_from_collection_"):
            # Extract sanitized collection name from action name
            sanitized_name = name[26:]  # Remove "on_remove_from_collection_"

            # Find the actual collection name by matching the sanitized name
            actual_collection_name = None
            for collection_name in self._collections.keys():
                if ''.join(c if c.isalnum() else '_' for c in collection_name) == sanitized_name:
                    actual_collection_name = collection_name
                    break

            if not actual_collection_name:
                raise AttributeError(f"No collection found for sanitized name '{sanitized_name}'")

            def remove_from_collection_action(action: Gio.SimpleAction, param: Optional[GLib.Variant]) -> None:
                selected_item = self.get_selected_item()
                if not selected_item or not selected_item.path:
                    return

                # Remove from the specified collection
                if actual_collection_name in self._collections:
                    collection = self._collections[actual_collection_name]
                    collection.remove(selected_item.path)
                    self._refresh_collection_dropdown()

                    # Refresh the view if we're currently filtering by this collection
                    current_query = self.get_search_text().strip()
                    self.on_search_changed(current_query)

            return remove_from_collection_action

        # Fallback to default behavior for other attributes
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def get_empty_icon(self) -> str:
        return "multimedia-player-symbolic"

    def get_loading_icon(self) -> str:
        return "multimedia-player-symbolic"

    def get_empty_title(self) -> str:
        return "No Music Found"

    def get_empty_description(self) -> str:
        return "Add some music to your Music directory and search for it here."

    def get_header_bar_left_widgets(self) -> List[Gtk.Widget]:
        starred_filter_active = self._settings.get_boolean("starred-filter-active")
        self._star_filter_button = StarButton(starred=starred_filter_active)
        self._star_filter_button.set_tooltip_text("Show only starred releases")
        self._star_filter_button.connect("star-toggled", self._on_star_filter_toggled)
        return [self._star_filter_button]

    def get_header_bar_title_widget(self) -> Optional[Gtk.Widget]:
        self._collection_dropdown = Gtk.DropDown()
        self._refresh_collection_dropdown()
        self._collection_dropdown.set_tooltip_text("Filter by collection")
        self._collection_dropdown.connect(
            "notify::selected", self._on_collection_selected
        )
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.append(self._search_entry)
        box.append(self._collection_dropdown)
        return box

    def get_header_bar_right_widgets(self) -> List[Gtk.Widget]:
        return [self._progress_widget]

    def _on_star_filter_toggled(self, star_button: StarButton, starred: bool) -> None:
        self._filter.on_star_filter_toggled(starred)

    def _on_collection_selected(self, dropdown: Gtk.DropDown, param) -> None:
        selected_index = dropdown.get_selected()
        if selected_index == 0:
            collection_name = ""
        else:
            collection_names = sorted(self._collections.keys())
            if selected_index - 1 < len(collection_names):
                collection_name = collection_names[selected_index - 1]
            else:
                collection_name = ""
        self._filter.on_collection_filter_changed(collection_name)

    def _show_progress(self) -> None:
        self._progress_widget.set_visible(True)

    def _hide_progress(self) -> None:
        self._progress_widget.set_visible(False)
        self._progress_widget.set_fraction(0.0)

    def _update_progress(self, fraction: float) -> None:
        self._progress_widget.set_fraction(fraction)
        if fraction > 0:
            self._show_progress()
        else:
            self._hide_progress()

    def on_close_request(self) -> bool:
        self._operations_coordinator.clear_all_operations()
        return False

    def save_releases_to_cache(self) -> None:
        from serialization import convert_release_items_to_data

        releases_data = convert_release_items_to_data(self._all_releases)
        self._scanner.cache.save_to_cache(releases_data)

    def toggle_starred(self, item: ReleaseItem) -> None:
        self._starred.toggle(item.path)
        item.set_property("starred", self._starred.contains(item.path))

    def set_starred(self, item: Any, starred: bool) -> None:
        if not item:
            return
        if starred:
            self._starred.add(item.path)
        else:
            self._starred.remove(item.path)
        item.set_property("starred", starred)

    def on_listview_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if keyval == Gdk.KEY_space:
            selected_item = self.get_selected_item()
            if selected_item:
                self.toggle_starred(selected_item)
                return True
        return False

    def on_escape_pressed(self) -> None:
        """Clear the search instead of closing the app"""
        self._search_entry.set_text("")

    def _refresh_collection_dropdown(self) -> None:
        if hasattr(self, "_collection_dropdown"):
            current_selected = self._collection_dropdown.get_selected()
            current_collection = ""
            if current_selected > 0:
                collection_names = sorted(self._collections.keys())
                if current_selected - 1 < len(collection_names):
                    current_collection = collection_names[current_selected - 1]
            collection_names = sorted(self._collections.keys())
            string_list = Gtk.StringList()
            string_list.append("Everything")
            for name in collection_names:
                string_list.append(name)
            self._collection_dropdown.set_model(string_list)
            if current_collection and current_collection in collection_names:
                new_index = collection_names.index(current_collection) + 1
                self._collection_dropdown.set_selected(new_index)
            else:
                self._collection_dropdown.set_selected(0)

    def get_global_context_menu_actions(self) -> dict:
        return {
            "scan_library": "on_scan_library_action",
            "open_music_folder": "on_open_music_folder_action",
        }

    def get_global_context_menu_model(self) -> Optional[Gio.Menu]:
        menu_model = Gio.Menu.new()
        menu_model.append("Scan Library", "global.scan_library")
        menu_model.append("Open Music Folder", "global.open_music_folder")
        return menu_model

    def on_scan_library_action(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        self._scanning_coordinator.start_scanning()

    def on_open_music_folder_action(
        self, action: Gio.SimpleAction, param: Optional[GLib.Variant]
    ) -> None:
        launcher = Gio.SubprocessLauncher.new(
            Gio.SubprocessFlags.SEARCH_PATH_FROM_ENVP
            | Gio.SubprocessFlags.STDERR_PIPE
            | Gio.SubprocessFlags.STDOUT_PIPE
        )
        try:
            launcher.spawnv(["xdg-open", str(self._music_dir)])
        except GLib.Error:
            pass


class MusicApplication(Adw.Application):

    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)

    def do_activate(self) -> None:
        window = MusicWindow(application=self)
        window.present()


def main() -> int:
    app = MusicApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    main()
