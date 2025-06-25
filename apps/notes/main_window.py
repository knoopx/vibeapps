import os
from datetime import datetime
from gi.repository import Gtk, Adw, Gio, Pango, Gdk, GLib
from constants import EXT, NOTES_DIR
from note_content_view import NoteContentView
from repository import Repository
from context_menu_window import ContextMenuWindow, ContextMenuAction

class MainWindow(Adw.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app, title='Markdown Notes')
        self.set_default_size(800, 600)
        self.settings = Gio.Settings.new('net.knoopx.notes')
        self.repository = Repository(notes_dir=NOTES_DIR, extension=EXT)
        self.header = Adw.HeaderBar()
        self.entry = Gtk.SearchEntry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text('Search or create note...')
        self.entry.connect('activate', self.on_entry_activate)
        self.entry.connect('search-changed', self.on_entry_changed)
        entry_shortcut_controller = Gtk.ShortcutController.new()
        entry_shortcut_controller.set_scope(Gtk.ShortcutScope.MANAGED)
        context_menu_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<Control>j'), Gtk.CallbackAction.new(self._show_note_context_menu_action_callback))
        entry_shortcut_controller.add_shortcut(context_menu_shortcut)
        self.entry.add_controller(entry_shortcut_controller)
        self.entry_key_controller = Gtk.EventControllerKey.new()
        self.entry_key_controller.connect('key-pressed', self.on_search_entry_key_press)
        self.entry.add_controller(self.entry_key_controller)
        self.header.set_title_widget(self.entry)
        self.filtered_notes = []
        self.current_note = None
        self.setup_actions()
        self.create_ui()
        self.setup_shortcuts()
        window_key_controller = Gtk.EventControllerKey.new()
        window_key_controller.connect('key-pressed', self.on_window_key_press)
        self.add_controller(window_key_controller)
        self.entry.grab_focus()

    def _show_note_context_menu_action_callback(self, widget, args):
        self.show_note_context_menu()
        return True

    def _toggle_sidebar_action_callback(self, widget, args):
        self.toggle_sidebar()
        return True

    def setup_actions(self):
        self.note_action_group = Gio.SimpleActionGroup()
        open_editor_action = Gio.SimpleAction.new('open_with_editor', None)
        open_editor_action.connect('activate', self.on_open_with_editor_action)
        self.note_action_group.add_action(open_editor_action)
        rename_action = Gio.SimpleAction.new('rename_note', None)
        rename_action.connect('activate', self.on_rename_note_action)
        self.note_action_group.add_action(rename_action)
        delete_action = Gio.SimpleAction.new('delete_note', None)
        delete_action.connect('activate', self.on_delete_note_action)
        self.note_action_group.add_action(delete_action)
        self.insert_action_group('app', self.note_action_group)

    def create_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        main_box.append(self.header)
        self.split_view = Adw.OverlaySplitView()
        self.split_view.set_vexpand(True)
        self.split_view.set_hexpand(True)
        self.vbox_sidebar_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.append(self.split_view)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        self.vbox_sidebar_content.append(scrolled_window)
        self.note_list = Gtk.ListBox()
        self.note_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.note_list.connect('row-selected', self.on_note_selected)
        scrolled_window.set_child(self.note_list)
        self.split_view.set_sidebar(self.vbox_sidebar_content)
        self.note_content_view = NoteContentView()
        self.note_content_view.set_parent_window(self)
        self.note_content_view.set_hexpand(True)
        self.note_content_view.set_vexpand(True)
        self.note_content_view.connect('content-saved', self.on_content_view_saved)
        self.note_content_view.connect('edit-mode-exited', self.on_content_view_edit_exited)
        self.split_view.set_content(self.note_content_view)
        self.sidebar_button = Gtk.Button()
        self.sidebar_button.set_child(Gtk.Image.new_from_icon_name('sidebar-show-symbolic'))
        self.sidebar_button.set_tooltip_text('Toggle Sidebar (Ctrl+B)')
        self.sidebar_button.connect('clicked', self.on_sidebar_button_clicked)
        self.header.pack_start(self.sidebar_button)
        self.refresh_note_list()
        self.restore_sidebar_state()

    def setup_shortcuts(self):
        shortcut_controller = Gtk.ShortcutController.new()
        toggle_sidebar_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('<control>b'), Gtk.CallbackAction.new(self._toggle_sidebar_action_callback))
        shortcut_controller.add_shortcut(toggle_sidebar_shortcut)
        self.add_controller(shortcut_controller)

    def show_note_context_menu(self, *args):
        selected_row = self.note_list.get_selected_row()
        if not selected_row or not hasattr(selected_row, 'note_object'):
            return
        actions = [ContextMenuAction('Open with Editor', 'open_with_editor', lambda: self.on_open_with_editor_action(None, None)), ContextMenuAction('Rename', 'rename_note', lambda: self.on_rename_note_action(None, None)), ContextMenuAction('Delete', 'delete_note', lambda: self.on_delete_note_action(None, None))]
        context_menu = ContextMenuWindow(self, actions)
        context_menu.present()

    def refresh_note_list(self):
        selected_note_relative_path = None
        if self.current_note:
            selected_note_relative_path = self.current_note.relative_path
        while True:
            row = self.note_list.get_first_child()
            if row is None:
                break
            self.note_list.remove(row)
        search_text = self.entry.get_text().lower()
        all_notes = self.repository.get_all_notes()
        self.filtered_notes = [note for note in all_notes if search_text in note.relative_path.lower()]
        self.filtered_notes.sort(key=lambda note: note.display_name.split(os.sep))
        select_row_after_refresh = None
        for note_obj in self.filtered_notes:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=note_obj.display_name)
            label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            label.set_max_width_chars(80)
            label.set_xalign(0)
            label.set_margin_start(5)
            label.set_margin_end(5)
            label.set_margin_top(5)
            label.set_margin_bottom(5)
            row.note_object = note_obj
            row.set_child(label)
            self.note_list.append(row)
            context_menu_gesture = Gtk.GestureClick.new()
            context_menu_gesture.set_button(Gdk.BUTTON_SECONDARY)
            context_menu_gesture.connect('pressed', self.on_row_right_click)
            row.add_controller(context_menu_gesture)
            if note_obj.relative_path == selected_note_relative_path:
                select_row_after_refresh = row
        if select_row_after_refresh:
            self.note_list.select_row(select_row_after_refresh)
        elif self.note_list.get_row_at_index(0):
            first_row = self.note_list.get_row_at_index(0)
            self.note_list.select_row(first_row)
            if first_row:
                if hasattr(first_row, 'note_object'):
                    note_obj = first_row.note_object
                    if note_obj:
                        self.current_note = note_obj
                        self.load_note_into_view()
        else:
            self.current_note = None
            self.note_content_view.set_content('')
        self.entry.grab_focus()

    def on_search_entry_key_press(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.entry.set_text('')
            return Gdk.EVENT_STOP
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
        if text == '@today':
            today = datetime.now()
            new_text = f'Journal/{today.year}/{today.month:02d}/{today.day:02d}'
            entry.handler_block_by_func(self.on_entry_changed)
            entry.set_text(new_text)
            entry.handler_unblock_by_func(self.on_entry_changed)
            entry.set_position(-1)
            return
        self.refresh_note_list()

    def on_entry_activate(self, entry):
        query = entry.get_text().strip()
        if not query:
            if self.current_note:
                self.note_content_view.enter_edit_mode()
            return
        if self.filtered_notes:
            first_note = self.filtered_notes[0]
            try:
                idx = 0
                row = self.note_list.get_row_at_index(idx)
                if row:
                    self.note_list.select_row(row)
                    self.note_content_view.enter_edit_mode()
                    return
            except (ValueError, AttributeError):
                print(f'Could not select first filtered note: {first_note.relative_path}')
        filename_with_ext = self.repository.ensure_note_extension(query)
        if os.path.sep in filename_with_ext:
            relative_path = os.path.normpath(filename_with_ext)
        else:
            relative_path = filename_with_ext
        existing_note = self.repository.get_note_by_relative_path(relative_path)
        if existing_note:
            try:
                self.refresh_note_list()
                idx = self.filtered_notes.index(existing_note)
                row = self.note_list.get_row_at_index(idx)
                if row:
                    self.note_list.select_row(row)
                    self.note_content_view.enter_edit_mode()
            except ValueError:
                print(f'Could not select existing note: {relative_path}')
        else:
            title_for_content = os.path.splitext(os.path.basename(relative_path))[0]
            initial_content = f"# {title_for_content}\n\n"
            new_note = self.repository.create_note(relative_path, initial_content)
            if new_note:
                self.current_note = new_note
                self.refresh_note_list()
                try:
                    idx = self.filtered_notes.index(new_note)
                    row = self.note_list.get_row_at_index(idx)
                    if row:
                        if not self.note_list.get_selected_row() == row:
                            self.note_list.select_row(row)
                        self.note_content_view.enter_edit_mode(cursor_at_end=True)
                except ValueError:
                    print(f'Could not auto-select and edit new note: {new_note.relative_path}')
                    if self.current_note == new_note:
                        self.load_note_into_view()
                        self.note_content_view.enter_edit_mode(cursor_at_end=True)
            else:
                print(f'Error creating note via repository: {relative_path}')

    def on_note_selected(self, listbox, row):
        if row:
            if hasattr(row, 'note_object'):
                note_obj = row.note_object
                if note_obj:
                    self.current_note = note_obj
                    self.load_note_into_view()
                    if self.split_view.get_collapsed():
                        self.entry.set_text('')
                        self.split_view.set_show_sidebar(False)
        else:
            self.current_note = None
            self.note_content_view.set_content('')

    def on_row_right_click(self, gesture, n_press, x, y):
        if n_press == 1 and gesture.get_current_button() == Gdk.BUTTON_SECONDARY:
            row = gesture.get_widget()
            if not row or not hasattr(row, 'note_object'):
                return
            self.note_list.select_row(row)
            if hasattr(row, 'note_object'):
                self.current_note = row.note_object
            menu_model = Gio.Menu.new()
            menu_model.append('Rename', 'app.rename_note')
            menu_model.append('Delete', 'app.delete_note')
            popover_menu = Gtk.PopoverMenu.new_from_model(menu_model)
            popover_menu.set_parent(row)
            popover_menu.popup()

    def on_rename_note_action(self, action, parameter):
        self.on_rename_note(None)

    def on_delete_note_action(self, action, parameter):
        self.on_delete_note(None)

    def on_open_with_editor_action(self, action, parameter):
        if not self.current_note:
            return
        try:
            full_path = os.path.join(self.repository.get_notes_dir(), self.current_note.relative_path)
            Gtk.show_uri(None, f'file://{full_path}', Gdk.CURRENT_TIME)
        except Exception as e:
            print(f'Error opening note with default editor: {e}')

    def on_rename_note(self, menu_item):
        if not self.current_note:
            return
        current_display_name_no_ext = os.path.splitext(self.current_note.display_name)[0]
        dialog = Gtk.Dialog(title='Rename Note', transient_for=self, modal=True)
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Rename', Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        content_area = dialog.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        content_area.append(box)
        label = Gtk.Label(label='Enter new path (e.g., folder/subfolder/new_name):')
        label.set_xalign(0)
        box.append(label)
        entry = Gtk.Entry()
        entry.set_text(current_display_name_no_ext)
        entry.set_activates_default(True)
        box.append(entry)
        dialog.present()
        dialog.connect('response', self.on_rename_dialog_response, entry)

    def on_rename_dialog_response(self, dialog, response_id, entry):
        if response_id == Gtk.ResponseType.OK:
            new_relative_path_without_ext = entry.get_text().strip()
            dialog.destroy()
            if not self.current_note:
                return
            if not new_relative_path_without_ext:
                print('New path cannot be empty.')
                error_dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text='Rename Failed', secondary_text='The new path cannot be empty.')
                error_dialog.connect('response', lambda d, r: d.destroy())
                error_dialog.present()
                return
            new_relative_path_with_ext = self.repository.ensure_note_extension(new_relative_path_without_ext)
            new_relative_path_with_ext = os.path.normpath(new_relative_path_with_ext)
            if not os.path.basename(new_relative_path_with_ext) or os.path.basename(new_relative_path_with_ext) == self.repository.extension:
                print('Invalid new path: filename cannot be empty.')
                error_dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text='Rename Failed', secondary_text='Invalid new path: the filename part cannot be empty or just the extension.')
                error_dialog.connect('response', lambda d, r: d.destroy())
                error_dialog.present()
                return
            existing_note = self.repository.get_note_by_relative_path(new_relative_path_with_ext)
            if existing_note and existing_note.relative_path.lower() != self.current_note.relative_path.lower():
                print(f"Note with path '{new_relative_path_with_ext}' already exists.")
                error_dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text='Rename Failed', secondary_text=f"A note with the path '{new_relative_path_with_ext}' already exists.")
                error_dialog.connect('response', lambda d, r: d.destroy())
                error_dialog.present()
                return
            if self.repository.rename_note(self.current_note, new_relative_path_with_ext):
                self.refresh_note_list()
            else:
                error_dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text='Rename Failed', secondary_text=f"Could not rename the note to '{new_relative_path_with_ext}'. Check logs for details or if the name is valid.")
                error_dialog.connect('response', lambda d, r: d.destroy())
                error_dialog.present()
        else:
            dialog.destroy()

    def on_delete_note(self, menu_item):
        if not self.current_note:
            return
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, buttons=Gtk.ButtonsType.NONE, message_type=Gtk.MessageType.WARNING, text='Confirm Delete', secondary_text=f"Are you sure you want to delete the note '{self.current_note.filename}'?")
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.add_button('Delete', Gtk.ResponseType.OK)
        dialog.connect('response', self.on_delete_confirmation_response)
        dialog.show()

    def on_delete_confirmation_response(self, dialog, response):
        dialog.close()
        if response != Gtk.ResponseType.OK:
            return
        if not self.current_note:
            return
        note_to_delete = self.current_note
        if self.repository.delete_note(note_to_delete):
            if self.current_note == note_to_delete:
                self.current_note = None
                self.note_content_view.set_content('', is_editing=False)
            self.refresh_note_list()
        else:
            error_dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text='Delete Failed', secondary_text=f"Could not delete note '{note_to_delete.filename}'. Check logs.")
            error_dialog.connect('response', lambda d, r: d.destroy())
            error_dialog.present()

    def load_note_into_view(self):
        content = ''
        if self.current_note:
            content = self.repository.load_note_content(self.current_note)
        self.note_content_view.set_content(content, is_editing=False)

    def on_content_view_saved(self, note_content_view, content):
        if self.current_note:
            if not self.repository.save_note_content(self.current_note, content):
                print(f'Failed to save content for {self.current_note.relative_path} via repository.')
                error_dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text='Save Failed', secondary_text=f"Could not save changes to '{self.current_note.filename}'. Check logs.")
                error_dialog.connect('response', lambda d, r: d.destroy())
                error_dialog.present()
        else:
            print('No current note to save.')

    def on_content_view_edit_exited(self, note_content_view):
        selected_row = self.note_list.get_selected_row()
        if selected_row:
            selected_row.grab_focus()

    def on_window_key_press(self, controller, keyval, keycode, state, user_data=None):
        focused = self.get_focus()
        if focused == self.entry:
            return Gdk.EVENT_PROPAGATE
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            selected_row = self.note_list.get_selected_row()
            if selected_row:
                self.note_content_view.enter_edit_mode()
                return Gdk.EVENT_STOP
        elif keyval == Gdk.KEY_Escape:
            self.entry.grab_focus()
            return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    def on_sidebar_button_clicked(self, button):
        self.toggle_sidebar()

    def toggle_sidebar(self, *args):
        is_visible = self.split_view.get_show_sidebar()
        self.split_view.set_show_sidebar(not is_visible)
        self.settings.set_boolean('sidebar-visible', self.split_view.get_show_sidebar())

    def restore_sidebar_state(self):
        if self.settings.get_boolean('sidebar-visible'):
            self.split_view.set_show_sidebar(True)
        else:
            self.split_view.set_show_sidebar(False)

    def navigate_to_note(self, note_path):
        self.entry.set_text(os.path.splitext(note_path)[0])
        self.refresh_note_list()
        found_note = next((n for n in self.filtered_notes if n.relative_path == note_path), None)
        if found_note:
            for i, note_obj_in_list in enumerate(self.filtered_notes):
                if note_obj_in_list == found_note:
                    row = self.note_list.get_row_at_index(i)
                    if row:
                        self.note_list.select_row(row)
                    break