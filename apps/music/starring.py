import json
from pathlib import Path
from typing import Set
from serialization import APP_ID


class StarringManager:
    """Manages starring/unstarring of music releases."""

    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            config_dir = Path.home() / ".config" / APP_ID

        self.config_dir = config_dir
        self.starred_file = config_dir / "starred.json"
        self._starred_releases: Set[str] = set()

        # Load starred releases on initialization
        self.load_starred_releases()

    def load_starred_releases(self) -> None:
        """Load starred releases from starred.json."""
        try:
            if self.starred_file.exists():
                with open(self.starred_file, "r", encoding="utf-8") as f:
                    starred_data = json.load(f)
                    self._starred_releases = set(starred_data.get("starred", []))
        except (json.JSONDecodeError, OSError):
            self._starred_releases = set()

    def save_starred_releases(self) -> None:
        """Save starred releases to starred.json."""
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            starred_data = {"starred": sorted(list(self._starred_releases))}

            # Write starred file atomically
            temp_file = self.starred_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(starred_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.starred_file)
        except (OSError, json.JSONDecodeError):
            pass

    def get_release_basename(self, release_path: str) -> str:
        """Get the basename of a release path."""
        return Path(release_path).name

    def is_release_starred(self, release_path: str) -> bool:
        """Check if a release is starred.

        Args:
            release_path: Path to the release directory

        Returns:
            True if the release is starred, False otherwise
        """
        basename = self.get_release_basename(release_path)
        return basename in self._starred_releases

    def toggle_release_starred(self, release_path: str) -> bool:
        """Toggle the starred status of a release.

        Args:
            release_path: Path to the release directory

        Returns:
            New starred status (True if now starred, False if unstarred)
        """
        basename = self.get_release_basename(release_path)
        if basename in self._starred_releases:
            self._starred_releases.remove(basename)
            new_status = False
        else:
            self._starred_releases.add(basename)
            new_status = True

        self.save_starred_releases()
        return new_status

    def star_release(self, release_path: str) -> None:
        """Star a release.

        Args:
            release_path: Path to the release directory
        """
        basename = self.get_release_basename(release_path)
        if basename not in self._starred_releases:
            self._starred_releases.add(basename)
            self.save_starred_releases()

    def unstar_release(self, release_path: str) -> None:
        """Unstar a release.

        Args:
            release_path: Path to the release directory
        """
        basename = self.get_release_basename(release_path)
        if basename in self._starred_releases:
            self._starred_releases.remove(basename)
            self.save_starred_releases()

    def get_starred_count(self) -> int:
        """Get the number of starred releases.

        Returns:
            Number of starred releases
        """
        return len(self._starred_releases)

    def get_starred_basenames(self) -> Set[str]:
        """Get a copy of the starred release basenames.

        Returns:
            Set of starred release basenames
        """
        return self._starred_releases.copy()

    def clear_all_starred(self) -> None:
        """Remove all starred releases."""
        self._starred_releases.clear()
        self.save_starred_releases()

    def import_starred_releases(self, basenames: Set[str]) -> None:
        """Import a set of starred release basenames.

        Args:
            basenames: Set of release basenames to mark as starred
        """
        self._starred_releases = set(basenames)
        self.save_starred_releases()
