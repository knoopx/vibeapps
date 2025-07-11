

import gi
import json
import subprocess
import sys
from typing import Optional, List

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, GObject, Gdk, Gio, Pango
from picker_window import PickerWindow, PickerItem

APP_ID = "net.knoopx.windows"
class WindowItemWidget(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)

        # Window icon (placeholder)
        self.icon = Gtk.Image.new_from_icon_name("application-x-executable")
        self.icon.set_icon_size(Gtk.IconSize.LARGE)
        self.icon.set_valign(Gtk.Align.CENTER)

        # Content box
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.content_box.set_hexpand(True)

        # Title and status row
        self.title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.title_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.add_css_class("heading")

        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self.urgent_badge = Gtk.Label()
        self.urgent_badge.add_css_class("caption")
        self.urgent_badge.add_css_class("error")
        self.urgent_badge.set_visible(False)

        self.floating_badge = Gtk.Label()
        self.floating_badge.add_css_class("caption")
        self.floating_badge.add_css_class("warning")
        self.floating_badge.set_visible(False)

        self.status_box.append(self.urgent_badge)
        self.status_box.append(self.floating_badge)

        self.title_row.append(self.title_label)
        self.title_row.append(self.status_box)

        # App info row
        self.app_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.app_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.app_label.add_css_class("caption")
        self.app_label.set_opacity(0.7)

        # Window details row
        self.details_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.id_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.id_label.add_css_class("caption")
        self.id_label.set_opacity(0.7)

        self.workspace_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.workspace_label.add_css_class("caption")
        self.workspace_label.set_opacity(0.7)

        self.pid_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self.pid_label.add_css_class("caption")
        self.pid_label.set_opacity(0.7)

        self.details_box.append(self.id_label)
        self.details_box.append(self.workspace_label)
        self.details_box.append(self.pid_label)

        self.content_box.append(self.title_row)
        self.content_box.append(self.app_label)
        self.content_box.append(self.details_box)

        self.append(self.icon)
        self.append(self.content_box)


class WindowItem(PickerItem):
    __gtype_name__ = "WindowItem"

    window_id = GObject.Property(type=int, default=0)
    title = GObject.Property(type=str, default="")
    app_id = GObject.Property(type=str, default="")
    pid = GObject.Property(type=int, default=0)
    workspace_id = GObject.Property(type=int, default=0)
    is_focused = GObject.Property(type=bool, default=False)
    is_floating = GObject.Property(type=bool, default=False)
    is_urgent = GObject.Property(type=bool, default=False)

    def __init__(self, window_data: dict):
        super().__init__()
        self.window_id = window_data.get("id", 0)
        self.title = window_data.get("title", "")
        self.app_id = window_data.get("app_id", "")
        self.pid = window_data.get("pid", 0)
        self.workspace_id = window_data.get("workspace_id", 0)
        self.is_focused = window_data.get("is_focused", False)
        self.is_floating = window_data.get("is_floating", False)
        self.is_urgent = window_data.get("is_urgent", False)

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
            title="Windows",
            search_placeholder="Search windows by title, app, or workspace...",
            **kwargs,
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
            if (
                query_lower in window.title.lower()
                or query_lower in window.app_id.lower()
                or query_lower in str(window.window_id)
                or query_lower in str(window.workspace_id)
                or query_lower in str(window.pid)
            ):
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
            subprocess.run(
                ["niri", "msg", "action", "focus-window", "--id", str(item.window_id)],
                check=True,
            )
            # Close the picker after focusing
            self.close()
        except subprocess.CalledProcessError as e:
            print(f"Error focusing window {item.window_id}: {e}")
            # Show error dialog
            dialog = Adw.MessageDialog.new(
                self, "Error Focusing Window", f"Failed to focus window: {e}"
            )
            dialog.add_response("close", "Close")
            dialog.set_default_response("close")
            dialog.present()

    def setup_list_item(self, list_item):
        widget = WindowItemWidget()
        list_item.set_child(widget)

    def bind_list_item(self, list_item, item):
        widget = list_item.get_child()
        if not isinstance(widget, WindowItemWidget):
            return

        widget.title_label.set_text(item.get_display_title())
        widget.app_label.set_text(item.get_display_app_id())
        widget.id_label.set_text(f"ID: {item.window_id}")
        widget.workspace_label.set_text(f"WS: {item.workspace_id}")
        widget.pid_label.set_text(f"PID: {item.pid}")

        # Set status badges
        if item.is_urgent:
            widget.urgent_badge.set_text("URGENT")
            widget.urgent_badge.set_visible(True)
        else:
            widget.urgent_badge.set_visible(False)

        if item.is_floating:
            widget.floating_badge.set_text("FLOATING")
            widget.floating_badge.set_visible(True)
        else:
            widget.floating_badge.set_visible(False)

        # Set appropriate icon based on app_id
        icon_name = self._get_icon_for_app(item.app_id)
        widget.icon.set_from_icon_name(icon_name)

    def _get_icon_for_app(self, app_id: str) -> str:
        """Get appropriate icon for app_id"""
        icon_mapping = {
            "org.gnome.Nautilus": "folder",
            "code": "com.visualstudio.code",
            "firefox": "firefox",
            "org.gnome.Terminal": "utilities-terminal",
            "org.gnome.gedit": "accessories-text-editor",
            "org.gnome.Calculator": "accessories-calculator",
            "org.gnome.Settings": "preferences-system",
        }

        return icon_mapping.get(app_id, "application-x-executable")

    def get_empty_icon(self):
        return "view-grid-symbolic"

    def get_loading_icon(self):
        return "view-refresh-symbolic"

    def get_empty_title(self):
        return "No Windows Found"

    def get_empty_description(self):
        return "No windows are currently open."

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        if not item or item.window_id == 0:
            return None

        menu_model = Gio.Menu.new()
        menu_model.append("Focus Window", "context.on_focus_window_action")
        menu_model.append("Close Window", "context.on_close_window_action")
        menu_model.append("Copy Window ID", "context.on_copy_window_id_action")
        menu_model.append("Copy Title", "context.on_copy_title_action")
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
            subprocess.run(
                [
                    "niri",
                    "msg",
                    "action",
                    "close-window",
                    "--id",
                    str(selected_item.window_id),
                ],
                check=True,
            )
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
            result = subprocess.run(
                ["niri", "msg", "--json", "windows"],
                capture_output=True,
                text=True,
                check=True,
            )

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
            self._show_empty(
                "No Windows Found", "No windows match your search criteria."
            )
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
            if item is not None and getattr(item, 'window_id', None) == selected_window_id:
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


if __name__ == "__main__":
    main()
