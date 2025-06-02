#!/usr/bin/env python
import gi
gi.require_version('Adw', '1')
gi.require_version('WebKit', '6.0')
gi.require_version('Gtk', '4.0')
gi.require_version('GtkSource', '5')
from gi.repository import Adw
from main_window import MainWindow

class NotesApplication(Adw.Application):

    def __init__(self):
        super().__init__(application_id='net.knoopx.notes')
        self.win = None
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        if not self.win:
            self.win = MainWindow(app)
        self.win.present()
if __name__ == '__main__':
    app = NotesApplication()
    app.run([])