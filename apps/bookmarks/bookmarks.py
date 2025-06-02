#!/usr/bin/env python3
import gi
import threading
import os
import getpass
import sqlite3
import shutil
import tempfile
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Adw, GLib, GObject, Gdk, Pango, Gio
from typing import Optional
from picker_window import PickerWindow, PickerItem
APP_ID = 'net.knoopx.bookmarks'

class BookmarkItem(PickerItem):
    __gtype_name__ = 'BookmarkItem'
    title = GObject.Property(type=str)
    url = GObject.Property(type=str)
    date_added = GObject.Property(type=int, default=0)

    def __init__(self, title, url, date_added=0):
        super().__init__()
        self.title = title
        self.url = url
        self.date_added = date_added

class BookmarksWindow(PickerWindow):

    def __init__(self, **kwargs):
        super().__init__(title='Bookmarks', search_placeholder='Search bookmarks...', **kwargs)
        self._all_bookmarks = []

    def get_item_type(self):
        return BookmarkItem

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
                if query_lower in bookmark.title.lower() or query_lower in bookmark.url.lower():
                    self.add_item(bookmark)
        if self._item_store.get_n_items() > 0:
            self._show_results()
        else:
            self._show_empty(title=f"No Results for '{query}'", description='Try a different search term.')

    def on_item_activated(self, item):
        if item and item.url:
            Gtk.show_uri(self, item.url, Gdk.CURRENT_TIME)
            GLib.timeout_add(50, self.get_application().quit)

    def setup_list_item(self, list_item):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)
        title_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR)
        title_label.add_css_class('title-4')
        url_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=True, wrap_mode=Pango.WrapMode.CHAR)
        url_label.add_css_class('dim-label')
        url_label.add_css_class('caption')
        main_box.append(title_label)
        main_box.append(url_label)
        list_item.set_child(main_box)

    def bind_list_item(self, list_item, item):
        main_box = list_item.get_child()
        title_label = main_box.get_first_child()
        url_label = title_label.get_next_sibling()
        title_label.set_markup(f'<b>{GLib.markup_escape_text(item.title)}</b>')
        url_label.set_text(item.url)

    def get_context_menu_actions(self) -> dict:
        return {'open_bookmark': 'on_open_bookmark_action', 'copy_url': 'on_copy_url_action', 'copy_title': 'on_copy_title_action'}

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        if not item:
            return None
        menu_model = Gio.Menu.new()
        menu_model.append('Open Bookmark', 'context.open_bookmark')
        menu_model.append('Copy URL', 'context.copy_url')
        menu_model.append('Copy Title', 'context.copy_title')
        return menu_model

    def on_open_bookmark_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and selected_item.url:
            Gtk.show_uri(self, selected_item.url, Gdk.CURRENT_TIME)

    def on_copy_url_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and hasattr(selected_item, 'url'):
            clipboard = self.get_clipboard()
            value = GObject.Value(str, selected_item.url)
            provider = Gdk.ContentProvider.new_for_value(value)
            clipboard.set_content(provider)

    def on_copy_title_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and hasattr(selected_item, 'title'):
            clipboard = self.get_clipboard()
            value = GObject.Value(str, selected_item.title)
            provider = Gdk.ContentProvider.new_for_value(value)
            clipboard.set_content(provider)

    def get_empty_icon(self):
        return 'user-bookmarks-symbolic'

    def get_loading_icon(self):
        return 'user-bookmarks-symbolic'

    def get_empty_title(self):
        return 'Search Bookmarks'

    def get_empty_description(self):
        return 'Type your query in the search bar above.'

    def _fetch_bookmarks(self):
        try:
            firefox_home = os.path.expanduser('~/.mozilla/firefox')
            profile_path = None
            username = getpass.getuser()
            for profile_dir in [username, 'default', 'default-release']:
                candidate = os.path.join(firefox_home, profile_dir)
                if os.path.exists(candidate):
                    profile_path = candidate
                    break
            if not profile_path:
                try:
                    for item in os.listdir(firefox_home):
                        candidate = os.path.join(firefox_home, item)
                        if os.path.isdir(candidate) and os.path.exists(os.path.join(candidate, 'places.sqlite')):
                            profile_path = candidate
                            break
                except OSError:
                    pass
            if not profile_path:
                raise RuntimeError('Could not find Firefox profile directory')
            db_path = os.path.join(profile_path, 'places.sqlite')
            if not os.path.exists(db_path):
                raise RuntimeError(f'places.sqlite not found at {db_path}')
            temp_db = None
            try:
                temp_fd, temp_db = tempfile.mkstemp(suffix='.sqlite', prefix='bookmarks_')
                os.close(temp_fd)
                shutil.copy2(db_path, temp_db)
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                query = 'SELECT p.title, p.url, b.dateAdded FROM moz_places p JOIN moz_bookmarks b ON p.id = b.fk WHERE b.type = 1 AND p.url IS NOT NULL AND p.title IS NOT NULL ORDER BY b.dateAdded DESC'
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
                    bookmarks.append(BookmarkItem(title.strip(), url.strip(), date_added_seconds))
            GLib.idle_add(self._process_bookmarks, bookmarks)
        except Exception as e:
            print(f'Error fetching bookmarks: {e}')
            GLib.idle_add(self._handle_error, str(e))

    def _process_bookmarks(self, bookmarks):
        if not self.get_visible() or not self.get_application():
            return GLib.SOURCE_REMOVE
        self._all_bookmarks = bookmarks
        for bookmark in bookmarks:
            self.add_item(bookmark)
        if self._item_store.get_n_items() > 0:
            self._show_results()
        else:
            self._show_empty(title='No Bookmarks Found', description='Your Firefox profile appears to have no bookmarks.')
        return GLib.SOURCE_REMOVE

    def _handle_error(self, error_message):
        if not self.get_visible() or not self.get_application():
            return GLib.SOURCE_REMOVE
        self._show_error(str(error_message))
        return GLib.SOURCE_REMOVE

class BookmarksApp(Adw.Application):

    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID, **kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = BookmarksWindow(application=app)
        self.win.present()
if __name__ == '__main__':
    app = BookmarksApp()
    app.run(None)