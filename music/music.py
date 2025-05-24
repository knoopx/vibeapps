#!/usr/bin/env python

from math import pi
from pathlib import Path
from typing import Optional, List, Set, Dict
import concurrent.futures
import gi
import os
import re
import subprocess
import threading
from functools import cached_property
import functools

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")

from gi.repository import (
    Gtk,
    Adw,
    GLib,
    Gio,
    Gst,
    GObject,
    Gdk,
)


@GObject.type_register
class Release(GObject.GObject):
    title = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    internal_year = GObject.Property(type=int, default=-1)
    artwork_path = GObject.Property(type=str)
    label = GObject.Property(type=str)

    def __init__(self, title: str, artist: str, year: Optional[int] = None):
        super().__init__()
        self.title = title
        self.artist = artist
        self.year = year
        self.tracks: List[Track] = []
        self.artwork_path = None
        self.tags: Set[str] = set()
        self._release_name = None

    @property
    def year(self) -> Optional[int]:
        return None if self.internal_year == -1 else self.internal_year

    @year.setter
    def year(self, value: Optional[int]):
        self.internal_year = -1 if value is None else value

    @cached_property
    def sort_key(self):
        return f"{self.artist}{self.title}"

    # Delegate to ReleaseName
    def tags_string(self) -> str:
        return " · ".join(sorted(self.tags)) if self.tags else ""

    def label_string(self) -> str:
        return self.label if self.label else ""


