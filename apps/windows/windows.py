#!/usr/bin/env python3
import gi
import json
import subprocess
import sys
from typing import Optional, List

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, GObject, Gdk, Gio, Pango
from picker_window import PickerWindow, PickerItem

APP_ID = 'net.knoopx.windows'

class WindowItem(PickerItem):
    __gtype_name__ = 'WindowItem'

    window_id = GObject.Property(type=int, default=0)
    title = GObject.Property(type=str, default='')
    app_id = GObject.Property(type=str, default='')
    pid = GObject.Property(type=int, default=0)
    workspace_id = GObject.Property(type=int, default=0)
    is_focused = GObject.Property(type=bool, default=False)
    is_floating = GObject.Property(type=bool, default=False)
    is_urgent = GObject.Property(type=bool, default=False)

    def __init__(self, window_data: dict):
        super().__init__()
        self.window_id = window_data.get('id', 0)
        self.title = window_data.get('title', '')
        self.app_id = window_data.get('app_id', '')
        self.pid = window_data.get('pid', 0)
        self.workspace_id = window_data.get('workspace_id', 0)
        self.is_focused = window_data.get('is_focused', False)
        self.is_floating = window_data.get('is_floating', False)
        self.is_urgent = window_data.get('is_urgent', False)

    def get_display_title(self):
        """Get a display-friendly title"""
        if self.title:
            return self.title
        return self.app_id or f"Window {self.window_id}"

    def get_display_app_id(self):
        """Get a display-friendly app ID"""
        if self.app_id:
            return self.app_id
        return "Unknown"

    def __eq__(self, other):
        if not isinstance(other, WindowItem):
            return False
        return self.window_id == other.window_id

    def __hash__(self):
        return hash(self.window_id)


