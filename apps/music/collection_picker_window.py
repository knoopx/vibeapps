#!/usr/bin/env python3
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, GLib, GObject, Pango
from picker_window import PickerWindow, PickerItem
from collection_manager import CollectionManager
from typing import Callable


class CollectionItem(PickerItem):
    __gtype_name__ = "CollectionItem"
    name = GObject.Property(type=str, default="")
    is_new = GObject.Property(type=bool, default=False)

    def __init__(self, name: str, is_new: bool = False):
        super().__init__()
        self.name = name
        self.is_new = is_new


class CollectionPickerWindow(PickerWindow):

    def __init__(
        self,
        parent_window: Gtk.Window,
        collection_manager: CollectionManager,
        on_collection_selected: Callable[[str], None],
        **kwargs,
    ):
        self._collections_manager = collection_manager
        self._on_collection_selected = on_collection_selected
        self._existing_collections = []
        super().__init__(
            title="Add to Collection",
            search_placeholder="Search or create collection...",
            context_menu_shortcut=None,
            window_size=(400, 500),
            **kwargs,
        )
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_resizable(True)
        self.add_css_class("collection-picker-window")

    def get_item_type(self):
        return CollectionItem

    def load_initial_data(self):
        self._existing_collections = list(self._collections_manager.keys())
        self._update_collection_list("")

    def on_search_changed(self, query: str):
        self._update_collection_list(query)

    def on_search_cleared(self):
        self._update_collection_list("")

    def _update_collection_list(self, query: str):
        self.remove_all_items()
        query_lower = query.strip().lower()
        matching_collections = []
        for collection_name in self._existing_collections:
            if not query_lower or query_lower in collection_name.lower():
                matching_collections.append(collection_name)
        matching_collections.sort()
        for collection_name in matching_collections:
            self.add_item(CollectionItem(collection_name, is_new=False))
        if query.strip() and query.strip() not in self._existing_collections:
            if (
                len(query.strip()) <= 50
                and query.strip()
                .replace(" ", "")
                .replace("_", "")
                .replace("-", "")
                .isalnum()
            ):
                self.add_item(CollectionItem(f"Create '{query.strip()}'", is_new=True))
        if self.get_item_count() > 0:
            self._show_results()
            if self._selection_model.get_selected() == Gtk.INVALID_LIST_POSITION:
                self._selection_model.set_selected(0)
        elif query_lower:
            self._show_empty(
                title="No Matching Collections",
                description="Type a name to create a new collection.",
            )
        else:
            self._show_empty(
                title="No Collections",
                description="Type a name to create your first collection.",
            )

    def get_item_count(self) -> int:
        return self._item_store.get_n_items()

    def on_item_activated(self, item: CollectionItem):
        if item.is_new:
            collection_name = item.name
            if collection_name.startswith("Create '") and collection_name.endswith("'"):
                collection_name = collection_name[8:-1]
        else:
            collection_name = item.name
        self.close()
        GLib.idle_add(lambda: self._on_collection_selected(collection_name))

    def get_context_menu_actions(self):
        return {}

    def get_context_menu_model(self, item):
        return None

    def setup_list_item(self, list_item: Gtk.ListItem):
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )
        icon = Gtk.Image.new_from_icon_name("folder-symbolic")
        icon.set_icon_size(Gtk.IconSize.NORMAL)
        icon.set_valign(Gtk.Align.CENTER)
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        main_box.append(icon)
        main_box.append(label)
        list_item.set_child(main_box)

    def bind_list_item(self, list_item: Gtk.ListItem, item: CollectionItem):
        main_box = list_item.get_child()
        if main_box is None:
            return
        first_child = main_box.get_first_child()
        if first_child is None:
            return
        second_child = first_child.get_next_sibling()
        if second_child is None:
            return
        icon = first_child
        label = second_child
        if item.is_new:
            if hasattr(icon, "set_from_icon_name"):
                icon.set_from_icon_name("folder-new-symbolic")
            if hasattr(label, "add_css_class"):
                label.add_css_class("dim-label")
        else:
            if hasattr(icon, "set_from_icon_name"):
                icon.set_from_icon_name("folder-symbolic")
            if hasattr(label, "remove_css_class"):
                label.remove_css_class("dim-label")
        if hasattr(label, "set_text"):
            label.set_text(item.name)

    def get_empty_icon(self) -> str:
        return "folder-symbolic"

    def get_empty_title(self) -> str:
        return "No Collections"

    def get_empty_description(self) -> str:
        return "Type a name to create your first collection."
