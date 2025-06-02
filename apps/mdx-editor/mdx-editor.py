#!/usr/bin/env python3
import gi
import os
import json
import tempfile
import threading
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, WebKit, GLib, Gio, Adw, GObject

class MDXEditorWidget(Gtk.Box):
    __gtype_name__ = 'MDXEditorWidget'

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._markdown = ''
        self.web_view = WebKit.WebView.new()
        self.web_view.set_hexpand(True)
        self.web_view.set_vexpand(True)
        self.content_manager = self.web_view.get_user_content_manager()
        self.content_manager.register_script_message_handler('markdownChanged', None)
        self.content_manager.register_script_message_handler('editorReady', None)
        self.content_manager.connect('script-message-received::markdownChanged', self.on_markdown_changed)
        self.content_manager.connect('script-message-received::editorReady', self.on_editor_ready)
        settings = self.web_view.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_developer_extras(True)
        settings.set_enable_write_console_messages_to_stdout(True)
        settings.set_property('allow-universal-access-from-file-urls', True)
        settings.set_property('allow-file-access-from-file-urls', True)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.html_path = os.path.join(os.path.dirname(__file__), 'index.html')
        print(f'Loading HTML from: {self.html_path}')
        file_uri = f'file://{self.html_path}'
        self.web_view.load_uri(file_uri)
        self.web_view.connect('load-changed', self.on_load_changed)
        self.web_view.connect('web-process-terminated', self.on_web_process_terminated)
        self.web_view.connect('load-failed', self.on_load_failed)
        self.append(self.web_view)

    def on_load_changed(self, web_view, load_event):
        if load_event == WebKit.LoadEvent.FINISHED:
            pass

    def on_markdown_changed(self, content_manager, js_result):
        self._markdown = js_result.to_string()
        self.notify('markdown')

    def on_editor_ready(self, content_manager, js_result):
        if self._markdown:
            self.set_markdown(self._markdown)

    def _js_callback(self, source_object, result, user_data=None):
        try:
            js_result = self.web_view.evaluate_javascript_finish(result)
            if js_result:
                pass
        except Exception as e:
            print(f'Error executing JavaScript: {e}')

    def set_markdown(self, markdown):
        self._markdown = markdown
        js_code = f'setMarkdown({json.dumps(markdown)});'
        self.web_view.evaluate_javascript(js_code, -1, None, None, None, self._js_callback)

    def get_markdown(self):
        return self._markdown
    markdown = GObject.Property(type=str, default='', getter=get_markdown, setter=set_markdown)

    def on_web_process_terminated(self, web_view, reason):
        print(f'WebKit process terminated: {reason}')

    def on_load_failed(self, web_view, load_event, failing_uri, error):
        print(f'Load failed: {failing_uri}, Error: {error}')

class MDXEditorApp(Adw.Application):

    def __init__(self):
        super().__init__(application_id='org.example.mdxeditor', flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_default_size(800, 600)
        self.win.set_title('MDX Editor')
        header = Adw.HeaderBar()
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.editor = MDXEditorWidget()
        main_box.append(header)
        main_box.append(self.editor)
        self.win.set_content(main_box)
        get_button = Gtk.Button(label='Get Markdown')
        get_button.connect('clicked', self.on_get_markdown)
        header.pack_start(get_button)
        set_button = Gtk.Button(label='Set Sample Markdown')
        set_button.connect('clicked', self.on_set_markdown)
        header.pack_start(set_button)
        self.win.present()

    def on_get_markdown(self, button):
        markdown = self.editor.get_markdown()
        print(f'Current Markdown:\n{markdown}')
        dialog = Adw.MessageDialog(transient_for=self.win, heading='Current Markdown', body=markdown or '(empty)')
        dialog.add_response('close', 'Close')
        dialog.present()

    def on_set_markdown(self, button):
        sample_markdown = "# Welcome\n\nThis is a **live demo** of MDXEditor with all default features on.\n\n> The overriding design goal for Markdown’s formatting syntax is to make it as readable as possible.\n> The idea is that a Markdown-formatted document should be publishable as-is, as plain text,\n> without looking like it’s been marked up with tags or formatting instructions.\n\n[— Daring Fireball](https://daringfireball.net/projects/markdown/).\n\nIn here, you can find the following markdown elements:\n\n* Headings\n* Lists\n  * Unordered\n  * Ordered\n  * Check lists\n  * And nested ;)\n* Links\n* Bold/Italic/Underline formatting\n* Tables\n* Code block editors\n* And much more.\n\nThe current editor content is styled using the `@tailwindcss/typography` [plugin](https://tailwindcss.com/docs/typography-plugin).\n\n## What can you do here?\n\nThis is a great location for you to test how editing markdown feels. If you have an existing markdown source, you can switch to source mode using the toggle group in the top right, paste it in there, and go back to rich text mode.\n\nIf you need a few ideas, here's what you can try:\n\n1. Add your own code sample\n2. Change the type of the headings\n3. Insert a table, add a few rows and columns\n4. Switch back to source markdown to see what you're going to get as an output\n5. Test the diff feature to see how the markdown has changed\n6. Add a frontmatter block through the toolbar button\n\n## A code sample\n\nMDXEditor embeds CodeMirror for code editing.\n\n```tsx\nexport default function App() {\n  return (<div>Hello world</div>)\n}\n```\n\n## A live code example\n\nThe block below is a live React component. You can configure multiple live code presets that specify the available npm packages and the default imports. You can also specify a default component that will be rendered in the live code block.\n\n```jsx live\nexport default function App() {\n  return (<div>\n  <p>This is a live React component, that's being previewed in codesandbox. </p>\n  <p>Editing it will update the fenced codeblock in the markdown.</p>\n  </div>)\n}\n```\n\n## A table\n\nPlay with the table below - add rows, columns, change column alignment. When editing,\nyou can navigate the cells with `enter`, `shift+enter`, `tab` and `shift+tab`.\n\n| Item              | In Stock | Price |\n| :---------------- | :------: | ----: |\n| Python Hat        |   True   | 23.99 |\n| SQL Hat           |   True   | 23.99 |\n| Codecademy Tee    |   False  | 19.99 |\n| Codecademy Hoodie |   False  | 42.99 |\n"
        self.editor.set_markdown(sample_markdown)
if __name__ == '__main__':
    app = MDXEditorApp()
    app.run(None)