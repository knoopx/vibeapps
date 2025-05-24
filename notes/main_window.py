import os
from datetime import datetime
from gi.repository import Gtk, Adw, Gio, Pango, Gdk, GLib
from constants import EXT, NOTES_DIR # Keep NOTES_DIR for potential direct uses if any, or for context
from note_content_view import NoteContentView
from repository import Repository # Import the new Repository class


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Markdown Notes")
        self.set_default_size(800, 600)

        # Initialize Repository
        self.repository = Repository(notes_dir=NOTES_DIR, extension=EXT)

        # Setup AdwHeaderBar
        self.header = Adw.HeaderBar()

        # Move search entry to header bar
        self.entry = Gtk.SearchEntry()
        self.entry.set_hexpand(True)

        self.entry.set_placeholder_text("Search or create note...")
        self.entry.connect("activate", self.on_entry_activate)
        self.entry.connect("search-changed", self.on_entry_changed)

        # Add entry-specific shortcut controller with high priority
        entry_shortcut_controller = Gtk.ShortcutController.new()
        entry_shortcut_controller.set_scope(
            Gtk.ShortcutScope.MANAGED
        )  # Higher priority than LOCAL
        context_menu_shortcut = Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<Control>o"),
            Gtk.CallbackAction.new(
                self._show_note_context_menu_action_callback
            ),  # Wrapper
        )
        entry_shortcut_controller.add_shortcut(context_menu_shortcut)
        self.entry.add_controller(entry_shortcut_controller)

        # Regular key controller for other entry shortcuts
        self.entry_key_controller = Gtk.EventControllerKey.new()
        self.entry_key_controller.connect("key-pressed", self.on_search_entry_key_press)
        self.entry.add_controller(self.entry_key_controller)

        self.header.set_title_widget(self.entry)

        # self.notes = [] # Will store Note objects - Now managed by repository
        self.filtered_notes = []  # Will store Note objects, result of filtering repository.notes
        self.current_note = None  # Will be a Note object or None

        self.setup_actions()  # Setup actions before loading notes that might use them
        # self.load_notes() # Notes are loaded by repository constructor

        self.create_ui()
        self.setup_shortcuts()

        # Add focus controller for text entry shortcut (Ctrl+/)
        window_key_controller = Gtk.EventControllerKey.new()
        window_key_controller.connect("key-pressed", self.on_window_key_press)
        self.add_controller(window_key_controller)

        self.entry.grab_focus()

    def _show_note_context_menu_action_callback(self, widget, args):
        self.show_note_context_menu()
        return True  # Gtk.CallbackAction expects a boolean

    def _toggle_sidebar_action_callback(self, widget, args):
        self.toggle_sidebar()
        return True  # Gtk.CallbackAction expects a boolean

    def setup_actions(self):
        """Setup Gio.SimpleActionGroup for note-specific actions."""
        self.note_action_group = Gio.SimpleActionGroup()

        open_editor_action = Gio.SimpleAction.new("open_with_editor", None)
        open_editor_action.connect("activate", self.on_open_with_editor_action)
        self.note_action_group.add_action(open_editor_action)

        rename_action = Gio.SimpleAction.new("rename_note", None)
        rename_action.connect("activate", self.on_rename_note_action)
        self.note_action_group.add_action(rename_action)

        delete_action = Gio.SimpleAction.new("delete_note", None)
        delete_action.connect("activate", self.on_delete_note_action)
        self.note_action_group.add_action(delete_action)

        self.insert_action_group("app", self.note_action_group)

    def create_ui(self):
        # Main layout with headerbar
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        main_box.append(self.header)

        # Use Adw.OverlaySplitView for sidebar and content
        self.split_view = Adw.OverlaySplitView()
        self.split_view.set_vexpand(True)
        self.split_view.set_hexpand(True)
        self.vbox_sidebar_content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=10
        )
        main_box.append(self.split_view)

        # Notes List
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        self.vbox_sidebar_content.append(scrolled_window)

        self.note_list = Gtk.ListBox()
        self.note_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.note_list.connect("row-selected", self.on_note_selected)
        scrolled_window.set_child(self.note_list)

        # Set the sidebar child of the SplitView
        self.split_view.set_sidebar(self.vbox_sidebar_content)

        self.note_content_view = NoteContentView()
        self.note_content_view.set_parent_window(self)  # Set parent reference
        self.note_content_view.set_hexpand(True)
        self.note_content_view.set_vexpand(True)

        # Connect signals from the NoteContentView
        self.note_content_view.connect("content-saved", self.on_content_view_saved)
        self.note_content_view.connect(
            "edit-mode-exited", self.on_content_view_edit_exited
        )

        # Set the content child of the SplitView
        # The NoteContentView contains the stack internally
        self.split_view.set_content(self.note_content_view)

        # Add sidebar toggle button to the header bar
        self.sidebar_button = Gtk.Button()
        self.sidebar_button.set_child(
            Gtk.Image.new_from_icon_name("sidebar-show-symbolic")
        )
        self.sidebar_button.set_tooltip_text("Toggle Sidebar (Ctrl+B)")
        self.sidebar_button.connect("clicked", self.on_sidebar_button_clicked)
        self.header.pack_start(self.sidebar_button)

        self.refresh_note_list()

    def setup_shortcuts(self):
        # Shortcut for toggling sidebar (Ctrl+B)
        shortcut_controller = Gtk.ShortcutController.new()
        toggle_sidebar_shortcut = Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("<control>b"),
            Gtk.CallbackAction.new(self._toggle_sidebar_action_callback),  # Wrapper
        )
        shortcut_controller.add_shortcut(toggle_sidebar_shortcut)

        self.add_controller(shortcut_controller)

    def show_note_context_menu(self, *args):
        """Shows the context menu for the currently selected note."""
        selected_row = self.note_list.get_selected_row()
        if not selected_row or not hasattr(
            selected_row, "note_object"
        ):  # Changed from get_data
            return

        # Create menu model
        menu_model = Gio.Menu.new()
        menu_model.append("Open with Editor", "app.open_with_editor")
        menu_model.append("Rename", "app.rename_note")
        menu_model.append("Delete", "app.delete_note")

        # Create PopoverMenu
        popover_menu = Gtk.PopoverMenu.new_from_model(menu_model)
        popover_menu.set_parent(selected_row)
        # Actions are already set up in self.note_action_group and inserted with "app" prefix
        popover_menu.popup()

    def refresh_note_list(self):
        # Keep track of the currently selected note's relative path
        selected_note_relative_path = None
        if self.current_note:
            selected_note_relative_path = self.current_note.relative_path

        # Remove all children from the list box
        while True:
            row = self.note_list.get_first_child()
            if row is None:
                break
            self.note_list.remove(row)

        # Filter and sort notes
        search_text = self.entry.get_text().lower()
        all_notes = self.repository.get_all_notes() # Get notes from repository
        self.filtered_notes = [
            note
            for note in all_notes # Iterate over notes from repository
            if search_text in note.relative_path.lower()
        ]
        self.filtered_notes.sort(
            key=lambda note: note.display_name.split(os.sep)
        )

        # Add filtered notes to the list box
        select_row_after_refresh = None
        for note_obj in self.filtered_notes:  # Iterate over Note objects
            row = Gtk.ListBoxRow()

            label = Gtk.Label(label=note_obj.display_name)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(80)
            label.set_xalign(0)
            label.set_margin_start(5)
            label.set_margin_end(5)
            label.set_margin_top(5)
            label.set_margin_bottom(5)

            # Store the Note object as a Python attribute
            row.note_object = note_obj  # Changed from set_data

            row.set_child(label)
            self.note_list.append(row)

            # Add gesture for context menu
            context_menu_gesture = Gtk.GestureClick.new()
            context_menu_gesture.set_button(Gdk.BUTTON_SECONDARY)  # Right mouse button
            context_menu_gesture.connect("pressed", self.on_row_right_click)
            row.add_controller(context_menu_gesture)

            # If this row was previously selected, mark it for re-selection
            if (
                note_obj.relative_path == selected_note_relative_path
            ):  # Compare relative_path
                select_row_after_refresh = row

        # Re-select the previously selected row if it still exists, otherwise select the first
        if select_row_after_refresh:
            self.note_list.select_row(select_row_after_refresh)
        elif self.note_list.get_row_at_index(0):
            first_row = self.note_list.get_row_at_index(0)
            self.note_list.select_row(first_row)
            # Update current_note if a new first row is selected
            if first_row:
                if hasattr(first_row, "note_object"):  # Changed from get_data
                    note_obj = first_row.note_object
                    if note_obj:
                        self.current_note = note_obj
                        self.load_note_into_view()  # Load content for the new selection
        else:
            # No rows left, clear content area
            self.current_note = None
            self.note_content_view.set_content("")  # Clear content in the view

        self.entry.grab_focus()  # Ensure the search entry is focused

    def on_search_entry_key_press(self, controller, keyval, keycode, state):
        # Handle Escape key to clear search
        if keyval == Gdk.KEY_Escape:
            self.entry.set_text("")  # Clear search
            return Gdk.EVENT_STOP  # Stop propagation

        num_rows = len(self.filtered_notes)
        if num_rows > 0:
            selected_row = self.note_list.get_selected_row()
            current_index = -1
            if selected_row:
                current_index = selected_row.get_index()

            if keyval == Gdk.KEY_Up:
                if current_index > 0:
                    next_row = self.note_list.get_row_at_index(current_index - 1)
                    self.note_list.select_row(next_row)
                    selected_row = self.note_list.get_selected_row()
                    if selected_row:
                        selected_row.grab_focus()
                return Gdk.EVENT_STOP

            elif keyval == Gdk.KEY_Down:
                if current_index < num_rows - 1:
                    next_row = self.note_list.get_row_at_index(current_index + 1)
                    self.note_list.select_row(next_row)
                    selected_row = self.note_list.get_selected_row()
                    if selected_row:
                        selected_row.grab_focus()
                return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE

    def on_entry_changed(self, entry):
        text = entry.get_text().strip()
        # Handle @today expansion immediately
        if text == "@today":
            today = datetime.now()
            new_text = f"Journal/{today.year}/{today.month:02d}/{today.day:02d}"
            # Temporarily block the changed signal to prevent recursion
            entry.handler_block_by_func(self.on_entry_changed)
            entry.set_text(new_text)
            entry.handler_unblock_by_func(self.on_entry_changed)
            # Move cursor to end
            entry.set_position(-1)
            return
        self.refresh_note_list()

    def on_entry_activate(self, entry):
        query = entry.get_text().strip()
        if not query:
            # If query is empty and a note is selected, open the selected note for editing
            if self.current_note:
                self.note_content_view.enter_edit_mode()
            return

        # Ensure the filename has the correct note extension
        filename_with_ext = self.repository.ensure_note_extension(query)

        # Determine the relative path. If query contains slashes, treat as path.
        if os.path.sep in filename_with_ext:
            relative_path = os.path.normpath(filename_with_ext)
        else: # Simple filename, place in root of NOTES_DIR by default
            relative_path = filename_with_ext

        # Generate a unique path if creating a new note and the name exists
        # For existing notes, we want to find it, not generate a unique one.

        existing_note = self.repository.get_note_by_relative_path(relative_path)

        if existing_note:
            # Note exists, select it
            # Find in filtered_notes to get the correct index for UI selection
            try:
                idx = self.filtered_notes.index(existing_note)
                row = self.note_list.get_row_at_index(idx)
                if row:
                    self.note_list.select_row(row)
                    # on_note_selected will be called, which sets self.current_note
                    # and loads content. Then enter edit mode.
                    self.note_content_view.enter_edit_mode()
            except ValueError:
                # Should not happen if refresh_note_list is up-to-date
                # Fallback: refresh and try to select
                self.refresh_note_list()
                try:
                    idx = self.filtered_notes.index(existing_note)
                    row = self.note_list.get_row_at_index(idx)
                    if row:
                        self.note_list.select_row(row)
                        self.note_content_view.enter_edit_mode()
                except ValueError:
                     print(f"Could not select existing note: {relative_path}")

        else:
            # Note does not exist, create it.
            # The repository's create_note will handle actual file creation.
            # Use generate_unique_relative_path from repository if there's a conflict,
            # though get_note_by_relative_path should have caught exact matches.
            # For now, assume `relative_path` is what the user wants, or Note.create handles uniqueness.
            # Let's refine: if user types "foo" and "foo.md" exists, they mean "foo.md".
            # If they type "foo" and "foo.md" does not exist, we create "foo.md".
            # The `ensure_note_extension` and `get_note_by_relative_path` handle this.

            title_for_content = os.path.splitext(os.path.basename(relative_path))[0]
            initial_content = f"# {title_for_content}\\n\\n"

            # The relative_path here is what the user typed (plus extension).
            # If it truly needs to be unique beyond what get_note_by_relative_path checks,
            # (e.g. case differences on case-insensitive FS), repo.create_note might fail.
            # Or, we can use repo.generate_unique_relative_path if that's desired behavior.
            # For now, let's assume `relative_path` is the target.

            new_note = self.repository.create_note(relative_path, initial_content)

            if new_note:
                # self.notes list is managed by repository.
                self.current_note = new_note
                self.refresh_note_list()  # This will re-filter, re-sort, and re-select

                # Ensure the new note is selected and edit mode is entered.
                # refresh_note_list should handle selection.
                # We need to find the row for the new_note to ensure edit mode is entered for it.
                try:
                    idx = self.filtered_notes.index(new_note)
                    row = self.note_list.get_row_at_index(idx)
                    if row:
                        if not self.note_list.get_selected_row() == row:
                             self.note_list.select_row(row) # Ensure it's selected
                        # on_note_selected would have been called by select_row or refresh.
                        self.note_content_view.enter_edit_mode()
                except ValueError:
                    # This might happen if refresh_note_list didn't immediately reflect the new note
                    # or if selection logic needs adjustment.
                    print(f"Could not auto-select and edit new note: {new_note.relative_path}")
                    # As a fallback, ensure it's loaded if it became current_note
                    if self.current_note == new_note:
                        self.load_note_into_view()
                        self.note_content_view.enter_edit_mode()

            else:
                print(f"Error creating note via repository: {relative_path}")

    def select_row_after_creation(
        self, row, note_filename_relative
    ):  # This might be redundant now
        """Helper to select a row after a short delay."""
        if row:
            self.note_list.select_row(row)
            # Manually trigger selection logic to ensure content is loaded
            self.on_note_selected(self.note_list, row)
        return GLib.SOURCE_REMOVE  # Remove the timeout source

    def on_note_selected(self, listbox, row):
        if row:
            if hasattr(row, "note_object"):  # Changed from get_data
                note_obj = row.note_object
                if note_obj:
                    self.current_note = note_obj
                    self.load_note_into_view()  # Load content into the NoteContentView
                    # Hide the sidebar on narrow widths after selecting a note if hide mode is active
                    if (
                        self.split_view.get_collapsed()
                    ):  # Check if sidebar is collapsed (narrow view)
                        self.entry.set_text("")
                        self.split_view.set_show_sidebar(False)
        else:
            # Handle case where selection is cleared or an invalid row is selected
            self.current_note = None
            self.note_content_view.set_content("")  # Clear content in the view

    def on_row_right_click(self, gesture, n_press, x, y):
        # Ensure it\\'s a right-click (BUTTON_SECONDARY = 3) and only one press
        if n_press == 1 and gesture.get_current_button() == Gdk.BUTTON_SECONDARY:
            row = gesture.get_widget()  # Get the row that was clicked
            if not row or not hasattr(row, "note_object"):  # Changed from get_data
                return

            # Select the row first so that subsequent actions apply to it
            self.note_list.select_row(row)
            # Update current_note
            if hasattr(row, "note_object"):  # Ensure attribute exists
                self.current_note = row.note_object  # Changed from get_data

            # Create a menu model
            menu_model = Gio.Menu.new()
            menu_model.append("Rename", "app.rename_note")
            menu_model.append("Delete", "app.delete_note")

            # Create a PopoverMenu
            popover_menu = Gtk.PopoverMenu.new_from_model(menu_model)
            popover_menu.set_parent(row)  # Attach to the clicked row
            # Actions are already set up in self.note_action_group and inserted with "app" prefix
            popover_menu.popup()

    # Modified handlers to be Gio.Action activated
    def on_rename_note_action(self, action, parameter):
        self.on_rename_note(None)  # Call the existing rename logic

    def on_delete_note_action(self, action, parameter):
        self.on_delete_note(None)  # Call the existing delete logic

    def on_open_with_editor_action(self, action, parameter):
        """Handler for opening the current note with the system\'s default editor"""
        if not self.current_note:  # Check current_note
            return

        try:
            Gtk.show_uri(
                None, f"file://{self.current_note.full_path}", Gdk.CURRENT_TIME
            )  # Use current_note.full_path
        except Exception as e:
            print(f"Error opening note with default editor: {e}")

    def on_rename_note(
        self,
        menu_item,  # menu_item is not used here, can be removed if not used by Gtk.CallbackAction either
    ):  # Keep this function, called by the action handler
        if not self.current_note:  # Check current_note
            return  # No note selected

        current_name_without_ext = os.path.splitext(self.current_note.filename)[0]
        # current_directory_relative = self.current_note.directory_relative # Unused

        # Create a dialog to get the new name
        dialog = Gtk.Dialog(title="Rename Note", transient_for=self, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Rename", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)

        content_area = dialog.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        content_area.append(box)

        label = Gtk.Label(label="Enter new name (without extension):")
        label.set_xalign(0)
        box.append(label)

        entry = Gtk.Entry()
        entry.set_text(current_name_without_ext)
        entry.set_activates_default(True)  # Activate default button on Enter key
        box.append(entry)

        dialog.present()
        dialog.connect(
            "response",
            self.on_rename_dialog_response,
            entry,
            # current_filename_relative, # No longer pass old relative path, get from self.current_note
            # current_directory_relative, # No longer pass old relative path
        )

    def on_rename_dialog_response(
        self,
        dialog,
        response_id,
        entry,
    ):
        if response_id == Gtk.ResponseType.OK:
            new_name_base = entry.get_text().strip()
            dialog.destroy()

            if not self.current_note:
                return

            if not new_name_base:
                print("New name cannot be empty.")
                return

            current_dir_rel = self.current_note.directory_relative
            new_filename_with_ext = self.repository.ensure_note_extension(new_name_base)

            if current_dir_rel and current_dir_rel != ".":
                new_relative_path = os.path.join(current_dir_rel, new_filename_with_ext)
            else:
                new_relative_path = new_filename_with_ext

            # Check if a note with the new name already exists (excluding the current note itself)
            # The repository's rename_note method should also handle this.
            existing_note = self.repository.get_note_by_relative_path(new_relative_path)
            if existing_note and existing_note != self.current_note:
                print(
                    f"Note with name '{new_name_base}' already exists in that location."
                )
                # Consider showing a Gtk.MessageDialog here
                error_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Rename Failed",
                    secondary_text=f"A note named '{new_name_base}' already exists in '{current_dir_rel or 'root'}'.",
                )
                error_dialog.connect("response", lambda d, r: d.destroy())
                error_dialog.present()
                return

            if self.repository.rename_note(self.current_note, new_relative_path):
                # self.current_note object's relative_path is updated by rename_note->note.rename
                # Repository's internal list is also updated and sorted.
                self.refresh_note_list()  # This will find the renamed note and re-select
            else:
                # Error message would be printed by repository/note methods
                error_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Rename Failed",
                    secondary_text=f"Could not rename '{self.current_note.filename}' to '{new_filename_with_ext}'. Check logs.",
                )
                error_dialog.connect("response", lambda d, r: d.destroy())
                error_dialog.present()
        else:
            dialog.destroy()

    def on_delete_note(self, menu_item):
        if not self.current_note:  # Check current_note
            return

        # Create a confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            buttons=Gtk.ButtonsType.NONE,
            message_type=Gtk.MessageType.WARNING,
            text="Confirm Delete",
            secondary_text=f"Are you sure you want to delete the note '{self.current_note.filename}'?",  # Use current_note.filename
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Delete", Gtk.ResponseType.OK)
        dialog.connect("response", self.on_delete_confirmation_response)
        dialog.show()

    def on_delete_confirmation_response(self, dialog, response):
        dialog.close() # Use close for Gtk.MessageDialog, or destroy

        if response != Gtk.ResponseType.OK:
            return

        if not self.current_note:
            return

        note_to_delete = self.current_note
        # current_note_full_path = note_to_delete.full_path # For logging if needed

        if self.repository.delete_note(note_to_delete):
            # Repository handles removing from its list and file deletion.
            if self.current_note == note_to_delete: # If the deleted note was the current one
                self.current_note = None
                self.note_content_view.set_content("", is_editing=False) # Clear content

            self.refresh_note_list()  # Refresh list, will select next or clear
        else:
            # Error message would be printed by repository/note methods
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Delete Failed",
                secondary_text=f"Could not delete note '{note_to_delete.filename}'. Check logs.",
            )
            error_dialog.connect("response", lambda d, r: d.destroy())
            error_dialog.present()
            # print(f"Error deleting note {current_note_full_path} via repository")

    def load_note_into_view(self):
        """
        Loads the content of the current note into the NoteContentView widget.
        """
        content = ""
        if self.current_note:
            content = self.repository.load_note_content(self.current_note)
            # Error handling for load is within repository/note methods (prints to console)

        # Set the content in the NoteContentView widget (defaults to preview mode)
        self.note_content_view.set_content(content, is_editing=False)

    def on_content_view_saved(self, note_content_view, content):
        """
        Handler for the 'content-saved' signal from NoteContentView.
        Saves the content to the current note file using the repository.
        """
        if self.current_note:
            if not self.repository.save_note_content(self.current_note, content):
                # Error would be printed by repository/note methods
                # Optionally show a dialog to the user
                print(f"Failed to save content for {self.current_note.relative_path} via repository.")
                # Simple dialog for feedback
                error_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Save Failed",
                    secondary_text=f"Could not save changes to '{self.current_note.filename}'. Check logs.",
                )
                error_dialog.connect("response", lambda d, r: d.destroy())
                error_dialog.present()
            # else:
                # print(f"Saved: {self.current_note.full_path} via repository") # For debugging
        else:
            print("No current note to save.")

    def on_content_view_edit_exited(self, note_content_view):
        """
        Handler for the 'edit-mode-exited' signal from NoteContentView.
        Returns focus to the search entry.
        """
        selected_row = self.note_list.get_selected_row()
        if selected_row:
            selected_row.grab_focus()
        # self.entry.grab_focus()

    def on_window_key_press(self, controller, keyval, keycode, state, user_data=None):
        # Let the search entry handle its own events when focused
        focused = self.get_focus()
        if focused == self.entry:
            return Gdk.EVENT_PROPAGATE

        # Handle other global shortcuts
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            selected_row = self.note_list.get_selected_row()
            if selected_row:
                self.note_content_view.enter_edit_mode()
                return Gdk.EVENT_STOP
        elif keyval == Gdk.KEY_Escape:
            self.entry.grab_focus()
            return Gdk.EVENT_STOP

        return Gdk.EVENT_PROPAGATE  # Continue propagation for other keys

    def on_sidebar_button_clicked(self, button):
        self.toggle_sidebar()

    def toggle_sidebar(self, *args):
        """Toggles the visibility of the sidebar using Adw.OverlaySplitView."""
        is_visible = self.split_view.get_show_sidebar()
        self.split_view.set_show_sidebar(not is_visible)

    def navigate_to_note(self, note_path):
        """Navigate to a note by its relative path"""
        self.entry.set_text(
            os.path.splitext(note_path)[0]
        )  # Set search text to allow refresh_note_list to find it
        self.refresh_note_list()  # This will filter and potentially select the note

        # After refresh, explicitly find and select if not already
        found_note = next(
            (n for n in self.filtered_notes if n.relative_path == note_path), None
        )
        if found_note:
            for i, note_obj_in_list in enumerate(self.filtered_notes):
                if note_obj_in_list == found_note:  # Corrected variable name
                    row = self.note_list.get_row_at_index(i)
                    if row:
                        if self.note_list.get_selected_row() != row:
                            self.note_list.select_row(row)
                            self.on_note_selected(
                                self.note_list, row
                            )  # Ensure it's loaded
                        # If you want to directly open it for editing:
                        # self.note_content_view.enter_edit_mode()
                    break
        else:
            # If note_path was intended to be a new note, on_entry_activate handles creation
            # This function is more for navigating to existing notes via external calls (e.g. CLI)
            self.entry.set_text(
                note_path
            )  # Set the full path for creation if it doesn't exist
            self.on_entry_activate(self.entry)
