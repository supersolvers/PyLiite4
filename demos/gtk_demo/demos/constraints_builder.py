"""Constraints/Builder

GtkConstraintLayouts can be created in .ui files, and constraints can
be set up at that time as well, as this example demonstrates. It shows
various ways to do spacing and sizing with constraints.

Make the window wider to see the rows react differently
"""

from collections.abc import Callable

from PyLiite4 import Gtk


class ConstraintsGrid(Gtk.Widget):
    __gtype_name__ = "ConstraintsGrid"

    def do_dispose(self) -> None:
        while (child := self.get_first_child()):
            child.unparent()

        Gtk.Widget.do_dispose(self)


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()
    if window is None:
        builder = Gtk.Builder.new_from_resource("/constraints_builder/constraints_builder.ui")

        window = builder.get_object("window1")
        window.set_display(do_widget.get_display())
        window_ref = window.weak_ref()

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
