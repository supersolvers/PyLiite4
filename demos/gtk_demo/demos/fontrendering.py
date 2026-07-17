"""Pango/Font Rendering

Demonstrates various aspects of font rendering,
such as hinting, antialiasing and grid alignment.

The demo lets you explore font rendering options
interactively to get a feeling for they affect the
shape and positioning of the glyphs.
"""

from collections.abc import Callable

from PyLiite4 import Gdk, GdkPixbuf, GLib, Graphene, Gsk, Gtk, Pango, cairo

# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None
font_button: Gtk.FontDialogButton
entry: Gtk.Entry
image: Gtk.Picture
hinting: Gtk.DropDown
anti_alias: Gtk.CheckButton
hint_metrics: Gtk.CheckButton
up_button: Gtk.Button
down_button: Gtk.Button
text_radio: Gtk.ToggleButton
show_grid: Gtk.CheckButton
show_extents: Gtk.CheckButton
show_pixels: Gtk.CheckButton
show_outlines: Gtk.CheckButton

context: Pango.Context | None = None

scale = 7
pixel_alpha = 1.0
outline_alpha = 0.0


def extents_to_pixels(inclusive: Pango.Rectangle | None, nearest: Pango.Rectangle | None) -> None:
    # pango_extents_to_pixels(), which crashes when called through PyGObject.
    if inclusive is not None:
        orig_x, orig_y = inclusive.x, inclusive.y
        inclusive.x = inclusive.x // Pango.SCALE
        inclusive.y = inclusive.y // Pango.SCALE
        inclusive.width = -(-(orig_x + inclusive.width) // Pango.SCALE) - inclusive.x
        inclusive.height = -(-(orig_y + inclusive.height) // Pango.SCALE) - inclusive.y
    if nearest is not None:
        orig_x, orig_y = nearest.x, nearest.y
        nearest.x = (nearest.x + Pango.SCALE // 2) >> 10
        nearest.y = (nearest.y + Pango.SCALE // 2) >> 10
        nearest.width = ((orig_x + nearest.width + Pango.SCALE // 2) >> 10) - nearest.x
        nearest.height = ((orig_y + nearest.height + Pango.SCALE // 2) >> 10) - nearest.y


def units_round(d: int) -> int:
    # PANGO_UNITS_ROUND(), a macro
    return (d + (Pango.SCALE >> 1)) & ~(Pango.SCALE - 1)


def pixbuf_from_surface(surface: cairo.ImageSurface) -> GdkPixbuf.Pixbuf:
    # gdk_pixbuf_new_from_data() on the surface's data, as in C: cairo's BGRA read as RGBA.
    surface.flush()
    return GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(surface.get_data())),
                                           GdkPixbuf.Colorspace.RGB, True, 8,
                                           surface.get_width(), surface.get_height(), surface.get_stride())


def draw_node(cr: cairo.Context, snapshot: Gtk.Snapshot) -> None:
    node = snapshot.to_node()
    if node is not None:
        node.draw(cr)


def update_image(*args: object) -> None:
    global context

    # pango_cairo_context_set_font_options() isn't in PyLiite4, which has no PangoCairo: the options are set on the
    # widget, and a context created from it takes them.
    text = entry.get_text()
    desc = font_button.get_font_desc()

    fopt = cairo.FontOptions()

    match hinting.get_selected():
        case 0:
            hintstyle = cairo.HINT_STYLE_NONE
        case 1:
            hintstyle = cairo.HINT_STYLE_SLIGHT
        case 2:
            hintstyle = cairo.HINT_STYLE_MEDIUM
        case 3:
            hintstyle = cairo.HINT_STYLE_FULL
        case _:
            hintstyle = cairo.HINT_STYLE_DEFAULT
    fopt.set_hint_style(hintstyle)

    if hint_metrics.get_active():
        hintmetrics = cairo.HINT_METRICS_ON
    else:
        hintmetrics = cairo.HINT_METRICS_OFF
    fopt.set_hint_metrics(hintmetrics)

    if anti_alias.get_active():
        antialias = cairo.ANTIALIAS_GRAY
    else:
        antialias = cairo.ANTIALIAS_NONE
    fopt.set_antialias(antialias)

    image.set_font_options(fopt)
    context = image.create_pango_context()
    context.set_round_glyph_positions(hintmetrics == cairo.HINT_METRICS_ON)
    context.changed()

    if text_radio.get_active():
        layout = Pango.Layout.new(context)
        layout.set_font_description(desc)
        layout.set_text(text, -1)
        ink, logical = layout.get_extents()
        baseline = layout.get_baseline()

        extents_to_pixels(ink, None)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, ink.width + 20, ink.height + 20)
        cr = cairo.Context(surface)
        cr.set_source_rgb(1, 1, 1)
        cr.paint()

        # pango_cairo_show_layout(), as a text node drawn with cairo
        snapshot = Gtk.Snapshot()
        snapshot.translate(Graphene.Point().init(10, 10))
        snapshot.append_layout(layout, Gdk.RGBA(red=0, green=0, blue=0, alpha=pixel_alpha))
        draw_node(cr, snapshot)

        # pango_cairo_layout_path(), through a GskPath
        builder = Gsk.PathBuilder.new()
        builder.add_layout(layout)
        cr.translate(10, 10)
        builder.to_path().to_cairo(cr)
        cr.identity_matrix()
        path = list(cr.copy_path())

        pixbuf = pixbuf_from_surface(surface)

        pixbuf2 = pixbuf.scale_simple(pixbuf.get_width() * scale,
                                      pixbuf.get_height() * scale,
                                      GdkPixbuf.InterpType.NEAREST)

        pixels = bytearray(pixbuf2.get_pixels())
        surface = cairo.ImageSurface.create_for_data(pixels,
                                                     cairo.FORMAT_ARGB32,
                                                     pixbuf2.get_width(),
                                                     pixbuf2.get_height(),
                                                     pixbuf2.get_rowstride())

        cr = cairo.Context(surface)
        cr.set_line_width(1)

        if show_grid.get_active():
            cr.set_source_rgba(0.2, 0, 0, 0.2)
            for i in range(1, ink.height + 20):
                cr.move_to(0, scale * i - 0.5)
                cr.line_to(scale * (ink.width + 20), scale * i - 0.5)
                cr.stroke()
            for i in range(1, ink.width + 20):
                cr.move_to(scale * i - 0.5, 0)
                cr.line_to(scale * i - 0.5, scale * (ink.height + 20))
                cr.stroke()

        if show_extents.get_active():
            cr.set_source_rgb(0, 0, 1)

            cr.rectangle(scale * (10 + Pango.units_to_double(logical.x)) - 0.5,
                         scale * (10 + Pango.units_to_double(logical.y)) - 0.5,
                         scale * Pango.units_to_double(logical.width) + 1,
                         scale * Pango.units_to_double(logical.height) + 1)
            cr.stroke()
            cr.move_to(scale * (10 + Pango.units_to_double(logical.x)) - 0.5,
                       scale * (10 + Pango.units_to_double(baseline)) - 0.5)
            cr.line_to(scale * (10 + Pango.units_to_double(logical.x + logical.width)) + 1,
                       scale * (10 + Pango.units_to_double(baseline)) - 0.5)
            cr.stroke()
            cr.set_source_rgb(1, 0, 0)
            cr.rectangle(scale * (10 + ink.x) - 0.5,
                         scale * (10 + ink.y) - 0.5,
                         scale * ink.width + 1,
                         scale * ink.height + 1)
            cr.stroke()

        cr.set_source_rgba(0, 0, 0, outline_alpha)
        cr.move_to(scale * 20 - 0.5, scale * 20 - 0.5)
        # cairo_append_path() of the path with its points scaled
        for kind, points in path:
            points = [p * scale for p in points]
            if kind == cairo.PATH_MOVE_TO:
                cr.move_to(*points)
            elif kind == cairo.PATH_LINE_TO:
                cr.line_to(*points)
            elif kind == cairo.PATH_CURVE_TO:
                cr.curve_to(*points)
            elif kind == cairo.PATH_CLOSE_PATH:
                cr.close_path()
            else:
                raise AssertionError("not reached")
        cr.stroke()

        surface.flush()
        del cr, surface
        pixbuf2 = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(pixels)), GdkPixbuf.Colorspace.RGB, True, 8,
                                                  pixbuf2.get_width(), pixbuf2.get_height(),
                                                  pixbuf2.get_rowstride())
    else:
        if text == "":
            text = " "

        ch = text[0]
        layout = Pango.Layout.new(context)

        while True:
            s = (ch + "‌") * 4

            layout.set_font_description(desc)
            layout.set_text(s, -1)
            ink, logical = layout.get_extents()
            extents_to_pixels(logical, None)

            iter = layout.get_iter()
            run = iter.get_run()

            if run.glyphs.num_glyphs < 8:
                # not a good char to use
                ch = "a"
                continue
            break

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, logical.width * 3 // 2, 4 * logical.height)
        cr = cairo.Context(surface)
        cr.set_source_rgb(1, 1, 1)
        cr.paint()

        # The C demo widens the run's four glyphs, gives each a quarter pixel more offset than the last, and shows
        # the layout. PyGObject only hands out copies of runs, and reads their glyph arrays with the wrong stride, so
        # the glyphs can't be changed: each is drawn instead, as a layout of its own, at the same positions.
        width = units_round(run.glyphs.get_width() * 3 // 2 // 4)
        glyph = Pango.Layout.new(context)
        glyph.set_font_description(desc)
        glyph.set_text(ch, -1)

        snapshot = Gtk.Snapshot()
        for j in range(4):
            for i in range(4):
                snapshot.save()
                snapshot.translate(Graphene.Point().init((i * width + i * (Pango.SCALE // 4)) / Pango.SCALE,
                                                         j * logical.height + j / 4))
                snapshot.append_layout(glyph, Gdk.RGBA(red=0, green=0, blue=0, alpha=1))
                snapshot.restore()
        draw_node(cr, snapshot)

        pixbuf = pixbuf_from_surface(surface)

        pixbuf2 = pixbuf.scale_simple(pixbuf.get_width() * scale,
                                      pixbuf.get_height() * scale,
                                      GdkPixbuf.InterpType.NEAREST)

    texture = Gdk.Texture.new_for_pixbuf(pixbuf2)
    image.set_paintable(texture)


fading = False
start_pixel_alpha = 0.0
end_pixel_alpha = 0.0
start_outline_alpha = 0.0
end_outline_alpha = 0.0
start_time = 0
end_time = 0


def ease_out_cubic(t: float) -> float:
    p = t - 1
    return p * p * p + 1


def change_alpha(widget: Gtk.Widget, clock: Gdk.FrameClock) -> bool:
    global pixel_alpha, outline_alpha, fading

    now = GLib.get_monotonic_time()

    t = ease_out_cubic((now - start_time) / (end_time - start_time))

    pixel_alpha = start_pixel_alpha + (end_pixel_alpha - start_pixel_alpha) * t
    outline_alpha = start_outline_alpha + (end_outline_alpha - start_outline_alpha) * t

    update_image()

    if now >= end_time:
        fading = False
        return GLib.SOURCE_REMOVE

    return GLib.SOURCE_CONTINUE


def start_alpha_fade(*args: object) -> None:
    global start_pixel_alpha, end_pixel_alpha, start_outline_alpha, end_outline_alpha, start_time, end_time, fading

    if fading:
        return

    pixels = show_pixels.get_active()
    outlines = show_outlines.get_active()

    start_pixel_alpha = pixel_alpha
    if pixels and outlines:
        end_pixel_alpha = 0.5
    elif pixels:
        end_pixel_alpha = 1
    else:
        end_pixel_alpha = 0

    start_outline_alpha = outline_alpha
    if outlines:
        end_outline_alpha = 1.0
    else:
        end_outline_alpha = 0.0

    start_time = GLib.get_monotonic_time()
    end_time = start_time + GLib.TIME_SPAN_SECOND // 2

    fading = True
    window_ref().add_tick_callback(change_alpha)


def update_buttons() -> None:
    up_button.set_sensitive(scale < 32)
    down_button.set_sensitive(scale > 1)


def scale_up(widget: Gtk.Widget) -> bool:
    global scale
    scale += 1
    update_buttons()
    update_image()
    return True


def scale_down(widget: Gtk.Widget) -> bool:
    global scale
    scale -= 1
    update_buttons()
    update_image()
    return True


def destroyed(win: Gtk.Window) -> None:
    global context
    # The context was made for this window's picture; a reopened window makes its own.
    context = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref, font_button, up_button, down_button, entry, image, hinting, anti_alias, hint_metrics
    global text_radio, show_grid, show_extents, show_pixels, show_outlines

    window = window_ref()
    if window is None:
        builder = Gtk.Builder.new_from_resource("/fontrendering/fontrendering.ui")
        window = builder.get_object("window")
        window.set_display(do_widget.get_display())
        window_ref = window.weak_ref()
        window.destroy.connect(destroyed)
        font_button = builder.get_object("font_button")
        up_button = builder.get_object("up_button")
        down_button = builder.get_object("down_button")
        entry = builder.get_object("entry")
        image = builder.get_object("image")
        hinting = builder.get_object("hinting")
        anti_alias = builder.get_object("antialias")
        hint_metrics = builder.get_object("hint_metrics")
        text_radio = builder.get_object("text_radio")
        show_grid = builder.get_object("show_grid")
        show_extents = builder.get_object("show_extents")
        show_pixels = builder.get_object("show_pixels")
        show_outlines = builder.get_object("show_outlines")

        up_button.clicked.connect(scale_up)
        down_button.clicked.connect(scale_down)
        entry.notify["text"].connect(update_image)
        font_button.notify["font-desc"].connect(update_image)
        hinting.notify["selected"].connect(update_image)
        anti_alias.notify["active"].connect(update_image)
        hint_metrics.notify["active"].connect(update_image)
        text_radio.notify["active"].connect(update_image)
        show_grid.notify["active"].connect(update_image)
        show_extents.notify["active"].connect(update_image)
        show_pixels.notify["active"].connect(start_alpha_fade)
        show_outlines.notify["active"].connect(start_alpha_fade)

        update_image()

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
