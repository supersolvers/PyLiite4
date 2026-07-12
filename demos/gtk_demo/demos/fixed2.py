"""Fixed Layout / Transformations
#Keywords: GtkLayoutManager

GtkFixed is a container that allows placing and transforming
widgets manually.

This demo shows how to rotate and scale a child widget using
a transform.
"""

import math
from collections.abc import Callable

from PyLiite4 import Gdk, GLib, Graphene, Gsk, Gtk

# The window, held weakly: GTK keeps a window until it is destroyed.
demo_window: Callable[[], Gtk.Window | None] = lambda: None
start_time = 0


def tick_cb(widget: Gtk.Widget, frame_clock: Gdk.FrameClock, child: Gtk.Widget) -> bool:
    fixed = widget
    now = GLib.get_monotonic_time()

    duration = (now - start_time) / GLib.TIME_SPAN_SECOND

    width = widget.get_width()
    height = widget.get_height()

    child_width = child.get_width()
    child_height = child.get_height()

    angle = duration * 90
    scale = 2 + math.sin(duration * math.pi)

    transform = (Gsk.Transform.new()
                 .translate(Graphene.Point().init(width / 2, height / 2))
                 .rotate(angle)
                 .scale(scale, scale)
                 .translate(Graphene.Point().init(- child_width / 2, - child_height / 2)))

    fixed.set_child_transform(child, transform)

    return GLib.SOURCE_CONTINUE


def create_demo_window(do_widget: Gtk.Widget) -> Gtk.Window:
    window = Gtk.Window()
    window.set_display(do_widget.get_display())
    window.set_title("Fixed Layout ‐ Transformations")
    window.set_default_size(400, 300)

    sw = Gtk.ScrolledWindow()
    window.set_child(sw)

    fixed = Gtk.Fixed()
    sw.set_child(fixed)

    child = Gtk.Label(label="All fixed?")
    fixed.put(child, 0, 0)
    fixed.set_overflow(Gtk.Overflow.VISIBLE)

    fixed.add_tick_callback(tick_cb, child)

    return window


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global demo_window, start_time

    window = demo_window()
    if window is None:
        window = create_demo_window(do_widget)
        demo_window = window.weak_ref()

    start_time = GLib.get_monotonic_time()

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
