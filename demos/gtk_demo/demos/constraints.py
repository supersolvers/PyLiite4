"""Constraints/Simple Constraints
#Keywords: GtkLayoutManager

GtkConstraintLayout provides a layout manager that uses relations
between widgets (also known as “constraints”) to compute the position
and size of each child.

In addition to child widgets, the constraints can involve spacer
objects (also known as “guides”). This example has a guide between
the two buttons in the top row.

Try resizing the window to see how the constraints react to update
the layout.
"""

from collections.abc import Callable

from PyLiite4 import Gtk


class SimpleGrid(Gtk.Widget):
    __gtype_name__ = "SimpleGrid"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)

        self.button1: Gtk.Widget | None = Gtk.Button.new_with_label("Child 1")
        self.button1.set_parent(self)

        self.button2: Gtk.Widget | None = Gtk.Button.new_with_label("Child 2")
        self.button2.set_parent(self)

        self.button3: Gtk.Widget | None = Gtk.Button.new_with_label("Child 3")
        self.button3.set_parent(self)

        manager = self.get_layout_manager()
        build_constraints(self, manager)

    def do_dispose(self) -> None:
        for name in ("button1", "button2", "button3"):
            button = getattr(self, name, None)
            if button is not None:
                button.unparent()
                setattr(self, name, None)

        Gtk.Widget.do_dispose(self)


SimpleGrid.set_layout_manager_type(Gtk.ConstraintLayout)


# Layout:
#
#   +-------------------------------------+
#   | +-----------++-------++-----------+ |
#   | |  Child 1  || Space ||  Child 2  | |
#   | +-----------++-------++-----------+ |
#   | +---------------------------------+ |
#   | |             Child 3             | |
#   | +---------------------------------+ |
#   +-------------------------------------+
#
# Constraints:
#
#   super.start = child1.start - 8
#   child1.width = child2.width
#   child1.end = space.start
#   space.end = child2.start
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
# To add some flexibility, we make the space
# stretchable:
#
#   space.width >= 10
#   space.width = 100
#   space.width <= 200
def build_constraints(self: SimpleGrid, manager: Gtk.ConstraintLayout) -> None:
    guide = Gtk.ConstraintGuide()
    guide.set_name("space")
    guide.set_min_size(10, 10)
    guide.set_nat_size(100, 10)
    guide.set_max_size(200, 20)
    guide.set_strength(Gtk.ConstraintStrength.STRONG)
    manager.add_guide(guide)

    manager.add_constraint(
        Gtk.Constraint.new_constant(self.button1,
                                    Gtk.ConstraintAttribute.WIDTH,
                                    Gtk.ConstraintRelation.LE,
                                    200.0,
                                    Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(None,
                           Gtk.ConstraintAttribute.START,
                           Gtk.ConstraintRelation.EQ,
                           self.button1,
                           Gtk.ConstraintAttribute.START,
                           1.0,
                           -8.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button1,
                           Gtk.ConstraintAttribute.WIDTH,
                           Gtk.ConstraintRelation.EQ,
                           self.button2,
                           Gtk.ConstraintAttribute.WIDTH,
                           1.0,
                           0.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button1,
                           Gtk.ConstraintAttribute.END,
                           Gtk.ConstraintRelation.EQ,
                           guide,
                           Gtk.ConstraintAttribute.START,
                           1.0,
                           0.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(guide,
                           Gtk.ConstraintAttribute.END,
                           Gtk.ConstraintRelation.EQ,
                           self.button2,
                           Gtk.ConstraintAttribute.START,
                           1.0,
                           0.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button2,
                           Gtk.ConstraintAttribute.END,
                           Gtk.ConstraintRelation.EQ,
                           None,
                           Gtk.ConstraintAttribute.END,
                           1.0,
                           -8.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(None,
                           Gtk.ConstraintAttribute.START,
                           Gtk.ConstraintRelation.EQ,
                           self.button3,
                           Gtk.ConstraintAttribute.START,
                           1.0,
                           -8.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button3,
                           Gtk.ConstraintAttribute.END,
                           Gtk.ConstraintRelation.EQ,
                           None,
                           Gtk.ConstraintAttribute.END,
                           1.0,
                           -8.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(None,
                           Gtk.ConstraintAttribute.TOP,
                           Gtk.ConstraintRelation.EQ,
                           self.button1,
                           Gtk.ConstraintAttribute.TOP,
                           1.0,
                           -8.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(None,
                           Gtk.ConstraintAttribute.TOP,
                           Gtk.ConstraintRelation.EQ,
                           self.button2,
                           Gtk.ConstraintAttribute.TOP,
                           1.0,
                           -8.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button1,
                           Gtk.ConstraintAttribute.BOTTOM,
                           Gtk.ConstraintRelation.EQ,
                           self.button3,
                           Gtk.ConstraintAttribute.TOP,
                           1.0,
                           -12.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button2,
                           Gtk.ConstraintAttribute.BOTTOM,
                           Gtk.ConstraintRelation.EQ,
                           self.button3,
                           Gtk.ConstraintAttribute.TOP,
                           1.0,
                           -12.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button3,
                           Gtk.ConstraintAttribute.HEIGHT,
                           Gtk.ConstraintRelation.EQ,
                           self.button1,
                           Gtk.ConstraintAttribute.HEIGHT,
                           1.0,
                           0.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button3,
                           Gtk.ConstraintAttribute.HEIGHT,
                           Gtk.ConstraintRelation.EQ,
                           self.button2,
                           Gtk.ConstraintAttribute.HEIGHT,
                           1.0,
                           0.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button3,
                           Gtk.ConstraintAttribute.BOTTOM,
                           Gtk.ConstraintRelation.EQ,
                           None,
                           Gtk.ConstraintAttribute.BOTTOM,
                           1.0,
                           -8.0,
                           Gtk.ConstraintStrength.REQUIRED))


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()
    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Simple Constraints")
        window.set_default_size(260, -1)
        window_ref = window.weak_ref()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        window.set_child(box)

        grid = SimpleGrid()
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        box.append(grid)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
