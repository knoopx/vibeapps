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

        # Add to collection action
        menu_model.append("Add to Collection", "context.on_add_to_collection_action")        # Add remove from collection actions for active collections
        if hasattr(self._parent_window, "_collections") and item.path:
            active_collections = self._parent_window._collections.lookup(item.path)
            if active_collections:
                # Add a separator if we have active collections
                menu_model.append_section(None, Gio.Menu.new())

                # Add remove actions for each active collection
                for collection in active_collections:
                    # Sanitize collection name for action name (replace spaces and special chars with underscores)
                    sanitized_name = ''.join(c if c.isalnum() else '_' for c in collection.name)
                    action_name = f"on_remove_from_collection_{sanitized_name}"
                    menu_label = f"Remove from {collection.name}"
                    menu_model.append(menu_label, f"context.{action_name}")

        # Standard actions
        menu_model.append("Reveal in Files", "context.on_reveal_action")
        menu_model.append("Move to Trash", "context.on_trash_release_action")
        return menu_model
