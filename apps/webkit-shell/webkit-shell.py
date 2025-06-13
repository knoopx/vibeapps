#!/usr/bin/env python
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gtk, Gdk, WebKit, GLib, Gio
import os
import sys
import argparse

APP_ID = "net.knoopx.webkit-shell"
COOKIES_FILE_NAME = "cookies.sqlite"


class WebKitShell(Gtk.Application):

    def __init__(
        self, app_id=APP_ID, url=None, width=800, height=600, title="WebKit Shell"
    ):
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE
            | Gio.ApplicationFlags.REPLACE,
        )
        self.url = url
        self.window_width = width
        self.window_height = height
        self.window = None
        self.webview = None
        self.web_context = None
        self.app_id = app_id
        self.title = title

    def do_startup(self):
        Gtk.Application.do_startup(self)
        user_data_dir = GLib.get_user_data_dir()
        session_data_path = os.path.join(user_data_dir, self.app_id)
        os.makedirs(session_data_path, exist_ok=True)
        print(f"Session data will be stored in: {session_data_path}")

    def on_decide_policy(self, webview, decision, decision_type):
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
        return False

    def do_activate(self):
        if not self.webview:
            settings = WebKit.Settings.new()
            settings.set_enable_developer_extras(True)
            settings.set_enable_javascript(True)
            settings.set_enable_write_console_messages_to_stdout(True)
            settings.set_property("allow-file-access-from-file-urls", True)
            settings.set_property("allow-universal-access-from-file-urls", True)
            settings.set_property("enable-developer-extras", True)
            settings.set_property("enable-javascript", True)
            settings.set_property("enable-media-stream", True)
            settings.set_property("enable-site-specific-quirks", True)
            settings.set_property("enable-webgl", True)
            settings.set_property("enable-write-console-messages-to-stdout", True)
            self.webview = WebKit.WebView()
            self.webview.set_settings(settings)
            self.webview.connect("decide-policy", self.on_decide_policy)
        if not self.window:
            self.window = Gtk.ApplicationWindow(application=self)
            self.window.set_title(self.title)
            width = 800
            height = 600
            if hasattr(self, "window_width") and hasattr(self, "window_height"):
                width = self.window_width
                height = self.window_height
            self.window.set_default_size(width, height)
            self.window.set_child(self.webview)
            self.window.present()
            if self.url:
                print(f"Loading URL: {self.url}")
                self.webview.load_uri(self.url)
            else:
                print(
                    "No URL provided. Please provide one via '--url <URL>' or as a positional argument."
                )
                self.webview.load_html(
                    "<h1>No URL Provided</h1><p>Please launch with a URL, e.g., <code>python webkit-shell.py https://www.google.com</code> or <code>python webkit-shell.py --url https://www.google.com</code></p>",
                    "file:///",
                )

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()
        if self.window:
            if "width" in options or "height" in options:
                width = options.get("width", self.window_width)
                height = options.get("height", self.window_height)
                self.window.set_default_size(width, height)
            if "url" in options:
                self.url = options["url"]
                self.webview.load_uri(self.url)
            if "title" in options:
                self.window.set_title(options["title"])
            self.window.present()
        else:
            self.activate()
        return 0


def main():
    parser = argparse.ArgumentParser(description="WebKit Shell - A minimal web browser")
    parser.add_argument(
        "--app-id", "-a", default=APP_ID, help="Application ID for the GTK application"
    )
    parser.add_argument("--url", "-u", help="URL to load in the web view")
    parser.add_argument("--width", "-w", type=int, default=800, help="Window width")
    parser.add_argument("--height", "-t", type=int, default=600, help="Window height")
    parser.add_argument("--title", "-l", default="WebKit Shell", help="Window title")
    args = parser.parse_args()
    app = WebKitShell(
        app_id=args.app_id,
        url=args.url,
        width=args.width,
        height=args.height,
        title=args.title,
    )
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
