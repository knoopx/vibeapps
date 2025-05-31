#!/usr/bin/env python3
"""
Context menu window that displays actions as a picker-style list.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib, GObject, Gio
from picker_window import PickerWindow, PickerItem
from typing import Callable, List


class ContextMenuAction(PickerItem):
    """Represents a context menu action."""
    __gtype_name__ = "ContextMenuAction"

    label = GObject.Property(type=str, default="")
    action_name = GObject.Property(type=str, default="")

    def __init__(self, label: str, action_name: str, callback: Callable = None):
        super().__init__()
        self.label = label
        self.action_name = action_name
        self.callback = callback


class ContextMenuWindow(PickerWindow):
    """
    A picker-style context menu window that shows actions as a list.
    """

    def __init__(self, parent_window: Gtk.Window, actions: List[ContextMenuAction], **kwargs):
        self._actions = actions

        super().__init__(
            title="Actions",
            search_placeholder="Search actions...",
            enable_context_menu=False,  # Don't enable context menu on the context menu
            **kwargs
        )

        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_resizable(False)
        self.add_css_class("context-menu-window")

        # Force load the actions immediately after UI setup
        GLib.idle_add(self._load_actions_immediately)

    def get_item_type(self):
        """Return the type of items this picker handles."""
        return ContextMenuAction

    def use_list_view(self):
        """Use ListView for modern appearance."""
        return True

    def load_initial_data(self):
        """Load the context menu actions - now handled by _load_actions_immediately."""
        # This is called by the parent class, but we handle loading in _load_actions_immediately
        # to ensure immediate display
        pass

    def on_search_changed(self, query: str):
        """Filter actions based on search query."""
        # Clear current items
        self._item_store.remove_all()

        # Filter and add matching actions
        query_lower = query.lower()
        for action in self._actions:
            if (not query or
                query_lower in action.label.lower() or
                query_lower in action.action_name.lower()):
                if action.label.strip():  # Skip separators
                    self._item_store.append(action)

        # Select first item if available
        if self._item_store.get_n_items() > 0:
            self._selection_model.set_selected(0)

    def on_item_activated(self, item):
        """Execute the selected action and close the menu."""
        if isinstance(item, ContextMenuAction) and hasattr(item, 'callback') and item.callback:
            self.close()
            # Execute callback after a short delay to ensure window closes first
            GLib.idle_add(item.callback)

    def get_context_menu_actions(self):
        """No context menu actions for context menu items."""
        return {}

    def get_context_menu_model(self, item):
        """No context menu for context menu items."""
        return None

    def _on_list_item_setup(self, factory, list_item):
        """Setup the UI for each action item."""
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        label.set_margin_start(12)
        label.set_margin_end(12)
        list_item.set_child(label)

    def _on_list_item_bind(self, factory, list_item):
        """Bind action data to the list item."""
        item = list_item.get_item()
        label = list_item.get_child()
        if isinstance(item, ContextMenuAction):
            label.set_text(item.label)

    def _load_actions_immediately(self):
        """Force load actions immediately and show results."""
        # Load the actions
        for action in self._actions:
            if action.label.strip():  # Skip separators
                self._item_store.append(action)

        # Select first item if available
        if self._item_store.get_n_items() > 0:
            self._selection_model.set_selected(0)

        # Show the results page immediately
        self._content_stack.set_visible_child_name("results")

        # Clear the search entry so it doesn't interfere
        self._search_entry.set_text("")

        # Focus on the list view for immediate navigation
        if hasattr(self, '_list_view'):
            self._list_view.grab_focus()

        return False  # Remove from idle queue

    def on_additional_key_pressed(self, keyval, keycode, state):
        """Handle additional key presses."""
        # Import Gdk here to avoid import order issues
        from gi.repository import Gdk

        # Escape closes the menu
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True

        # Enter activates the selected item immediately
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            selected_item = self.get_selected_item()
            if selected_item:
                self.on_item_activated(selected_item)
                return True

        # Arrow keys for navigation (handled by parent class)
        return False
