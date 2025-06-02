from math import pi
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk

class CircularProgress(Gtk.DrawingArea):

    def __init__(self):
        super().__init__()
        self.fraction = 0
        self.set_content_width(18)
        self.set_content_height(18)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, width, height):
        radius = min(width, height) / 2
        cr.arc(width / 2, height / 2, radius, 0, 2 * pi)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.2)
        cr.fill()
        if self.fraction > 0:
            cr.arc(width / 2, height / 2, radius, -pi / 2, (2 * self.fraction - 0.5) * pi)
            cr.line_to(width / 2, height / 2)
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
            cr.fill()

    def set_fraction(self, fraction):
        self.fraction = fraction
        self.queue_draw()