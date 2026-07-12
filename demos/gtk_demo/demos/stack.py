"""Stack

GtkStack is a container that shows a single child at a time,
with nice transitions when the visible child changes.

GtkStackSwitcher adds buttons to control which child is visible.
"""

from PyLiite4 import Gtk

window: Gtk.Window | None = None


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        builder = Gtk.Builder.new_from_resource("/stack/stack.ui")
        window = builder.get_object("window1")
        window.set_display(do_widget.get_display())
        window.destroy.connect(destroyed)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
