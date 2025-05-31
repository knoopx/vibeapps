#!/usr/bin/env python3
"""
Abstract PickerWindow class that implements common navigation patterns
for applications with search bars, list views, and keyboard navigation.

Used by launcher, nix-packages, bookmarks, and other picker-style applications.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gio, GLib, GObject, Gdk
from abc import ABC, abstractmethod
from typing import Optional, Any, List, Callable


class PickerItem(GObject.Object):
    """Base class for picker items. Subclasses should define their own properties."""
    __gtype_name__ = "PickerItem"


class GObjectABCMeta(type(GObject.Object), type(ABC)):
    """Metaclass that combines GObject and ABC metaclasses."""
    pass


class PickerWindow(Adw.ApplicationWindow, ABC, metaclass=GObjectABCMeta):
    """
    Abstract base class for picker-style windows with search and keyboard navigation.

    Features:
    - Search entry in header bar
    - List view with selection
    - Keyboard navigation (Up/Down/Enter/Escape)
    - Content stack for different states (loading, empty, results, error)
    - Auto-scrolling to selected items
    - Search debouncing
    """

    def __init__(self,
                 title: str = "Picker",
                 search_placeholder: str = "Search...",
                 window_size: tuple = (500, 900),
                 search_delay_ms: int = 300,
                 enable_context_menu: bool = True,
                 context_menu_shortcut: str = "<Control>j",
                 **kwargs):
        super().__init__(**kwargs)

        # Configuration
        self._title = title
        self._search_placeholder = search_placeholder
        self._search_delay_ms = search_delay_ms
        self._enable_context_menu = enable_context_menu
        self._context_menu_shortcut = context_menu_shortcut

        # Internal state
        self._item_store = Gio.ListStore.new(self.get_item_type())
        self._selection_model = Gtk.SingleSelection(model=self._item_store)
        self._search_delay_id = 0
        self._is_loading = False

        # Setup window
        self.set_default_size(*window_size)
        self.set_title(title)

        self._setup_ui()
        self._setup_signals()

        # Setup context menu actions if enabled
        if self._enable_context_menu:
            self._setup_context_menu_actions()

        # Initialize data
        self.load_initial_data()

    def _setup_ui(self):
        """Setup the main UI structure."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header with search
        self._header_bar = Adw.HeaderBar()
        main_box.append(self._header_bar)

        self._search_entry = Gtk.SearchEntry(
            hexpand=True,
            placeholder_text=self._search_placeholder
        )
        self._header_bar.set_title_widget(self._search_entry)

        # Content stack for different states
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        main_box.append(self._content_stack)

        # Results view
        self._setup_results_view()

        # Status pages
        self._setup_status_pages()

        # Show initial state
        self._content_stack.set_visible_child_name("empty")

    def _setup_results_view(self):
        """Setup the main results list view."""
        scrolled_window = Gtk.ScrolledWindow(vexpand=True)

        if self.use_list_view():
            # Modern ListView approach (used by nix-packages, bookmarks)
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self._on_list_item_setup)
            factory.connect("bind", self._on_list_item_bind)

            self._list_view = Gtk.ListView(
                model=self._selection_model,
                factory=factory
            )
            self._list_view.set_vexpand(True)
            self._list_view.set_can_focus(True)
            # Enable single-click activation for ListView
            self._list_view.set_single_click_activate(True)

            # Add click controller to grab focus when clicked
            click_controller = Gtk.GestureClick()
            click_controller.connect("pressed", self._on_list_view_clicked)
            self._list_view.add_controller(click_controller)

            scrolled_window.set_child(self._list_view)
            self._scrolled_window = scrolled_window
        else:
            # Traditional ListBox approach (used by launcher)
            self._list_box = Gtk.ListBox()
            self._list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
            self._list_box.set_activate_on_single_click(True)
            self._list_box.set_can_focus(True)

            # Add click controller to grab focus when clicked
            click_controller = Gtk.GestureClick()
            click_controller.connect("pressed", self._on_list_box_clicked)
            self._list_box.add_controller(click_controller)

            scrolled_window.set_child(self._list_box)
            self._scrolled_window = scrolled_window

        self._content_stack.add_named(scrolled_window, "results")

    def _setup_status_pages(self):
        """Setup loading, empty, and error status pages."""
        # Loading page
        loading_page = Adw.StatusPage(
            title="Loading...",
            icon_name=self.get_loading_icon()
        )
        spinner = Gtk.Spinner(
            spinning=True,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER
        )
        loading_page.set_child(spinner)
        self._content_stack.add_named(loading_page, "loading")

        # Empty page
        self._empty_page = Adw.StatusPage(
            title=self.get_empty_title(),
            description=self.get_empty_description(),
            icon_name=self.get_empty_icon()
        )
        self._content_stack.add_named(self._empty_page, "empty")

        # Error page
        self._error_page = Adw.StatusPage(
            title="An Error Occurred",
            description="Could not load data.",
            icon_name="dialog-error-symbolic"
        )
        self._content_stack.add_named(self._error_page, "error")

    def _setup_signals(self):
        """Setup event handlers and signals."""
        # Search entry signals
        self._search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry.connect("activate", self._on_search_activated)

        # Keyboard navigation for search entry
        search_key_controller = Gtk.EventControllerKey()
        search_key_controller.connect("key-pressed", self._on_search_key_pressed)
        self._search_entry.add_controller(search_key_controller)

        # Context menu shortcut for search entry (if enabled)
        if self._enable_context_menu:
            search_shortcut_controller = Gtk.ShortcutController.new()
            search_shortcut_controller.set_scope(Gtk.ShortcutScope.MANAGED)
            context_menu_shortcut = Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(self._context_menu_shortcut),
                Gtk.CallbackAction.new(self._show_context_menu_action_callback),
            )
            search_shortcut_controller.add_shortcut(context_menu_shortcut)
            self._search_entry.add_controller(search_shortcut_controller)

        # Global keyboard navigation for the window
        window_key_controller = Gtk.EventControllerKey()
        window_key_controller.connect("key-pressed", self._on_window_key_pressed)
        self.add_controller(window_key_controller)

        # List activation
        if self.use_list_view():
            # ListView activation via keybinding or click
            self._list_view.connect("activate", self._on_list_view_activate)
            # Also handle selection changes
            self._selection_model.connect("selection-changed", self._on_selection_changed)
        else:
            self._list_box.connect("row-activated", self._on_row_activated)

        # Window signals
        self.connect("close-request", self._on_close_request)
        self.connect("map", self._on_window_map)

    def _setup_context_menu_actions(self):
        """Setup context menu actions. Subclasses can override to add custom actions."""
        # Create action group for context menu actions
        self._context_action_group = Gio.SimpleActionGroup()

        # Add default context menu actions
        for action_name, method_name in self.get_context_menu_actions().items():
            action = Gio.SimpleAction.new(action_name, None)
            if hasattr(self, method_name):
                action.connect("activate", getattr(self, method_name))
                self._context_action_group.add_action(action)

        # Insert action group with "context" prefix
        self.insert_action_group("context", self._context_action_group)

    def _show_context_menu_action_callback(self, widget, args):
        """Callback wrapper for context menu shortcut."""
        self.show_context_menu()  # For keyboard, no specific anchor
        return True

    def show_context_menu(self, anchor_widget: Optional[Gtk.Widget] = None):
        """Show context menu for the currently selected item using a picker window."""
        selected_item = self.get_selected_item()
        if not selected_item:
            return

        # Get menu model from subclass to extract actions
        menu_model = self.get_context_menu_model(selected_item)
        if not menu_model:
            return

        # Convert Gio.Menu to ContextMenuAction list
        from context_menu_window import ContextMenuWindow, ContextMenuAction

        actions = []

        # Extract actions from menu model
        for i in range(menu_model.get_n_items()):
            label = menu_model.get_item_attribute_value(i, "label", None)
            action = menu_model.get_item_attribute_value(i, "action", None)

            if label and action:
                label_str = label.get_string()
                action_str = action.get_string()

                # Skip separators (empty labels)
                if not label_str.strip():
                    continue

                # Create callback for the action
                def make_callback(action_name):
                    def callback():
                        # Find and activate the action in our context action group
                        action_name_clean = action_name.replace("context.", "")
                        if hasattr(self, '_context_action_group') and self._context_action_group.has_action(action_name_clean):
                            self._context_action_group.activate_action(action_name_clean, None)
                    return callback

                action_obj = ContextMenuAction(label_str, action_str, make_callback(action_str))
                actions.append(action_obj)

        if not actions:
            return

        # Create and show context menu window
        context_menu = ContextMenuWindow(self, actions)
        context_menu.present()

    def _setup_context_menu_gesture(self, widget, item, list_item=None):
        """Setup right-click gesture for context menu on list items."""
        if not self._enable_context_menu:
            return

        context_menu_gesture = Gtk.GestureClick.new()
        context_menu_gesture.set_button(Gdk.BUTTON_SECONDARY)  # Right mouse button
        context_menu_gesture.connect("pressed", self._on_item_right_click, item, list_item)
        widget.add_controller(context_menu_gesture)

    def _on_item_right_click(self, gesture, n_press, x, y, item, list_item=None):
        """Handle right-click on list items."""
        if n_press == 1:  # Ensure it's a single click
            # Select the item first
            if self.use_list_view():
                if list_item:  # list_item is available if gesture was on a ListItem's child
                    position = list_item.get_position()
                    # Ensure the item is selected
                    if self._selection_model.get_selected() != position:
                        self._selection_model.set_selected(position)
                # If selection is still not right, consider selecting based on 'item' if robustly comparable
            else:  # ListBox
                # For ListBox, the gesture is on a child of the ListBoxRow.
                # We need to find the ListBoxRow to select it.
                row_widget_ancestor = gesture.get_widget()
                while row_widget_ancestor and not isinstance(row_widget_ancestor, Gtk.ListBoxRow):
                    row_widget_ancestor = row_widget_ancestor.get_parent()
                if row_widget_ancestor and isinstance(row_widget_ancestor, Gtk.ListBoxRow):
                    if self._list_box.get_selected_row() != row_widget_ancestor:
                        self._list_box.select_row(row_widget_ancestor)

            # Determine the anchor for the menu
            anchor_for_menu = gesture.get_widget() # This is the direct widget that received the click
            if not self.use_list_view():  # It's a ListBox, try to anchor to the ListBoxRow
                row_candidate = gesture.get_widget()
                while row_candidate and not isinstance(row_candidate, Gtk.ListBoxRow):
                    row_candidate = row_candidate.get_parent()
                if row_candidate: # If a ListBoxRow is found, use it as anchor
                    anchor_for_menu = row_candidate

            self.show_context_menu(anchor_widget=anchor_for_menu)

    def _on_window_map(self, window):
        """Called when window is mapped (shown)."""
        self._search_entry.grab_focus()
        self.on_window_shown()

    def _on_search_changed(self, entry):
        """Handle search text changes with debouncing."""
        if self._search_delay_id > 0:
            GLib.source_remove(self._search_delay_id)

        query = entry.get_text().strip()

        if not query:
            self._search_delay_id = 0
            self._apply_empty_search()
            return

        self._search_delay_id = GLib.timeout_add(
            self._search_delay_ms,
            self._apply_search,
            query
        )

    def _apply_empty_search(self):
        """Handle empty search - show all items or initial state."""
        self.on_search_cleared()
        if self._item_store.get_n_items() > 0:
            self._show_results()
        else:
            self._show_empty()

    def _apply_search(self, query: str):
        """Apply search filter with the given query."""
        self._search_delay_id = 0
        self.on_search_changed(query)
        return GLib.SOURCE_REMOVE

    def _on_search_activated(self, entry):
        """Handle Enter key in search entry."""
        if self.use_list_view():
            selected_pos = self._selection_model.get_selected()
            if selected_pos != Gtk.INVALID_LIST_POSITION:
                item = self._item_store.get_item(selected_pos)
                if item:
                    self.on_item_activated(item)
        else:
            selected_row = self._list_box.get_selected_row()
            if selected_row:
                self.on_item_activated(self.get_row_item(selected_row))

    def _on_search_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard navigation in search entry."""
        if keyval == Gdk.KEY_Escape:
            # Search entry has focus, close the window
            self.close()
            return True
        elif keyval == Gdk.KEY_Up or keyval == Gdk.KEY_Down:
            # Forward navigation to list view and give it focus
            self._forward_navigation_to_list(keyval, keycode, state)
            return True

        return False

    def _on_window_key_pressed(self, controller, keyval, keycode, state):
        """Handle global keyboard navigation when not in search entry."""
        has_search_focus = self._search_entry.has_focus()

        # Only handle navigation keys when search entry doesn't have focus
        if has_search_focus:
            return False

        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            # Activate selected item
            selected_item = self.get_selected_item()
            if selected_item:
                self.on_item_activated(selected_item)
                return True
        elif keyval == Gdk.KEY_Escape:
            # Search entry doesn't have focus, grab focus and select all text
            self._search_entry.grab_focus()
            self._search_entry.select_region(0, -1)  # Select all text
            # Position cursor at the end
            text_length = len(self._search_entry.get_text())
            self._search_entry.set_position(text_length)
            return True
        elif keyval == Gdk.KEY_Up or keyval == Gdk.KEY_Down:
            # Forward navigation to list view
            self._forward_navigation_to_list(keyval, keycode, state)
            return True

        # Allow subclasses to handle additional keys
        return self.on_additional_key_pressed(keyval, keycode, state)

    def _on_list_view_clicked(self, gesture, n_press, x, y):
        """Handle ListView clicks - grab focus and update selection."""
        self._list_view.grab_focus()

    def _on_list_box_clicked(self, gesture, n_press, x, y):
        """Handle ListBox clicks - grab focus."""
        self._list_box.grab_focus()

    def _forward_navigation_to_list(self, keyval, keycode, state):
        """Forward keyboard navigation to the appropriate list view."""
        if self.use_list_view():
            # Give focus to ListView and let it handle navigation natively
            self._list_view.grab_focus()
            # Ensure we have a selection for navigation to work
            if self._selection_model.get_selected() == Gtk.INVALID_LIST_POSITION and self._item_store.get_n_items() > 0:
                self._selection_model.set_selected(0)
        else:
            # Give focus to ListBox and let it handle navigation natively
            self._list_box.grab_focus()
            # Ensure we have a selection for navigation to work
            if not self._list_box.get_selected_row() and self._list_box.get_first_child():
                first_visible = self._find_next_visible_row(-1, 1)
                if first_visible:
                    self._list_box.select_row(first_visible)

    def _find_next_visible_row(self, start_index: int, direction: int):
        """Find next visible row in ListBox (for filtering)."""
        index = start_index + direction
        n_items = self._list_box.observe_children().get_n_items()

        while 0 <= index < n_items:
            row = self._list_box.get_row_at_index(index)
            if row and row.get_visible():
                return row
            index += direction

        return None

    def _on_selection_changed(self, selection_model, position, n_items):
        """Handle ListView selection changes."""
        # Override in subclass if needed
        pass

    def _on_list_view_activate(self, list_view, position):
        """Handle ListView activation (Enter key or double-click)."""
        item = self._item_store.get_item(position)
        if item:
            self.on_item_activated(item)

    def _on_row_activated(self, list_box, row):
        """Handle ListBox row activation."""
        self.on_item_activated(self.get_row_item(row))

    def _on_close_request(self, window):
        """Handle window close request."""
        return self.on_close_request()

    def _on_list_item_setup(self, factory, list_item):
        """Setup ListView item UI (delegate to subclass)."""
        self.setup_list_item(list_item)

    def _on_list_item_bind(self, factory, list_item):
        """Bind data to ListView item (delegate to subclass)."""
        item = list_item.get_item()
        self.bind_list_item(list_item, item)

        # Setup context menu gesture for ListView items
        child_widget = list_item.get_child()
        if child_widget and item:
            self._setup_context_menu_gesture(child_widget, item, list_item)

    # State management methods
    def _show_loading(self):
        """Show loading state."""
        self._is_loading = True
        self._content_stack.set_visible_child_name("loading")

    def _show_results(self):
        """Show results list."""
        self._is_loading = False
        self._content_stack.set_visible_child_name("results")

        # Auto-select first item - GTK will handle scrolling automatically
        if self.use_list_view():
            if self._item_store.get_n_items() > 0:
                self._selection_model.set_selected(0)
        else:
            first_visible = self._find_next_visible_row(-1, 1)
            if first_visible:
                self._list_box.select_row(first_visible)

    def _show_empty(self, title: Optional[str] = None, description: Optional[str] = None):
        """Show empty state."""
        self._is_loading = False
        if title:
            self._empty_page.set_title(title)
        if description:
            self._empty_page.set_description(description)
        self._content_stack.set_visible_child_name("empty")

    def _show_error(self, message: str):
        """Show error state."""
        self._is_loading = False
        self._error_page.set_description(message)
        self._content_stack.set_visible_child_name("error")

    # Public API methods
    def add_item(self, item):
        """Add an item to the store."""
        self._item_store.append(item)

    def remove_all_items(self):
        """Clear all items from the store."""
        self._item_store.remove_all()

    def get_selected_item(self):
        """Get the currently selected item."""
        if self.use_list_view():
            selected_pos = self._selection_model.get_selected()
            if selected_pos != Gtk.INVALID_LIST_POSITION:
                return self._item_store.get_item(selected_pos)
        else:
            selected_row = self._list_box.get_selected_row()
            if selected_row:
                return self.get_row_item(selected_row)
        return None

    def set_loading(self, loading: bool):
        """Set loading state."""
        if loading:
            self._show_loading()
        elif self._item_store.get_n_items() > 0:
            self._show_results()
        else:
            self._show_empty()

    def set_search_text(self, text: str):
        """Set search entry text."""
        self._search_entry.set_text(text)

    def get_search_text(self) -> str:
        """Get current search text."""
        return self._search_entry.get_text().strip()

    # Abstract methods that subclasses must implement
    @abstractmethod
    def get_item_type(self) -> type:
        """Return the GObject type for items in this picker."""
        pass

    @abstractmethod
    def use_list_view(self) -> bool:
        """Return True to use modern ListView, False for traditional ListBox."""
        pass

    @abstractmethod
    def on_item_activated(self, item):
        """Called when an item is activated (Enter key or double-click)."""
        pass

    @abstractmethod
    def load_initial_data(self):
        """Load initial data for the picker."""
        pass

    @abstractmethod
    def on_search_changed(self, query: str):
        """Handle search query changes."""
        pass

    # Abstract methods for context menu support
    @abstractmethod
    def get_context_menu_actions(self) -> dict:
        """
        Return a dictionary mapping action names to method names for context menu.

        Example:
        {
            "open_item": "on_open_item_action",
            "delete_item": "on_delete_item_action",
            "rename_item": "on_rename_item_action"
        }
        """
        pass

    @abstractmethod
    def get_context_menu_model(self, item) -> Optional[Gio.Menu]:
        """
        Return a Gio.Menu for the context menu of the given item.
        Return None if no context menu should be shown.

        Example:
        menu_model = Gio.Menu.new()
        menu_model.append("Open", "context.open_item")
        menu_model.append("Delete", "context.delete_item")
        return menu_model
        """
        pass

    # Optional methods that subclasses can override
    def on_search_cleared(self):
        """Called when search is cleared. Default: do nothing."""
        pass

    def on_escape_pressed(self):
        """Handle Escape key. Default behavior: close window."""
        self.close()

    def on_close_request(self) -> bool:
        """Handle close request. Return True to prevent default close."""
        return False

    def on_window_shown(self):
        """Called when window is shown. Default: do nothing."""
        pass

    def get_loading_icon(self) -> str:
        """Return icon name for loading page."""
        return "find-location-symbolic"

    def get_empty_icon(self) -> str:
        """Return icon name for empty page."""
        return "system-search-symbolic"

    def get_empty_title(self) -> str:
        """Return title for empty page."""
        return f"Search {self._title}"

    def get_empty_description(self) -> str:
        """Return description for empty page."""
        return "Type your query in the search bar above."

    # Methods for ListView approach
    def setup_list_item(self, list_item):
        """Setup UI for a ListView item. Override if using ListView."""
        pass

    def bind_list_item(self, list_item, item):
        """Bind data to a ListView item. Override if using ListView."""
        pass

    # Methods for ListBox approach
    def get_row_item(self, row):
        """Get the item associated with a ListBox row. Override if using ListBox."""
        return getattr(row, 'item', None)

    def create_row_widget(self, item):
        """Create widget for a ListBox row. Override if using ListBox."""
        return Gtk.Label(label=str(item))

    # Optional methods that subclasses can override
    def on_additional_key_pressed(self, keyval, keycode, state) -> bool:
        """
        Handle additional key presses not covered by default navigation.
        Return True if the key was handled, False otherwise.
        """
        return False

    def _items_equal(self, item1, item2):
        """
        Compare two items for equality. Subclasses can override this for better comparison.
        Default implementation uses object identity.
        """
        return item1 == item2
