import json
from pathlib import Path
from typing import Set


class Collection:
    def __init__(self, file) -> None:
        self.file = file
        self.name = file.stem
        self._releases: Set[str] = set()
        self.load()

    def load(self) -> None:
        try:
            if self.file.exists():
                with open(self.file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._releases = set([self.key(d) for d in data])
        except (json.JSONDecodeError, OSError):
            self._releases = set()

    def save(self) -> None:
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            data = sorted(list(self._releases))
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (OSError, json.JSONDecodeError):
            pass

    def key(self, release_path: str) -> str:
        return Path(release_path).name.lower()

    def contains(self, release_path: str) -> bool:
        basename = self.key(release_path)
        return basename in self._releases

    def toggle(self, release_path: str) -> bool:
        basename = self.key(release_path)
        if basename in self._releases:
            self._releases.remove(basename)
            new_status = False
        else:
            self._releases.add(basename)
            new_status = True
        self.save()
        return new_status

    def add(self, release_path: str) -> None:
        basename = self.key(release_path)
        if basename not in self._releases:
            self._releases.add(basename)
            self.save()

    def remove(self, release_path: str) -> None:
        basename = self.key(release_path)
        if basename in self._releases:
            self._releases.remove(basename)
            self.save()

    def __len__(self) -> int:
        return len(self._releases)

    def releases(self) -> Set[str]:
        return self._releases.copy()

    def clear(self) -> None:
        self._releases.clear()
        self.save()

    def replace(self, basenames: Set[str]) -> None:
        self._releases = set(basenames)
        self.save()
