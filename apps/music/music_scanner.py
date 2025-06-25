import os
import re
from pathlib import Path
from typing import Generator, Tuple, Union
import gi

gi.require_version("GLib", "2.0")
from caching import ReleaseData, MusicLibrary

AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".opus",
    ".wma",
    ".ape",
    ".alac",
}


class MusicScanner:
    def __init__(
        self,
        music_dir: Path,
    ):
        self.music_dir = music_dir
        self.cache = MusicLibrary(music_dir)
        self._scan_cancelled = False
        self._scan_total_estimated = 0
        self._scan_generator = None
        self._scan_progress = 0.0

    def cancel_scan(self) -> None:
        self._scan_cancelled = True

    def initialize_scanning(self) -> None:
        self._scan_generator = None
        self._scan_cancelled = False
        self._scan_progress = 0.0

    def start_incremental_scan(self):
        self._scan_generator = self.scan_music_directory()
        return self._scan_generator

    def continue_scanning(
        self,
    ) -> Tuple[Union[ReleaseData, Tuple[str, float], None], bool]:
        if (
            not hasattr(self, "_scan_generator")
            or self._scan_generator is None
            or self._scan_cancelled
        ):
            return (None, True)
        try:
            result = next(self._scan_generator)
            if (
                isinstance(result, tuple)
                and len(result) == 2
                and (result[0] == "progress")
            ):
                self._scan_progress = result[1]
                return (result, False)
            elif result is not None:
                return (result, False)
            else:
                return (None, False)
        except StopIteration:
            return (None, True)

    def scan_music_directory(
        self,
    ) -> Generator[Union[ReleaseData, Tuple[str, float], None], None, None]:
        try:
            found_releases = set()
            dirs_processed = 0
            total_dirs_estimated = 0
            for root, _, files in os.walk(self.music_dir, followlinks=True):
                total_dirs_estimated += 1
                if total_dirs_estimated > 10000:
                    break
            self._scan_total_estimated = total_dirs_estimated
            for root, _, files in os.walk(self.music_dir, followlinks=True):
                if self._scan_cancelled:
                    return
                root_path = Path(root)
                if any((part.startswith(".") for part in root_path.parts)):
                    continue
                try:
                    relative_path = root_path.relative_to(self.music_dir)
                    if len(relative_path.parts) > 10:
                        continue
                except ValueError:
                    continue
                audio_files = [
                    f for f in files if Path(f).suffix.lower() in AUDIO_EXTENSIONS
                ]
                if audio_files:
                    release_path = root_path
                    release_title = self._clean_release_title(release_path.name)
                    if release_path == self.music_dir:
                        continue
                    path_str = str(release_path)
                    if path_str not in found_releases:
                        found_releases.add(path_str)
                        new_release = ReleaseData(
                            title=release_title,
                            path=path_str,
                            track_count=len(audio_files),
                        )
                        yield new_release
                dirs_processed += 1
                if dirs_processed % 10 == 0:
                    if self._scan_total_estimated > 0:
                        progress = min(dirs_processed / self._scan_total_estimated, 1.0)
                        yield ("progress", progress)
                    yield None
        except Exception as e:
            raise e

    def _clean_release_title(self, title: str) -> str:
        title = re.sub("_", " ", title)
        title = re.sub("\\-+", "-", title)
        title = re.sub("\\s+", " ", title)
        title = re.sub(" - ", "-", title)
        return title.strip()
