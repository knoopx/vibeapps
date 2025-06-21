import gi
from abc import ABC, abstractmethod
from typing import Optional, Any

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
from picker_window import PickerWindow, GObjectABCMeta


class PickerWindowWithPreview(PickerWindow, ABC, metaclass=GObjectABCMeta):
    def __init__(
        self,
        title: str = "Picker",
        search_placeholder: str = "Search...",
        window_size: tuple = (1280, 620),
        search_delay_ms: int = 300,
        context_menu_shortcut: Optional[str] = "<Control>j",
        global_context_menu_shortcut: Optional[str] = "<Control><Shift>j",
        preview_panel_width: int = 400,
        preview_debounce_ms: int = 300,
        **kwargs: Any
    ) -> None:
        self._preview_panel_width = preview_panel_width
        self._preview_widget = None
        self._preview_debounce_ms = preview_debounce_ms
        self._preview_debounce_timeout_id = None
        super().__init__(
            title=title,
            search_placeholder=search_placeholder,
            window_size=window_size,
            search_delay_ms=search_delay_ms,
            context_menu_shortcut=context_menu_shortcut,
            global_context_menu_shortcut=global_context_menu_shortcut,
            **kwargs
        )
        self.connect("destroy", self._on_window_destroy)

    def _on_window_destroy(self, widget) -> None:
        if self._preview_debounce_timeout_id:
            GLib.source_remove(self._preview_debounce_timeout_id)
            self._preview_debounce_timeout_id = None

    def _setup_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        self._header_bar = Adw.HeaderBar()
        main_box.append(self._header_bar)
        self._search_entry = Gtk.SearchEntry(
            hexpand=True, placeholder_text=self._search_placeholder
        )
        self._setup_header_bar()
        self._main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._main_paned.set_vexpand(True)
        main_box.append(self._main_paned)
        self._content_stack = Gtk.Stack()
        self._content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._content_stack.set_size_request(600 - self._preview_panel_width, -1)
        self._main_paned.set_start_child(self._content_stack)
        self._preview_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._preview_panel.set_size_request(self._preview_panel_width, -1)
        self._preview_panel.add_css_class("preview-panel")
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        separator.add_css_class("preview-separator")
        preview_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preview_container.append(separator)
        preview_container.append(self._preview_panel)
        self._main_paned.set_end_child(preview_container)
        self._setup_results_view()
        self._setup_status_pages()
        self._setup_preview_panel()
        self._content_stack.set_visible_child_name("empty")

    def _setup_preview_panel(self) -> None:
        self._preview_empty_page = Adw.StatusPage(
            title=self.get_preview_empty_title(),
            description=self.get_preview_empty_description(),
            icon_name=self.get_preview_empty_icon(),
        )
        self._preview_empty_page.set_vexpand(True)
        self._preview_empty_page.set_hexpand(True)
        self._preview_panel.append(self._preview_empty_page)

    def _on_selection_changed(
        self, selection_model: Gtk.SelectionModel, position: int, n_items: int
    ) -> None:
        super()._on_selection_changed(selection_model, position, n_items)
        if self._preview_debounce_timeout_id:
            GLib.source_remove(self._preview_debounce_timeout_id)
            self._preview_debounce_timeout_id = None
        selected_item = self.get_selected_item()
        self._preview_debounce_timeout_id = GLib.timeout_add(
            self._preview_debounce_ms, self._debounced_preview_update, selected_item
        )

    def _debounced_preview_update(self, selected_item: Optional[Any]) -> bool:
        self._preview_debounce_timeout_id = None
        if selected_item:
            self._update_preview(selected_item)
        else:
            self._clear_preview()
        return False

    def _update_preview(self, item: Any) -> None:
        if self._preview_widget:
            self._preview_panel.remove(self._preview_widget)
            self._preview_widget = None
        self._preview_empty_page.set_visible(False)
        preview_widget = self.create_preview_widget(item)
        if preview_widget:
            self._preview_widget = preview_widget
            self._preview_panel.append(self._preview_widget)
        else:
            self._preview_empty_page.set_visible(True)

    def _clear_preview(self) -> None:
        if self._preview_widget:
            self._preview_panel.remove(self._preview_widget)
            self._preview_widget = None
        self._preview_empty_page.set_visible(True)

    def set_preview_widget(self, widget: Optional[Gtk.Widget]) -> None:
        if self._preview_widget:
            self._preview_panel.remove(self._preview_widget)
            self._preview_widget = None
        if widget:
            self._preview_empty_page.set_visible(False)
            self._preview_widget = widget
            self._preview_panel.append(self._preview_widget)
        else:
            self._preview_empty_page.set_visible(True)

    def get_preview_panel(self) -> Gtk.Box:
        return self._preview_panel

    def set_preview_panel_width(self, width: int) -> None:
        self._preview_panel_width = width
        self._preview_panel.set_size_request(width, -1)

    def set_preview_debounce_ms(self, debounce_ms: int) -> None:
        self._preview_debounce_ms = debounce_ms

    def get_preview_debounce_ms(self) -> int:
        return self._preview_debounce_ms

    def force_preview_update(self) -> None:
        """Force an immediate preview update without debounce."""
        if self._preview_debounce_timeout_id:
            GLib.source_remove(self._preview_debounce_timeout_id)
            self._preview_debounce_timeout_id = None
        selected_item = self.get_selected_item()
        if selected_item:
            self._update_preview(selected_item)
        else:
            self._clear_preview()

    @abstractmethod
    def create_preview_widget(self, item: Any) -> Optional[Gtk.Widget]:
        pass

    def on_preview_item_changed(self, item: Optional[Any]) -> None:
        pass

    def get_preview_empty_title(self) -> str:
        return "No Selection"

    def get_preview_empty_description(self) -> str:
        return "Select an item to see preview"

    def get_preview_empty_icon(self) -> str:
        return "view-reveal-symbolic"
