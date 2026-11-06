"""Drawing Area
#Keywords: GtkDrawingArea

GtkDrawingArea is a blank area where you can draw custom displays
of various kinds.

This demo has two drawing areas. The checkerboard area shows
how you can just draw something; all you have to do is set a function
via gtk_drawing_area_set_draw_func(), as shown here.

The "scribble" area is a bit more advanced, and shows how to handle
events such as button presses and mouse motion. Click the mouse
and drag in the scribble area to draw squiggles. Resize the window
to clear the area.
"""

import math
from collections.abc import Callable

from PyLiite4 import Gtk, cairo

# The window, held weakly: GTK keeps a window until it is destroyed, and "destroy" comes when it goes away.
window_ref: Callable[[], Gtk.Window | None] = lambda: None
# The scribble area's surface, which keeps the current scribbles.
surface: cairo.ImageSurface | None = None


# Replaces the surface with a white one of the widget's size, which clears the scribbles.
def create_surface(widget: Gtk.Widget) -> None:
    global surface

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, widget.get_width(), widget.get_height())

    cr = cairo.Context(surface)

    cr.set_source_rgb(1, 1, 1)
    cr.paint()


def scribble_resize(widget: Gtk.DrawingArea, width: int, height: int) -> None:
    create_surface(widget)


# Redraws the screen from the surface.
def scribble_draw(da: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
    cr.set_source_surface(surface, 0, 0)
    cr.paint()


# Draws a round dot on the surface, where the scribbles are kept, and queues a redraw.
def draw_brush(widget: Gtk.Widget, x: float, y: float) -> None:
    if (surface is None or
            surface.get_width() != widget.get_width() or
            surface.get_height() != widget.get_height()):
        create_surface(widget)

    cr = cairo.Context(surface)

    cr.move_to(x, y)
    cr.line_to(x, y)
    cr.set_line_width(6)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_source_rgb(0, 0, 0)
    cr.stroke()

    widget.queue_draw()


start_x = 0.0
start_y = 0.0


def drag_begin(gesture: Gtk.GestureDrag, x: float, y: float, area: Gtk.Widget) -> None:
    global start_x, start_y
    start_x = x
    start_y = y

    draw_brush(area, x, y)


def drag_update(gesture: Gtk.GestureDrag, x: float, y: float, area: Gtk.Widget) -> None:
    draw_brush(area, start_x + x, start_y + y)


def drag_end(gesture: Gtk.GestureDrag, x: float, y: float, area: Gtk.Widget) -> None:
    draw_brush(area, start_x + x, start_y + y)


def oval_path(cr: cairo.Context, xc: float, yc: float, xr: float, yr: float) -> None:
    cr.save()

    cr.translate(xc, yc)
    cr.scale(1.0, yr / xr)
    cr.move_to(xr, 0.0)
    cr.arc(0, 0,
           xr,
           0, 2 * math.pi)
    cr.close_path()

    cr.restore()


CHECK_SIZE = 16


# Fills the given area with checks in the standard style for showing compositing effects.
#
# A repeating surface would make sense here, but most implementations of RENDER have broken repeat + transform, even
# when the transform is a translation.
def fill_checks(cr: cairo.Context, x: int, y: int, width: int, height: int) -> None:
    cr.rectangle(x, y, width, height)
    cr.set_source_rgb(0.4, 0.4, 0.4)
    cr.fill()

    # Only works when CHECK_SIZE is a power of 2.
    j = x & (-CHECK_SIZE)

    while j < height:
        i = y & (-CHECK_SIZE)
        while i < width:
            if (i // CHECK_SIZE + j // CHECK_SIZE) % 2 == 0:
                cr.rectangle(i, j, CHECK_SIZE, CHECK_SIZE)
            i += CHECK_SIZE
        j += CHECK_SIZE

    cr.set_source_rgb(0.7, 0.7, 0.7)
    cr.fill()


# Draws a red, a green and a blue circle, equally spaced inside the larger circle of the given radius at (xc, yc).
def draw_3circles(cr: cairo.Context, xc: float, yc: float, radius: float, alpha: float) -> None:
    subradius = radius * (2 / 3. - 0.1)

    cr.set_source_rgba(1., 0., 0., alpha)
    oval_path(cr,
              xc + radius / 3. * math.cos(math.pi * (0.5)),
              yc - radius / 3. * math.sin(math.pi * (0.5)),
              subradius, subradius)
    cr.fill()

    cr.set_source_rgba(0., 1., 0., alpha)
    oval_path(cr,
              xc + radius / 3. * math.cos(math.pi * (0.5 + 2 / .3)),
              yc - radius / 3. * math.sin(math.pi * (0.5 + 2 / .3)),
              subradius, subradius)
    cr.fill()

    cr.set_source_rgba(0., 0., 1., alpha)
    oval_path(cr,
              xc + radius / 3. * math.cos(math.pi * (0.5 + 4 / .3)),
              yc - radius / 3. * math.sin(math.pi * (0.5 + 4 / .3)),
              subradius, subradius)
    cr.fill()


def groups_draw(darea: Gtk.DrawingArea, cr: cairo.Context, width: int, height: int) -> None:
    radius = 0.5 * (width if width < height else height) - 10
    xc = width / 2.
    yc = height / 2.

    overlay = cr.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, width, height)

    punch = cr.get_target().create_similar(cairo.CONTENT_ALPHA, width, height)

    circles = cr.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, width, height)

    fill_checks(cr, 0, 0, width, height)

    # A black circle on the overlay
    overlay_cr = cairo.Context(overlay)
    overlay_cr.set_source_rgb(0., 0., 0.)
    oval_path(overlay_cr, xc, yc, radius, radius)
    overlay_cr.fill()

    # Three circles drawn to the punch surface are cut out of the black circle in the overlay.
    punch_cr = cairo.Context(punch)
    draw_3circles(punch_cr, xc, yc, radius, 1.0)
    del punch_cr

    overlay_cr.set_operator(cairo.OPERATOR_DEST_OUT)
    overlay_cr.set_source_surface(punch, 0, 0)
    overlay_cr.paint()

    # The three circles are drawn again in a group of their own at half intensity, and OPERATOR_ADD joins them to
    # the overlay without seams.
    circles_cr = cairo.Context(circles)

    circles_cr.set_operator(cairo.OPERATOR_OVER)
    draw_3circles(circles_cr, xc, yc, radius, 0.5)
    del circles_cr

    overlay_cr.set_operator(cairo.OPERATOR_ADD)
    overlay_cr.set_source_surface(circles, 0, 0)
    overlay_cr.paint()

    del overlay_cr

    cr.set_source_surface(overlay, 0, 0)
    cr.paint()


