#!/usr/bin/env python

from typing import List, Dict
import concurrent.futures
import gi
import os
import re
import subprocess
import threading
import json
import time

from circular_progress import CircularProgress
from scanner import Scanner
from release import Release

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")

from gi.repository import (
    Gtk,
    Adw,
    GLib,
    Gio,
    Gst,
    Gdk,
    Pango,  # Add this import
)

MUSIC_DIR = "/mnt/music/"


class SearchFilter(Gtk.Filter):
    def __init__(self):
        super().__init__()
        self.search_text = ""
        # Add regex patterns for CD notations
        self.cd_patterns = [
            r"\s+CD\d+",  # Matches: CD1, CD2, CD3, etc
            r"\s+\d+CD",  # Matches: 2CD, 3CD, etc
            r"\s+CDS\d+",  # Matches: CDS1, CDS2, etc
        ]

    def set_search_text(self, search_text: str):
        self.search_text = search_text.lower()
        self.changed(Gtk.FilterChange.DIFFERENT)

    def do_match(self, item: Release) -> bool:
        if not self.search_text:
            return True

        terms = self.search_text.split()

        # Clean up title by removing all CD notations
        clean_title = item.title
        for pattern in self.cd_patterns:
            clean_title = re.sub(pattern, "", clean_title, flags=re.IGNORECASE)

        # Include label in the searchable text with cleaned title
        text = f"{clean_title} {item.artist} {item.year if item.year else ''} {item.tags_string} {item.label_string}".lower()

        return all(term in text for term in terms)

    def do_get_strictness(self):
        return Gtk.FilterMatch.SOME


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_release = None

        # Add CSS provider
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(
            """
            .tag-pill {
                background-color: alpha(currentColor, 0.1);
                border-radius: 4px;
                padding: 2px 8px;
                margin: 2px;
                font-size: 0.8em;
            }

            .rounded {
                border-radius: 6px;
                overflow: hidden;
            }

            .title-box {
                min-height: 24px;
            }

            .loading-page {
                margin: 48px;
            }
        """.encode()
        )
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.header = Adw.HeaderBar()
        self.search = Gtk.SearchEntry()
        self.search.set_hexpand(True)
        self.search.connect("search-changed", self._on_search_changed)
        self.header.set_title_widget(self.search)
        self.header.add_css_class("flat")

        # Add key controller for escape to focus search
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_press)
        self.add_controller(key_controller)

        # Create overlay for header
        self.header_overlay = Gtk.Overlay()
        self.header_overlay.set_child(self.header)

        # Add circular progress in an overlay
        progress_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        progress_box.set_halign(Gtk.Align.START)
        progress_box.set_valign(Gtk.Align.CENTER)
        progress_box.set_margin_start(12)

        self.progress = CircularProgress()
        self.progress.set_visible(False)
        progress_box.append(self.progress)

        self.header_overlay.add_overlay(progress_box)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.albums_page = Gtk.Box()
        self.queue_page = Gtk.Box()

        # Add loading page
        loading_page = Adw.StatusPage(
            title="Loading Music Library...",
            icon_name="folder-music-symbolic",
            css_classes=["loading-page"],
        )
        spinner = Gtk.Spinner(
            spinning=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER
        )
        loading_page.set_child(spinner)
        self.stack.add_named(loading_page, "loading")

        self.stack.add_titled(self.albums_page, "albums", "Albums")
        self.stack.add_titled(self.queue_page, "queue", "Queue")

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.append(self.header_overlay)  # Use header_overlay instead of header
        self.box.append(self.stack)

        self.set_content(self.box)
        self.set_default_size(800, 600)

        self.setup_albums_view()

    def setup_albums_view(self):
        self.albums_model = Gio.ListStore(item_type=Release)
        self.search_filter = SearchFilter()
        self.filtered_model = Gtk.FilterListModel(
            model=self.albums_model, filter=self.search_filter
        )

        # Add search controller
        self.search.set_margin_start(100)
        self.search.set_margin_end(100)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_album_setup)
        factory.connect("bind", self._on_album_bind)

        selection = Gtk.SingleSelection(model=self.filtered_model)
        selection.connect("selection-changed", self._on_selection_changed)
        self.albums_list = Gtk.ListView(model=selection, factory=factory)
        self.albums_list.add_css_class("navigation-sidebar")
        self.albums_list.connect("activate", self._on_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_child(self.albums_list)
        self.albums_page.append(scrolled)

    def _on_album_setup(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_hexpand(True)  # Make box expand horizontally
        box.set_margin_start(9)
        box.set_margin_end(9)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_valign(Gtk.Align.CENTER)

        # Add right-click gesture
        gesture = Gtk.GestureClick.new()
        gesture.set_button(Gdk.BUTTON_SECONDARY)  # Button 3 is right-click
        gesture.connect("pressed", self._on_album_right_click)
        box.add_controller(gesture)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        info_box.set_hexpand(True)
        info_box.set_valign(Gtk.Align.CENTER)

        upper_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        upper_box.set_hexpand(True)

        # Create box for just title and year that will stay together
        title_year_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_year_box.set_hexpand(True)

        title = Gtk.Label(xalign=0, css_classes=["title"])
        title.add_css_class("heading")
        title.set_valign(Gtk.Align.CENTER)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title_year_box.append(title)

        year = Gtk.Label(xalign=0)
        year.add_css_class("caption")
        year.add_css_class("dim-label")
        year.set_valign(Gtk.Align.CENTER)
        year.set_hexpand(True)
        year.set_wrap(False)
        title_year_box.append(year)

        # Add title_year_box to upper_box first
        upper_box.append(title_year_box)

        # Then add tags_box to upper_box
        tags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        tags_box.set_hexpand(False)
        upper_box.append(tags_box)

        artist = Gtk.Label(xalign=0, css_classes=["artist"])
        artist.add_css_class("caption")
        artist.set_opacity(0.7)
        artist.set_ellipsize(Pango.EllipsizeMode.END)  # Add ellipsis for overflow

        info_box.append(upper_box)
        info_box.append(artist)

        box.append(info_box)
        list_item.set_child(box)

    def _on_album_bind(self, factory, list_item):
        box = list_item.get_child()
        release = list_item.get_item()

        info_box = box.get_first_child()
        upper_box = info_box.get_first_child()
        title_year_box = upper_box.get_first_child()
        tags_box = upper_box.get_last_child()

        title = title_year_box.get_first_child()
        year = title_year_box.get_last_child()
        artist = info_box.get_last_child()

        title.set_text(release.title)
        year.set_text(str(release.year) if release.year else "")
        artist.set_text(release.artist)

        # Remove old tags and label pills
        while tags_box.get_first_child():
            tags_box.remove(tags_box.get_first_child())

        # Add label pill if it exists
        if release.label:
            label_pill = Gtk.Label(label=release.label)
            label_pill.add_css_class("tag-pill")
            label_pill.add_css_class("caption")
            label_pill.add_css_class("dim-label")
            tags_box.append(label_pill)

        # Use tags directly from release instead of track
        for tag in sorted(release.tags):
            pill = Gtk.Label(label=tag)
            pill.add_css_class("tag-pill")
            pill.add_css_class("caption")
            pill.add_css_class("dim-label")
            tags_box.append(pill)

    def _on_album_right_click(self, gesture, n_press, x, y):
        if n_press == 1:
            # Get the box widget that contains our gesture
            box = gesture.get_widget()
            if not box:
                return

            # Find the list item that contains this box
            list_item = box.get_parent()
            if not list_item:
                return

            # Get list item index based on parent/child relationship in ListView
            release_item = None
            idx = 0
            curr = self.albums_list.get_first_child()
            while curr:
                if curr == list_item:
                    release_item = self.filtered_model.get_item(idx)
                    break
                curr = curr.get_next_sibling()
                idx += 1

            if not release_item:
                return

            # Update current selection
            self.selected_release = release_item
            # Use set_selected for SingleSelection model
            self.albums_list.get_model().set_selected(idx)

            # Create the menu
            menu = Gio.Menu.new()
            menu.append("Reveal in File Explorer", "app.reveal_in_file_explorer")

            # Create and show the popover menu
            popover = Gtk.PopoverMenu.new_from_model(menu)
            popover.set_parent(box)  # Attach to the box widget
            popover.popup()

    def _on_selection_changed(self, selection, position, n_items):
        self.selected_release = selection.get_selected_item()

    def _on_row_activated(self, list_view, position):
        if self.selected_release and self.selected_release.tracks:
            # Launch amberol with the selected release's directory
            folder = os.path.dirname(self.selected_release.tracks[0].path)
            subprocess.run(["amberol", folder])

    def _on_search_changed(self, search):
        self.search_filter.set_search_text(search.get_text())

    def _on_key_press(self, controller, keyval, keycode, state):
        # Check if the pressed key is the Escape key
        if keyval == Gdk.KEY_Escape:
            self.search.grab_focus()
            return True  # Indicate that the event was handled
        return False  # Let other handlers process the event

    def has_releases(self):
        return self.albums_model.get_n_items() > 0

    def start_loading(self):
        self.progress.set_visible(True)
        self.progress.set_fraction(0)
        # Only show loading page if we have no releases
        if not self.has_releases():
            self.stack.set_visible_child_name("loading")

    def stop_loading(self):
        self.progress.set_visible(False)
        if self.has_releases():
            self.stack.set_visible_child_name("albums")
        else:
            # Show loading page if we still have no releases
            self.stack.set_visible_child_name("loading")

    def update_progress(self, current: int, total: int):
        self.progress.set_fraction(current / total if total > 0 else 0)


class MusicPlayer(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.knoopx.music")
        # Get XDG_DATA_HOME or fallback to ~/.local/share
        data_home = os.environ.get(
            "XDG_DATA_HOME", os.path.expanduser("~/.local/share")
        )
        app_data_dir = os.path.join(data_home, "music")

        # Ensure directory exists
        os.makedirs(app_data_dir, exist_ok=True)

        self.cache_file = os.path.join(app_data_dir, "releases.json")
        self.scanner = Scanner()
        self.all_releases: Dict[str, Release] = (
            {}
        )  # Store all releases here, keyed by directory path
        # Use a ThreadPoolExecutor for parallel scanning
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=os.cpu_count() or 4
        )
        # Add the reveal action
        self.add_action(Gio.SimpleAction.new("reveal_in_file_explorer", None))
        self.lookup_action("reveal_in_file_explorer").connect(
            "activate", self.on_reveal_in_file_explorer
        )
        self.last_scan_time = 0
        self.CACHE_TTL = 24 * 60 * 60  # 24 hours in seconds

    def load_cached_data(self):
        """Load releases from cache if available and not too old"""
        def load_cache_thread():
            try:
                if os.path.exists(self.cache_file):
                    cache_stat = os.stat(self.cache_file)
                    if time.time() - cache_stat.st_mtime < self.CACHE_TTL:
                        with open(self.cache_file, "r") as f:
                            data = json.load(f)
                            self.last_scan_time = data.get("timestamp", 0)
                            releases_data = data.get("releases", [])

                            releases = []
                            for release_data in releases_data:
                                try:
                                    release = Release.from_json(release_data)
                                    releases.append(release)
                                    # Update global collection
                                    key = (
                                        os.path.dirname(release.tracks[0].path)
                                        if release.tracks
                                        else None
                                    )
                                    if key:
                                        self.all_releases[key] = release
                                except Exception as e:
                                    print(f"Error loading release from cache: {e}")

                            # Sort releases before sending to UI
                            releases.sort(key=lambda r: f"{r.artist.lower()}{r.title.lower()}")
                            GLib.idle_add(self._apply_cached_data, releases)
                            return
            except Exception as e:
                print(f"Error loading cache: {e}")
            GLib.idle_add(self.load_library)

        thread = threading.Thread(target=load_cache_thread, daemon=True)
        thread.start()

    def _apply_cached_data(self, releases):
        """Apply cached data to the UI (called on main thread)"""
        window = self.get_active_window()
        if window:
            window.albums_model.splice(0, 0, releases)
            # Switch to albums view immediately if we loaded cached data
            if window.has_releases():
                window.stack.set_visible_child_name("albums")
        # Start fresh scan after loading cache
        self.load_library()
        return False

    def do_activate(self):
        win = MainWindow(application=self)
        win.present()
        # Just start loading cache, which will trigger scan when done
        self.load_cached_data()

    def load_library(self):
        window = self.get_active_window()
        window.start_loading()
        # Don't clear existing releases or model when starting scan
        if not self.all_releases:
            self.all_releases = {}
            window.albums_model.remove_all()

        def scan_thread():
            music_dir = MUSIC_DIR
            directories_to_scan = []
            total_directories = 0
            processed_directories = 0

            # First pass to find all directories containing music files
            # This part is still single-threaded but fast
            try:
                for root, dirs, files in os.walk(music_dir):
                    # Check if the directory itself contains music files
                    if any(f.lower().endswith((".mp3", ".flac")) for f in files):
                        directories_to_scan.append(root)
                        total_directories += 1
                    # Optionally, check subdirectories too if releases can span folders,
                    # but current Track parsing assumes release info is in the immediate parent dir name.
                    # For now, stick to directories directly containing music.

            except Exception as e:
                print(f"Error walking music directory {music_dir}: {e}")
                GLib.idle_add(self.on_scan_complete)
                return

            if total_directories == 0:
                print("No music directories found.")
                GLib.idle_add(self.on_scan_complete)
                return

            print(f"Found {total_directories} directories to scan.")
            # Submit scanning tasks to the thread pool
            futures = {
                self.executor.submit(
                    self.scanner.scan_single_directory, dir_path
                ): dir_path
                for dir_path in directories_to_scan
            }

            batch_size = 50  # Still process in batches for UI updates
            current_batch: List[Release] = []

            # Process results as they complete
            for future in concurrent.futures.as_completed(futures):
                processed_directories += 1
                dir_path = futures[future]
                try:
                    releases_in_dir = future.result()
                    for release in releases_in_dir:
                        # Use directory path as key for the global collection
                        key = (
                            os.path.dirname(release.tracks[0].path)
                            if release.tracks
                            else None
                        )
                        if key and key not in self.all_releases:
                            self.all_releases[key] = release
                            current_batch.append(release)

                            # Yield batch to UI thread when size is reached
                            if len(current_batch) >= batch_size:
                                # Sort batch before yielding
                                sorted_batch = sorted(
                                    current_batch,
                                    key=lambda r: f"{r.artist.lower()}{r.title.lower()}",
                                )
                                GLib.idle_add(self.on_batch_complete, sorted_batch)
                                current_batch = []

                except Exception as exc:
                    print(
                        f"Scanning directory {dir_path} generated an exception: {exc}"
                    )

                # Update progress after each directory is processed
                GLib.idle_add(
                    window.update_progress, processed_directories, total_directories
                )

            # Process any remaining items in the last batch
            if current_batch:
                sorted_batch = sorted(
                    current_batch, key=lambda r: f"{r.artist.lower()}{r.title.lower()}"
                )
                GLib.idle_add(self.on_batch_complete, sorted_batch)

            # Final progress update and completion signal
            GLib.idle_add(
                window.update_progress, total_directories, total_directories
            )  # Ensure 100%
            GLib.idle_add(self.on_scan_complete)

        # Start the thread that manages the thread pool
        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()
    # Modified on_batch_complete to just append the batch
    def on_batch_complete(self, batch):
        """Appends a batch of releases to the UI model."""
        def update_ui():
            window = self.get_active_window()
            if window:
                window.albums_model.splice(window.albums_model.get_n_items(), 0, batch)
            return False

        # Save to cache after batch is processed
        self.save_to_cache()
        # Ensure UI updates happen on the main thread
        GLib.idle_add(update_ui)
        return False

    def save_to_cache(self):
        """Save current releases to cache file"""
        try:
            # Create a static copy of releases before serializing
            releases_list = list(self.all_releases.values())
            data = {
                "timestamp": time.time(),
                "releases": [release.to_json() for release in releases_list],
            }
            with open(self.cache_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def on_scan_complete(self):
        """Signals the end of the scanning process."""
        window = self.get_active_window()
        window.stop_loading()
        print(f"Scan complete. Found {len(self.all_releases)} releases.")

    def on_reveal_in_file_explorer(self, action, parameter):
        """Reveals the selected release's directory in the file explorer."""
        window = self.get_active_window()
        release = window.selected_release
        if release and release.tracks:
            folder = os.path.dirname(release.tracks[0].path)
            try:
                # Use Gtk.show_uri to open the folder with the default file manager
                Gtk.show_uri(window, f"file://{folder}", Gdk.CURRENT_TIME)
            except Exception as e:
                print(f"Error opening directory {folder}: {e}")

if __name__ == "__main__":
    Gst.init(None)
    app = MusicPlayer()
    app.run(None)
