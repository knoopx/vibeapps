#!/usr/bin/env python
import os
import json
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, Gdk, GLib


class AppHistory:
    def __init__(self):
        data_home = os.environ.get(
            "XDG_DATA_HOME", os.path.expanduser("~/.local/share")
        )
        self.data_file = Path(data_home) / "net.knoopx.launcher" / "history.json"
        self.term_app_launches = self._load_data()

    def _load_data(self):
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            if self.data_file.exists():
                with open(self.data_file, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_data(self):
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, "w") as f:
                json.dump(self.term_app_launches, f, indent=2)
        except Exception:
            pass

    def record_launch(self, app_id, search_term):
        if not search_term.strip():
            return
        normalized_term = search_term.strip().lower()
        if normalized_term not in self.term_app_launches:
            self.term_app_launches[normalized_term] = {}
        self.term_app_launches[normalized_term][app_id] = (
            self.term_app_launches[normalized_term].get(app_id, 0) + 1
        )
        self._save_data()

    def get_total_launch_count(self, app_id):
        total = 0
        for search_term_data in self.term_app_launches.values():
            total += search_term_data.get(app_id, 0)
        return total

    def get_search_term_launch_count(self, app_id, search_term):
        if not search_term.strip():
            return 0
        normalized_term = search_term.strip().lower()
        if normalized_term not in self.term_app_launches:
            return 0
        return self.term_app_launches[normalized_term].get(app_id, 0)

    def get_search_relevance_score(self, app_id, search_term):
        if not search_term.strip():
            return 0
        normalized_term = search_term.strip().lower()
        exact_match_count = self.get_search_term_launch_count(app_id, normalized_term)
        if exact_match_count > 0:
            return exact_match_count * 100
        partial_score = 0
        for stored_term, app_counts in self.term_app_launches.items():
            if app_id in app_counts:
                if normalized_term in stored_term or stored_term in normalized_term:
                    partial_score += app_counts[app_id] * 10
        return partial_score + self.get_total_launch_count(app_id)


