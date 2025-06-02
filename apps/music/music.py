#!/usr/bin/env python3
import gi
import sys
from pathlib import Path
from typing import Optional
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Pango', '1.0')
gi.require_version('GLib', '2.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Adw, GLib, Gio, Pango, Gdk
from picker_window import PickerWindow
from star_button import StarButton
from circular_progress import CircularProgress
from scanning import MusicScanner, ScanningCoordinator
from starring import StarringManager
from filtering import MusicFilter, OperationsCoordinator
from serialization import APP_ID, ReleaseItem

class MusicWindow(PickerWindow):

    def __init__(self, **kwargs):
        self._all_releases = []
        self._music_dir = Path.home() / 'Music'
        self._starring_manager = StarringManager()
        self._scanner = MusicScanner(self._music_dir, self._starring_manager.is_release_starred)
        self._settings = Gio.Settings.new('net.knoopx.music')
        self._progress_widget = CircularProgress()
        self._progress_widget.set_visible(False)
        self._filter = None
        self._scanning_coordinator = ScanningCoordinator(self, self._scanner, self._update_progress)
        super().__init__(title='Music', search_placeholder='Search music...', **kwargs)
        self._filter = MusicFilter(self)
        self._operations_coordinator = OperationsCoordinator(self, self._filter, self._scanning_coordinator)
        self._setup_keyboard_shortcuts()
        self._setup_css()

    def _setup_keyboard_shortcuts(self):
        toggle_starred_action = Gio.SimpleAction.new('toggle-starred-filter', None)
        toggle_starred_action.connect('activate', self._on_toggle_starred_filter_shortcut)
        self.add_action(toggle_starred_action)
        refresh_filter_action = Gio.SimpleAction.new('refresh-filter', None)
        refresh_filter_action.connect('activate', self._on_refresh_filter_shortcut)
        self.add_action(refresh_filter_action)
        app = self.get_application()
        if app:
            app.set_accels_for_action('win.toggle-starred-filter', ['<Control>s'])
            app.set_accels_for_action('win.refresh-filter', ['<Control>r'])

    def _on_toggle_starred_filter_shortcut(self, action, param):
        if hasattr(self, '_star_filter_button'):
            current_state = self._star_filter_button.get_starred()
            new_state = not current_state
            self._star_filter_button.set_starred(new_state)
            self._on_star_filter_toggled(self._star_filter_button, new_state)

    def _on_refresh_filter_shortcut(self, action, param):
        current_query = self.get_search_text().strip()
        self.on_search_changed(current_query)

    def _setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(StarButton.get_css_style().encode())
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def get_item_type(self):
        return ReleaseItem

    def _refresh_single_item(self, item):
        for i in range(self._item_store.get_n_items()):
            store_item = self._item_store.get_item(i)
            if store_item and store_item.path == item.path:
                self._item_store.items_changed(i, 1, 1)
                break

    def load_initial_data(self):
        self._scanning_coordinator.start_scanning()

    def _scan_music_directory(self):
        self._scanning_coordinator._scan_music_directory()

    def _update_releases(self, releases):
        self._all_releases = releases
        self.remove_all_items()
        for release in self._all_releases:
            self.add_item(release)
        if self._all_releases:
            self._show_results()
        else:
            self._show_empty(title='No Music Found', description=f'No audio files found in {self._music_dir}')

    def _create_release_item_converter(self):
        from serialization import create_release_item_converter
        return create_release_item_converter(self._starring_manager)

    def on_search_changed(self, query: str):
        if self._filter:
            self._filter.search_changed(query)

    def on_item_activated(self, item):
        if item and item.path:
            launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.SEARCH_PATH_FROM_ENVP | Gio.SubprocessFlags.STDERR_PIPE | Gio.SubprocessFlags.STDOUT_PIPE)
            try:
                launcher.spawnv(['amberol', item.path])
            except GLib.Error:
                try:
                    launcher.spawnv(['xdg-open', item.path])
                except GLib.Error:
                    pass

    def setup_list_item(self, list_item):
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)
        star_button = StarButton(starred=False)
        star_button.connect('star-toggled', self._on_star_button_toggled)
        main_box.append(star_button)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
        title_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=False, single_line_mode=True, ellipsize=Pango.EllipsizeMode.END)
        title_label.add_css_class('heading')
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        track_count_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        track_count_label.add_css_class('dim-label')
        track_count_label.add_css_class('caption')
        info_box.append(track_count_label)
        content_box.append(title_label)
        content_box.append(info_box)
        main_box.append(content_box)
        list_item.set_child(main_box)

    def bind_list_item(self, list_item, item):
        if not item:
            return
        main_box = list_item.get_child()
        if not main_box:
            return
        star_button = main_box.get_first_child()
        if not star_button:
            return
        content_box = star_button.get_next_sibling()
        if not content_box:
            return
        title_label = content_box.get_first_child()
        if not title_label:
            return
        info_box = title_label.get_next_sibling()
        if not info_box:
            return
        track_count_label = info_box.get_first_child()
        if not track_count_label:
            return
        star_button.set_starred(item.starred)
        star_button.item = item
        title_label.set_markup(f'<b>{GLib.markup_escape_text(item.title)}</b>')
        track_text = f"{item.track_count} track{('s' if item.track_count != 1 else '')}"
        track_count_label.set_text(track_text)

    def get_context_menu_actions(self) -> dict:
        return {'toggle_star': 'on_toggle_star_action', 'open_release': 'on_open_release_action', 'reveal': 'on_reveal_action', 'trash_release': 'on_trash_release_action'}

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        if not item:
            return None
        menu_model = Gio.Menu.new()
        star_label = 'Unstar' if item.starred else 'Star'
        menu_model.append(star_label, 'context.toggle_star')
        menu_model.append('Open with Amberol', 'context.open_release')
        menu_model.append('Reveal in Files', 'context.reveal')
        menu_model.append('Move to Trash', 'context.trash_release')
        return menu_model

    def on_toggle_star_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            self._starring_manager.toggle_release_starred(selected_item.path)
            selected_item.starred = self._starring_manager.is_release_starred(selected_item.path)
            self._refresh_single_item(selected_item)

    def on_open_release_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            self.on_item_activated(selected_item)

    def on_reveal_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and selected_item.path:
            launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.SEARCH_PATH_FROM_ENVP | Gio.SubprocessFlags.STDERR_PIPE | Gio.SubprocessFlags.STDOUT_PIPE)
            try:
                launcher.spawnv(['xdg-open', selected_item.path])
            except GLib.Error:
                pass

    def on_trash_release_action(self, action, param):
        selected_item = self.get_selected_item()
        if not selected_item or not selected_item.path:
            return
        dialog = Adw.MessageDialog.new(self, f"Move '{selected_item.title}' to Trash?")
        dialog.set_body(f'This will move the entire directory and all its contents to trash.\n\nPath: {selected_item.path}')
        dialog.add_response('cancel', 'Cancel')
        dialog.add_response('trash', 'Move to Trash')
        dialog.set_response_appearance('trash', Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response('cancel')
        dialog.set_close_response('cancel')
        dialog.connect('response', self._on_trash_dialog_response, selected_item)
        dialog.present()

    def _on_trash_dialog_response(self, dialog, response, item):
        if response == 'trash':
            try:
                file = Gio.File.new_for_path(item.path)
                file.trash(None)
                self._all_releases = [r for r in self._all_releases if r.path != item.path]
                self.on_search_changed(self.get_search_text())
            except Exception as e:
                error_dialog = Adw.MessageDialog.new(self, 'Error Moving to Trash')
                error_dialog.set_body(f"Could not move '{item.title}' to trash:\n{str(e)}")
                error_dialog.add_response('ok', 'OK')
                error_dialog.set_default_response('ok')
                error_dialog.present()

    def get_empty_icon(self) -> str:
        return 'multimedia-player-symbolic'

    def get_loading_icon(self) -> str:
        return 'multimedia-player-symbolic'

    def get_empty_title(self) -> str:
        return 'No Music Found'

    def get_empty_description(self) -> str:
        return 'Add some music to your Music directory and search for it here.'

    def get_header_bar_left_widgets(self) -> list:
        starred_filter_active = self._settings.get_boolean('starred-filter-active')
        self._star_filter_button = StarButton(starred=starred_filter_active)
        self._star_filter_button.set_tooltip_text('Show only starred releases')
        self._star_filter_button.connect('star-toggled', self._on_star_filter_toggled)
        return [self._star_filter_button]

    def get_header_bar_right_widgets(self) -> list:
        return [self._progress_widget]

    def _on_star_filter_toggled(self, star_button, starred):
        if self._filter:
            self._filter.on_star_filter_toggled(starred)

    def _show_progress(self):
        self._progress_widget.set_visible(True)

    def _hide_progress(self):
        self._progress_widget.set_visible(False)
        self._progress_widget.set_fraction(0.0)

    def _update_progress(self, fraction):
        self._progress_widget.set_fraction(fraction)
        if fraction > 0:
            self._show_progress()
        else:
            self._hide_progress()

    def _refresh_ui_with_sorted_releases(self):
        if self._filter:
            self._filter.refresh_ui_with_sorted_releases()

    def on_close_request(self):
        self._operations_coordinator.clear_all_operations()
        return False

    def _on_star_button_toggled(self, star_button, starred):
        item = getattr(star_button, 'item', None)
        if not item:
            return
        self._starring_manager.toggle_release_starred(item.path)
        item.starred = self._starring_manager.is_release_starred(item.path)
        star_button.set_starred(item.starred)

    def save_releases_to_cache(self):
        from serialization import convert_release_items_to_data
        releases_data = convert_release_items_to_data(self._all_releases)
        self._scanner.cache.save_to_cache(releases_data)

    def on_additional_key_pressed(self, keyval, keycode, state) -> bool:
        """Handle additional keyboard shortcuts."""
        if keyval == Gdk.KEY_space:
            selected_item = self.get_selected_item()
            if selected_item:
                print("Toggling starred status for:", selected_item.title)
                # Toggle the starred status
                self._starring_manager.toggle_release_starred(selected_item.path)
                selected_item.starred = self._starring_manager.is_release_starred(selected_item.path)
                # Refresh the UI for this item
                self._refresh_single_item(selected_item)
                return True
        return False

class MusicApplication(Adw.Application):

    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        window = MusicWindow(application=self)
        window.present()

def main():
    app = MusicApplication()
    return app.run(sys.argv)
if __name__ == '__main__':
    main()