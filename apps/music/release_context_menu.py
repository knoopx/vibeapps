from typing import Optional
from gi.repository import Gtk, Gio
from serialization import ReleaseItem


class ReleaseContextMenu(Gtk.Widget):

    def __init__(self, parent_window):
        super().__init__()
        self._parent_window = parent_window

    def get_context_menu_model(self, item: Optional[ReleaseItem]) -> Optional[Gio.Menu]:
        if not item:
            return None
        menu_model = Gio.Menu.new()
        menu_model.append("Add to Collection", "context.on_add_to_collection_action")
        menu_model.append("Reveal in Files", "context.on_reveal_action")
        menu_model.append("Move to Trash", "context.on_trash_release_action")
        return menu_model
