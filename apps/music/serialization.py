from picker_window import PickerWindow, PickerItem
from gi.repository import Gtk, Adw, GLib, GObject, Gio, Pango


class ReleaseItem(PickerItem):
    """Represents a music release (album/directory)."""

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


# Make sure the ReleaseItem type is properly registered
GObject.type_ensure(ReleaseItem)


class ReleaseData:
    """Data class for music release information."""

    def __init__(self, title: str, path: str, track_count: int = 0):
        self.title = title
        self.path = path
        self.track_count = track_count

    def to_dict(self) -> dict:
        """Convert to dictionary for caching."""
        return {"title": self.title, "path": self.path, "track_count": self.track_count}

    @classmethod
    def from_dict(cls, data: dict) -> "ReleaseData":
        """Create from dictionary data."""
        return cls(
            title=data["title"], path=data["path"], track_count=data["track_count"]
        )

    def __eq__(self, other):
        """Check equality based on path."""
        if not isinstance(other, ReleaseData):
            return False
        return self.path == other.path

    def __hash__(self):
        """Hash based on path for set operations."""
        return hash(self.path)


def create_release_item_converter(starring_manager):
    """
    Create a converter function that converts ReleaseData to ReleaseItem.

    Args:
        starring_manager: StarringManager instance to check starred status

    Returns:
        Function that converts ReleaseData to ReleaseItem
    """

    def converter(release_data: ReleaseData):
        # Always use standard import for ReleaseItem
        # The ReleaseItem class needs to be registered before we can convert

        # Create ReleaseItem directly
        return ReleaseItem(
            title=release_data.title,
            path=release_data.path,
            track_count=release_data.track_count,
            starred=starring_manager.is_release_starred(release_data.path),
        )

    return converter


def convert_release_items_to_data(release_items):
    """
    Convert a list of ReleaseItems to ReleaseData objects.

    Args:
        release_items: List of ReleaseItem objects

    Returns:
        List of ReleaseData objects
    """
    return [
        ReleaseData(item.title, item.path, item.track_count) for item in release_items
    ]
