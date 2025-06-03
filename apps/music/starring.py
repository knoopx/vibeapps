import json
from pathlib import Path
from typing import Set, Optional
from serialization import APP_ID

class StarringManager:

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        if config_dir is None:
            config_dir = Path.home() / '.config' / APP_ID
        self.config_dir = config_dir
        self.starred_file = config_dir / 'starred.json'
        self._starred_releases: Set[str] = set()
        self.load_starred_releases()

    def load_starred_releases(self) -> None:
        try:
            if self.starred_file.exists():
                with open(self.starred_file, 'r', encoding='utf-8') as f:
                    starred_data = json.load(f)
                    self._starred_releases = set(starred_data.get('starred', []))
        except (json.JSONDecodeError, OSError):
            self._starred_releases = set()

    def save_starred_releases(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            starred_data = {'starred': sorted(list(self._starred_releases))}
            temp_file = self.starred_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(starred_data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.starred_file)
        except (OSError, json.JSONDecodeError):
            pass

    def get_release_basename(self, release_path: str) -> str:
        return Path(release_path).name

    def is_release_starred(self, release_path: str) -> bool:
        basename = self.get_release_basename(release_path)
        return basename in self._starred_releases

    def toggle_release_starred(self, release_path: str) -> bool:
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
        basename = self.get_release_basename(release_path)
        if basename not in self._starred_releases:
            self._starred_releases.add(basename)
            self.save_starred_releases()

    def unstar_release(self, release_path: str) -> None:
        basename = self.get_release_basename(release_path)
        if basename in self._starred_releases:
            self._starred_releases.remove(basename)
            self.save_starred_releases()

    def get_starred_count(self) -> int:
        return len(self._starred_releases)

    def get_starred_basenames(self) -> Set[str]:
        return self._starred_releases.copy()

    def clear_all_starred(self) -> None:
        self._starred_releases.clear()
        self.save_starred_releases()

    def import_starred_releases(self, basenames: Set[str]) -> None:
        self._starred_releases = set(basenames)
        self.save_starred_releases()