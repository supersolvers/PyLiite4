"""Constraints/VFL

GtkConstraintLayout allows defining constraints using a
compact syntax called Visual Format Language, or VFL.

A typical example of a VFL specification looks like this:

H:|-[button1(==button2)]-12-[button2]-|
"""

import sys
from collections.abc import Callable

from PyLiite4 import GLib, Gtk


class VflGrid(Gtk.Widget):
    __gtype_name__ = "VflGrid"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        self.button1: Gtk.Widget | None = Gtk.Button.new_with_label("Child 1")
        self.button1.set_parent(self)
        self.button1.set_name("button1")

        self.button2: Gtk.Widget | None = Gtk.Button.new_with_label("Child 2")
        self.button2.set_parent(self)
        self.button2.set_name("button2")

        self.button3: Gtk.Widget | None = Gtk.Button.new_with_label("Child 3")
        self.button3.set_parent(self)
        self.button3.set_name("button3")

        manager = self.get_layout_manager()
        build_constraints(self, manager)

    def do_dispose(self) -> None:
        for name in ("button1", "button2", "button3"):
            button = getattr(self, name, None)
            if button is not None:
                button.unparent()
                setattr(self, name, None)

        Gtk.Widget.do_dispose(self)


VflGrid.set_layout_manager_type(Gtk.ConstraintLayout)


# Layout:
#
#   +-----------------------------+
#   | +-----------+ +-----------+ |
#   | |  Child 1  | |  Child 2  | |
#   | +-----------+ +-----------+ |
#   | +-------------------------+ |
#   | |         Child 3         | |
#   | +-------------------------+ |
#   +-----------------------------+
#
# Constraints:
#
#   super.start = child1.start - 8
#   child1.width = child2.width
#   child1.end = child2.start - 12
#   child2.end = super.end - 8
#   super.start = child3.start - 8
#   child3.end = super.end - 8
#   super.top = child1.top - 8
#   super.top = child2.top - 8
#   child1.bottom = child3.top - 12
#   child2.bottom = child3.top - 12
#   child3.height = child1.height
#   child3.height = child2.height
#   child3.bottom = super.bottom - 8
#
# Visual format:
#
#   H:|-8-[view1(==view2)-12-[view2]-8-|
#   H:|-8-[view3]-8-|
#   V:|-8-[view1]-12-[view3(==view1)]-8-|
#   V:|-8-[view2]-12-[view3(==view2)]-8-|
def build_constraints(self: VflGrid, manager: Gtk.ConstraintLayout) -> None:
    vfl = [
        "H:|-[button1(==button2)]-12-[button2]-|",
        "H:|-[button3]-|",
        "V:|-[button1]-12-[button3(==button1)]-|",
        "V:|-[button2]-12-[button3(==button2)]-|",
    ]

    try:
        manager.add_constraints_from_description(vfl, 8, 8,
                                                 {"button1": self.button1,
                                                  "button2": self.button2,
                                                  "button3": self.button3})
    except GLib.Error as error:
        print(f"VFL parsing error:\n{error.message}", end="", file=sys.stderr)


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()
    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Constraints — VFL")
        window.set_default_size(260, -1)
        window_ref = window.weak_ref()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        window.set_child(box)

        grid = VflGrid()
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        box.append(grid)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
