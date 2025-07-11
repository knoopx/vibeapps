import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, GObject
from picker_window import PickerWindow, PickerItem
from typing import Callable, List, Optional


class ContextMenuAction(PickerItem):
    __gtype_name__ = "ContextMenuAction"
    label = GObject.Property(type=str, default="")
    action_name = GObject.Property(type=str, default="")

    def __init__(self, label: str, action_name: str, callback: 'Optional[Callable]' = None):
        super().__init__()
        self.label = label
        self.action_name = action_name
        self.callback = callback



class ContextMenuListItem(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.label = Gtk.Label()
        self.label.set_halign(Gtk.Align.START)
        self.label.set_margin_top(8)
        self.label.set_margin_bottom(8)
        self.label.set_margin_start(12)
        self.label.set_margin_end(12)
        self.append(self.label)

class ContextMenuWindow(PickerWindow):

    def __init__(
        self, parent_window: Gtk.Window, actions: List[ContextMenuAction], **kwargs
    ):
        self._actions = actions
        super().__init__(
            title="Actions",
            search_placeholder="Search actions...",
            context_menu_shortcut=None,
            window_size=(300, 400),
            **kwargs
        )
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_resizable(False)
        self.add_css_class("context-menu-window")
        GLib.idle_add(self._load_actions_immediately)

    def get_item_type(self):
        return ContextMenuAction

    def load_initial_data(self):
        pass

    def on_search_changed(self, query: str):
        self._item_store.remove_all()
        query_lower = query.lower()
        for action in self._actions:
            if (
                not query
                or query_lower in action.label.lower()
                or query_lower in action.action_name.lower()
            ):
                if action.label.strip():
                    self._item_store.append(action)
        if self._item_store.get_n_items() > 0:
            self._selection_model.set_selected(0)

    def on_item_activated(self, item):
        if (
            isinstance(item, ContextMenuAction)
            and hasattr(item, "callback")
            and item.callback
        ):
            self.close()
            GLib.idle_add(item.callback)

    def get_context_menu_model(self, item):
        return None

    def setup_list_item(self, list_item):
        widget = ContextMenuListItem()
        list_item.set_child(widget)

    def bind_list_item(self, list_item, item):
        widget = list_item.get_child()
        assert isinstance(widget, ContextMenuListItem)
        widget.label.set_text(item.label)

    def _load_actions_immediately(self):
        for action in self._actions:
            if action.label.strip():
                self._item_store.append(action)
        if self._item_store.get_n_items() > 0:
            self._selection_model.set_selected(0)
        self._content_stack.set_visible_child_name("results")
        self._search_entry.set_text("")
        if hasattr(self, "_list_view"):
            self._list_view.grab_focus()
        return False
