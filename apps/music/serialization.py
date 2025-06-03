from picker_window import PickerItem
from gi.repository import GObject
from typing import List

APP_ID = "net.knoopx.music"


class ReleaseItem(PickerItem):
    __gtype_name__ = "ReleaseItem"
    title = GObject.Property(type=str, default="")
    path = GObject.Property(type=str, default="")
    track_count = GObject.Property(type=int, default=0)
    starred = GObject.Property(type=bool, default=False)

    def __init__(
        self, title: str, path: str, track_count: int = 0, starred: bool = False
    ):
        super().__init__()
        self.title = title
        self.path = path
        self.track_count = track_count
        self.starred = starred


GObject.type_ensure(ReleaseItem)


class ReleaseData:

    def __init__(self, title: str, path: str, track_count: int = 0, starred: bool = False):
        self.title = title
        self.path = path
        self.track_count = track_count
        self.starred = starred

    def to_dict(self) -> dict:
        return {"title": self.title, "path": self.path, "track_count": self.track_count, "starred": self.starred}

    @classmethod
    def from_dict(cls, data: dict) -> "ReleaseData":
        return cls(
            title=data["title"],
            path=data["path"],
            track_count=data["track_count"],
            starred=data.get("starred", False)
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, ReleaseData):
            return False
        return self.path == other.path

    def __hash__(self) -> int:
        return hash(self.path)


def create_release_item_converter(starring_manager):

    def converter(release_data: ReleaseData) -> ReleaseItem:
        return ReleaseItem(
            title=release_data.title,
            path=release_data.path,
            track_count=release_data.track_count,
            starred=starring_manager.is_release_starred(release_data.path),
        )

    return converter


def convert_release_items_to_data(release_items) -> List["ReleaseData"]:
    return [
        ReleaseData(item.title, item.path, item.track_count, item.starred) for item in release_items
    ]
