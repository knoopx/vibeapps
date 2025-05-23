from pathlib import Path
from typing import Optional
import gi
import os

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")


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
