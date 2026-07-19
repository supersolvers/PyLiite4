"""Masking

Demonstrates mask nodes.

This demo uses a text node as mask for
an animated linear gradient.
"""

from PyLiite4 import Gtk

from .demo4widget import demo4_widget_new

window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        window = Gtk.Window()
        window.set_title("Mask Nodes")
        window.set_default_size(600, 400)
        window.set_display(do_widget.get_display())

        window.close_request.connect(close_request)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        window.set_child(box)

        demo = demo4_widget_new()
        demo.set_hexpand(True)
        demo.set_vexpand(True)

        box.append(demo)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 0.1)
        scale.set_value(0.5)
        scale.get_adjustment().bind_property("value", demo, "progress", 0)

        box.append(scale)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
