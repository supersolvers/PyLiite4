"""Layout Manager/Transition
#Keywords: GtkLayoutManager

This demo shows a simple example of a custom layout manager
and a widget using it. The layout manager places the children
of the widget in a grid or a circle.

The widget is animating the transition between the two layouts.

Click to start the transition.
"""

from PyLiite4 import Gtk

from .demochild import demo_child_new
from .demowidget import demo_widget_new

window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(parent: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        color = [
            "red", "orange", "yellow", "green",
            "blue", "grey", "magenta", "lime",
            "yellow", "firebrick", "aqua", "purple",
            "tomato", "pink", "thistle", "maroon",
        ]

        window = Gtk.Window()
        window.set_title("Layout Manager — Transition")
        window.set_default_size(600, 600)
        window.close_request.connect(close_request)

        widget = demo_widget_new()

        for i in range(16):
            child = demo_child_new(color[i])
            child.set_margin_start(4)
            child.set_margin_end(4)
            child.set_margin_top(4)
            child.set_margin_bottom(4)
            widget.add_child(child)

        window.set_child(widget)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
