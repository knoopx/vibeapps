import subprocess
from gi.repository import GLib, GObject, Gdk, Gtk, GtkSource, WebKit
from constants import NOTES_DIR

import threading


def markdown(markdown_content):
    proc = subprocess.Popen(
        ["md2html"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(markdown_content)

    if proc.returncode != 0:
        raise RuntimeError(f"Error: {stderr.strip()}")

    return stdout.strip()


class NoteContentView(Gtk.Box):
    """
    A custom widget that displays either a GtkSourceView for editing
    or a WebKitWebView for previewing markdown content.
    """

    # Define signals that this widget can emit
    __gsignals__ = {
        "content-saved": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "edit-mode-exited": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.parent_window = None  # Store reference to parent window

        self.is_editing = False
        self._current_content = ""  # Store the current content being displayed/edited
        self.processing_enter_edit_mode = False # Flag to manage focus during edit mode transition

        # Content Area - Stack to switch between edit and preview
        self.content_stack = Gtk.Stack()
        self.content_stack.set_hexpand(True)
        self.content_stack.set_vexpand(True)
        self.append(self.content_stack)

        # --- Source view for editing ---
        edit_scroll = Gtk.ScrolledWindow()
        edit_scroll.set_margin_start(40)
        edit_scroll.set_margin_end(40)
        edit_scroll.set_margin_top(40)
        edit_scroll.set_margin_bottom(40)

        # Setup GtkSourceView with markdown highlighting
        lang_manager = GtkSource.LanguageManager()
        buffer = GtkSource.Buffer()
        markdown_lang = lang_manager.get_language("markdown")
        if markdown_lang:
            buffer.set_language(markdown_lang)

        self.source_view = GtkSource.View(buffer=buffer)
        self.source_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.source_view.set_monospace(True)
        self.content_buffer = self.source_view.get_buffer()

        # Set a dark style scheme if available
        style_manager = GtkSource.StyleSchemeManager.get_default()
        style_scheme = style_manager.get_scheme("catppuccin-mocha")  # Attempt to use 'stylix'
        # style_scheme = None
        if not style_scheme:
            # Fallback to other common dark schemes if 'stylix' is not found
            for scheme_id in ["oblivion", "dracula", "darcula", "darkmate"]:
                style_scheme = style_manager.get_scheme(scheme_id)
                if style_scheme:
                    break

        if style_scheme:
            self.content_buffer.set_style_scheme(style_scheme)

        edit_scroll.set_child(self.source_view)
        self.content_stack.add_titled(edit_scroll, "edit", "Edit")

        # Add key controller to the source view for shortcuts (like Escape, Ctrl+S)
        content_key_controller = Gtk.EventControllerKey()
        content_key_controller.connect("key-pressed", self.on_content_key_press)
        self.source_view.add_controller(content_key_controller)

        # Add focus controller to the source view to detect when editing stops
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", self.on_source_view_focus_leave)
        self.source_view.add_controller(focus_controller)

        # --- WebView for previewing ---
        preview_scroll = Gtk.ScrolledWindow()
        self.webview = WebKit.WebView()
        self.webview.set_vexpand(True)
        self.webview.set_hexpand(True)
        rgba = Gdk.RGBA()
        rgba.parse("rgba(0,0,0,0)")
        self.webview.set_background_color(rgba)

        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_developer_extras(True)
        settings.set_enable_write_console_messages_to_stdout(True)
        settings.set_property("allow-universal-access-from-file-urls", True)
        settings.set_property("allow-file-access-from-file-urls", True)

        # Connect to the decide-policy signal to handle link clicks
        self.webview.connect("decide-policy", self.on_webview_decide_policy)

        # Add gesture for double-click to enter edit mode
        click_gesture = Gtk.GestureClick()
        click_gesture.set_button(1)  # Left mouse button
        click_gesture.connect("pressed", self.on_webview_double_click)
        self.webview.add_controller(click_gesture)

        preview_scroll.set_child(self.webview)
        preview_scroll.set_margin_start(40)
        preview_scroll.set_margin_end(40)

        self.content_stack.add_titled(preview_scroll, "preview", "Preview")

        # Default to preview mode initially
        self.content_stack.set_visible_child_name("preview")

    def set_parent_window(self, parent):
        """Set the parent NotesApp window reference"""
        self.parent_window = parent

    def set_content(self, content, is_editing=False):
        """
        Sets the content to be displayed and switches between edit/preview mode.
        """
        self._current_content = content
        self.is_editing = is_editing

        if self.is_editing:
            self.content_buffer.set_text(self._current_content)
            # Set cursor position at the start before switching view and focusing
            start_iter = self.content_buffer.get_start_iter()
            self.content_buffer.place_cursor(start_iter)
            self.content_stack.set_visible_child_name("edit")
            self.source_view.grab_focus()
        else:
            # Start a background thread for markdown conversion
            def convert_and_load():
                try:
                    html_content = markdown(self._current_content)
                    GLib.idle_add(self._update_preview, html_content)
                except Exception as e:
                    print(f"Error converting markdown: {e}")
                    GLib.idle_add(self._update_preview, f"<p>Error: {e}</p>")

            thread = threading.Thread(target=convert_and_load)
            thread.daemon = True
            thread.start()
            # Show preview immediately, content will update when ready
            self.content_stack.set_visible_child_name("preview")

    def _update_preview(self, html_content):
        """Updates the preview with HTML content (called in main thread)"""
        self.webview.load_html(html_content, f"file://{NOTES_DIR}/")
        return False  # Remove idle source

    def get_content(self):
        """
        Gets the current content from the editor buffer.
        """
        start_iter = self.content_buffer.get_start_iter()
        end_iter = self.content_buffer.get_end_iter()
        return self.content_buffer.get_text(start_iter, end_iter, True)

    def save_content(self):
        """
        Retrieves content from the editor and emits the 'content-saved' signal.
        """
        if self.is_editing:
            content = self.get_content()
            self.emit("content-saved", content)
            self._current_content = content  # Update internal state after saving

    def enter_edit_mode(self):
        """
        Switches to the edit view and populates the buffer.
        """
        if not self.is_editing:
            self.is_editing = True
            # Set flag to handle potential spurious focus "leave" event during transition
            self.processing_enter_edit_mode = True

            # Load the current content into the editor buffer
            self.content_buffer.set_text(self._current_content)
            # Set cursor position at the start before switching view and focusing
            start_iter = self.content_buffer.get_start_iter()
            self.content_buffer.place_cursor(start_iter)
            self.content_stack.set_visible_child_name("edit")
            self.source_view.grab_focus()

            # Schedule the flag to be reset after current event processing cycle
            GLib.idle_add(self._reset_processing_enter_edit_mode_flag)

    def _reset_processing_enter_edit_mode_flag(self):
        """Resets the flag used during the enter_edit_mode transition."""
        self.processing_enter_edit_mode = False
        return GLib.SOURCE_REMOVE # Ensure the idle source is removed

    def exit_edit_mode(self):
        """
        Saves content, switches to preview, and emits 'edit-mode-exited'.
        """
        if self.is_editing:
            self.save_content()  # Save before exiting edit mode
            self.is_editing = False
            # Reload content into preview (it was just saved)
            self.set_content(self._current_content, is_editing=False)
            self.emit("edit-mode-exited")  # Notify parent that editing stopped

    def on_webview_double_click(self, gesture, n_press, x, y):
        """
        Handler for double-click on the preview area.
        """
        if n_press == 2:
            self.enter_edit_mode()

    def on_content_key_press(self, controller, keyval, keycode, state, user_data=None):
        """
        Handler for key presses in the source view (edit mode).
        """
        # Handle Escape key to exit edit mode
        if keyval == Gdk.KEY_Escape:
            self.exit_edit_mode()
            return Gdk.EVENT_STOP  # Stop propagation

        # Handle Ctrl+S shortcut for saving
        if keyval == Gdk.KEY_s and state & Gdk.ModifierType.CONTROL_MASK:
            self.save_content()
            # print("Note content saved!") # Optional feedback
            return Gdk.EVENT_STOP  # Stop propagation

        return Gdk.EVENT_PROPAGATE  # Continue propagation for other keys

    def on_source_view_focus_leave(self, controller, user_data=None):
        """
        Handler for when the source view loses focus.
        Used to automatically exit edit mode if focus leaves the editor.
        """
        # If we are in the middle of programmatically trying to enter edit mode,
        # a "leave" event might fire spuriously. Ignore it in this case.
        if self.processing_enter_edit_mode:
            return

        if self.is_editing: # This check is important
            self.exit_edit_mode()

    def on_webview_decide_policy(self, webview, decision, decision_type):
        """
        Handler for link clicks in the WebView.
        Prevents opening external links within the WebView itself.
        """
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            navigation_action = decision.get_navigation_action()
            if (
                navigation_action.get_navigation_type()
                == WebKit.NavigationType.LINK_CLICKED
            ):
                uri = navigation_action.get_request().get_uri()
                if uri.startswith("http://") or uri.startswith("https://"):
                    decision.ignore()
                    Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)  # Requires Gtk 4.4+
                    return True  # Indicate that we handled the decision

                elif uri.startswith("note://"):
                    # Handle internal note links through parent window
                    if self.parent_window:
                        note_path = uri.replace("note://", "", 1)
                        self.parent_window.navigate_to_note(note_path)
                    decision.ignore()
                    return True
        return False  # Allow other types of decisions/navigations