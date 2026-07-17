"""Theming/Style Classes

GTK uses CSS for theming. Style classes can be associated
with widgets to inform the theme about intended rendering.

This demo shows some common examples where theming features
of GTK are used for certain effects: primary toolbars
and linked buttons.
"""

from PyLiite4 import Gtk

window: Gtk.Window | None = None


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window
    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Style Classes")
        window.set_resizable(False)
        window.destroy.connect(destroyed)

        builder = Gtk.Builder.new_from_resource("/theming_style_classes/theming.ui")

        grid = builder.get_object("grid")
        window.set_child(grid)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
