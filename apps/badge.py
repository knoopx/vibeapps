from gi.repository import Gtk
from typing import Optional


class Badge(Gtk.Label):

    def __init__(self, text: str = "", style_classes: Optional[list] = None):
        super().__init__(label=text)
        self.add_css_class("dim-label")
        self.add_css_class("caption")
        self.add_css_class("badge")
        if style_classes:
            for style_class in style_classes:
                self.add_css_class(style_class)
        self.set_margin_start(2)
        self.set_margin_end(2)
        self.set_margin_top(1)
        self.set_margin_bottom(1)

    @staticmethod
    def get_css_style() -> str:
        return """
        .badge {
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 0.75em;
            margin: 0px 2px;
        }
        """

    def set_text(self, text: str):
        self.set_label(text)

    def get_text(self) -> str:
        return self.get_label()
