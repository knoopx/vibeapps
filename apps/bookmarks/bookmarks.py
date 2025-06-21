#!/usr/bin/env python3
import gi
import threading
import os
import getpass
import sqlite3
import shutil
import tempfile
from typing import Optional

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
gi.require_version("WebKit", "6.0")

from gi.repository import Gtk, Adw, GLib, GObject, Gdk, Pango, Gio, WebKit


from picker_window import PickerItem
from picker_window_with_preview import PickerWindowWithPreview

APP_ID = "net.knoopx.bookmarks"


class BookmarkItem(PickerItem):
    __gtype_name__ = "BookmarkItem"
    title = GObject.Property(type=str)
    url = GObject.Property(type=str)
    date_added = GObject.Property(type=int, default=0)

    def __init__(self, title, url, date_added=0):
        super().__init__()
        self.title = title
        self.url = url
        self.date_added = date_added


class BookmarksWindow(PickerWindowWithPreview):
    def __init__(self, **kwargs):
        super().__init__(
            title="Bookmarks",
            search_placeholder="Search bookmarks...",
            **kwargs,
        )
        self._all_bookmarks = []

    def get_item_type(self):
        return BookmarkItem

    def create_preview_widget(
        self, item: Optional[BookmarkItem]
    ) -> Optional[Gtk.Widget]:
        """Create a webkit preview widget for the selected bookmark."""
        if not item or not item.url:
            return None

        try:
            # Create WebView with settings that match working webkit-shell.py
            webview = WebKit.WebView()

            # Configure WebKit settings based on working webkit-shell.py
            settings = WebKit.Settings.new()
            settings.set_enable_developer_extras(True)
            settings.set_enable_javascript(True)
            settings.set_enable_write_console_messages_to_stdout(True)
            settings.set_property("allow-file-access-from-file-urls", True)
            settings.set_property("allow-universal-access-from-file-urls", True)
            settings.set_property("enable-developer-extras", True)
            settings.set_property("enable-javascript", True)
            settings.set_property("enable-media-stream", True)
            settings.set_property("enable-site-specific-quirks", True)
            settings.set_property("enable-webgl", True)
            settings.set_property("enable-write-console-messages-to-stdout", True)

            webview.set_settings(settings)
            webview.set_vexpand(True)
            webview.set_hexpand(True)

            # Handle navigation to prevent leaving the preview
            webview.connect("decide-policy", self._on_webview_decide_policy)

            # Add loading state handling
            webview.connect("load-changed", self._on_webview_load_changed)

            # Add error handling for load failures
            webview.connect("load-failed", self._on_webview_load_failed)

            # Load the URL
            webview.load_uri(item.url)

            return webview

        except Exception as e:
            print(f"Error creating webkit preview: {e}")
            # Fallback to simple text preview
            return self._create_fallback_preview(item)

    def _create_fallback_preview(self, item: BookmarkItem) -> Gtk.Widget:
        """Create a simple text-based preview as fallback."""
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        preview_box.set_margin_start(16)
        preview_box.set_margin_end(16)
        preview_box.set_margin_top(16)
        preview_box.set_margin_bottom(16)

        # Title
        title_label = Gtk.Label()
        title_label.set_text(item.title)
        title_label.set_halign(Gtk.Align.START)
        title_label.add_css_class("title-1")
        title_label.set_wrap(True)
        preview_box.append(title_label)

        # URL
        url_frame = Gtk.Frame()
        url_frame.add_css_class("card")

        url_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        url_box.set_margin_start(12)
        url_box.set_margin_end(12)
        url_box.set_margin_top(12)
        url_box.set_margin_bottom(12)

        url_header = Gtk.Label()
        url_header.set_text("URL")
        url_header.set_halign(Gtk.Align.START)
        url_header.add_css_class("heading")
        url_box.append(url_header)

        url_label = Gtk.Label()
        url_label.set_text(item.url)
        url_label.set_halign(Gtk.Align.START)
        url_label.set_wrap(True)
        url_label.set_selectable(True)
        url_box.append(url_label)

        url_frame.set_child(url_box)
        preview_box.append(url_frame)

        # Status message
        status_label = Gtk.Label()
        status_label.set_text("WebKit preview unavailable")
        status_label.set_halign(Gtk.Align.CENTER)
        status_label.add_css_class("dim-label")
        preview_box.append(status_label)

        return preview_box

    def _on_webview_decide_policy(self, webview, decision, decision_type):
        """Handle webview navigation policy to prevent leaving the preview."""
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            navigation_action = decision.get_navigation_action()
            if (
                navigation_action.get_navigation_type()
                == WebKit.NavigationType.LINK_CLICKED
            ):
                # Prevent following links in the preview
                decision.ignore()
                return True
        return False

    def _on_webview_load_changed(self, webview, load_event):
        """Handle webview load state changes."""
        if load_event == WebKit.LoadEvent.STARTED:
            print(f"Loading preview for: {webview.get_uri()}")
        elif load_event == WebKit.LoadEvent.FINISHED:
            print(f"Finished loading preview for: {webview.get_uri()}")

    def _on_webview_load_failed(self, webview, load_event, failing_uri, error):
        """Handle webview load failures."""
        print(f"Failed to load preview for: {failing_uri} - Error: {error.message}")
        # Try to load a simple error page or fallback
        error_html = f"""
        <html>
        <head><title>Load Failed</title></head>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h2>Failed to load website</h2>
            <p>Could not load: <strong>{failing_uri}</strong></p>
            <p>Error: {error.message}</p>
            <p><small>This might be due to network issues, HTTPS certificate problems, or the website being unavailable.</small></p>
        </body>
        </html>
        """
        webview.load_html(error_html, None)
        return True

    def load_initial_data(self):
        self.set_loading(True)
        thread = threading.Thread(target=self._fetch_bookmarks)
        thread.daemon = True
        thread.start()

    def on_search_changed(self, query):
        self.remove_all_items()
        if not query:
            for bookmark in self._all_bookmarks:
                self.add_item(bookmark)
        else:
            query_lower = query.lower()
            for bookmark in self._all_bookmarks:
                if (
                    query_lower in bookmark.title.lower()
                    or query_lower in bookmark.url.lower()
                ):
                    self.add_item(bookmark)
        if self._item_store.get_n_items() > 0:
            self._show_results()
            # Automatically select the first item to show its preview
            self._selection_model.set_selected(0)
            # Force update the preview immediately
            self.force_preview_update()
        else:
            self._show_empty(
                title=f"No Results for '{query}'",
                description="Try a different search term.",
            )

    def on_item_activated(self, item):
        if item and item.url:
            Gtk.show_uri(self, item.url, Gdk.CURRENT_TIME)
            GLib.timeout_add(50, self.get_application().quit)

    def setup_list_item(self, list_item):
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )
        title_label = Gtk.Label(
            halign=Gtk.Align.START,
            xalign=0,
            wrap=True,
            wrap_mode=Pango.WrapMode.WORD_CHAR,
        )
        title_label.add_css_class("title-4")
        url_label = Gtk.Label(
            halign=Gtk.Align.START, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.CHAR
        )
        url_label.add_css_class("dim-label")
        url_label.add_css_class("caption")
        main_box.append(title_label)
        main_box.append(url_label)
        list_item.set_child(main_box)

    def bind_list_item(self, list_item, item):
        main_box = list_item.get_child()
        title_label = main_box.get_first_child()
        url_label = title_label.get_next_sibling()
        title_label.set_markup(f"<b>{GLib.markup_escape_text(item.title)}</b>")
        url_label.set_text(item.url)

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        if not item:
            return None
        menu_model = Gio.Menu.new()
        menu_model.append("Open Bookmark", "context.on_open_bookmark_action")
        menu_model.append("Open in External Browser", "context.on_open_external_action")
        menu_model.append("Copy URL", "context.on_copy_url_action")
        menu_model.append("Copy Title", "context.on_copy_title_action")
        return menu_model

    def on_open_bookmark_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and selected_item.url:
            self.on_item_activated(selected_item)

    def on_open_external_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and selected_item.url:
            Gtk.show_uri(self, selected_item.url, Gdk.CURRENT_TIME)

    def on_copy_url_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and hasattr(selected_item, "url"):
            clipboard = self.get_clipboard()
            clipboard.set_text(selected_item.url, -1)

    def on_copy_title_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and hasattr(selected_item, "title"):
            clipboard = self.get_clipboard()
            clipboard.set_text(selected_item.title, -1)

    def get_empty_icon(self):
        return "user-bookmarks-symbolic"

    def get_loading_icon(self):
        return "user-bookmarks-symbolic"

    def get_empty_title(self):
        return "Search Bookmarks"

    def get_empty_description(self):
        return "Type your query in the search bar above."

    def get_preview_empty_title(self) -> str:
        """Get the title for the empty preview state."""
        return "No Bookmark Selected"

    def get_preview_empty_description(self) -> str:
        """Get the description for the empty preview state."""
        return "Select a bookmark to see its preview"

    def get_preview_empty_icon(self) -> str:
        """Get the icon for the empty preview state."""
        return "user-bookmarks-symbolic"

    def on_preview_item_changed(self, item: Optional[BookmarkItem]) -> None:
        """Called when the preview item changes."""
        if item:
            print(f"Previewing bookmark: {item.title}")

    def _fetch_bookmarks(self):
        try:
            firefox_home = os.path.expanduser("~/.mozilla/firefox")
            profile_path = None
            username = getpass.getuser()
            for profile_dir in [username, "default", "default-release"]:
                candidate = os.path.join(firefox_home, profile_dir)
                if os.path.exists(candidate):
                    profile_path = candidate
                    break
            if not profile_path:
                try:
                    for item in os.listdir(firefox_home):
                        candidate = os.path.join(firefox_home, item)
                        if os.path.isdir(candidate) and os.path.exists(
                            os.path.join(candidate, "places.sqlite")
                        ):
                            profile_path = candidate
                            break
                except OSError:
                    pass
            if not profile_path:
                raise RuntimeError("Could not find Firefox profile directory")
            db_path = os.path.join(profile_path, "places.sqlite")
            if not os.path.exists(db_path):
                raise RuntimeError(f"places.sqlite not found at {db_path}")
            temp_db = None
            try:
                temp_fd, temp_db = tempfile.mkstemp(
                    suffix=".sqlite", prefix="bookmarks_"
                )
                os.close(temp_fd)
                shutil.copy2(db_path, temp_db)
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                query = "SELECT p.title, p.url, b.dateAdded FROM moz_places p JOIN moz_bookmarks b ON p.id = b.fk WHERE b.type = 1 AND p.url IS NOT NULL AND p.title IS NOT NULL ORDER BY b.dateAdded DESC"
                cursor.execute(query)
                results = cursor.fetchall()
                conn.close()
            finally:
                if temp_db and os.path.exists(temp_db):
                    try:
                        os.unlink(temp_db)
                    except OSError:
                        pass
            bookmarks = []
            for title, url, date_added in results:
                if title and url:
                    date_added_seconds = date_added // 1000000 if date_added else 0
                    bookmarks.append(
                        BookmarkItem(title.strip(), url.strip(), date_added_seconds)
                    )
            GLib.idle_add(self._process_bookmarks, bookmarks)
        except Exception as e:
            print(f"Error fetching bookmarks: {e}")
            GLib.idle_add(self._handle_error, str(e))

    def _process_bookmarks(self, bookmarks):
        if not self.get_visible() or not self.get_application():
            return GLib.SOURCE_REMOVE
        self._all_bookmarks = bookmarks
        for bookmark in bookmarks:
            self.add_item(bookmark)
        if self._item_store.get_n_items() > 0:
            self._show_results()
            # Automatically select the first item to show its preview
            self._selection_model.set_selected(0)
            # Force update the preview immediately
            self.force_preview_update()
        else:
            self._show_empty(
                title="No Bookmarks Found",
                description="Your Firefox profile appears to have no bookmarks.",
            )
        self.set_loading(False)
        return GLib.SOURCE_REMOVE

    def _handle_error(self, error_message):
        if not self.get_visible() or not self.get_application():
            return GLib.SOURCE_REMOVE
        self._show_error(str(error_message))
        self.set_loading(False)
        return GLib.SOURCE_REMOVE


class BookmarksApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID, **kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = BookmarksWindow(application=app)
        self.win.present()


if __name__ == "__main__":
    app = BookmarksApp()
    app.run(None)
