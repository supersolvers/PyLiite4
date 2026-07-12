"""Constraints/Interactive Constraints
#Keywords: GtkConstraintLayout

This example shows how constraints can be updated during user interaction.
The vertical edge between the buttons can be dragged with the mouse.
"""

from collections.abc import Callable

from PyLiite4 import Gtk


class InteractiveGrid(Gtk.Widget):
    __gtype_name__ = "InteractiveGrid"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)

        self.guide: Gtk.ConstraintGuide | None = None
        self.constraint: Gtk.Constraint | None = None

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

        drag = Gtk.GestureDrag()
        drag.drag_update.connect(drag_cb, self)
        self.add_controller(drag)

    def do_dispose(self) -> None:
        for name in ("button1", "button2", "button3"):
            button = getattr(self, name, None)
            if button is not None:
                button.unparent()
                setattr(self, name, None)

        Gtk.Widget.do_dispose(self)


InteractiveGrid.set_layout_manager_type(Gtk.ConstraintLayout)


def build_constraints(self: InteractiveGrid, manager: Gtk.ConstraintLayout) -> None:
    self.guide = Gtk.ConstraintGuide()
    manager.add_guide(self.guide)

    manager.add_constraint(
        Gtk.Constraint.new_constant(self.guide,
                                    Gtk.ConstraintAttribute.WIDTH,
                                    Gtk.ConstraintRelation.EQ,
                                    0.0,
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
                           Gtk.ConstraintAttribute.END,
                           Gtk.ConstraintRelation.EQ,
                           self.guide,
                           Gtk.ConstraintAttribute.START,
                           1.0,
                           0.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button2,
                           Gtk.ConstraintAttribute.START,
                           Gtk.ConstraintRelation.EQ,
                           self.guide,
                           Gtk.ConstraintAttribute.END,
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
                           self.guide,
                           Gtk.ConstraintAttribute.START,
                           1.0,
                           0.0,
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
        Gtk.Constraint.new(self.button2,
                           Gtk.ConstraintAttribute.TOP,
                           Gtk.ConstraintRelation.EQ,
                           self.button1,
                           Gtk.ConstraintAttribute.BOTTOM,
                           1.0,
                           0.0,
                           Gtk.ConstraintStrength.REQUIRED))
    manager.add_constraint(
        Gtk.Constraint.new(self.button3,
                           Gtk.ConstraintAttribute.TOP,
                           Gtk.ConstraintRelation.EQ,
                           self.button2,
                           Gtk.ConstraintAttribute.BOTTOM,
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


def drag_cb(drag: Gtk.GestureDrag, offset_x: float, offset_y: float, self: InteractiveGrid) -> None:
    layout = self.get_layout_manager()

    if self.constraint:
        layout.remove_constraint(self.constraint)
        self.constraint = None

    _ok, x, y = drag.get_start_point()
    self.constraint = Gtk.Constraint.new_constant(self.guide,
                                                  Gtk.ConstraintAttribute.LEFT,
                                                  Gtk.ConstraintRelation.EQ,
                                                  x + offset_x,
                                                  Gtk.ConstraintStrength.REQUIRED)
    layout.add_constraint(self.constraint)
    self.queue_allocate()


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()
    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Interactive Constraints")
        window.set_default_size(260, -1)
        window_ref = window.weak_ref()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        window.set_child(box)

        grid = InteractiveGrid()
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        box.append(grid)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