class ReleaseName(str):
    def __new__(cls, content):
        instance = super().__new__(cls, content)
        # Initialize cached properties
        instance._artist = None
        instance._title = None
        instance._year = None
        instance._label = None
        instance._tags = None
        instance._is_split = None
        return instance

    def _clean_string(self, input: str, transforms: List[tuple] = None) -> str:
        if transforms is None:
            transforms = []

        patterns = (
            [
                (r"(\([^\)]*\)?)+", "", 0),
                (r"(\[[^\]]*\]?)+", "", 0),
                (r"[_]+", " ", 0),
                (r"\s+", " ", 0),
                (r"\b\s*&\s*\b", " and ", 0),
                (r"\b([_\'\-\s]+)n([_\'\-\s])+\b", " and ", 0),
            ]
            + transforms
            + [(r"^[_\-\s]+", "", 0), (r"[_\-\s]+$", "", 0)]
        )

        result = input
        for pattern, replacement, flags in patterns:
            result = re.sub(pattern, replacement, result, flags=flags)
            if not result.strip():
                result = replacement
        return result.strip()

    def _extract_label_part(self) -> str:
        match = re.search(r"[-]+(\d{4})[-]+(.*)$", self)
        if match:
            return match.group(2)

        match = re.search(r"\b(\d{4})\b(.*)$", self)
        if match:
            return match.group(2)

        return ""

    @cached_property
    def year(self) -> Optional[int]:
        match = re.search(r"[-]+(\d{4})[-]+", self)
        if not match:
            match = re.search(r"\b(\d{4})\b", self)

        if match:
            try:
                year = int(match.group(1))
                if 1900 <= year <= 2100:
                    return year
            except ValueError:
                pass
        return None

    @cached_property
    def is_split(self) -> bool:
        patterns = [
            r"[-_\s]split[-_\s]",
            r"\b\d+[-_\s]*artists\b",
            r"[-_\s]vs[-_\s]",
            r"[-_\s]with[-_\s]",
            r"(?:^|[-_\s])and(?:[-_\s]|$)",  # Match "and" with boundaries
            r"__",  # Double underscore often indicates split
            r"[-_\s]&[-_\s]",  # Additional split indicator
        ]
        return any(re.search(pattern, self, re.I) for pattern in patterns)

    def _extract_artists(self, text: str) -> List[str]:
        # Split on common separators while preserving the separators in the result
        separators = ["-", "_", " and ", " & ", "__"]
        parts = [text]
        for sep in separators:
            new_parts = []
            for part in parts:
                if sep in part:
                    split_parts = [p.strip() for p in part.split(sep)]
                    new_parts.extend(p for p in split_parts if p)
                else:
                    new_parts.append(part)
            parts = new_parts
        return [
            p
            for p in parts
            if p and not re.match(r"^(split|ep|vinyl|cd|web)$", p, re.I)
        ]

    @cached_property
    def title(self) -> str:
        # Special case for names like "1982_Trio-A-B-2014-gF"
        special_match = re.match(r"^([^-]+)-([^-]+(?:-[^-]+)*)-(\d{4})-([^-]+)$", self)
        if special_match:
            title_part = special_match.group(2)
        elif "--" in self:
            parts = self.split("--", 1)
            title_part = parts[1]
        else:
            parts = self.split("-", 1)
            title_part = parts[1] if len(parts) > 1 else parts[0]

        # Special handling for split releases
        if self.is_split:
            # Extract all artists from the title part
            artists = self._extract_artists(title_part)
            if artists:
                # Join artists with " / " for display
                title_part = " / ".join(artists)

        # Updated title cleaning transforms
        title_transforms = [
            # Convert '_' to spaces first
            (r"_", " ", 0),
            # Extract and clean up series/volumes
            (
                r"(?i)(single[\s_]*serie[s]?[\s_]*(?:part[\s_]*)?(\d+))",
                r"Single Series Part \2",
                0,
            ),
            # Remove inch measurements completely
            (r"(?i)(\d+[\s_]*(?:inch|\"|\u201D))", "", 0),
            # Move format/media info to tags
            (r"(?i)\b(vinyl|cd|web|tape|digital)\b", "", 0),
            # Clean up region codes
            (r"-([A-Z]{2})-", "", 0),
            # Remove year and anything after
            (r"[-]+\d{4}[-]+.*$", "", 0),
            (r"\b\d{4}\b.*$", "", 0),
            # Other existing transforms
            (r"\b(TRACKFIX|DIRFIX|READ[\-\s]*NFO)\b", "", re.I),
            (
                r"\b(S[\-\_\s\.]*T[\-\_\s\.]|SELF[\-\_\s\.]*TITLED)\b",
                "Self-Titled",
                re.I,
            ),
            (r"\b((RE[\-\s]*)?(MASTERED|ISSUE|PACKAGE|EDITION))\b", "", re.I),
            (
                r"\b(ADVANCE|PROMO|SAMPLER|PROPER|RERIP|RETAIL|REMIX|BONUS|LTD\.?|LIMITED)\b",
                "",
                re.I,
            ),
            (
                r"\b(CDM|CDEP|CDR|CDS|CD|MCD|DVDA|DVD|TAPE|VINYL|VLS|WEB|SAT|CABLE)\b",
                "",
                re.I,
            ),
            (r"\b(EP|LP|BOOTLEG|SINGLE)\b", "", re.I),
            (r"\b(WEB|FLAC|MP3|320|V0|V2|AAC)\b", "", re.I),
            (r"\b(VA|OST)\b[\-\s]*", "", re.I),
            (r"\bsplit\b", "", re.I),
            # Clean up multiple spaces and trim
            (r"\s+", " ", 0),
        ]

        return self._clean_string(title_part, title_transforms)

    @property
    def artist(self) -> str:
        if self._artist is None:
            # Special case for names like "1982_Trio-A-B-2014-gF"
            special_match = re.match(
                r"^([^-]+)-([^-]+(?:-[^-]+)*)-(\d{4})-([^-]+)$", self
            )
            if special_match:
                artist_part = special_match.group(1)
            # Process splits differently
            elif self.is_split:
                if "--" in self:
                    artist_part = self.split("--", 1)[0]
                else:
                    artist_part = self.split("-", 1)[0]

                artists = self._extract_artists(artist_part)
                if artists:
                    # Join multiple artists with " / "
                    self._artist = " / ".join(artists)
                else:
                    self._artist = "Various Artists"  # Fallback for splits
                return self._artist
            else:
                # Regular releases
                if "--" in self:
                    artist_part = self.split("--", 1)[0]
                else:
                    artist_part = self.split("-", 1)[0]

            # Clean up the artist name using existing method
            self._artist = self._clean_string(artist_part)
        return self._artist

    @cached_property
    def tags(self) -> Set[str]:
        tags = set()
        if self.is_split:
            tags.add("Split")

        format_patterns = [
            (r"(?i)(\d+)\s*(?:inch|\"|\u201D)", r'\1"'),
            (r"(?i)\b(vinyl|cd|web|tape|digital)\b", r"\1"),
        ]

        for pattern, tag_format in format_patterns:
            match = re.search(pattern, self, re.I)
            if match:
                tags.add(match.expand(tag_format).title())

        # Add region code if present
        region_match = re.search(r"-([A-Z]{2})-", self)
        if region_match:
            tags.add(region_match.group(1))

        # Only add INT tag here, group name will be handled separately
        if self.endswith("_INT") or re.search(r"[-]([A-Za-z0-9]+)_INT$", self):
            tags.add("INT")

        return tags

    @cached_property
    def label(self) -> str:
        # Extract group name separately from _INT suffix
        int_group_match = re.search(r"[-]([A-Za-z0-9]+)_INT$", self)
        if int_group_match:
            return int_group_match.group(1)  # Return just the group name

        # Handle regular group/label
        if scene_match := re.search(r"[-]([A-Za-z0-9]+)$", self):
            return scene_match.group(1)

        # Fall back to standard label extraction for other cases
        return self._clean_string(self._extract_label_part())


