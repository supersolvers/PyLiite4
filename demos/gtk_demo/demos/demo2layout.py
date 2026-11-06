"""A layout manager that places children on a sphere, for the layout manager transformation demo."""

import math

from PyLiite4 import Graphene, Gsk, Gtk

from .four_point_transform import perspective_3d


def RADIANS(angle: float) -> float:
    return angle * math.pi / 180.0


# Spherical coordinates
def SX(r: float, t: float, p: float) -> float:
    return r * math.sin(t) * math.cos(p)


def SZ(r: float, t: float, p: float) -> float:
    return r * math.sin(t) * math.sin(p)


def SY(r: float, t: float, p: float) -> float:
    return r * math.cos(t)


def map_offset(x: float) -> float:
    x = math.fmod(x, 180.0)
    if x < 0.0:
        x += 180.0

    return x


class Demo2Layout(Gtk.LayoutManager):
    __gtype_name__ = "Demo2Layout"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        self.position = 0.0
        self.offset = 0.0

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

        return minimum_size, 3 * natural_size, -1, -1

    def do_allocate(self, widget: Gtk.Widget, width: int, height: int, baseline: int) -> None:
        position = self.position
        offset = self.offset

        # For simplicity, all children are assumed to be the same size.
        _, child_req = widget.get_first_child().get_preferred_size()
        w = child_req.width
        h = child_req.height

        r = 300
        x0 = y0 = 300

        child = widget.get_first_child()
        i = 0
        while child is not None:
            j = i // 36
            k = i % 36

            child.set_child_visible(False)

            p1 = Graphene.Point3D().init(w, h, 1.)
            p2 = Graphene.Point3D().init(w, 0., 1.)
            p3 = Graphene.Point3D().init(0., 0., 1.)
            p4 = Graphene.Point3D().init(0., h, 1.)

            t_1 = RADIANS(map_offset(offset + 10 * j))
            t_2 = RADIANS(map_offset(offset + 10 * (j + 1)))
            p_1 = RADIANS(position + 10 * k)
            p_2 = RADIANS(position + 10 * (k + 1))

            if t_2 >= t_1 and not (SZ(r, t_1, p_1) > 0 or SZ(r, t_2, p_1) > 0
                                   or SZ(r, t_1, p_2) > 0 or SZ(r, t_2, p_2) > 0):
                child.set_child_visible(True)

                q1 = Graphene.Point3D().init(x0 + SX(r, t_1, p_1), y0 + SY(r, t_1, p_1), SZ(r, t_1, p_1))
                q2 = Graphene.Point3D().init(x0 + SX(r, t_2, p_1), y0 + SY(r, t_2, p_1), SZ(r, t_2, p_1))
                q3 = Graphene.Point3D().init(x0 + SX(r, t_2, p_2), y0 + SY(r, t_2, p_2), SZ(r, t_2, p_2))
                q4 = Graphene.Point3D().init(x0 + SX(r, t_1, p_2), y0 + SY(r, t_1, p_2), SZ(r, t_1, p_2))

                # A matrix that moves p1 -> q1, p2 -> q2, ...
                m = perspective_3d(p1, p2, p3, p4, q1, q2, q3, q4)

                transform = Gsk.Transform.new().matrix(m)

                # The matrix was built for transforming points with z = 1, so a translation to the z = 1 plane is
                # prepended.
                transform = transform.translate_3d(Graphene.Point3D().init(0, 0, 1))

                child.allocate(w, h, -1, transform)

            child = child.get_next_sibling()
            i += 1

    def do_get_request_mode(self, widget: Gtk.Widget) -> Gtk.SizeRequestMode:
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def set_position(self, position: float) -> None:
        self.position = position

    def get_position(self) -> float:
        return self.position

    def set_offset(self, offset: float) -> None:
        self.offset = offset

    def get_offset(self) -> float:
        return self.offset


def demo2_layout_new() -> Gtk.LayoutManager:
    return Demo2Layout()