def close_window(win: Gtk.Window) -> None:
    global surface

    surface = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        window = Gtk.Window()
        window_ref = window.weak_ref()
        window.set_display(do_widget.get_display())
        window.set_title("Drawing Area")
        window.set_default_size(250, -1)

        window.destroy.connect(close_window)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)
        window.set_child(vbox)

        # The groups area
        label = Gtk.Label(label="Knockout groups")
        label.add_css_class("heading")
        vbox.append(label)

        frame = Gtk.Frame()
        frame.set_vexpand(True)
        vbox.append(frame)

        da = Gtk.DrawingArea(accessible_role=Gtk.AccessibleRole.IMG)
        frame.set_child(da)
        da.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])

        da.set_content_width(100)
        da.set_content_height(100)
        da.set_draw_func(groups_draw)

        # The scribble area
        label = Gtk.Label(label="Scribble area")
        label.add_css_class("heading")
        vbox.append(label)

        frame = Gtk.Frame()
        frame.set_vexpand(True)
        vbox.append(frame)

        da = Gtk.DrawingArea(accessible_role=Gtk.AccessibleRole.IMG)
        frame.set_child(da)
        da.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])

        da.set_content_width(100)
        da.set_content_height(100)
        da.set_draw_func(scribble_draw)

        da.resize.connect(scribble_resize)

        drag = Gtk.GestureDrag()
        drag.set_button(0)
        da.add_controller(drag)

        drag.drag_begin.connect(drag_begin, da)
        drag.drag_update.connect(drag_update, da)
        drag.drag_end.connect(drag_end, da)

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
