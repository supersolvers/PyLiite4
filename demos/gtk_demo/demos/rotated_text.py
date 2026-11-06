"""Pango/Rotated Text

This demo shows how to use PangoCairo to draw rotated and transformed
text. The right pane shows a rotated GtkLabel widget.

In both cases, a custom PangoCairo shape renderer is installed to draw
a red heart using cairo drawing operations instead of the Unicode heart
character.
"""

import math

from PyLiite4 import Gtk, Pango, cairo

try:
    from PyLiite4 import PangoCairo
except ImportError:
    # PyLiite4 doesn't wrap PangoCairo, though bundled wheels carry its typelib: bind it the way PyLiite4's modules do.
    from types import ModuleType

    from PyLiite4 import _runtime

    PangoCairo = ModuleType("PangoCairo")
    _runtime.bind(PangoCairo.__dict__, "PangoCairo", "1.0", (), {})

HEART = "♥"
text = "I ♥ GTK"

RADIUS = 150
N_WORDS = 5
FONT = "Serif 18"

window: Gtk.Window | None = None


def fancy_shape_renderer(cr: cairo.Context, attr: Pango.AttrShape, do_path: bool) -> None:
    x, y = cr.get_current_point()
    cr.translate(x, y)

    cr.scale(attr.ink_rect.width / Pango.SCALE, attr.ink_rect.height / Pango.SCALE)

    # C keeps the character in the attribute's data; Python can't set it, and every shape here is a heart:
    # U+2665 BLACK HEART SUIT
    cr.move_to(.5, .0)
    cr.line_to(.9, -.4)
    cr.curve_to(1.1, -.8, .5, -.9, .5, -.5)
    cr.curve_to(.5, -.9, -.1, -.8, .1, -.4)
    cr.close_path()

    if not do_path:
        cr.set_source_rgb(1., 0., 0.)
        cr.fill()


def create_fancy_attr_list_for_layout(layout: Pango.Layout) -> Pango.AttrList:
    # The font metrics give the size of the fancy shapes.
    metrics = layout.get_context().get_metrics(layout.get_font_description(), None)
    ascent = metrics.get_ascent()
    logical_rect = Pango.Rectangle()
    logical_rect.x = 0
    logical_rect.width = ascent
    logical_rect.y = -ascent
    logical_rect.height = ascent
    ink_rect = logical_rect

    # Every heart gets a shape attribute.
    attrs = Pango.AttrList()
    encoded = text.encode()
    heart = HEART.encode()
    p = encoded.find(heart)
    while p != -1:
        attr = Pango.attr_shape_new(ink_rect, logical_rect)

        attr.start_index = p
        attr.end_index = attr.start_index + len(heart)

        attrs.insert(attr)
        p = encoded.find(heart, p + len(heart))

    return attrs


def rotated_text_draw(da: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
    # A transformation matrix makes the user space coordinates of the centered square drawn in [-RADIUS, RADIUS],
    # [-RADIUS, RADIUS]: first it centers, then it changes the scale.
    device_radius = min(width, height) / 2.
    cr.translate(device_radius + (width - 2 * device_radius) / 2,
                 device_radius + (height - 2 * device_radius) / 2)
    cr.scale(device_radius / RADIUS, device_radius / RADIUS)

    # A subtle gradient as the source.
    pattern = cairo.LinearGradient(-RADIUS, -RADIUS, RADIUS, RADIUS)
    pattern.add_color_stop_rgb(0., .5, .0, .0)
    pattern.add_color_stop_rgb(1., .0, .0, .5)
    cr.set_source(pattern)

    # A Pango context that draws shapes with fancy_shape_renderer().
    context = da.create_pango_context()
    PangoCairo.context_set_shape_renderer(context, fancy_shape_renderer)

    layout = Pango.Layout.new(context)
    layout.set_text(text, -1)
    desc = Pango.FontDescription.from_string(FONT)
    layout.set_font_description(desc)

    attrs = create_fancy_attr_list_for_layout(layout)
    layout.set_attributes(attrs)

    # The layout is drawn N_WORDS times in a circle.
    for i in range(N_WORDS):
        # Pango lays the text out again for the new transformation matrix.
        PangoCairo.update_layout(cr, layout)

        layout_width, layout_height = layout.get_pixel_size()
        cr.move_to(- layout_width / 2, - RADIUS * .9)
        PangoCairo.show_layout(cr, layout)

        # Rotates for the next turn.
        cr.rotate(math.pi * 2 / N_WORDS)


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Rotated Text")
        window.set_default_size(4 * RADIUS, 2 * RADIUS)
        window.destroy.connect(destroyed)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.set_homogeneous(True)
        window.set_child(box)

        drawing_area = Gtk.DrawingArea()
        box.append(drawing_area)
        drawing_area.add_css_class("view")

        drawing_area.set_draw_func(rotated_text_draw)

        label = Gtk.Label(label=text)
        box.append(label)

        # The label draws the hearts the same way.
        layout = label.get_layout()
        PangoCairo.context_set_shape_renderer(layout.get_context(), fancy_shape_renderer)
        attrs = create_fancy_attr_list_for_layout(layout)
        label.set_attributes(attrs)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
