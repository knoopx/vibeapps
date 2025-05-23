#!/usr/bin/env python

import gi
import os
from pathlib import Path
from typing import Optional, List, Dict
import re
from typing import List, Set
import threading
import subprocess
from math import pi
import concurrent.futures # Import ThreadPoolExecutor

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Adw, GLib, Gio, Gst, GObject

@GObject.type_register
class Release(GObject.GObject):
    title = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    internal_year = GObject.Property(type=int, default=-1)
    artwork_path = GObject.Property(type=str)

    def __init__(self, title: str, artist: str, year: Optional[int] = None):
        super().__init__()
        self.title = title
        self.artist = artist
        self.year = year
        self.tracks: List[Track] = []
        self.artwork_path = None

    @property
    def year(self) -> Optional[int]:
        return None if self.internal_year == -1 else self.internal_year

    @year.setter
    def year(self, value: Optional[int]):
        self.internal_year = -1 if value is None else value

    @property
    def sort_key(self):
        return f"{self.artist}{self.title}"

    @property
    def tags_string(self) -> str:
        return " · ".join(sorted(self.tracks[0].tags)) if self.tracks else ""

class ReleaseName:
    def __init__(self, name: str):
        self.raw_name = name
        self._parse()

    def _parse(self):
        self.artist = self._parse_artist()
        self.title = self._parse_title()
        self.year = self._parse_year()
        self.tags = self._parse_tags()

    def _clean_string(self, input: str, transforms: List[tuple] = None) -> str:
        if transforms is None:
            transforms = []

        patterns = [
            (r'(\([^\)]*\)?)+', '', 0),
            (r'(\[[^\]]*\]?)+', '', 0),
            (r'[_]+', ' ', 0),
            (r'\s+', ' ', 0),
            (r'\b\s*&\s*\b', ' and ', 0),
            (r'\b([_\'\-\s]+)n([_\'\-\s])+\b', ' and ', 0)
        ] + transforms + [
            (r'^[_\-\s]+', '', 0),
            (r'[_\-\s]+$', '', 0)
        ]

        result = input
        for pattern, replacement, flags in patterns:
            result = re.sub(pattern, replacement, result, flags=flags)
            if not result.strip():
                result = replacement
        return result.strip()

    def _parse_artist(self) -> str:
        # Split by single or double hyphen, prioritize double hyphen
        if '--' in self.raw_name:
            artist_part = self.raw_name.split('--')[0]
        else:
            artist_part = self.raw_name.split('-')[0]
        return self._clean_string(artist_part, [(r'\b(ft|feat|presents)[\_\-\s\.]+.+$', '', re.I)])

    def _parse_title(self) -> str:
        # Handle both single and double hyphen cases
        if '--' in self.raw_name:
            parts = self.raw_name.split('--', 1)
        else:
            parts = self.raw_name.split('-', 1)

        if len(parts) < 2:
            return self._clean_string(self.raw_name)

        title_part = parts[1]
        # Remove country code if present (e.g., -JP-)
        title_part = re.sub(r'-([A-Z]{2})-', '-', title_part)
        # Remove year and label if present (YYYY or -YYYY- or --YYYY--)
        title_part = re.sub(r'[-]+\d{4}[-]+.*$', '', title_part)
        title_part = re.sub(r'\b\d{4}\b.*$', '', title_part)

        # Clean up common release tags
        album_transforms = [
            (r'\b(TRACKFIX|DIRFIX|READ[\-\s]*NFO)\b', '', re.I),
            (r'\b\d+[\-\s]*(inch|"|i)(\s*vinyl)?\b', '', re.I),
            (r'\b(S[\-\_\s\.]*T[\-\_\s\.]|SELF[\-\_\s\.]*TITLED)\b', 'Self-Titled', re.I),
            (r'\b((RE[\-\s]*)?(MASTERED|ISSUE|PACKAGE|EDITION))\b', '', re.I),
            (r'\b(ADVANCE|PROMO|SAMPLER|PROPER|RERIP|RETAIL|REMIX|BONUS|LTD\.?|LIMITED)\b', '', re.I),
            (r'\b(CDM|CDEP|CDR|CDS|CD|MCD|DVDA|DVD|TAPE|VINYL|VLS|WEB|SAT|CABLE)\b', '', re.I),
            (r'\b(EP|LP|BOOTLEG|SINGLE)\b', '', re.I),
            (r'\b(WEB|FLAC|MP3|320|V0|V2|AAC)\b', '', re.I),
            (r'\b(VA|OST)\b[\-\s]*', '', re.I)
        ]
        return self._clean_string(title_part, album_transforms)

    def _parse_year(self) -> Optional[int]:
        # Look for year in either single or double hyphen format
        match = re.search(r'[-]+(\d{4})[-]+', self.raw_name)
        if not match:
            # Try finding a standalone year
            match = re.search(r'\b(\d{4})\b', self.raw_name)

        if match:
            try:
                year = int(match.group(1))
                if 1900 <= year <= 2100:
                    return year
            except ValueError:
                pass
        return None

    def _parse_tags(self) -> Set[str]:
        tag_patterns = {
            'Vinyl': r'\b(VINYL|VLS)\b',
            'CD': r'\b(CDM|CDEP|CDR|CDS|CD|MCD)\b',
            'DVD': r'\b(DVDA|DVD)\b',
            'Cassette': r'\b(TAPE)\b',
            'File': r'\b(WEB)\b',
            'Limited Edition': r'\b(LTD\.?|LIMITED)\b',
            'Remastered': r'\b(REMASTERED)\b',
            'Reissue': r'\b(REISSUE)\b',
            'Advance': r'\b(ADVANCE)\b',
            'Promo': r'\b(PROMO)\b',
            'Rerip': r'\b(RERIP)\b',
            'Remix': r'\b(REMIX|RMX)\b',
            'Proper': r'\b(PROPER)\b',
            'Retail': r'\b(RETAIL)\b',
            'Sampler': r'\b(SAMPLER)\b',
            'EP': r'\b(EP)\b',
            'LP': r'\b(LP)\b',
            'Bootleg': r'\b(BOOTLEG)\b',
            'Single': r'\b(SINGLE|VLS|CDS)\b',
            'Compilation': r'^VA-'
        }
        tags = {tag for tag, pattern in tag_patterns.items() if re.search(pattern, self.raw_name, re.I)}

        # Extract and add country code if present (e.g., -JP-)
        country_match = re.search(r'-([A-Z]{2})-', self.raw_name)
        if country_match:
            tags.add(country_match.group(1))

        return tags

