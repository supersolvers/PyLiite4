"""Paintable/Symbolic Paintable

GdkPaintables can be made to follow the theme's colors. GTK calls
icons that do this symbolic icons, paintables that want to have
the same effect can implement the GtkSymbolicPaintable interface.

We will adapt the original paintable example by adding the ability
to recolor the paintable based on the symbolic colors.
"""

import random
from enum import IntEnum

from PyLiite4 import Gdk, GObject, Gtk

from .paintable import gtk_nuclear_snapshot, rgba

window: Gtk.Window | None = None


class WarningLevel(IntEnum):
    """A few warning levels, so we can pick colors based on them."""

    NONE = 0
    ALERT = 1
    EMERGENCY = 2


class GtkNuclearSymbolic(GObject.Object, Gdk.Paintable, Gtk.SymbolicPaintable):
    """We need to implement both the GdkPaintable and the GtkSymbolicPaintable interface."""

    __gtype_name__ = "GtkNuclearSymbolic"

    def __init__(self) -> None:
        super().__init__()
        self.warning_level = WarningLevel.NONE

    def do_snapshot_symbolic(self, snapshot: Gdk.Snapshot, width: float, height: float,
                             colors: list[Gdk.RGBA], n_colors: int) -> None:  # PyGObject passes the length too
        """Draw the nuclear icon in the given colors."""
        transparent = rgba(0, 0, 0, 0)

        # select the right background color from the warning level
        if self.warning_level == WarningLevel.NONE:
            bg_color = transparent
        elif self.warning_level == WarningLevel.ALERT:
            bg_color = colors[Gtk.SymbolicColor.WARNING]
        elif self.warning_level == WarningLevel.EMERGENCY:
            bg_color = colors[Gtk.SymbolicColor.ERROR]
        else:
            # This should never happen, but we better do defensive coding
            # with this critical icon
            raise AssertionError("not reached")

        # Draw the icon with the selected warning color
        gtk_nuclear_snapshot(snapshot,
                             colors[Gtk.SymbolicColor.FOREGROUND],
                             bg_color,
                             width, height,
                             0)

    # We need to implement the functionality required by the GdkPaintable interface

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        # Calling this function without passing a color is a neat trick
        # to make GTK use default colors and otherwise forward the call
        # to the snapshotting function above.
        self.snapshot_symbolic(snapshot, width, height, [])

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # This image has a static size, but the contents may change:
        # We draw different things when the warning level changes.
        return Gdk.PaintableFlags.STATIC_SIZE


def gtk_nuclear_symbolic_new() -> Gdk.Paintable:
    return GtkNuclearSymbolic()


def nuclear_button_clicked(button: Gtk.Button, nuclear: GtkNuclearSymbolic) -> None:
    """Add some fun feature to the button."""
    if nuclear.warning_level >= WarningLevel.EMERGENCY:
        # On maximum warning level, reset the warning
        nuclear.warning_level = WarningLevel.NONE

        # And sometimes (but not always to confuse people)
        # close the window.
        if random.getrandbits(1):
            window.close()
    else:
        # Otherwise just increase the warning level
        nuclear.warning_level = WarningLevel(nuclear.warning_level + 1)

    # Don't forget to emit the signal causing the paintable to redraw.
    # Changing the warning level changes the background color after all.
    nuclear.invalidate_contents()


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Don't click!")
        window.set_default_size(200, 200)
        window.close_request.connect(close_request)

        button = Gtk.Button()
        window.set_child(button)

        nuclear = gtk_nuclear_symbolic_new()
        image = Gtk.Image.new_from_paintable(nuclear)
        image.set_pixel_size(256)
        button.set_child(image)
        button.clicked.connect(nuclear_button_clicked, nuclear)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