class LauncherWindow(Adw.ApplicationWindow):
    def __init__(self, launcher_app=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.launcher_app = launcher_app  # Reference to launcher app
        self.app_history = launcher_app.app_history if launcher_app else AppHistory()
        self.apps_loaded = False

        self.set_default_size(500, 620)
        self.set_title("Applications")

        # Create UI components
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(box)

        header = Adw.HeaderBar()
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_hexpand(True)
        header.set_title_widget(self.search_entry)
        box.append(header)

        # Add key controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_press)
        self.search_entry.add_controller(key_controller)

        # Create list box
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(True)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(self.list_box)
        self.scrolled = scrolled
        box.append(scrolled)

        # Connect signals
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", self.on_search_activate)
        self.list_box.connect("row-activated", self.on_row_activated)
        self.connect("close-request", self.on_close_request)
        self.connect("map", self.on_window_map)

    def on_window_map(self, window):
        # Load UI with pre-loaded apps if available
        if not self.apps_loaded and self.launcher_app and self.launcher_app.apps:
            self._populate_apps_from_launcher()

        self.search_entry.grab_focus()
        current_text = self.search_entry.get_text()
        if current_text:
            self.search_entry.select_region(0, -1)
            self.on_search_changed(self.search_entry)
        else:
            self._select_first_visible_row()

    def _populate_apps_from_launcher(self):
        """Populate UI with apps already loaded by launcher app"""
        if not self.launcher_app or not self.launcher_app.apps:
            return

        # Clear existing apps
        self._clear_list_box()

        # Load apps from launcher app
        for app_info in self.launcher_app.apps:
            self._create_row_for_app(app_info)

        self.apps_loaded = True

        # Reapply current search filter if one exists
        current_search = self.search_entry.get_text()
        if current_search.strip():
            self.on_search_changed(self.search_entry)
        else:
            # If no search text, trigger sorting by total launches
            self.on_search_changed(self.search_entry)
            self._select_first_visible_row()

        return False  # Don't repeat timeout

    def _select_first_visible_row(self):
        """Helper to select the first visible row"""
        first_visible = self.find_next_visible_row(-1, 1)
        if first_visible:
            self.list_box.select_row(first_visible)
            self.scroll_to_row(first_visible)

    def _clear_list_box(self):
        """Clear all rows from list box"""
        child = self.list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.list_box.remove(child)
            child = next_child

    def _create_row_for_app(self, app_info):
        """Create a row for an app"""
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(5)
        box.set_margin_bottom(5)

        # Handle icon safely
        icon_gicon = app_info.get_icon()
        if icon_gicon:
            icon = Gtk.Image.new_from_gicon(icon_gicon)
        else:
            icon = Gtk.Image.new_from_icon_name("application-x-executable")
        icon.set_pixel_size(32)
        box.append(icon)

        label = Gtk.Label(label=app_info.get_name())
        label.set_halign(Gtk.Align.START)
        box.append(label)

        row.set_child(box)
        # Store app_info as a custom property
        setattr(row, "app_info", app_info)

        self.list_box.append(row)
        return row

    def on_search_changed(self, entry):
        search_text = entry.get_text().lower()
        visible_rows = []

        # Iterate through all children of the list box
        child = self.list_box.get_first_child()
        while child:
            app_info = getattr(child, "app_info", None)
            if app_info:
                app_name = app_info.get_name().lower()
                if not search_text or search_text in app_name:
                    if search_text:
                        # When filtering, use relevance score
                        relevance_score = self.app_history.get_search_relevance_score(
                            app_info.get_id(), search_text
                        )
                    else:
                        # When no filter, use total launch count
                        relevance_score = self.app_history.get_total_launch_count(app_info.get_id())
                    visible_rows.append((child, relevance_score))
                    child.set_visible(True)
                else:
                    child.set_visible(False)
            child = child.get_next_sibling()

        # Sort visible rows by relevance/launch count
        visible_rows.sort(
            key=lambda x: (-x[1], getattr(x[0], "app_info").get_name().lower())
        )

        # Reorder rows in list box
        for i, (row, _) in enumerate(visible_rows):
            self.list_box.remove(row)
            self.list_box.insert(row, i)

        # Select first visible row
        first_row_to_select = visible_rows[0][0] if visible_rows else None
        if first_row_to_select:
            GLib.idle_add(self._select_row_safe, first_row_to_select)
        else:
            GLib.idle_add(self.list_box.unselect_all)

    def _select_row_safe(self, row):
        try:
            if row.get_parent() == self.list_box:
                self.list_box.select_row(row)
                self.scroll_to_row(row)
        except Exception:
            pass
        return False

    def on_key_press(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            return False
        elif keyval == Gdk.KEY_Up:
            self.move_selection(-1)
            return True
        elif keyval == Gdk.KEY_Down:
            self.move_selection(1)
            return True
        elif keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def on_search_activate(self, entry):
        selected = self.list_box.get_selected_row()
        search_term = entry.get_text()
        if selected is None:
            first_visible = self.find_next_visible_row(-1, 1)
            if first_visible is not None:
                self.list_box.select_row(first_visible)
                selected = first_visible
        if selected:
            app_info = getattr(selected, "app_info", None)
            if app_info:
                self.launch_app(app_info, search_term)
        return True

    def scroll_to_row(self, row):
        adj = self.scrolled.get_vadjustment()
        if not adj:
            return
        row_height = row.get_allocated_height()
        row_y = row.get_allocation().y
        visible_height = self.scrolled.get_allocated_height()
        visible_top = adj.get_value()
        visible_bottom = visible_top + visible_height
        if row_y < visible_top or row_y + row_height > visible_bottom:
            target = row_y - (visible_height - row_height) / 2
            target = max(0, min(target, adj.get_upper() - visible_height))
            adj.set_value(target)

    def move_selection(self, direction):
        selected = self.list_box.get_selected_row()
        start_index = (
            selected.get_index()
            if selected
            else -1 if direction > 0 else self.list_box.observe_children().get_n_items()
        )
        next_row = self.find_next_visible_row(start_index, direction)
        if next_row:
            self.list_box.select_row(next_row)
            self.scroll_to_row(next_row)

    def find_next_visible_row(self, start_index, direction):
        index = start_index + direction
        n_items = self.list_box.observe_children().get_n_items()
        while 0 <= index < n_items:
            row = self.list_box.get_row_at_index(index)
            if row and row.get_visible():
                return row
            index += direction
        return None

    def launch_app(self, app_info, search_term):
        if search_term.strip():
            self.app_history.record_launch(app_info.get_id(), search_term)
        try:
            context = self.get_display().get_app_launch_context()
            launched = app_info.launch_uris_as_manager(
                [], context, GLib.SpawnFlags.SEARCH_PATH, None, None
            )
            if not launched:
                print(f"Failed to launch {app_info.get_id()}")
        except Exception as e:
            print(f"Error launching {app_info.get_id()}: {str(e)}")
        self.close()

    def on_row_activated(self, list_box, row):
        search_term = self.search_entry.get_text()
        app_info = getattr(row, "app_info", None)
        if app_info:
            self.launch_app(app_info, search_term)

    def on_close_request(self, window):
        # Refresh apps when window is closed
        if self.launcher_app:
            self.launcher_app.refresh_apps()
        self.set_visible(False)
        return True

class Launcher(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="net.knoopx.launcher",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.window = None
        self.apps = []  # Store apps at application level
        self.app_history = AppHistory()  # Move app history to application level

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.hold()
        # Load apps on application startup
        self._load_apps_on_startup()

    def _load_apps_on_startup(self):
        """Load apps in background during application startup"""
        def load_apps_worker():
            unsorted_apps = [
                app_info for app_info in Gio.AppInfo.get_all() if app_info.should_show()
            ]

            # Sort by launch count and name
            sorted_apps = sorted(
                unsorted_apps,
                key=lambda app: (
                    -self.app_history.get_total_launch_count(app.get_id()),
                    app.get_name().lower(),
                ),
            )

            # Store apps at application level
            self.apps = sorted_apps

        # Load apps in background thread
        threading.Thread(target=load_apps_worker, daemon=True).start()

    def do_activate(self):
        # Create window only when first activated
        if not self.window:
            self.window = LauncherWindow(application=self, launcher_app=self)

        if self.window.get_visible():
            self.window.set_visible(False)
        else:
            self.window.present()

    def refresh_apps(self):
        """Refresh apps when window is closed"""
        self._load_apps_on_startup()

    def do_command_line(self, command_line):
        self.activate()
        return 0


if __name__ == "__main__":
    app = Launcher()
    app.run(None)
