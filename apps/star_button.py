import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject


class StarButton(Gtk.Button):
    __gtype_name__ = "StarButton"
    starred = GObject.Property(type=bool, default=False)
    __gsignals__ = {"star-toggled": (GObject.SignalFlags.RUN_LAST, None, (bool,))}

    def __init__(self, starred: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_css_class("flat")
        self.add_css_class("ghost-star")
        self.set_valign(Gtk.Align.CENTER)

        # Connect to property change notification before setting the property
        self.connect("notify::starred", self._on_starred_changed)

        # Set the initial starred state
        self.set_property("starred", starred)
        self._update_icon()

        # Connect click handler
        self.connect("clicked", self._on_clicked)

    def _on_starred_changed(self, obj, pspec):
        self._update_icon()

    def _update_icon(self) -> None:
        starred = self.get_property("starred")
        icon_name = "starred-symbolic" if starred else "non-starred-symbolic"
        self.set_icon_name(icon_name)

    def _on_clicked(self, button) -> None:
        self.toggle_starred()

    def toggle_starred(self) -> None:
        current_starred = self.get_property("starred")
        new_starred = not current_starred
        self.set_property("starred", new_starred)
        self.emit("star-toggled", new_starred)

    def set_starred(self, starred: bool) -> None:
        self.set_property("starred", starred)

    def get_starred(self) -> bool:
        return self.get_property("starred")

    @staticmethod
    def get_css_style():
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