class TrackName:
    def __init__(self, name: str):
        self.raw_name = name
        self._parse()

    def _parse(self):
        # Add track-specific parsing logic here when needed
        pass


class Track:
    ARTWORK_PATTERNS = [
        "*cover*.*",
        "*artwork*.*",
        "*front*.*",
        "folder.*",
        "*.jpg",
        "*.jpeg",
        "*.png",
    ]

    def __init__(self, path):
        self.path = path
        self.release = None  # Will be set when added to a Release
        self.artwork_path = self._find_artwork()

    def _find_artwork(self) -> Optional[str]:
        directory = os.path.dirname(self.path)
        for pattern in self.ARTWORK_PATTERNS:
            for file in Path(directory).glob(pattern):
                if file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    return str(file)
        return None


class Scanner:
    def __init__(self):
        # The scanner itself doesn't need to store all releases anymore
        pass

    # Modify scan_directory to process a single directory
    def scan_single_directory(self, path: str) -> List[Release]:
        """Scans a single directory for music files and returns a list of Releases found."""
        release_tracks: Dict[str, List[Track]] = {}
        releases_in_dir: List[Release] = []

        # Find tracks in this specific directory
        try:
            for file in os.listdir(path):
                full_path = os.path.join(path, file)
                if os.path.isfile(full_path) and file.lower().endswith(
                    (".mp3", ".flac")
                ):
                    try:
                        track = Track(full_path)
                        # Use directory path as unique key for releases within this function
                        key = os.path.dirname(track.path)  # This will be 'path'
                        if key not in release_tracks:
                            release_tracks[key] = []
                        release_tracks[key].append(track)
                    except Exception as e:
                        # Log error but continue scanning
                        print(f"Error scanning track {full_path}: {e}")
        except Exception as e:
            # Log error for directory listing
            print(f"Error listing directory {path}: {e}")
            return []  # Return empty list if directory listing fails

        # Create or update releases for this directory
        for key, tracks in release_tracks.items():
            # Assuming one release per directory for simplicity based on current Track parsing
            if tracks:
                dirname = os.path.basename(key)
                release_name = ReleaseName(dirname)
                release = Release(
                    release_name.title, release_name.artist, release_name.year
                )
                release._release_name = release_name  # Store reference
                release.artwork_path = tracks[0].artwork_path
                release.label = release_name.label
                release.tags = release_name.tags

                # Set release reference for each track
                for track in tracks:
                    track.release = release

                release.tracks = sorted(tracks, key=lambda t: t.path)
                releases_in_dir.append(release)

        return releases_in_dir

    # The main scan method will be handled by the MusicPlayer now using this single-directory scanner