class WindowsWindow(PickerWindow):

    def __init__(self, **kwargs):
        self._current_windows = []
        self._filtered_windows = []
        super().__init__(
            title='Windows',
            search_placeholder='Search windows by title, app, or workspace...',
            **kwargs
        )

    def get_item_type(self):
        return WindowItem

    def load_initial_data(self):
        self._refresh_windows()

    def on_search_changed(self, query):
        if not query.strip():
            self.on_search_cleared()
            return

        query_lower = query.lower()
        filtered = []
        for window in self._current_windows:
            if (query_lower in window.title.lower() or
                query_lower in window.app_id.lower() or
                query_lower in str(window.window_id) or
                query_lower in str(window.workspace_id) or
                query_lower in str(window.pid)):
                filtered.append(window)

        self._filtered_windows = filtered
        self._update_ui()

    def on_search_cleared(self):
        self._filtered_windows = self._current_windows[:]
        self._update_ui()

    def on_item_activated(self, item):
        if not item or item.window_id == 0:
            return

        # Focus the selected window using niri msg
        try:
            subprocess.run([
                'niri', 'msg', 'action', 'focus-window',
                '--id', str(item.window_id)
            ], check=True)
            # Close the picker after focusing
            self.close()
        except subprocess.CalledProcessError as e:
            print(f"Error focusing window {item.window_id}: {e}")
            # Show error dialog
            dialog = Adw.MessageDialog.new(
                self,
                'Error Focusing Window',
                f'Failed to focus window: {e}'
            )
            dialog.add_response('close', 'Close')
            dialog.set_default_response('close')
            dialog.present()

    def setup_list_item(self, list_item):
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12
        )

        # Window icon (placeholder)
        icon = Gtk.Image.new_from_icon_name('application-x-executable')
        icon.set_icon_size(Gtk.IconSize.LARGE)
        icon.set_valign(Gtk.Align.CENTER)

        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        content_box.set_hexpand(True)

        # Title and status row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        title_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.add_css_class('heading')

        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        urgent_badge = Gtk.Label()
        urgent_badge.add_css_class('caption')
        urgent_badge.add_css_class('error')
        urgent_badge.set_visible(False)

        floating_badge = Gtk.Label()
        floating_badge.add_css_class('caption')
        floating_badge.add_css_class('warning')
        floating_badge.set_visible(False)

        status_box.append(urgent_badge)
        status_box.append(floating_badge)

        title_row.append(title_label)
        title_row.append(status_box)

        # App info row
        app_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        app_label.set_ellipsize(Pango.EllipsizeMode.END)
        app_label.add_css_class('caption')
        app_label.set_opacity(0.7)

        # Window details row
        details_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        id_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        id_label.add_css_class('caption')
        id_label.set_opacity(0.7)

        workspace_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        workspace_label.add_css_class('caption')
        workspace_label.set_opacity(0.7)

        pid_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        pid_label.add_css_class('caption')
        pid_label.set_opacity(0.7)

        details_box.append(id_label)
        details_box.append(workspace_label)
        details_box.append(pid_label)

        content_box.append(title_row)
        content_box.append(app_label)
        content_box.append(details_box)

        main_box.append(icon)
        main_box.append(content_box)

        list_item.set_child(main_box)

    def bind_list_item(self, list_item, item):
        main_box = list_item.get_child()
        icon = main_box.get_first_child()
        content_box = main_box.get_last_child()

        title_row = content_box.get_first_child()
        app_label = title_row.get_next_sibling()
        details_box = app_label.get_next_sibling()

        title_label = title_row.get_first_child()
        status_box = title_row.get_last_child()

        urgent_badge = status_box.get_first_child()
        floating_badge = urgent_badge.get_next_sibling()

        id_label = details_box.get_first_child()
        workspace_label = id_label.get_next_sibling()
        pid_label = workspace_label.get_next_sibling()

        # Set content
        title_label.set_text(item.get_display_title())
        app_label.set_text(item.get_display_app_id())

        id_label.set_text(f"ID: {item.window_id}")
        workspace_label.set_text(f"WS: {item.workspace_id}")
        pid_label.set_text(f"PID: {item.pid}")

        # Set status badges
        if item.is_urgent:
            urgent_badge.set_text("URGENT")
            urgent_badge.set_visible(True)
        else:
            urgent_badge.set_visible(False)

        if item.is_floating:
            floating_badge.set_text("FLOATING")
            floating_badge.set_visible(True)
        else:
            floating_badge.set_visible(False)

        # Set appropriate icon based on app_id
        icon_name = self._get_icon_for_app(item.app_id)
        icon.set_from_icon_name(icon_name)

    def _get_icon_for_app(self, app_id: str) -> str:
        """Get appropriate icon for app_id"""
        icon_mapping = {
            'org.gnome.Nautilus': 'folder',
            'code': 'com.visualstudio.code',
            'firefox': 'firefox',
            'org.gnome.Terminal': 'utilities-terminal',
            'org.gnome.gedit': 'accessories-text-editor',
            'org.gnome.Calculator': 'accessories-calculator',
            'org.gnome.Settings': 'preferences-system',
        }

        return icon_mapping.get(app_id, 'application-x-executable')

    def get_empty_icon(self):
        return 'view-grid-symbolic'

    def get_loading_icon(self):
        return 'view-refresh-symbolic'

    def get_empty_title(self):
        return 'No Windows Found'

    def get_empty_description(self):
        return 'No windows are currently open.'

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        if not item or item.window_id == 0:
            return None

        menu_model = Gio.Menu.new()
        menu_model.append('Focus Window', 'context.on_focus_window_action')
        menu_model.append('Close Window', 'context.on_close_window_action')
        menu_model.append('Copy Window ID', 'context.on_copy_window_id_action')
        menu_model.append('Copy Title', 'context.on_copy_title_action')
        return menu_model

    def on_focus_window_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            self.on_item_activated(selected_item)

    def on_close_window_action(self, action, param):
        selected_item = self.get_selected_item()
        if not selected_item or selected_item.window_id == 0:
            return

        try:
            subprocess.run([
                'niri', 'msg', 'action', 'close-window',
                '--id', str(selected_item.window_id)
            ], check=True)
            # Refresh the list after closing
            self._refresh_windows()
        except subprocess.CalledProcessError as e:
            print(f"Error closing window {selected_item.window_id}: {e}")

    def on_copy_window_id_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set(str(selected_item.window_id))

    def on_copy_title_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set(selected_item.title)

    def _refresh_windows(self):
        """Refresh the windows list using niri msg"""
        try:
            result = subprocess.run([
                'niri', 'msg', '--json', 'windows'
            ], capture_output=True, text=True, check=True)

            windows_data = json.loads(result.stdout)
            windows = []

            for window_data in windows_data:
                try:
                    window_item = WindowItem(window_data)
                    if window_item.window_id > 0:
                        windows.append(window_item)
                except Exception as e:
                    print(f"Error creating window item: {e}")
                    continue

            # Sort by workspace, then by title
            windows.sort(key=lambda w: (w.workspace_id, w.title.lower()))

            GLib.idle_add(self._update_windows_list, windows)

        except subprocess.CalledProcessError as e:
            print(f"Error getting windows list: {e}")
            GLib.idle_add(self._update_windows_list, [])
        except json.JSONDecodeError as e:
            print(f"Error parsing windows JSON: {e}")
            GLib.idle_add(self._update_windows_list, [])

    def _update_windows_list(self, windows):
        """Update the windows list in the UI thread"""
        self._current_windows = windows
        current_query = self.get_search_text()
        if current_query.strip():
            self.on_search_changed(current_query)
        else:
            self.on_search_cleared()
        return GLib.SOURCE_REMOVE

    def _update_ui(self):
        """Update the UI with filtered windows"""
        if not self._filtered_windows:
            self.remove_all_items()
            self._show_empty('No Windows Found', 'No windows match your search criteria.')
            return

        # Get currently selected window ID to restore selection
        selected_window_id = None
        selected_position = self._selection_model.get_selected()
        if selected_position != Gtk.INVALID_LIST_POSITION:
            selected_item = self._item_store.get_item(selected_position)
            if selected_item:
                selected_window_id = selected_item.window_id

        # Clear and repopulate for simplicity
        self.remove_all_items()
        for window in self._filtered_windows:
            self.add_item(window)

        self._show_results()

        # Restore selection
        if selected_window_id is not None:
            self._restore_selection(selected_window_id)

    def _restore_selection(self, selected_window_id):
        """Restore selection based on window ID"""
        for i in range(self._item_store.get_n_items()):
            item = self._item_store.get_item(i)
            if item.window_id == selected_window_id:
                self._selection_model.set_selected(i)
                return True
        return False

    def on_close_request(self):
        return False


class WindowsApplication(Adw.Application):

    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = WindowsWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)


def main():
    app = WindowsApplication()
    return app.run(sys.argv)


if __name__ == '__main__':
    main()