class TrackName:
    def __init__(self, name: str):
        self.raw_name = name
        self._parse()

    def _parse(self):
        # Add track-specific parsing logic here when needed
        pass

class Track:
    ARTWORK_PATTERNS = [
        '*cover*.*', '*artwork*.*', '*front*.*', 'folder.*',
        '*.jpg', '*.jpeg', '*.png'
    ]

    def __init__(self, path):
        self.path = path
        self._parse_filename()
        self.artwork_path = self._find_artwork()

    def _parse_filename(self):
        dirname = os.path.basename(os.path.dirname(self.path))
        release_name = ReleaseName(dirname)

        self.artist = release_name.artist
        self.album = release_name.title
        self.year = release_name.year
        self.tags = release_name.tags

    def _find_artwork(self) -> Optional[str]:
        directory = os.path.dirname(self.path)
        for pattern in self.ARTWORK_PATTERNS:
            for file in Path(directory).glob(pattern):
                if file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
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
                if os.path.isfile(full_path) and file.lower().endswith(('.mp3', '.flac')):
                    try:
                        track = Track(full_path)
                        if track.artist and track.album:
                            # Use directory path as unique key for releases within this function
                            key = os.path.dirname(track.path) # This will be 'path'
                            if key not in release_tracks:
                                release_tracks[key] = []
                            release_tracks[key].append(track)
                    except Exception as e:
                        # Log error but continue scanning
                        print(f"Error scanning track {full_path}: {e}")
        except Exception as e:
             # Log error for directory listing
             print(f"Error listing directory {path}: {e}")
             return [] # Return empty list if directory listing fails


        # Create or update releases for this directory
        for key, tracks in release_tracks.items():
            # Assuming one release per directory for simplicity based on current Track parsing
            if tracks:
                sample_track = tracks[0]
                release = Release(sample_track.album, sample_track.artist, sample_track.year)
                release.artwork_path = sample_track.artwork_path
                release.tracks = sorted(tracks, key=lambda t: t.path) # Add all tracks to release
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
        text = f"{item.title} {item.artist} {item.year if item.year else ''} {item.tags_string}".lower()

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
        cr.arc(width/2, height/2, radius, 0, 2*pi)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.2)
        cr.fill()

        # Draw progress arc
        if self.fraction > 0:
            cr.arc(width/2, height/2, radius, -pi/2, (2*self.fraction - 0.5)*pi)
            cr.line_to(width/2, height/2)
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
            cr.fill()

    def set_fraction(self, fraction):
        self.fraction = fraction
        self.queue_draw()

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Add CSS provider
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
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
        """.encode())
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.header = Adw.HeaderBar()
        self.search = Gtk.SearchEntry()
        self.search.set_hexpand(True)
        self.search.connect('search-changed', self._on_search_changed)
        self.header.set_title_widget(self.search)
        self.header.add_css_class("flat")

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
        self.filtered_model = Gtk.FilterListModel(model=self.albums_model, filter=self.search_filter)

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
        year_label.set_text(f"({release.year})" if release.year else "")
        artist_label.set_text(release.artist)

        # Remove old tags
        while tags_box.get_first_child():
            tags_box.remove(tags_box.get_first_child())

        # Add new tag pills
        if release.tracks:
            for tag in sorted(release.tracks[0].tags):
                pill = Gtk.Label(label=tag)
                pill.add_css_class("tag-pill")
                pill.add_css_class("caption")
                pill.add_css_class("dim-label")
                tags_box.append(pill)

    def _on_selection_changed(self, selection, position, n_items):
        self.selected_release = selection.get_selected_item()

    def _on_row_activated(self, list_view, position):
        if self.selected_release and self.selected_release.tracks:
            folder = os.path.dirname(self.selected_release.tracks[0].path)
            subprocess.run(["xdg-open", folder])

    def _on_search_changed(self, search):
        self.search_filter.set_search_text(search.get_text())

    def start_loading(self):
        self.progress.set_visible(True)
        self.progress.set_fraction(0)

    def stop_loading(self):
        self.progress.set_visible(False)

    def update_progress(self, current: int, total: int):
        self.progress.set_fraction(current / total if total > 0 else 0)

class MusicPlayer(Adw.Application):
    def __init__(self):
        super().__init__(application_id='org.knoopx.Music')
        self.scanner = Scanner()
        self.all_releases: Dict[str, Release] = {} # Store all releases here, keyed by directory path
        # Use a ThreadPoolExecutor for parallel scanning
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 4)

    def do_activate(self):
        win = MainWindow(application=self)
        win.present()
        self.load_library()

    def load_library(self):
        window = self.get_active_window()
        window.start_loading()
        self.all_releases = {} # Clear previous scan results
        window.albums_model.remove_all() # Clear the UI model using remove_all()

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
                    if any(f.lower().endswith(('.mp3', '.flac')) for f in files):
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
            futures = {self.executor.submit(self.scanner.scan_single_directory, dir_path): dir_path for dir_path in directories_to_scan}

            batch_size = 50 # Still process in batches for UI updates
            current_batch: List[Release] = []

            # Process results as they complete
            for future in concurrent.futures.as_completed(futures):
                processed_directories += 1
                dir_path = futures[future]
                try:
                    releases_in_dir = future.result()
                    for release in releases_in_dir:
                         # Use directory path as key for the global collection
                         key = os.path.dirname(release.tracks[0].path) if release.tracks else None
                         if key and key not in self.all_releases:
                             self.all_releases[key] = release
                             current_batch.append(release)

                             # Yield batch to UI thread when size is reached
                             if len(current_batch) >= batch_size:
                                 # Sort batch before yielding
                                 sorted_batch = sorted(current_batch, key=lambda r: f"{r.artist.lower()}{r.title.lower()}")
                                 GLib.idle_add(self.on_batch_complete, sorted_batch)
                                 current_batch = []

                except Exception as exc:
                    print(f'Scanning directory {dir_path} generated an exception: {exc}')

                # Update progress after each directory is processed
                GLib.idle_add(window.update_progress, processed_directories, total_directories)


            # Process any remaining items in the last batch
            if current_batch:
                 sorted_batch = sorted(current_batch, key=lambda r: f"{r.artist.lower()}{r.title.lower()}")
                 GLib.idle_add(self.on_batch_complete, sorted_batch)

            # Final progress update and completion signal
            GLib.idle_add(window.update_progress, total_directories, total_directories) # Ensure 100%
            GLib.idle_add(self.on_scan_complete)

        # Start the thread that manages the thread pool
        thread = threading.Thread(target=scan_thread, daemon=True)
        thread.start()

    # Modified on_batch_complete to just append the batch
    def on_batch_complete(self, batch):
        """Appends a batch of releases to the UI model."""
        window = self.get_active_window()
        window.albums_model.splice(window.albums_model.get_n_items(), 0, batch)
        # Progress is updated separately now
        return False

    def on_scan_complete(self):
        """Signals the end of the scanning process."""
        window = self.get_active_window()
        window.stop_loading()
        print(f"Scan complete. Found {len(self.all_releases)} releases.")
        return False

if __name__ == '__main__':
    Gst.init(None)
    app = MusicPlayer()
    app.run(None)
