#!/usr/bin/env python3
"""
StarButton widget for starring/unstarring items.

A reusable GTK4 button widget that displays a star icon and handles
toggling between starred and unstarred states.
"""

import gi
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, GObject


class StarButton(Gtk.Button):
    """A button widget for starring/unstarring items."""
    __gtype_name__ = "StarButton"

    # Properties
    starred = GObject.Property(type=bool, default=False)

    # Signals
    __gsignals__ = {
        'star-toggled': (GObject.SignalFlags.RUN_LAST, None, (bool,)),
    }

    def __init__(self, starred: bool = False, **kwargs):
        super().__init__(**kwargs)

        # Configure button appearance
        self.add_css_class("flat")
        self.add_css_class("ghost-star")
        self.set_valign(Gtk.Align.CENTER)

        # Set initial state
        self.starred = starred
        self._update_icon()

        # Connect click handler
        self.connect("clicked", self._on_clicked)

    def _update_icon(self):
        """Update the icon based on starred state."""
        icon_name = "starred-symbolic" if self.starred else "non-starred-symbolic"
        self.set_icon_name(icon_name)

    def _on_clicked(self, button):
        """Handle button click - toggle starred state and emit signal."""
        self.toggle_starred()

    def toggle_starred(self):
        """Toggle the starred state and emit the star-toggled signal."""
        self.starred = not self.starred
        self._update_icon()
        self.emit('star-toggled', self.starred)

    def set_starred(self, starred: bool):
        """Set the starred state without emitting a signal."""
        if self.starred != starred:
            self.starred = starred
            self._update_icon()

    def get_starred(self) -> bool:
        """Get the current starred state."""
        return self.starred

    @staticmethod
    def get_css_style():
        """Get the CSS style for ghost star buttons."""
        return """
        .ghost-star {
            padding: 4px;
            min-width: 24px;
            min-height: 24px;
            opacity: 0.5;
            background: none;
            color: currentColor;
        }

        .ghost-star:hover {
            opacity: 1;
            background: none;
        }
        """
