from typing import List, Dict
import gi
import os

from release import Release
from release_name import ReleaseName
from track import Track

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")


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
