#!/usr/bin/env python3

import json
import time
from pathlib import Path
from typing import Optional, List, Tuple


# Cache configuration
CACHE_DIR = Path.home() / ".cache" / "net.knoopx.music"
CACHE_FILE = CACHE_DIR / "releases_cache.json"
CACHE_VERSION = 1  # Increment when cache format changes


class ReleaseData:
    """Data class for music release information."""

    def __init__(self, title: str, path: str, track_count: int = 0):
        self.title = title
        self.path = path
        self.track_count = track_count

    def to_dict(self) -> dict:
        """Convert to dictionary for caching."""
        return {
            'title': self.title,
            'path': self.path,
            'track_count': self.track_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ReleaseData':
        """Create from dictionary data."""
        return cls(
            title=data['title'],
            path=data['path'],
            track_count=data['track_count']
        )


class MusicCache:
    """Handles caching of music release data."""

    def __init__(self, music_dir: Path):
        self.music_dir = music_dir

    def load_from_cache(self) -> Tuple[bool, Optional[List[ReleaseData]]]:
        """
        Load releases from cache if available and valid.

        Returns:
            Tuple of (cache_valid, releases_data)
            - cache_valid: True if cache was loaded successfully
            - releases_data: List of release data if cache is valid, None otherwise
        """
        try:
            if not CACHE_FILE.exists():
                return False, None

            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Validate cache format and version
            if (cache_data.get('version') != CACHE_VERSION or
                'music_dir' not in cache_data or
                'releases' not in cache_data or
                'last_modified' not in cache_data):
                return False, None

            # Check if cache is for the same music directory
            if cache_data['music_dir'] != str(self.music_dir):
                return False, None

            # Check if music directory has been modified since cache was created
            music_dir_mtime = self.music_dir.stat().st_mtime
            cache_mtime = cache_data['last_modified']

            # If music dir is newer than cache, cache is stale
            if music_dir_mtime > cache_mtime:
                return False, None

            # Convert cache data to ReleaseData objects
            releases = [ReleaseData.from_dict(item) for item in cache_data['releases']]

            return True, releases

        except (json.decoder.JSONDecodeError, KeyError, OSError, FileNotFoundError):
            # If cache is corrupted or unreadable, remove it
            try:
                CACHE_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            return False, None

    def save_to_cache(self, releases: List[ReleaseData]) -> None:
        """Save releases to cache."""
        try:
            # Ensure cache directory exists
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

            # Prepare cache data
            cache_data = {
                'version': CACHE_VERSION,
                'music_dir': str(self.music_dir),
                'last_modified': time.time(),
                'releases': [release.to_dict() for release in releases]
            }

            # Write cache atomically
            temp_file = CACHE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(CACHE_FILE)

        except (OSError, json.decoder.JSONDecodeError):
            # If caching fails, just ignore it but don't crash
            pass
