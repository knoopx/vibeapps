import gi
from typing import Optional, List, Set
from functools import cached_property

from track import Track

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")

from gi.repository import (
    GObject,
)


@GObject.type_register
class Release(GObject.GObject):
    title = GObject.Property(type=str)
    artist = GObject.Property(type=str)
    internal_year = GObject.Property(type=int, default=-1)
    artwork_path = GObject.Property(type=str)
    group = GObject.Property(type=str)
    path = GObject.Property(type=str)  # Add path property

    def __init__(self, title: str, artist: str, path: str, year: Optional[int] = None):
        super().__init__()
        self.title = title
        self.artist = artist
        self.path = path
        self.year = year
        self.tracks: List[Track] = []
        self.artwork_path = None
        self.tags: Set[str] = set()
        self._release_name = None
        self.starred = False  # Add starred attribute with default value

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
        return self.group if self.group else ""

    def to_json(self):
        return {
            "title": self.title,
            "artist": self.artist,
            "year": self.year,
            "label": self.group,
            "path": self.path,  # Add path to JSON serialization
            "tags": list(self.tags),
            "starred": self.starred,  # Add starred to JSON serialization
            "tracks": (
                [{"path": t.path, "artwork_path": t.artwork_path} for t in self.tracks]
                if self.tracks
                else []
            ),
        }

    @classmethod
    def from_json(cls, data):
        from track import Track  # Import here to avoid circular dependency

        release = cls(data["title"], data["artist"], data["path"], data["year"])
        release.group = data["label"]
        release.tags = set(data["tags"])
        release.starred = data.get(
            "starred", False
        )  # Load starred from JSON with default False

        # Reconstruct tracks
        tracks = []
        for track_data in data["tracks"]:
            track = Track(track_data["path"])
            track.artwork_path = track_data.get("artwork_path")
            track.release = release
            tracks.append(track)

        release.tracks = tracks
        return release
