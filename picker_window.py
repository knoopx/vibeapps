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
                 window_size: tuple = (400, 800),
                 search_delay_ms: int = 300,
                 **kwargs):
        super().__init__(**kwargs)

        # Configuration
        self._title = title
        self._search_placeholder = search_placeholder
        self._search_delay_ms = search_delay_ms

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

            scrolled_window.set_child(self._list_view)
            self._scrolled_window = scrolled_window
        else:
            # Traditional ListBox approach (used by launcher)
            self._list_box = Gtk.ListBox()
            self._list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
            self._list_box.set_activate_on_single_click(True)

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

        # Keyboard navigation
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self._search_entry.add_controller(key_controller)

        # List activation
        if self.use_list_view():
            # ListView doesn't have row-activated signal, handle via selection change
            self._selection_model.connect("selection-changed", self._on_selection_changed)
        else:
            self._list_box.connect("row-activated", self._on_row_activated)

        # Window signals
        self.connect("close-request", self._on_close_request)
        self.connect("map", self._on_window_map)

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

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard navigation."""
        if keyval == Gdk.KEY_Escape:
            self.on_escape_pressed()
            return True
        elif keyval == Gdk.KEY_Up:
            self._move_selection(-1)
            return True
        elif keyval == Gdk.KEY_Down:
            self._move_selection(1)
            return True

        return False

    def _move_selection(self, direction: int):
        """Move selection up or down."""
        if self.use_list_view():
            selected_pos = self._selection_model.get_selected()
            new_pos = selected_pos + direction

            if 0 <= new_pos < self._item_store.get_n_items():
                self._selection_model.set_selected(new_pos)
                self._scroll_to_selected_list_view()
        else:
            selected_row = self._list_box.get_selected_row()
            if not selected_row:
                # No selection, select first visible
                first_visible = self._find_next_visible_row(0, 1)
                if first_visible:
                    self._list_box.select_row(first_visible)
                    self._scroll_to_row(first_visible)
                return

            start_index = selected_row.get_index()
            next_row = self._find_next_visible_row(start_index, direction)
            if next_row:
                self._list_box.select_row(next_row)
                self._scroll_to_row(next_row)

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

    def _scroll_to_selected_list_view(self):
        """Scroll ListView to show selected item."""
        selected_pos = self._selection_model.get_selected()
        if selected_pos != Gtk.INVALID_LIST_POSITION:
            GLib.idle_add(
                lambda: self._list_view.scroll_to(
                    selected_pos, Gtk.ListScrollFlags.FOCUS, None
                )
            )

    def _scroll_to_row(self, row):
        """Scroll ListBox to show specific row."""
        adj = self._scrolled_window.get_vadjustment()
        if not adj:
            return

        row_height = row.get_allocated_height()
        row_y = row.get_allocation().y
        visible_height = self._scrolled_window.get_allocated_height()
        visible_top = adj.get_value()
        visible_bottom = visible_top + visible_height

        if row_y < visible_top or (row_y + row_height) > visible_bottom:
            target = row_y - (visible_height - row_height) / 2
            target = max(0, min(target, adj.get_upper() - visible_height))
            adj.set_value(target)

    def _on_selection_changed(self, selection_model, position, n_items):
        """Handle ListView selection changes."""
        # Override in subclass if needed
        pass

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

    # State management methods
    def _show_loading(self):
        """Show loading state."""
        self._is_loading = True
        self._content_stack.set_visible_child_name("loading")

    def _show_results(self):
        """Show results list."""
        self._is_loading = False
        self._content_stack.set_visible_child_name("results")

        # Auto-select first item
        if self.use_list_view():
            if self._item_store.get_n_items() > 0:
                self._selection_model.set_selected(0)
                self._scroll_to_selected_list_view()
        else:
            first_visible = self._find_next_visible_row(-1, 1)
            if first_visible:
                self._list_box.select_row(first_visible)
                self._scroll_to_row(first_visible)

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

    # Optional methods that subclasses can override
    def on_search_cleared(self):
        """Called when search is cleared. Default: do nothing."""
        pass

    def on_escape_pressed(self):
        """Handle Escape key. Default: close window."""
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
