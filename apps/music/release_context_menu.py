from typing import Optional, Dict
from gi.repository import Gtk, Gio
from serialization import ReleaseItem


class ReleaseContextMenu(Gtk.Widget):

    def __init__(self, parent_window):
        super().__init__()
        self._parent_window = parent_window
        self._action_group = None

    def setup_actions(self):
        self._action_group = Gio.SimpleActionGroup()
        actions = self.get_context_menu_actions()
        for action_name, method_name in actions.items():
            action = Gio.SimpleAction.new(action_name, None)
            if hasattr(self._parent_window, method_name):
                action.connect("activate", getattr(self._parent_window, method_name))
                self._action_group.add_action(action)
        self._parent_window.insert_action_group("context", self._action_group)

    def get_context_menu_actions(self) -> Dict[str, str]:
        return {
            "reveal": "on_reveal_action",
            "trash_release": "on_trash_release_action",
            "add_to_collection": "on_add_to_collection_action",
        }

    def get_context_menu_model(self, item: Optional[ReleaseItem]) -> Optional[Gio.Menu]:
        if not item:
            return None
        menu_model = Gio.Menu.new()
        menu_model.append("Add to Collection", "context.add_to_collection")
        menu_model.append("Reveal in Files", "context.reveal")
        menu_model.append("Move to Trash", "context.trash_release")
        return menu_model
