#!/usr/bin/env python3

import gi
import subprocess
import threading
import os
import getpass

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib, GObject, Gdk

APP_ID = "net.knoopx.bookmarks"


class BookmarkItem(GObject.Object):
    __gtype_name__ = "BookmarkItem"

    title = GObject.Property(type=str)
    url = GObject.Property(type=str)

    def __init__(self, title, url):
        super().__init__()
        self.title = title
        self.url = url


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_default_size(400, 800)
        self.set_title("Bookmarks")

        self._bookmark_store = Gio.ListStore.new(BookmarkItem)
        self._filtered_store = Gtk.FilterListModel.new(self._bookmark_store, None)
        self._search_delay_id = 0
        self._all_bookmarks = []

        # Create a selection model
        self._selection_model = Gtk.SingleSelection(model=self._filtered_store)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        self._header_bar = Adw.HeaderBar()
        main_box.append(self._header_bar)

        self._search_entry = Gtk.SearchEntry(
            hexpand=True, placeholder_text="Search bookmarks..."
        )
        self._search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry.connect("activate", self._on_search_activated)
        self._header_bar.set_title_widget(self._search_entry)

        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        main_box.append(self._content_stack)

        scrolled_window = Gtk.ScrolledWindow(vexpand=True)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_list_item_setup)
        factory.connect("bind", self._on_list_item_bind)

        self._list_view = Gtk.ListView(model=self._selection_model, factory=factory)
        self._list_view.set_vexpand(True)
        self._list_view.set_hexpand(True)
        self._list_view.set_can_focus(True)  # Allow ListView to receive focus

        scrolled_window.set_child(self._list_view)
        self._content_stack.add_named(scrolled_window, "results")

        loading_page = Adw.StatusPage(
            title="Loading Bookmarks...",
            icon_name="user-bookmarks-symbolic",
        )
        spinner = Gtk.Spinner(
            spinning=True, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER
        )
        loading_page.set_child(spinner)
        self._content_stack.add_named(loading_page, "loading")

        self._empty_page = Adw.StatusPage(
            title="Search Bookmarks",
            description="Type your query in the search bar above.",
            icon_name="user-bookmarks-symbolic",
        )
        self._content_stack.add_named(self._empty_page, "empty")

        self._error_page = Adw.StatusPage(
            title="Error Loading Bookmarks",
            description="Could not fetch bookmark information.",
            icon_name="dialog-error-symbolic",
        )
        self._content_stack.add_named(self._error_page, "error")

        # Add event controller for key presses
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self._search_entry.add_controller(key_controller)

        # Load bookmarks on startup
        self._load_bookmarks()

    def _on_search_activated(self, _):
        selected_pos = self._selection_model.get_selected()
        if selected_pos != Gtk.INVALID_LIST_POSITION:
            bookmark_item = self._filtered_store.get_item(selected_pos)
            if bookmark_item and bookmark_item.url:
                Gtk.show_uri(self, bookmark_item.url, Gdk.CURRENT_TIME)
                GLib.timeout_add(50, self.get_application().quit)

    def _scroll_to_selected(self):
        """Scroll the ListView to make the selected item visible."""
        selected_pos = self._selection_model.get_selected()
        if selected_pos != Gtk.INVALID_LIST_POSITION:
            # Use GLib.idle_add to ensure the ListView has been updated
            GLib.idle_add(lambda: self._list_view.scroll_to(selected_pos, Gtk.ListScrollFlags.FOCUS, None))

    def _on_key_pressed(self, controller, keyval, keycode, state):
        selected_pos = self._selection_model.get_selected()

        if keyval == Gdk.KEY_Escape:
            self.get_application().quit()

        if keyval == Gdk.KEY_Up:
            if selected_pos != Gtk.INVALID_LIST_POSITION and selected_pos > 0:
                self._selection_model.set_selected(selected_pos - 1)
                self._scroll_to_selected()
            return True
        elif keyval == Gdk.KEY_Down:
            if selected_pos != Gtk.INVALID_LIST_POSITION and selected_pos < self._filtered_store.get_n_items() - 1:
                self._selection_model.set_selected(selected_pos + 1)
                self._scroll_to_selected()
            return True
        return False

    def _on_list_item_setup(self, factory, list_item):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=12,
            margin_end=12,
        )
        title_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=True)
        url_label = Gtk.Label(
            halign=Gtk.Align.START, xalign=0, wrap=True, css_classes=["dim-label"]
        )
        box.append(title_label)
        box.append(url_label)
        list_item.set_child(Adw.ActionRow(child=box))

    def _on_list_item_bind(self, factory, list_item):
        bookmark_item = list_item.get_item()
        action_row = list_item.get_child()
        box = action_row.get_child()
        widgets = {}
        child = box.get_first_child()
        idx = 0
        while child:
            if idx == 0:
                widgets["title"] = child
            elif idx == 1:
                widgets["url"] = child
            child = child.get_next_sibling()
            idx += 1
        widgets["title"].set_markup(
            f"<big><b>{GLib.markup_escape_text(bookmark_item.title)}</b></big>"
        )
        widgets["url"].set_text(bookmark_item.url)

    def _on_search_changed(self, search_entry):
        if self._search_delay_id > 0:
            GLib.source_remove(self._search_delay_id)
        query = search_entry.get_text().strip().lower()

        if not query:
            # Show all bookmarks
            self._filtered_store.set_filter(None)
            if self._bookmark_store.get_n_items() > 0:
                self._content_stack.set_visible_child_name("results")
                self._selection_model.set_selected(0)
                self._scroll_to_selected()
            else:
                self._content_stack.set_visible_child_name("empty")
            self._search_delay_id = 0
            return

        self._search_delay_id = GLib.timeout_add(200, self._apply_filter, query)

    def _apply_filter(self, query):
        self._search_delay_id = 0

        # Create a filter function
        def filter_func(item):
            title_match = query in item.title.lower()
            url_match = query in item.url.lower()
            return title_match or url_match

        # Create and apply the filter
        filter_obj = Gtk.CustomFilter.new(filter_func)
        self._filtered_store.set_filter(filter_obj)

        if self._filtered_store.get_n_items() > 0:
            self._content_stack.set_visible_child_name("results")
            self._selection_model.set_selected(0)
            self._scroll_to_selected()
        else:
            self._empty_page.set_title(f"No Results for '{GLib.markup_escape_text(query)}'")
            self._empty_page.set_description("Try a different search term.")
            self._content_stack.set_visible_child_name("empty")

        return GLib.SOURCE_REMOVE

    def _load_bookmarks(self):
        self._content_stack.set_visible_child_name("loading")
        thread = threading.Thread(target=self._fetch_bookmarks)
        thread.daemon = True
        thread.start()

    def _fetch_bookmarks(self):
        try:
            # Determine Firefox profile path
            firefox_home = os.path.expanduser("~/.mozilla/firefox")
            profile_path = None

            # Try common profile patterns
            username = getpass.getuser()
            for profile_dir in [username, "default", "default-release"]:
                candidate = os.path.join(firefox_home, profile_dir)
                if os.path.exists(candidate):
                    profile_path = candidate
                    break

            # If no profile found, try to find any directory with places.sqlite
            if not profile_path:
                try:
                    for item in os.listdir(firefox_home):
                        candidate = os.path.join(firefox_home, item)
                        if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, "places.sqlite")):
                            profile_path = candidate
                            break
                except OSError:
                    pass

            # Run foxmarks command
            cmd = ["foxmarks", "bookmarks"]
            if profile_path:
                cmd = ["foxmarks", "--profile-path", profile_path, "bookmarks"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise RuntimeError(f"foxmarks failed: {result.stderr}")

            # Parse bookmarks
            bookmarks = []
            for line in result.stdout.strip().split('\n'):
                if line.strip() and ';' in line:
                    parts = line.split(';', 1)  # Split only on first semicolon
                    if len(parts) == 2:
                        title, url = parts
                        bookmarks.append(BookmarkItem(title.strip(), url.strip()))

            GLib.idle_add(self._process_bookmarks, bookmarks)

        except Exception as e:
            print(f"Error fetching bookmarks: {e}")
            GLib.idle_add(self._handle_error, str(e))

    def _process_bookmarks(self, bookmarks):
        if not self.get_visible() or not self.get_application():
            return GLib.SOURCE_REMOVE

        self._bookmark_store.remove_all()
        self._all_bookmarks = bookmarks

        for bookmark in bookmarks:
            self._bookmark_store.append(bookmark)

        if self._bookmark_store.get_n_items() > 0:
            self._content_stack.set_visible_child_name("results")
            self._selection_model.set_selected(0)
            self._scroll_to_selected()
        else:
            self._empty_page.set_title("No Bookmarks Found")
            self._empty_page.set_description("Your Firefox profile appears to have no bookmarks.")
            self._content_stack.set_visible_child_name("empty")

        return GLib.SOURCE_REMOVE

    def _handle_error(self, error_message):
        if not self.get_visible() or not self.get_application():
            return GLib.SOURCE_REMOVE

        self._error_page.set_description(str(error_message))
        self._content_stack.set_visible_child_name("error")
        return GLib.SOURCE_REMOVE


class BookmarksApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID, **kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


if __name__ == "__main__":
    app = BookmarksApp()
    app.run(None)