class SearchFilter(Gtk.Filter):
    def __init__(self):
        super().__init__()
        self.search_text = ""

    def set_search_text(self, search_text: str):
        self.search_text = search_text.lower()
        self.changed(Gtk.FilterChange.DIFFERENT)

    def do_match(self, item: Release) -> bool:
        if not self.search_text:
            return True

        terms = self.search_text.split()
        # Include label in the searchable text
        text = f"{item.title} {item.artist} {item.year if item.year else ''} {item.tags_string} {item.label_string}".lower()

        return all(term in text for term in terms)

    def do_get_strictness(self):
        return Gtk.FilterMatch.SOME


class CircularProgress(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.fraction = 0
        self.set_content_width(18)
        self.set_content_height(18)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, width, height):
        radius = min(width, height) / 2

        # Draw background circle
        cr.arc(width / 2, height / 2, radius, 0, 2 * pi)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.2)
        cr.fill()

        # Draw progress arc
        if self.fraction > 0:
            cr.arc(
                width / 2, height / 2, radius, -pi / 2, (2 * self.fraction - 0.5) * pi
            )
            cr.line_to(width / 2, height / 2)
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
            cr.fill()

    def set_fraction(self, fraction):
        self.fraction = fraction
        self.queue_draw()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_release = None  # Add this line near the start of __init__

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
        self.albums_page = Gtk.Box()
        self.queue_page = Gtk.Box()

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
        info_box.set_valign(Gtk.Align.CENTER)

        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_box.add_css_class("title-box")
        title_box.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label(xalign=0, css_classes=["title"])
        title.add_css_class("heading")
        title.set_valign(Gtk.Align.CENTER)
        title_box.append(title)

        year = Gtk.Label(xalign=0)
        year.add_css_class("caption")
        year.add_css_class("dim-label")
        year.set_valign(Gtk.Align.CENTER)
        title_box.append(year)

        tags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        title_box.append(tags_box)

        artist = Gtk.Label(xalign=0, css_classes=["artist"])
        artist.add_css_class("caption")
        artist.set_opacity(0.7)

        info_box.append(title_box)
        info_box.append(artist)

        box.append(info_box)
        list_item.set_child(box)

    def _on_album_bind(self, factory, list_item):
        box = list_item.get_child()
        release = list_item.get_item()

        info_box = box.get_first_child()
        title_box = info_box.get_first_child()

        title_label = title_box.get_first_child()
        year_label = title_label.get_next_sibling()
        tags_box = year_label.get_next_sibling()

        artist_label = title_box.get_next_sibling()

        title_label.set_text(release.title)
        year_label.set_text(str(release.year) if release.year else "")
        artist_label.set_text(release.artist)

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

    def start_loading(self):
        self.progress.set_visible(True)
        self.progress.set_fraction(0)

    def stop_loading(self):
        self.progress.set_visible(False)

    def update_progress(self, current: int, total: int):
        self.progress.set_fraction(current / total if total > 0 else 0)


class MusicPlayer(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.knoopx.music")
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

    def do_activate(self):
        win = MainWindow(application=self)
        win.present()
        self.load_library()

    def load_library(self):
        window = self.get_active_window()
        window.start_loading()
        self.all_releases = {}  # Clear previous scan results
        window.albums_model.remove_all()  # Clear the UI model using remove_all()

        def scan_thread():
            music_dir = "/mnt/music/"
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
        window = self.get_active_window()
        window.albums_model.splice(window.albums_model.get_n_items(), 0, batch)
        return False

    def on_scan_complete(self):
        """Signals the end of the scanning process."""
        window = self.get_active_window()
        window.stop_loading()
        print(f"Scan complete. Found {len(self.all_releases)} releases.")
        return False

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
