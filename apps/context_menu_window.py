#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, GObject, Gio
from picker_window import PickerWindow, PickerItem
from typing import Callable, List

class ContextMenuAction(PickerItem):
    __gtype_name__ = 'ContextMenuAction'
    label = GObject.Property(type=str, default='')
    action_name = GObject.Property(type=str, default='')

    def __init__(self, label: str, action_name: str, callback: Callable=None):
        super().__init__()
        self.label = label
        self.action_name = action_name
        self.callback = callback

class ContextMenuWindow(PickerWindow):

    def __init__(self, parent_window: Gtk.Window, actions: List[ContextMenuAction], **kwargs):
        self._actions = actions
        super().__init__(title='Actions', search_placeholder='Search actions...', enable_context_menu=False, window_size=(300, 400), **kwargs)
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_resizable(False)
        self.add_css_class('context-menu-window')
        GLib.idle_add(self._load_actions_immediately)

    def get_item_type(self):
        return ContextMenuAction

    def use_list_view(self):
        return True

    def load_initial_data(self):
        pass

    def on_search_changed(self, query: str):
        self._item_store.remove_all()
        query_lower = query.lower()
        for action in self._actions:
            if not query or query_lower in action.label.lower() or query_lower in action.action_name.lower():
                if action.label.strip():
                    self._item_store.append(action)
        if self._item_store.get_n_items() > 0:
            self._selection_model.set_selected(0)

    def on_item_activated(self, item):
        if isinstance(item, ContextMenuAction) and hasattr(item, 'callback') and item.callback:
            self.close()
            GLib.idle_add(item.callback)

    def get_context_menu_actions(self):
        return {}

    def get_context_menu_model(self, item):
        return None

    def _on_list_item_setup(self, factory, list_item):
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        label.set_margin_start(12)
        label.set_margin_end(12)
        list_item.set_child(label)

    def _on_list_item_bind(self, factory, list_item):
        item = list_item.get_item()
        label = list_item.get_child()
        if isinstance(item, ContextMenuAction):
            label.set_text(item.label)

    def _load_actions_immediately(self):
        for action in self._actions:
            if action.label.strip():
                self._item_store.append(action)
        if self._item_store.get_n_items() > 0:
            self._selection_model.set_selected(0)
        self._content_stack.set_visible_child_name('results')
        self._search_entry.set_text('')
        if hasattr(self, '_list_view'):
            self._list_view.grab_focus()
        return False

    def on_additional_key_pressed(self, keyval, keycode, state):
        from gi.repository import Gdk
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            selected_item = self.get_selected_item()
            if selected_item:
                self.on_item_activated(selected_item)
                return True
        return False