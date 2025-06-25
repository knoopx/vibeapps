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
    __gsignals__ = {
        "content-saved": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "edit-mode-exited": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.parent_window = None
        self.is_editing = False
        self._current_content = ""
        self.content_stack = Gtk.Stack()
        self.content_stack.set_hexpand(True)
        self.content_stack.set_vexpand(True)
        self.append(self.content_stack)
        edit_scroll = Gtk.ScrolledWindow()
        edit_scroll.set_margin_start(40)
        edit_scroll.set_margin_end(40)
        edit_scroll.set_margin_top(40)
        edit_scroll.set_margin_bottom(40)
        lang_manager = GtkSource.LanguageManager()
        buffer = GtkSource.Buffer()
        markdown_lang = lang_manager.get_language("markdown")
        if markdown_lang:
            buffer.set_language(markdown_lang)
        self.source_view = GtkSource.View(buffer=buffer)
        self.source_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.source_view.set_monospace(True)
        self.content_buffer = self.source_view.get_buffer()
        style_manager = GtkSource.StyleSchemeManager.get_default()
        style_scheme = style_manager.get_scheme("catppuccin-mocha")
        if not style_scheme:
            for scheme_id in ["oblivion", "dracula", "darcula", "darkmate"]:
                style_scheme = style_manager.get_scheme(scheme_id)
                if style_scheme:
                    break
        if style_scheme:
            self.content_buffer.set_style_scheme(style_scheme)
        edit_scroll.set_child(self.source_view)
        self.content_stack.add_titled(edit_scroll, "edit", "Edit")
        content_key_controller = Gtk.EventControllerKey()
        content_key_controller.connect("key-pressed", self.on_content_key_press)
        self.source_view.add_controller(content_key_controller)
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
        self.webview.connect("decide-policy", self.on_webview_decide_policy)
        click_gesture = Gtk.GestureClick()
        click_gesture.set_button(1)
        click_gesture.connect("pressed", self.on_webview_double_click)
        self.webview.add_controller(click_gesture)
        preview_scroll.set_child(self.webview)
        preview_scroll.set_margin_start(40)
        preview_scroll.set_margin_end(40)
        self.content_stack.add_titled(preview_scroll, "preview", "Preview")
        self.content_stack.set_visible_child_name("preview")

    def set_parent_window(self, parent):
        self.parent_window = parent

    def set_content(self, content, is_editing=False):
        self._current_content = content
        self.is_editing = is_editing
        if self.is_editing:
            self.content_buffer.set_text(self._current_content)
            start_iter = self.content_buffer.get_start_iter()
            self.content_buffer.place_cursor(start_iter)
            self.content_stack.set_visible_child_name("edit")
            self.source_view.grab_focus()
        else:

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
            self.content_stack.set_visible_child_name("preview")

    def _update_preview(self, html_content):
        self.webview.load_html(html_content, f"file://{NOTES_DIR}/")
        return False

    def get_content(self):
        start_iter = self.content_buffer.get_start_iter()
        end_iter = self.content_buffer.get_end_iter()
        return self.content_buffer.get_text(start_iter, end_iter, True)

    def save_content(self):
        if self.is_editing:
            content = self.get_content()
            self.emit("content-saved", content)
            self._current_content = content

    def enter_edit_mode(self, cursor_at_end=False):
        if not self.is_editing:
            self.is_editing = True
            self.processing_enter_edit_mode = True
            self.content_buffer.set_text(self._current_content)
            if cursor_at_end:
                end_iter = self.content_buffer.get_end_iter()
                self.content_buffer.place_cursor(end_iter)
            else:
                start_iter = self.content_buffer.get_start_iter()
                self.content_buffer.place_cursor(start_iter)
            self.content_stack.set_visible_child_name("edit")
            self.source_view.grab_focus()
            GLib.idle_add(self._reset_processing_enter_edit_mode_flag)

    def _reset_processing_enter_edit_mode_flag(self):
        self.processing_enter_edit_mode = False
        return GLib.SOURCE_REMOVE

    def exit_edit_mode(self):
        if self.is_editing:
            self.save_content()
            self.is_editing = False
            self.set_content(self._current_content, is_editing=False)
            self.emit("edit-mode-exited")

    def on_webview_double_click(self, gesture, n_press, x, y):
        if n_press == 2:
            self.enter_edit_mode()

    def on_content_key_press(self, controller, keyval, keycode, state, user_data=None):
        if keyval == Gdk.KEY_Escape:
            self.exit_edit_mode()
            return Gdk.EVENT_STOP
        if keyval == Gdk.KEY_s and state & Gdk.ModifierType.CONTROL_MASK:
            self.save_content()
            return Gdk.EVENT_STOP
        return Gdk.EVENT_PROPAGATE

    def on_webview_decide_policy(self, webview, decision, decision_type):
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            navigation_action = decision.get_navigation_action()
            if (
                navigation_action.get_navigation_type()
                == WebKit.NavigationType.LINK_CLICKED
            ):
                uri = navigation_action.get_request().get_uri()
                if uri.startswith("http://") or uri.startswith("https://"):
                    decision.ignore()
                    Gtk.show_uri(None, uri, Gdk.CURRENT_TIME)
                    return True
                elif uri.startswith("note://"):
                    if self.parent_window:
                        note_path = uri.replace("note://", "", 1)
                        self.parent_window.navigate_to_note(note_path)
                    decision.ignore()
                    return True
        return False
