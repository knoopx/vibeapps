import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib, GObject, Gdk
from abc import ABC, abstractmethod
from typing import Optional, Any, List, Callable


class PickerItem(GObject.Object):
    __gtype_name__ = "PickerItem"


class GObjectABCMeta(type(GObject.Object), type(ABC)):
    pass


class PickerWindow(Adw.ApplicationWindow, ABC, metaclass=GObjectABCMeta):
    # ============================================================================
    # INITIALIZATION & SETUP
    # ============================================================================

    def __init__(
        self,
        title: str = "Picker",
        search_placeholder: str = "Search...",
        window_size: tuple = (500, 900),
        search_delay_ms: int = 300,
        context_menu_shortcut: Optional[str] = "<Control>j",
        global_context_menu_shortcut: Optional[str] = "<Control><Shift>j",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._search_placeholder = search_placeholder
        self._search_delay_ms = search_delay_ms
        self._context_menu_shortcut = context_menu_shortcut
        self._global_context_menu_shortcut = global_context_menu_shortcut
        self._item_store = Gio.ListStore.new(self.get_item_type())
        self._selection_model = Gtk.SingleSelection(model=self._item_store)
        self._search_delay_id = 0
        self._is_loading = False
        self.set_default_size(*window_size)
        self.set_title(title)
        self._setup_ui()
        self._setup_signals()
        if self._context_menu_shortcut is not None:
            self._setup_context_menu_actions()
        if self._global_context_menu_shortcut is not None:
            self._setup_global_context_menu_actions()
        self.load_initial_data()

    # ============================================================================
    # UI SETUP METHODS
    # ============================================================================

    def _setup_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        self._header_bar = Adw.HeaderBar()
        main_box.append(self._header_bar)
        self._search_entry = Gtk.SearchEntry(
            hexpand=True, placeholder_text=self._search_placeholder
        )
        self._setup_header_bar()
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        main_box.append(self._content_stack)
        self._setup_results_view()
        self._setup_status_pages()
        self._content_stack.set_visible_child_name("empty")

    def _setup_header_bar(self) -> None:
        left_widgets = self.get_header_bar_left_widgets()
        for widget in left_widgets:
            self._header_bar.pack_start(widget)
        title_widget = self.get_header_bar_title_widget()
        if title_widget:
            self._header_bar.set_title_widget(title_widget)
        else:
            self._header_bar.set_title_widget(self._search_entry)
        right_widgets = self.get_header_bar_right_widgets()
        for widget in right_widgets:
            self._header_bar.pack_end(widget)

    def _setup_results_view(self) -> None:
        scrolled_window = Gtk.ScrolledWindow(vexpand=True)
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_list_item_setup)
        factory.connect("bind", self._on_list_item_bind)
        self._list_view = Gtk.ListView(model=self._selection_model, factory=factory)
        self._list_view.set_vexpand(True)
        self._list_view.set_can_focus(True)
        self._list_view.set_single_click_activate(True)
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", self._on_list_view_clicked)
        self._list_view.add_controller(click_controller)
        scrolled_window.set_child(self._list_view)
        self._scrolled_window = scrolled_window
        self._content_stack.add_named(scrolled_window, "results")

        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self.on_listview_key_pressed)
        self._list_view.add_controller(controller)

    def _setup_status_pages(self) -> None:
        loading_page = Adw.StatusPage(
            title="Loading...", icon_name=self.get_loading_icon()
        )
        spinner = Gtk.Spinner(
            spinning=True, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER
        )
        loading_page.set_child(spinner)
        self._content_stack.add_named(loading_page, "loading")
        self._empty_page = Adw.StatusPage(
            title=self.get_empty_title(),
            description=self.get_empty_description(),
            icon_name=self.get_empty_icon(),
        )
        self._content_stack.add_named(self._empty_page, "empty")
        self._error_page = Adw.StatusPage(
            title="An Error Occurred",
            description="Could not load data.",
            icon_name="dialog-error-symbolic",
        )
        self._content_stack.add_named(self._error_page, "error")

    def _setup_signals(self) -> None:
        self._search_entry.connect("search-changed", self._on_search_changed)
        self._search_entry.connect("activate", self._on_search_activated)
        search_key_controller = Gtk.EventControllerKey()
        search_key_controller.connect("key-pressed", self._on_search_key_pressed)
        self._search_entry.add_controller(search_key_controller)
        if self._context_menu_shortcut is not None:
            search_shortcut_controller = Gtk.ShortcutController.new()
            search_shortcut_controller.set_scope(Gtk.ShortcutScope.MANAGED)
            context_menu_shortcut = Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(self._context_menu_shortcut),
                Gtk.CallbackAction.new(self._show_context_menu_action_callback),
            )
            search_shortcut_controller.add_shortcut(context_menu_shortcut)
            self._search_entry.add_controller(search_shortcut_controller)
        if self._global_context_menu_shortcut is not None:
            global_shortcut_controller = Gtk.ShortcutController.new()
            global_shortcut_controller.set_scope(Gtk.ShortcutScope.MANAGED)
            global_context_menu_shortcut = Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(self._global_context_menu_shortcut),
                Gtk.CallbackAction.new(self._show_global_context_menu_action_callback),
            )
            global_shortcut_controller.add_shortcut(global_context_menu_shortcut)
            self.add_controller(global_shortcut_controller)
        window_key_controller = Gtk.EventControllerKey()
        window_key_controller.connect("key-pressed", self._on_window_key_pressed)
        self.add_controller(window_key_controller)
        self._list_view.connect("activate", self._on_list_view_activate)
        self._selection_model.connect("selection-changed", self._on_selection_changed)
        self.connect("close-request", self._on_close_request)
        self.connect("map", self._on_window_map)

    # ============================================================================
    # CONTEXT MENU METHODS
    # ============================================================================

    def _setup_context_menu_actions(self) -> None:
        self._context_action_group = Gio.SimpleActionGroup()
        self.insert_action_group("context", self._context_action_group)

    def _show_context_menu_action_callback(self, widget: Gtk.Widget, args: Any) -> bool:
        self.show_context_menu()
        return True

    def show_context_menu(self, anchor_widget: Optional[Gtk.Widget] = None) -> None:
        selected_item = self.get_selected_item()

        if not selected_item:
            return

        menu_model = self.get_context_menu_model(selected_item)
        if not menu_model:
            return

        for i in range(menu_model.get_n_items()):
            action = menu_model.get_item_attribute_value(i, "action", None)
            if action:
                action_str = action.get_string()
                if action_str.startswith("context."):
                    method_name = action_str.replace("context.", "")
                    if hasattr(
                        self, method_name
                    ) and not self._context_action_group.has_action(method_name):
                        gio_action = Gio.SimpleAction.new(method_name, None)
                        gio_action.connect("activate", getattr(self, method_name))
                        self._context_action_group.add_action(gio_action)

        from context_menu_window import ContextMenuWindow, ContextMenuAction

        actions = []
        for i in range(menu_model.get_n_items()):
            label = menu_model.get_item_attribute_value(i, "label", None)
            action = menu_model.get_item_attribute_value(i, "action", None)
            if label and action:
                label_str = label.get_string()
                action_str = action.get_string()
                if not label_str.strip():
                    continue

                def make_callback(action_name: str) -> Callable[[], None]:

                    def callback() -> None:
                        action_name_clean = action_name.replace("context.", "")
                        if hasattr(
                            self, "_context_action_group"
                        ) and self._context_action_group.has_action(action_name_clean):
                            self._context_action_group.activate_action(
                                action_name_clean, None
                            )

                    return callback

                action_obj = ContextMenuAction(
                    label_str, action_str, make_callback(action_str)
                )
                actions.append(action_obj)
        if not actions:
            return
        context_menu = ContextMenuWindow(self, actions)
        context_menu.present()

    def _setup_context_menu_gesture(
        self, widget: Gtk.Widget, item: Any, list_item: Optional[Gtk.ListItem] = None
    ) -> None:
        if self._context_menu_shortcut is None:
            return
        context_menu_gesture = Gtk.GestureClick.new()
        context_menu_gesture.set_button(Gdk.BUTTON_SECONDARY)
        context_menu_gesture.connect(
            "pressed", self._on_item_right_click, item, list_item
        )
        widget.add_controller(context_menu_gesture)

    def _setup_global_context_menu_actions(self) -> None:
        self._global_context_action_group = Gio.SimpleActionGroup()
        for action_name, method_name in self.get_global_context_menu_actions().items():
            action = Gio.SimpleAction.new(action_name, None)
            if hasattr(self, method_name):
                action.connect("activate", getattr(self, method_name))
                self._global_context_action_group.add_action(action)
        self.insert_action_group("global", self._global_context_action_group)

    def _show_global_context_menu_action_callback(
        self, widget: Gtk.Widget, args: Any
    ) -> bool:
        self.show_global_context_menu()
        return True

    def show_global_context_menu(
        self, anchor_widget: Optional[Gtk.Widget] = None
    ) -> None:
        menu_model = self.get_global_context_menu_model()
        if not menu_model:
            return
        from context_menu_window import ContextMenuWindow, ContextMenuAction

        actions = []
        for i in range(menu_model.get_n_items()):
            label = menu_model.get_item_attribute_value(i, "label", None)
            action = menu_model.get_item_attribute_value(i, "action", None)
            if label and action:
                label_str = label.get_string()
                action_str = action.get_string()
                if not label_str.strip():
                    continue

                def make_callback(action_name: str) -> Callable[[], None]:

                    def callback() -> None:
                        action_name_clean = action_name.replace("global.", "")
                        if hasattr(
                            self, "_global_context_action_group"
                        ) and self._global_context_action_group.has_action(
                            action_name_clean
                        ):
                            self._global_context_action_group.activate_action(
                                action_name_clean, None
                            )

                    return callback

                action_obj = ContextMenuAction(
                    label_str, action_str, make_callback(action_str)
                )
                actions.append(action_obj)
        if not actions:
            return
        context_menu = ContextMenuWindow(self, actions)
        context_menu.present()

    # ============================================================================
    # EVENT HANDLERS
    # ============================================================================

    def _on_window_map(self, window: Gtk.Window) -> None:
        self._search_entry.grab_focus()
        self.on_window_shown()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        if self._search_delay_id > 0:
            GLib.source_remove(self._search_delay_id)
        query = entry.get_text().strip()
        if not query:
            self._search_delay_id = 0
            self._apply_empty_search()
            return
        self._search_delay_id = GLib.timeout_add(
            self._search_delay_ms, self._apply_search, query
        )

    def _on_search_activated(self, entry: Gtk.SearchEntry) -> None:
        selected_pos = self._selection_model.get_selected()
        if selected_pos != Gtk.INVALID_LIST_POSITION:
            item = self._item_store.get_item(selected_pos)
            if item:
                self.on_item_activated(item)

    def _on_search_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        elif keyval == Gdk.KEY_Up or keyval == Gdk.KEY_Down:
            self._forward_navigation_to_list(keyval, keycode, state)
            return True
        return False

    def _on_window_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            selected_item = self.get_selected_item()
            if selected_item:
                self.on_item_activated(selected_item)
                return True
        elif keyval == Gdk.KEY_Escape:
            self._search_entry.grab_focus()
            self._search_entry.select_region(0, -1)
            text_length = len(self._search_entry.get_text())
            self._search_entry.set_position(text_length)
            return True

        return False

    def on_listview_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ):
        return False

    def _on_list_view_clicked(
        self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float
    ) -> None:
        self._list_view.grab_focus()

    def _on_list_view_activate(self, list_view: Gtk.ListView, position: int) -> None:
        item = self._item_store.get_item(position)
        if item:
            self.on_item_activated(item)

    def _on_selection_changed(
        self, selection_model: Gtk.SelectionModel, position: int, n_items: int
    ) -> None:
        pass

    def _on_list_item_setup(
        self, factory: Gtk.ListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        self.setup_list_item(list_item)

    def _on_list_item_bind(
        self, factory: Gtk.ListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        item = list_item.get_item()
        self.bind_list_item(list_item, item)
        child_widget = list_item.get_child()
        if child_widget and item:
            self._setup_context_menu_gesture(child_widget, item, list_item)

    def _on_item_right_click(
        self,
        gesture: Gtk.GestureClick,
        n_press: int,
        x: float,
        y: float,
        item: Any,
        list_item: Optional[Gtk.ListItem] = None,
    ) -> None:
        if n_press == 1:
            if list_item:
                position = list_item.get_position()
                if self._selection_model.get_selected() != position:
                    self._selection_model.set_selected(position)
            anchor_for_menu = gesture.get_widget()
            self.show_context_menu(anchor_widget=anchor_for_menu)

    def _on_close_request(self, window: Gtk.Window) -> bool:
        return self.on_close_request()

    # ============================================================================
    # SEARCH & NAVIGATION HELPERS
    # ============================================================================

    def _apply_empty_search(self) -> None:
        self.on_search_cleared()
        if self._item_store.get_n_items() > 0:
            self._show_results()
        else:
            self._show_empty()

    def _apply_search(self, query: str) -> bool:
        self._search_delay_id = 0
        self.on_search_changed(query)
        return GLib.SOURCE_REMOVE

    def _forward_navigation_to_list(
        self, keyval: int, keycode: int, state: Gdk.ModifierType
    ) -> None:
        self._list_view.grab_focus()
        if (
            self._selection_model.get_selected() == Gtk.INVALID_LIST_POSITION
            and self._item_store.get_n_items() > 0
        ):
            self._selection_model.set_selected(0)

    # ============================================================================
    # STATE MANAGEMENT METHODS
    # ============================================================================

    def _show_loading(self) -> None:
        self._is_loading = True
        self._content_stack.set_visible_child_name("loading")

    def _show_results(self) -> None:
        self._is_loading = False
        self._content_stack.set_visible_child_name("results")
        if self._item_store.get_n_items() > 0:
            self._selection_model.set_selected(0)

    def _show_empty(
        self, title: Optional[str] = None, description: Optional[str] = None
    ) -> None:
        self._is_loading = False
        if title:
            self._empty_page.set_title(title)
        if description:
            self._empty_page.set_description(description)
        self._content_stack.set_visible_child_name("empty")

    def _show_error(self, message: str) -> None:
        self._is_loading = False
        self._error_page.set_description(message)
        self._content_stack.set_visible_child_name("error")

    # ============================================================================
    # ITEM MANAGEMENT METHODS
    # ============================================================================

    def add_item(self, item: Any) -> None:
        self._item_store.append(item)

    def remove_all_items(self) -> None:
        self._item_store.remove_all()

    def get_selected_item(self) -> Optional[Any]:
        selected_pos = self._selection_model.get_selected()
        if selected_pos != Gtk.INVALID_LIST_POSITION:
            return self._item_store.get_item(selected_pos)
        return None

    # ============================================================================
    # PUBLIC API METHODS
    # ============================================================================

    def set_loading(self, loading: bool) -> None:
        if loading:
            self._show_loading()
        elif self._item_store.get_n_items() > 0:
            self._show_results()
        else:
            self._show_empty()

    def set_search_text(self, text: str) -> None:
        self._search_entry.set_text(text)

    def get_search_text(self) -> str:
        return self._search_entry.get_text().strip()

    # ============================================================================
    # ABSTRACT METHODS (MUST BE IMPLEMENTED BY SUBCLASSES)
    # ============================================================================

    @abstractmethod
    def get_item_type(self) -> type:
        pass

    @abstractmethod
    def setup_list_item(self, list_item: Gtk.ListItem) -> None:
        pass

    @abstractmethod
    def bind_list_item(self, list_item: Gtk.ListItem, item: Any) -> None:
        pass

    @abstractmethod
    def on_item_activated(self, item: Any) -> None:
        pass

    @abstractmethod
    def load_initial_data(self) -> None:
        pass

    @abstractmethod
    def on_search_changed(self, query: str) -> None:
        pass

    @abstractmethod
    def get_context_menu_model(self, item: Any) -> Optional[Gio.Menu]:
        pass

    def get_global_context_menu_actions(self) -> dict:
        """Return global context menu actions. Override to provide global actions."""
        return {}

    def get_global_context_menu_model(self) -> Optional[Gio.Menu]:
        """Return global context menu model. Override to provide global menu."""
        return None

    # ============================================================================
    # VIRTUAL/HOOK METHODS (CAN BE OVERRIDDEN BY SUBCLASSES)
    # ============================================================================

    def on_search_cleared(self) -> None:
        pass

    def on_escape_pressed(self) -> None:
        self.close()

    def on_close_request(self) -> bool:
        return False

    def on_window_shown(self) -> None:
        pass

    # ============================================================================
    # CONFIGURATION METHODS (CAN BE OVERRIDDEN FOR CUSTOMIZATION)
    # ============================================================================

    def get_loading_icon(self) -> str:
        return "find-location-symbolic"

    def get_empty_icon(self) -> str:
        return "system-search-symbolic"

    def get_empty_title(self) -> str:
        return f"Search {self._title}"

    def get_empty_description(self) -> str:
        return "Type your query in the search bar above."

    def get_header_bar_left_widgets(self) -> List[Gtk.Widget]:
        return []

    def get_header_bar_title_widget(self) -> Optional[Gtk.Widget]:
        return self._search_entry

    def get_header_bar_right_widgets(self) -> List[Gtk.Widget]:
        return []
