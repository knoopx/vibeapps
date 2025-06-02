#!/usr/bin/env python3
import gi
import json
import requests
import threading
from typing import Optional
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, GObject, Gdk, Gio
from picker_window import PickerWindow, PickerItem
APP_ID = 'net.knoopx.nix-packages'
SEARCH_URL = 'https://search.nixos.org/backend/latest-43-nixos-unstable/_search'
AUTH_TOKEN = 'Basic YVdWU0FMWHBadjpYOGdQSG56TDUyd0ZFZWt1eHNmUTljU2g='

class PackageItem(PickerItem):
    __gtype_name__ = 'PackageItem'
    name = GObject.Property(type=str)
    version = GObject.Property(type=str)
    description = GObject.Property(type=str)
    homepage = GObject.Property(type=str)
    licenses = GObject.Property(type=str)

    def __init__(self, name, version, description, homepage, licenses):
        super().__init__()
        self.name = name
        self.version = version
        self.description = description if description else 'No description available.'
        self.homepage = homepage
        self.licenses = licenses

class NixPackagesWindow(PickerWindow):

    def __init__(self, **kwargs):
        super().__init__(title='Nix Package Search', search_placeholder='Search for packages...', **kwargs)
        self._current_search_thread = None

    def get_item_type(self):
        return PackageItem

    def use_list_view(self):
        return True

    def load_initial_data(self):
        pass

    def on_search_changed(self, query):
        self.set_loading(True)
        self.remove_all_items()
        if self._current_search_thread and self._current_search_thread.is_alive():
            print('Note: Previous search thread still running. New search queued.')
        self._current_search_thread = threading.Thread(target=self._perform_search_request, args=(query,))
        self._current_search_thread.daemon = True
        self._current_search_thread.start()

    def on_search_cleared(self):
        self.remove_all_items()
        self._show_empty()

    def on_item_activated(self, item):
        if item and item.homepage:
            Gtk.show_uri(self, item.homepage, Gdk.CURRENT_TIME)
            GLib.timeout_add(50, self.get_application().quit)

    def setup_list_item(self, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=12, margin_end=12)
        title_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=True)
        version_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=True, css_classes=['dim-label'])
        desc_label = Gtk.Label(halign=Gtk.Align.START, xalign=0, wrap=True, lines=3)
        box.append(title_label)
        box.append(version_label)
        box.append(desc_label)
        list_item.set_child(Adw.ActionRow(child=box))

    def bind_list_item(self, list_item, item):
        action_row = list_item.get_child()
        box = action_row.get_child()
        title_label = box.get_first_child()
        version_label = title_label.get_next_sibling()
        desc_label = version_label.get_next_sibling()
        title_label.set_markup(f'<big><b>{GLib.markup_escape_text(item.name)}</b></big>')
        version_label.set_text(f'Version: {item.version}')
        desc_label.set_text(item.description)

    def get_empty_icon(self):
        return 'system-search-symbolic'

    def get_loading_icon(self):
        return 'find-location-symbolic'

    def get_empty_title(self):
        return 'Search for Nix Packages'

    def get_empty_description(self):
        return 'Type your query in the search bar above.'

    def get_context_menu_actions(self) -> dict:
        return {'open_homepage': 'on_open_homepage_action', 'copy_name': 'on_copy_name_action', 'copy_description': 'on_copy_description_action'}

    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        if not item:
            return None
        menu_model = Gio.Menu.new()
        if item.homepage:
            menu_model.append('Open Homepage', 'context.open_homepage')
        menu_model.append('Copy Package Name', 'context.copy_name')
        menu_model.append('Copy Description', 'context.copy_description')
        return menu_model

    def on_open_homepage_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item and selected_item.homepage:
            Gtk.show_uri(self, selected_item.homepage, Gdk.CURRENT_TIME)

    def on_copy_name_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set(selected_item.name)

    def on_copy_description_action(self, action, param):
        selected_item = self.get_selected_item()
        if selected_item:
            clipboard = self.get_clipboard()
            clipboard.set(selected_item.description)

    def _perform_search_request(self, query):
        query_payload = {'query': {'bool': {'must': {'multi_match': {'query': query, 'fields': ['package_attr_name^3', 'package_pname^2', 'package_description', 'package_programs'], 'operator': 'and'}}, 'filter': [{'term': {'type': 'package'}}]}}, 'size': 50, 'sort': ['_score'], '_source': ['package_attr_name', 'package_pversion', 'package_description', 'package_homepage', 'package_license_set'], 'track_total_hits': True}
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:138.0) Gecko/20100101 Firefox/138.0', 'Origin': 'https://search.nixos.org/', 'Accept': 'application/json', 'Authorization': AUTH_TOKEN}
        try:
            response = requests.post(SEARCH_URL, json=query_payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            GLib.idle_add(self._process_search_results, data, query)
        except requests.exceptions.RequestException as e:
            print(f'Request failed: {e}')
            GLib.idle_add(self._handle_search_error, f'Request failed: {e}')
        except json.JSONDecodeError as e:
            print(f'Failed to parse JSON response: {e}')
            GLib.idle_add(self._handle_search_error, f'Invalid response from server: {e}')

    def _handle_search_error(self, error_message):
        if not self.get_visible() or not self.get_application():
            return GLib.SOURCE_REMOVE
        self._show_error(str(error_message))
        return GLib.SOURCE_REMOVE

    def _process_search_results(self, data, original_query):
        if not self.get_visible() or not self.get_application():
            return GLib.SOURCE_REMOVE
        current_query_in_entry = self.get_search_text()
        if original_query != current_query_in_entry:
            print(f"Search query changed ('{current_query_in_entry}' vs '{original_query}'), discarding old results.")
            return GLib.SOURCE_REMOVE
        try:
            if not isinstance(data, dict) or 'hits' not in data:
                raise ValueError("Response JSON missing 'hits' structure")
            hits_outer_obj = data.get('hits')
            if not isinstance(hits_outer_obj, dict) or 'hits' not in hits_outer_obj:
                raise ValueError("Response JSON missing 'hits.hits' array")
            packages_array = hits_outer_obj.get('hits')
            if not isinstance(packages_array, list):
                raise ValueError("'hits.hits' is not an array")
            if not packages_array:
                self._show_empty(title=f"No Results for '{GLib.markup_escape_text(original_query)}'", description='Try a different search term or check for typos.')
                return GLib.SOURCE_REMOVE
            for hit_element in packages_array:
                if not isinstance(hit_element, dict) or '_source' not in hit_element:
                    print(f'Warning: Skipping invalid hit element: {hit_element}')
                    continue
                source_obj = hit_element.get('_source')
                if not isinstance(source_obj, dict):
                    print(f'Warning: Skipping hit with invalid _source: {source_obj}')
                    continue
                name = source_obj.get('package_attr_name', 'Unknown Package')
                version = source_obj.get('package_pversion', 'N/A')
                description = source_obj.get('package_description')
                homepage_list_raw = source_obj.get('package_homepage', [])
                homepage_list = []
                if isinstance(homepage_list_raw, list):
                    for hp in homepage_list_raw:
                        if isinstance(hp, str):
                            homepage_list.append(hp)
                homepage_url = homepage_list[0] if homepage_list else ''
                licenses_list_raw = source_obj.get('package_license_set', [])
                licenses_list = []
                if isinstance(licenses_list_raw, list):
                    for lic in licenses_list_raw:
                        if isinstance(lic, str):
                            licenses_list.append(lic)
                licenses_str = ', '.join(licenses_list)
                package = PackageItem(name, version, description, homepage_url, licenses_str)
                self.add_item(package)
            if self._item_store.get_n_items() > 0:
                self._show_results()
            else:
                self._show_empty(title=f"No displayable results for '{GLib.markup_escape_text(original_query)}'", description='The server returned data, but it could not be shown.')
        except Exception as e:
            print(f'Error processing search results: {e}')
            self._show_error(f'Could not process search results: {e}')
        return GLib.SOURCE_REMOVE

class NixPackageSearchApp(Adw.Application):

    def __init__(self, **kwargs):
        super().__init__(application_id=APP_ID, **kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = NixPackagesWindow(application=app)
        self.win.present()
if __name__ == '__main__':
    app = NixPackageSearchApp()
    app.run(None)