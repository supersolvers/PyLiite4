"""Pango/Text Mask

This demo shows how to use PangoCairo to draw text with more than
just a single color.
"""

from PyLiite4 import Gtk, Pango, cairo

try:
    from PyLiite4 import PangoCairo
except ImportError:
    # PyLiite4 doesn't wrap PangoCairo, though bundled wheels carry its typelib: bind it the way PyLiite4's modules do.
    from types import ModuleType

    from PyLiite4 import _runtime

    PangoCairo = ModuleType("PangoCairo")
    _runtime.bind(PangoCairo.__dict__, "PangoCairo", "1.0", (), {})

window: Gtk.Window | None = None
da: Gtk.DrawingArea


def draw_text(da: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
    cr.save()

    layout = da.create_pango_layout("Pango power!\nPango power!\nPango power!")
    desc = Pango.FontDescription.from_string("sans bold 34")
    layout.set_font_description(desc)

    cr.move_to(30, 20)
    PangoCairo.layout_path(cr, layout)

    pattern = cairo.LinearGradient(0.0, 0.0, width, height)
    pattern.add_color_stop_rgb(0.0, 1.0, 0.0, 0.0)
    pattern.add_color_stop_rgb(0.2, 1.0, 0.0, 0.0)
    pattern.add_color_stop_rgb(0.3, 1.0, 1.0, 0.0)
    pattern.add_color_stop_rgb(0.4, 0.0, 1.0, 0.0)
    pattern.add_color_stop_rgb(0.6, 0.0, 1.0, 1.0)
    pattern.add_color_stop_rgb(0.7, 0.0, 0.0, 1.0)
    pattern.add_color_stop_rgb(0.8, 1.0, 0.0, 1.0)
    pattern.add_color_stop_rgb(1.0, 1.0, 0.0, 1.0)

    cr.set_source(pattern)
    cr.fill_preserve()

    cr.set_source_rgb(0.0, 0.0, 0.0)
    cr.set_line_width(0.5)
    cr.stroke()

    cr.restore()


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window, da
    if window is None:
        window = Gtk.Window()
        window.set_resizable(True)
        window.set_size_request(400, 240)
        window.set_title("Text Mask")
        window.destroy.connect(destroyed)

        da = Gtk.DrawingArea()

        window.set_child(da)
        da.set_draw_func(draw_text)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
