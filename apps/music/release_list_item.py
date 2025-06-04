from typing import Callable, Optional, List
from gi.repository import Gtk, Pango
from star_button import StarButton
from serialization import ReleaseItem
from badge import Badge


class ReleaseListItem(Gtk.Box):

    def __init__(self, on_star_toggled: Optional[Callable] = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self._on_star_toggled = on_star_toggled
        self._current_item = None
        self._item_starred_connection_id = None
        self._setup_ui()

    def _setup_ui(self):
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_spacing(12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self._star_button = StarButton(starred=False)
        self._star_button.connect("star-toggled", self._handle_star_toggled)
        self.append(self._star_button)
        self._content_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True
        )
        self._title_label = Gtk.Label(
            halign=Gtk.Align.START,
            xalign=0,
            wrap=False,
            single_line_mode=True,
            ellipsize=Pango.EllipsizeMode.END,
        )
        self._title_label.add_css_class("heading")
        self._info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._collections_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=2
        )
        self._info_box.append(self._collections_box)
        self._track_count_label = Gtk.Label(halign=Gtk.Align.START, xalign=0)
        self._track_count_label.add_css_class("dim-label")
        self._track_count_label.add_css_class("caption")
        self._info_box.append(self._track_count_label)
        self._content_box.append(self._title_label)
        self._content_box.append(self._info_box)
        self.append(self._content_box)

    def _create_collection_badge(self, collection_name: str) -> Badge:
        return Badge(collection_name)

    def _clear_collection_badges(self):
        child = self._collections_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self._collections_box.remove(child)
            child = next_child

    def _handle_star_toggled(self, star_button, starred):
        if self._on_star_toggled:
            self._on_star_toggled(star_button, starred)

    def bind_to_item(self, item: ReleaseItem, collections: Optional[List[str]] = None):
        if self._current_item and self._item_starred_connection_id:
            self._current_item.disconnect(self._item_starred_connection_id)
            self._item_starred_connection_id = None
        self._current_item = item
        self._item_starred_connection_id = item.connect(
            "notify::starred", self._on_item_starred_changed
        )
        self._title_label.set_text(item.title)
        self._star_button.set_starred(item.starred)
        self._clear_collection_badges()
        if collections:
            for collection in sorted(collections):
                badge = self._create_collection_badge(collection)
                self._collections_box.append(badge)
            self._collections_box.set_visible(True)
        else:
            self._collections_box.set_visible(False)
        track_text = (
            f"{item.track_count} tracks" if item.track_count != 1 else "1 track"
        )
        self._track_count_label.set_text(track_text)

    def _on_item_starred_changed(self, item, pspec):
        self._star_button.set_starred(item.starred)
