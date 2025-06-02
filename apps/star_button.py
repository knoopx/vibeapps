#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject

class StarButton(Gtk.Button):
    __gtype_name__ = 'StarButton'
    starred = GObject.Property(type=bool, default=False)
    __gsignals__ = {'star-toggled': (GObject.SignalFlags.RUN_LAST, None, (bool,))}

    def __init__(self, starred: bool=False, **kwargs):
        super().__init__(**kwargs)
        self.add_css_class('flat')
        self.add_css_class('ghost-star')
        self.set_valign(Gtk.Align.CENTER)
        self.starred = starred
        self._update_icon()
        self.connect('clicked', self._on_clicked)

    def _update_icon(self):
        icon_name = 'starred-symbolic' if self.starred else 'non-starred-symbolic'
        self.set_icon_name(icon_name)

    def _on_clicked(self, button):
        self.toggle_starred()

    def toggle_starred(self):
        self.starred = not self.starred
        self._update_icon()
        self.emit('star-toggled', self.starred)

    def set_starred(self, starred: bool):
        if self.starred != starred:
            self.starred = starred
            self._update_icon()

    def get_starred(self) -> bool:
        return self.starred

    @staticmethod
    def get_css_style():
        return '\n        .ghost-star {\n            padding: 4px;\n            min-width: 24px;\n            min-height: 24px;\n            opacity: 0.5;\n            background: none;\n            color: currentColor;\n        }\n\n        .ghost-star:hover {\n            opacity: 1;\n            background: none;\n        }\n        '