#!/usr/bin/env python

from typing import Dict
import concurrent.futures
import gi
import os
import re
import threading
import json
import time
import orjson  # Add this import

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

MUSIC_DIR = os.path.expanduser("~/Music")


class SearchFilter(Gtk.Filter):
    def __init__(self):
        super().__init__()
        self.search_text = ""
        self.pending_text = ""
        self._update_timeout = None
        self.show_starred_only = False
        # Add regex patterns for CD notations
        self.cd_patterns = [
            r"\s+CD\d+",  # Matches: CD1, CD2, CD3, etc
            r"\s+\d+CD",  # Matches: 2CD, 3CD, etc
            r"\s+CDS\d+",  # Matches: CDS1, CDS2, etc
        ]

    def set_search_text(self, search_text: str):
        self.pending_text = search_text.lower()
        # Cancel any pending update
        if self._update_timeout:
            GLib.source_remove(self._update_timeout)
        # Schedule update in 150ms
        self._update_timeout = GLib.timeout_add(150, self._do_update_filter)

    def _do_update_filter(self):
        self.search_text = self.pending_text
        self.changed(Gtk.FilterChange.DIFFERENT)
        self._update_timeout = None
        return GLib.SOURCE_REMOVE

    def set_show_starred_only(self, show_starred):
        self.show_starred_only = show_starred
        self.changed(Gtk.FilterChange.DIFFERENT)

    def do_match(self, item: Release) -> bool:
        if self.show_starred_only and not item.starred:
            return False

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

            .loading-page.compact {
                font-size: 0.9em;
            }

            .loading-page.compact picture {
                -gtk-icon-size: 32px;
            }

            .ghost-star {
                padding: 4px;
                min-width: 24px;
                min-height: 24px;
                opacity: 0.5;
                background: none;
                color: currentColor;
            }

            .ghost-star:hover {
                opacity: 1;
                background: none;
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

        # Add star filter button
        self.star_filter = Gtk.ToggleButton(icon_name="non-starred-symbolic")
        self.star_filter.add_css_class("flat")
        self.star_filter.add_css_class("ghost-star")
        self.star_filter.connect("toggled", self._on_star_filter_toggled)
        self.header.pack_end(self.star_filter)  # Changed from pack_start to pack_end

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
        loading_page = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            css_classes=["loading-page", "compact"],
        )
        spinner = Gtk.Spinner(
            spinning=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            width_request=48,  # Set explicit size
            height_request=48,  # Set explicit size
        )
        loading_page.append(spinner)

        # Add CSS for compact loading page
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

            .loading-page.compact {
                font-size: 0.9em;
            }

            .loading-page.compact spinner {
                min-width: 48px;
                min-height: 48px;
            }

            .loading-page.compact picture {
                -gtk-icon-size: 32px;
            }

            .ghost-star {
                padding: 4px;
                min-width: 24px;
                min-height: 24px;
                opacity: 0.5;
                background: none;
                color: currentColor;
            }

            .ghost-star:hover {
                opacity: 1;
                background: none;
            }
        """.encode()
        )

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

    def _on_star_filter_toggled(self, button):
        if button.get_active():
            button.set_icon_name("starred-symbolic")
        else:
            button.set_icon_name("non-starred-symbolic")
        self.search_filter.set_show_starred_only(button.get_active())

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

        # Add star button
        star_button = Gtk.Button(icon_name="non-starred-symbolic")
        star_button.add_css_class("flat")
        star_button.add_css_class("ghost-star")
        star_button.set_valign(Gtk.Align.CENTER)
        box.append(star_button)

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
        if release.group:
            label_pill = Gtk.Label(label=release.group)
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

        # Update star button
        star_button = box.get_last_child()
        star_button.set_icon_name(
            "starred-symbolic" if release.starred else "non-starred-symbolic"
        )
        star_button.connect("clicked", self._on_star_clicked, release)

    def _on_star_clicked(self, button, release):
        release.starred = not release.starred
        button.set_icon_name(
            "starred-symbolic" if release.starred else "non-starred-symbolic"
        )
        # Save changes to cache
        self.get_application().save_to_cache()

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
            folder = os.path.dirname(self.selected_release.tracks[0].path)
            launcher = Gio.SubprocessLauncher.new(
                Gio.SubprocessFlags.SEARCH_PATH_FROM_ENVP
                | Gio.SubprocessFlags.STDERR_PIPE
                | Gio.SubprocessFlags.STDOUT_PIPE
            )
            # Launch process detached from our window
            try:
                launcher.spawnv(["amberol", folder])
            except GLib.Error as e:
                print(f"Failed to launch Amberol: {e.message}")

    def do_close_request(self):
        self.get_application().quit()
        return True

    def _on_search_changed(self, search):
        # Move to idle callback to avoid blocking UI
        GLib.idle_add(self.search_filter.set_search_text, search.get_text())

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
        self.window = None  # Add window reference
        # Get XDG_DATA_HOME or fallback to ~/.local/share
        data_home = os.environ.get(
            "XDG_DATA_HOME", os.path.expanduser("~/.local/share")
        )
        app_data_dir = os.path.join(data_home, "music")

        # Ensure directory exists
        os.makedirs(app_data_dir, exist_ok=True)

        self.cache_file = os.path.join(app_data_dir, "releases.jsonl")
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
        self.cached_dirs = {}  # Store cached directory timestamps
        self.cache_lock = threading.Lock()  # Add lock for thread safety
        self._save_timer = None  # Add timer for debounced saving
        self._pending_save = False
        self._shutdown_event = threading.Event()
        self._active_threads = []

    def load_cached_data(self):
        """Load releases from cache by streaming JSONL"""
        window = self.get_active_window()
        window.start_loading()

        def load_cache_thread():
            batch_size = 500  # Larger batch for fewer UI updates
            current_batch = []
            releases_loaded = 0
            # total_lines = 0 # No longer used for primary progress logic

            try:
                if os.path.exists(self.cache_file):
                    total_file_size = os.path.getsize(self.cache_file)
                    bytes_read = 0

                    with open(self.cache_file, "rb") as f:  # Open in binary mode for orjson
                        # Read header first
                        header_line = f.readline()
                        if not header_line:
                            GLib.idle_add(self.on_cache_loaded)
                            return

                        bytes_read += len(header_line)
                        try:
                            header = orjson.loads(header_line)
                            self.last_scan_time = header.get("timestamp", 0)
                            self.cached_dirs = header.get("cached_dirs", {})
                        except orjson.JSONDecodeError as e:
                            print(f"Error parsing cache header: {e}")
                            GLib.idle_add(self.on_cache_loaded) # Proceed to scan if header fails
                            return

                        # Process remaining lines one at a time
                        for line_number, line in enumerate(f, 1): # Start line_number from 1 for content lines
                            line_bytes = len(line)
                            bytes_read += line_bytes
                            try:
                                release_data = orjson.loads(line)
                                release = Release.from_json(release_data)
                                key = release.path

                                if key and key not in self.all_releases:
                                    self.all_releases[key] = release
                                    current_batch.append(release)
                                    releases_loaded += 1

                                    # Send batch when it reaches size limit
                                    if len(current_batch) >= batch_size:
                                        GLib.idle_add(self._apply_cached_batch, current_batch[:])
                                        current_batch = []

                                # Update progress periodically
                                if line_number % 200 == 0: # Update every 200 lines
                                    GLib.idle_add(
                                        window.update_progress,
                                        bytes_read,
                                        total_file_size,
                                    )

                            except orjson.JSONDecodeError as e:
                                print(f"Error parsing cache line {line_number + 1}: {e}") # +1 because header was line 0 effectively
                                continue
                            except Exception as e:
                                print(f"Error processing release from cache line {line_number + 1}: {e}")
                                continue

                    # Send final batch if any remains
                    if current_batch:
                        GLib.idle_add(self._apply_cached_batch, current_batch)

                    # Ensure progress reaches 100% if file was processed
                    if total_file_size > 0 : # Avoid division by zero if cache_file was just a header
                        GLib.idle_add(window.update_progress, total_file_size, total_file_size)

            except FileNotFoundError:
                print(f"Cache file not found: {self.cache_file}")
            except Exception as e:
                print(f"Error loading cache: {e}")
            finally:
                # Always start library scan after cache load attempt
                GLib.idle_add(self.on_cache_loaded)

        thread = threading.Thread(target=load_cache_thread, daemon=True)
        self._active_threads.append(thread)
        thread.start()

    def on_cache_loaded(self):
        """Callback after cache is loaded to start scanning."""
        self.load_library()
        return False

    def _apply_cached_batch(self, releases):
        """Apply a batch of cached releases to the UI"""
        window = self.get_active_window()
        if window and releases:
            window.albums_model.splice(window.albums_model.get_n_items(), 0, releases)
            # Only set visible child if this is the first batch
            if window.stack.get_visible_child_name() != "albums":
                window.stack.set_visible_child_name("albums")
        return False

    def do_activate(self):
        # Only create one window
        if not self.window:
            self.window = MainWindow(application=self)
        self.window.present()
        self.load_cached_data()

    def load_library(self):
        window = self.get_active_window()
        window.start_loading()
        if not self.all_releases:
            self.all_releases = {}
            window.albums_model.remove_all()

        def scan_thread():
            try:
                music_dir = MUSIC_DIR
                new_dirs = []
                cached_dirs = []

                # Check shutdown flag early
                if self._shutdown_event.is_set():
                    return

                # First pass to categorize directories
                try:
                    for root, dirs, files in os.walk(music_dir, followlinks=True):
                        # Check shutdown flag during walk
                        if self._shutdown_event.is_set():
                            return

                        # Resolve real path if it's a symlink
                        real_root = os.path.realpath(root)

                        if any(f.lower().endswith((".mp3", ".flac")) for f in files):
                            dir_mtime = os.path.getmtime(real_root)
                            cached_time = self.cached_dirs.get(real_root, 0)

                            if real_root not in self.cached_dirs or dir_mtime > cached_time:
                                new_dirs.append(real_root)
                            else:
                                cached_dirs.append(real_root)
                except Exception as e:
                    print(f"Error walking music directory {music_dir}: {e}")
                    GLib.idle_add(self.on_scan_complete)
                    return

                total_directories = len(new_dirs) + len(cached_dirs)
                if total_directories == 0:
                    print("No music directories found.")
                    GLib.idle_add(self.on_scan_complete)
                    return

                print(
                    f"Found {len(new_dirs)} new/modified and {len(cached_dirs)} cached directories"
                )

                # Process new/modified directories first
                processed_directories = 0
                batch_size = 50
                current_batch = []

                # Function to process directories with progress updates
                def process_directories(directories):
                    nonlocal processed_directories, current_batch

                    futures = {
                        self.executor.submit(
                            self.scanner.scan_single_directory, dir_path
                        ): dir_path
                        for dir_path in directories
                    }

                    for future in concurrent.futures.as_completed(futures):
                        # Check shutdown flag during processing
                        if self._shutdown_event.is_set():
                            for f in futures:
                                f.cancel()
                            return

                        dir_path = futures[future]
                        processed_directories += 1
                        try:
                            releases_in_dir = future.result()
                            for release in releases_in_dir:
                                key = (
                                    os.path.dirname(release.tracks[0].path)
                                    if release.tracks
                                    else None
                                )
                                if key and (key not in self.all_releases):
                                    self.all_releases[key] = release
                                    current_batch.append(release)
                                    self.cached_dirs[key] = os.path.getmtime(key)

                                    if len(current_batch) >= batch_size:
                                        sorted_batch = sorted(
                                            current_batch,
                                            key=lambda r: f"{r.artist.lower()}{r.title.lower()}",
                                        )
                                        GLib.idle_add(
                                            self.on_batch_complete, sorted_batch
                                        )
                                        current_batch = []

                        except Exception as exc:
                            print(f"Error scanning directory {dir_path}: {exc}")

                        GLib.idle_add(
                            window.update_progress,
                            processed_directories,
                            total_directories,
                        )

                # Process new directories first
                process_directories(new_dirs)
                # Then process cached directories
                process_directories(cached_dirs)

                # Process final batch
                if current_batch:
                    sorted_batch = sorted(
                        current_batch,
                        key=lambda r: f"{r.artist.lower()}{r.title.lower()}",
                    )
                    GLib.idle_add(self.on_batch_complete, sorted_batch)

                GLib.idle_add(
                    window.update_progress, total_directories, total_directories
                )
                GLib.idle_add(self.on_scan_complete)
            finally:
                GLib.idle_add(window.stop_loading)
                if thread in self._active_threads:
                    self._active_threads.remove(thread)

        thread = threading.Thread(target=scan_thread, daemon=True)
        self._active_threads.append(thread)
        thread.start()

    # Modified on_batch_complete to just append the batch
    def on_batch_complete(self, batch):
        """Appends a batch of releases to the UI model."""

        def update_ui():
            window = self.get_active_window()
            if window:
                with self.cache_lock:  # Protect UI updates
                    window.albums_model.splice(
                        window.albums_model.get_n_items(), 0, batch
                    )
                    # Switch to albums view as soon as we have any releases
                    if batch:
                        window.stack.set_visible_child_name("albums")
            return False

        # Schedule a debounced cache save
        self.schedule_cache_save()
        GLib.idle_add(update_ui)
        return False

    def schedule_cache_save(self):
        """Schedule a debounced cache save operation"""
        if self._save_timer:
            GLib.source_remove(self._save_timer)
        self._save_timer = GLib.timeout_add_seconds(5, self._do_save_cache)
        self._pending_save = True

    def _do_save_cache(self):
        """Save cache using JSONL format for better streaming"""
        if not self._pending_save:
            return False

        def save_thread():
            try:
                with self.cache_lock:
                    # Create a static copy of the data we want to save
                    releases_to_save = list(self.all_releases.values())
                    cached_dirs_copy = dict(self.cached_dirs)

                    # Write directly to the cache file
                    with open(self.cache_file, "wb") as f:  # Write in binary mode for orjson
                        # Write header as first line
                        header = {
                            "timestamp": time.time(),
                            "cached_dirs": cached_dirs_copy,
                        }
                        f.write(orjson.dumps(header) + b"\n")

                        # Write each release as a separate line
                        for release in releases_to_save:
                            f.write(orjson.dumps(release.to_json()) + b"\n")

                    self._pending_save = False

            except Exception as e:
                print(f"Error saving cache: {e}")

        thread = threading.Thread(target=save_thread, daemon=True)
        thread.start()
        return False

    def save_to_cache(self):
        """Schedule an immediate cache save"""
        self.schedule_cache_save()

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

    def quit(self):
        print("Shutting down threads...")
        self._shutdown_event.set()

        # First attempt graceful shutdown of executor
        self.executor.shutdown(wait=False)
        try:
            # Clear internal thread references
            self.executor._threads.clear()
            # Final shutdown attempt
            self.executor.shutdown(wait=True)
        except Exception as e:
            print(f"Warning: Error during executor shutdown: {e}")

        # Then handle active threads
        remaining_threads = []
        for thread in self._active_threads:
            if thread.is_alive():
                try:
                    thread.join(timeout=1.0)
                    if thread.is_alive():
                        remaining_threads.append(thread)
                except Exception as e:
                    print(f"Warning: Error joining thread: {e}")

        if remaining_threads:
            print(f"Warning: {len(remaining_threads)} threads didn't shut down cleanly")

        # Save cache one last time before quitting
        if self._pending_save:
            self._do_save_cache()

        super().quit()


if __name__ == "__main__":
    Gst.init(None)
    app = MusicPlayer()
    app.run(None)
