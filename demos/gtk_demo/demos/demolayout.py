"""A layout manager that places 16 children in a grid or a circle, for the layout manager demo."""

import math
import random

from PyLiite4 import Gdk, Gtk


class DemoLayout(Gtk.LayoutManager):
    __gtype_name__ = "DemoLayout"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        self.position = 0.0
        self.pos = list(range(16))

    def do_measure(self, widget: Gtk.Widget, orientation: Gtk.Orientation,
                   for_size: int) -> tuple[int, int, int, int]:
        minimum_size = 0
        natural_size = 0

        child = widget.get_first_child()
        while child is not None:
            if child.should_layout():
                child_min, child_nat, _, _ = child.measure(orientation, -1)
                minimum_size = max(minimum_size, child_min)
                natural_size = max(natural_size, child_nat)
            child = child.get_next_sibling()

        # A back-of-a-napkin calculation, reserving enough space to arrange 16 children in a circle.
        minimum = int(16 * minimum_size / math.pi + minimum_size)
        natural = int(16 * natural_size / math.pi + natural_size)
        return minimum, natural, -1, -1

    def do_allocate(self, widget: Gtk.Widget, width: int, height: int, baseline: int) -> None:
        child_width = 0
        child_height = 0

        t = self.position

        child = widget.get_first_child()
        while child is not None:
            if child.should_layout():
                _, child_req = child.get_preferred_size()

                child_width = max(child_width, child_req.width)
                child_height = max(child_height, child_req.height)
            child = child.get_next_sibling()

        # The center of the layout.
        x0 = width // 2
        y0 = height // 2

        # The radius of the circle of children.
        r = 8 * child_width / math.pi

        child = widget.get_first_child()
        i = 0
        while child is not None:
            a = self.pos[i] * math.pi / 8

            if child.should_layout():
                _, child_req = child.get_preferred_size()

                # The grid position of child.
                gx = x0 + (i % 4 - 2) * child_width
                gy = y0 + (i // 4 - 2) * child_height

                # The circle position of child, adjusted by half the child's size to put the child's center on a
                # centered circle. This assumes the children don't use align flags or uneven margins that would shift
                # the center.
                cx = int(x0 + math.sin(a) * r - child_req.width // 2)
                cy = int(y0 + math.cos(a) * r - child_req.height // 2)

                # The two layouts are interpolated according to the position set on the layout.
                x = int(t * cx + (1 - t) * gx)
                y = int(t * cy + (1 - t) * gy)

                allocation = Gdk.Rectangle()
                allocation.x, allocation.y, allocation.width, allocation.height = x, y, child_width, child_height
                child.size_allocate(allocation, -1)

            child = child.get_next_sibling()
            i += 1

    def do_get_request_mode(self, widget: Gtk.Widget) -> Gtk.SizeRequestMode:
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def set_position(self, position: float) -> None:
        self.position = position

    def shuffle(self) -> None:
        """Shuffle the circle positions of the children.
        Should be called when we are in the grid layout.
        """
        for i in range(16):
            j = random.randrange(0, i + 1)
            self.pos[i], self.pos[j] = self.pos[j], self.pos[i]


def demo_layout_new() -> Gtk.LayoutManager:
    return DemoLayout()
