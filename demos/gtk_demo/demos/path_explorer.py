"""PathExplorer: a widget that shows a GskPath and some of its features, used by the Path Explorer demo.

Ported from GTK Demo's path_explorer.c and path_explorer.h.
"""

import ctypes
import math

from PyLiite4 import Gdk, GLib, GObject, Graphene, Gsk, Gtk

# PyGObject can't allocate a GskPathPoint (its fields are in an anonymous union), so gsk_path_get_closest_point()
# and gsk_path_measure_get_point() fail with "Could not caller allocate argument". Call them, and the functions
# taking their result, through ctypes instead; a boxed type's hash is its C pointer.
_gtk = ctypes.CDLL("libgtk-4.so.1")


class GskPathPoint(ctypes.Structure):
    _fields_ = [("padding", ctypes.c_void_p * 8)]


class graphene_point_t(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]


_gtk.gsk_path_get_closest_point.argtypes = [ctypes.c_void_p, ctypes.POINTER(graphene_point_t), ctypes.c_float,
                                            ctypes.POINTER(GskPathPoint), ctypes.POINTER(ctypes.c_float)]
_gtk.gsk_path_get_closest_point.restype = ctypes.c_int
_gtk.gsk_path_measure_get_point.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.POINTER(GskPathPoint)]
_gtk.gsk_path_measure_get_point.restype = ctypes.c_int
_gtk.gsk_path_point_get_position.argtypes = [ctypes.POINTER(GskPathPoint), ctypes.c_void_p,
                                             ctypes.POINTER(graphene_point_t)]
_gtk.gsk_path_point_get_position.restype = None
_gtk.gsk_path_point_get_tangent.argtypes = [ctypes.POINTER(GskPathPoint), ctypes.c_void_p, ctypes.c_int,
                                            ctypes.c_void_p]
_gtk.gsk_path_point_get_tangent.restype = None
_gtk.gsk_path_point_get_curvature.argtypes = [ctypes.POINTER(GskPathPoint), ctypes.c_void_p, ctypes.c_int,
                                              ctypes.POINTER(graphene_point_t)]
_gtk.gsk_path_point_get_curvature.restype = ctypes.c_float
_gtk.gsk_path_builder_add_segment.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GskPathPoint),
                                              ctypes.POINTER(GskPathPoint)]
_gtk.gsk_path_builder_add_segment.restype = None


def gsk_path_get_closest_point(path: Gsk.Path, point: Graphene.Point, threshold: float,
                               result: GskPathPoint) -> tuple[bool, float]:
    distance = ctypes.c_float()
    found = _gtk.gsk_path_get_closest_point(hash(path), ctypes.byref(graphene_point_t(point.x, point.y)),
                                            threshold, ctypes.byref(result), ctypes.byref(distance))
    return bool(found), distance.value


def gsk_path_measure_get_point(measure: Gsk.PathMeasure, distance: float, point: GskPathPoint) -> bool:
    return bool(_gtk.gsk_path_measure_get_point(hash(measure), distance, ctypes.byref(point)))


def gsk_path_point_get_position(point: GskPathPoint, path: Gsk.Path) -> Graphene.Point:
    position = graphene_point_t()
    _gtk.gsk_path_point_get_position(ctypes.byref(point), hash(path), ctypes.byref(position))
    return Graphene.Point().init(position.x, position.y)


def gsk_path_point_get_tangent(point: GskPathPoint, path: Gsk.Path,
                               direction: Gsk.PathDirection) -> tuple[float, float]:
    # graphene_vec2_t is a 16-byte aligned SIMD value.
    buffer = (ctypes.c_float * 8)()
    address = (ctypes.addressof(buffer) + 15) & ~15
    _gtk.gsk_path_point_get_tangent(ctypes.byref(point), hash(path), int(direction), address)
    tangent = (ctypes.c_float * 2).from_address(address)
    return tangent[0], tangent[1]


def gsk_path_point_get_curvature(point: GskPathPoint, path: Gsk.Path, direction: Gsk.PathDirection,
                                 center: Graphene.Point) -> float:
    """Sets center, if the curvature isn't 0, as C does."""
    result = graphene_point_t(center.x, center.y)
    curvature = _gtk.gsk_path_point_get_curvature(ctypes.byref(point), hash(path), int(direction),
                                                  ctypes.byref(result))
    center.x, center.y = result.x, result.y
    return curvature


def gsk_path_builder_add_segment(builder: Gsk.PathBuilder, path: Gsk.Path, start: GskPathPoint,
                                 end: GskPathPoint) -> None:
    _gtk.gsk_path_builder_add_segment(hash(builder), hash(path), ctypes.byref(start), ctypes.byref(end))


def rgba(red: float, green: float, blue: float, alpha: float) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = red, green, blue, alpha
    return color


def _gsk_stroke_set_dashes(stroke: Gsk.Stroke, dashes: str | None) -> None:
    if not dashes:
        if dashes is None:
            return

    d: list[float] = []
    strings = dashes.split(",")

    for string in strings:
        string = string.strip()
        try:
            # g_ascii_strtod() parses nothing from an empty string, and leaves nothing behind.
            f = float(string) if string else 0.0
        except ValueError:
            msg = f"Failed to parse '{string}' as number"
            GLib.log_default_handler(None, GLib.LogLevelFlags.LEVEL_WARNING, f"{msg}\n")
            d = []
            break

        d.append(f)

    stroke.set_dash(d)


def motion(controller: Gtk.EventControllerMotion, x: float, y: float, self: "PathExplorer") -> None:
    self.pos.x = x
    self.pos.y = y

    self.update_closest_point()


def rounded_rect_init(x: float, y: float, w: float, h: float, cx: float, cy: float) -> Gsk.RoundedRect:
    corner = Graphene.Size().init(cx, cy)
    # GskRoundedRect isn't boxed, so what gsk_rounded_rect_init() returns doesn't keep the struct alive:
    # initialize one that is held here.
    rect = Gsk.RoundedRect()
    rect.init(Graphene.Rect().init(x, y, w, h), corner, corner, corner, corner)
    return rect


def get_initial_path() -> Gsk.Path:
    builder = Gsk.PathBuilder.new()
    builder.add_circle(Graphene.Point().init(150, 150), 100)
    builder.add_rounded_rect(rounded_rect_init(90, 90, 120, 120, 20, 20))
    builder.add_rect(Graphene.Rect().init(120, 120, 60, 60))
    builder.move_to(400, 50)
    builder.cubic_to(500, 50, 500, 150, 400, 150)
    builder.cubic_to(300, 150, 300, 250, 400, 250)
    builder.line_to(400, 350)
    builder.line_to(350, 270)

    return builder.to_path()


def draw_point(snapshot: Gtk.Snapshot, pt: Graphene.Point) -> None:
    color = rgba(1, 0, 0, 1)

    bounds = Graphene.Rect().init(pt.x - 2, pt.y - 2, 4, 4)

    snapshot.append_color(color, bounds)


def point_cb(op: Gsk.PathOperation, pts: list[Graphene.Point], n_ts: int, weight: float,
             user_data: Gtk.Snapshot) -> bool:
    snapshot = user_data

    if op == Gsk.PathOperation.MOVE:
        draw_point(snapshot, pts[0])
    elif op == Gsk.PathOperation.CLOSE:
        draw_point(snapshot, pts[0])
    elif op == Gsk.PathOperation.LINE:
        draw_point(snapshot, pts[1])
    elif op in (Gsk.PathOperation.QUAD, Gsk.PathOperation.CONIC):
        draw_point(snapshot, pts[2])
    elif op == Gsk.PathOperation.CUBIC:
        draw_point(snapshot, pts[3])
    else:
        raise AssertionError("not reached")

    return True


# C passes -1: every operation.
ALL_OPERATIONS = Gsk.PathForeachFlags.QUAD | Gsk.PathForeachFlags.CUBIC | Gsk.PathForeachFlags.CONIC


def _float_property(minimum: float, maximum: float, default: float, getter, setter) -> GObject.Property:
    return GObject.Property(type=GObject.TYPE_FLOAT, minimum=minimum, maximum=maximum, default=default,
                            getter=getter, setter=setter)


class PathExplorer(Gtk.Widget):
    __gtype_name__ = "PathExplorer"

    def __init__(self, **properties: object) -> None:
        self._path = get_initial_path()
        self.segment = self._path
        self.pos = Graphene.Point().init(0, 0)
        self._start = 0.0
        self._end = 1.0
        self.bounds = Graphene.Rect().init(0, 0, 0, 0)
        self.zoom = 1.0

        self.do_fill = False
        self.do_stroke = True

        self._fill_color = rgba(1, 1, 0, 1)
        self._stroke_color = rgba(0, 0, 0, 1)

        self._stroke = Gsk.Stroke.new(1)
        self._dashes: str | None = None
        self._fill_rule = Gsk.FillRule.WINDING

        self._show_points = False
        self._show_bounds = False

        self.point = Graphene.Point().init(0, 0)
        self.tangent1 = (0.0, 0.0)
        self.tangent2 = (0.0, 0.0)
        self.curvature = 0.0
        self.center = Graphene.Point().init(0, 0)
        self.distance = 0.0

        super().__init__(**properties)

        controller = Gtk.EventControllerMotion()
        controller.motion.connect(motion, self)
        self.add_controller(controller)

    # Properties. Unlike most, C's notify on every set, besides the explicit notifications of their setters;
    # GObject does the former here, and the setters leave out the latter.

    path = GObject.Property(type=Gsk.Path, getter=lambda self: self._path,
                            setter=lambda self, value: self.set_path(value))
    fill = GObject.Property(type=bool, default=False, getter=lambda self: self.do_fill,
                            setter=lambda self, value: self.set_fill(value))
    stroke = GObject.Property(type=bool, default=True, getter=lambda self: self.do_stroke,
                              setter=lambda self, value: self.set_stroke(value))
    line_width = _float_property(0, GLib.MAXFLOAT, 1, lambda self: self._stroke.get_line_width(),
                                 lambda self, value: self.set_line_width(value))
    line_cap = GObject.Property(type=Gsk.LineCap, default=Gsk.LineCap.BUTT,
                                getter=lambda self: self._stroke.get_line_cap(),
                                setter=lambda self, value: self.set_line_cap(value))
    line_join = GObject.Property(type=Gsk.LineJoin, default=Gsk.LineJoin.MITER,
                                 getter=lambda self: self._stroke.get_line_join(),
                                 setter=lambda self, value: self.set_line_join(value))
    miter_limit = _float_property(0, GLib.MAXFLOAT, 4, lambda self: self._stroke.get_miter_limit(),
                                  lambda self, value: self.set_miter_limit(value))
    dashes = GObject.Property(type=str, getter=lambda self: self._dashes if self._dashes else "",
                              setter=lambda self, value: self.set_dashes(value))
    dash_offset = _float_property(0, GLib.MAXFLOAT, 0, lambda self: self._stroke.get_dash_offset(),
                                  lambda self, value: self.set_dash_offset(value))
    fill_rule = GObject.Property(type=Gsk.FillRule, default=Gsk.FillRule.WINDING,
                                 getter=lambda self: self._fill_rule,
                                 setter=lambda self, value: self.set_fill_rule(value))
    show_points = GObject.Property(type=bool, default=False, getter=lambda self: self._show_points,
                                   setter=lambda self, value: self.set_show_points(value))
    show_bounds = GObject.Property(type=bool, default=False, getter=lambda self: self._show_bounds,
                                   setter=lambda self, value: self.set_show_bounds(value))
    start = _float_property(0, 1, 0, lambda self: self._start, lambda self, value: self.set_start(value))
    end = _float_property(0, 1, 1, lambda self: self._end, lambda self, value: self.set_end(value))
    fill_color = GObject.Property(type=Gdk.RGBA, getter=lambda self: self._fill_color,
                                  setter=lambda self, value: self.set_fill_color(value))
    stroke_color = GObject.Property(type=Gdk.RGBA, getter=lambda self: self._stroke_color,
                                    setter=lambda self, value: self.set_stroke_color(value))

    def update_bounds(self) -> None:
        if self.do_stroke:
            ok, self.bounds = self._path.get_stroke_bounds(self._stroke)
        else:
            ok, self.bounds = self._path.get_bounds()
        if not ok:
            self.bounds = Graphene.Rect().init(0, 0, 0, 0)

        self.queue_resize()

    def update_closest_point(self) -> None:
        point = GskPathPoint()

        _, self.distance = gsk_path_get_closest_point(self.segment, self.pos, math.inf, point)
        self.point = gsk_path_point_get_position(point, self.segment)
        self.tangent1 = gsk_path_point_get_tangent(point, self.segment, Gsk.PathDirection.TO_END)
        self.tangent2 = gsk_path_point_get_tangent(point, self.segment, Gsk.PathDirection.TO_START)
        c1 = gsk_path_point_get_curvature(point, self.segment, Gsk.PathDirection.FROM_START, self.center)
        c2 = gsk_path_point_get_curvature(point, self.segment, Gsk.PathDirection.FROM_END, self.center)

        if c1 == 0 or c2 == 0:
            self.curvature = 0
        else:
            self.curvature = (c1 + c2) / 2

        self.queue_draw()

    def update_path(self) -> None:
        start = self._start
        end = self._end

        self.segment = None

        if start > 0 or end < 1:
            start_point = GskPathPoint()
            end_point = GskPathPoint()

            measure = Gsk.PathMeasure.new(self._path)
            length = measure.get_length()
            gsk_path_measure_get_point(measure, start * length, start_point)
            gsk_path_measure_get_point(measure, end * length, end_point)
            builder = Gsk.PathBuilder.new()
            gsk_path_builder_add_segment(builder, self._path, start_point, end_point)
            self.segment = builder.to_path()
        else:
            self.segment = self._path

        self.update_closest_point()

    def set_path(self, path: Gsk.Path | None) -> None:
        # C hands gsk_path_ref() a NULL path, from text that doesn't parse, and fails a check; this ignores it.
        if path is None:
            return

        self._path = path

        self.update_path()
        self.update_bounds()

    def set_fill(self, fill: bool) -> None:
        self.do_fill = fill
        self.update_bounds()

    def set_stroke(self, stroke: bool) -> None:
        self.do_stroke = stroke
        self.update_bounds()

    def set_line_width(self, line_width: float) -> None:
        if self._stroke.get_line_width() == line_width:
            return

        self._stroke.set_line_width(line_width)
        self.update_bounds()

    def set_line_cap(self, line_cap: Gsk.LineCap) -> None:
        if self._stroke.get_line_cap() == line_cap:
            return

        self._stroke.set_line_cap(line_cap)
        self.update_bounds()

    def set_line_join(self, line_join: Gsk.LineJoin) -> None:
        if self._stroke.get_line_join() == line_join:
            return

        self._stroke.set_line_join(line_join)
        self.update_bounds()

    def set_miter_limit(self, miter_limit: float) -> None:
        if self._stroke.get_miter_limit() == miter_limit:
            return

        self._stroke.set_miter_limit(miter_limit)
        self.update_bounds()

    def set_fill_rule(self, fill_rule: Gsk.FillRule) -> None:
        if self._fill_rule == fill_rule:
            return

        self._fill_rule = fill_rule
        self.queue_draw()

    def set_show_points(self, show_points: bool) -> None:
        if self._show_points == show_points:
            return

        self._show_points = show_points
        self.queue_draw()

    def set_show_bounds(self, show_bounds: bool) -> None:
        if self._show_bounds == show_bounds:
            return

        self._show_bounds = show_bounds
        self.queue_draw()

    def set_start(self, start: float) -> None:
        if self._start == start:
            return

        self._start = start
        self.update_path()

    def set_end(self, end: float) -> None:
        if self._end == end:
            return

        self._end = end
        self.update_path()

    def set_fill_color(self, color: Gdk.RGBA) -> None:
        if self._fill_color.equal(color):
            return

        self._fill_color = color.copy()
        self.queue_draw()

    def set_stroke_color(self, color: Gdk.RGBA) -> None:
        if self._stroke_color.equal(color):
            return

        self._stroke_color = color.copy()
        self.queue_draw()

    def set_dashes(self, dashes: str | None) -> None:
        if self._dashes == dashes:
            return
        self._dashes = dashes

        _gsk_stroke_set_dashes(self._stroke, dashes)
        self.queue_draw()

    def set_dash_offset(self, dash_offset: float) -> None:
        if self._stroke.get_dash_offset() == dash_offset:
            return

        self._stroke.set_dash_offset(dash_offset)
        self.queue_draw()

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        if orientation == Gtk.Orientation.HORIZONTAL:
            size = self.zoom * (self.bounds.origin.x + self.bounds.size.width)
        else:
            size = self.zoom * (self.bounds.origin.y + self.bounds.size.height)

        return int(size), int(size), -1, -1

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        if not self._path:
            return

        width = self.get_width()
        height = self.get_width()

        snapshot.save()
        snapshot.scale(self.zoom, self.zoom)

        if self.do_fill:
            snapshot.push_fill(self.segment, self._fill_rule)
            snapshot.append_color(self._fill_color, Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()

        if self.do_stroke:
            snapshot.push_stroke(self.segment, self._stroke)
            snapshot.append_color(self._stroke_color, Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()

        if self._show_bounds:
            builder = Gsk.PathBuilder.new()
            builder.add_rect(self.bounds)
            path = builder.to_path()

            stroke = Gsk.Stroke.new(1.0)
            snapshot.push_stroke(path, stroke)

            snapshot.append_color(rgba(0, 0, 0, 0.5), Graphene.Rect().init(0, 0, width, height))

            snapshot.pop()

        if self._show_points:
            self.segment.foreach(ALL_OPERATIONS,
                                 lambda op, pts, n_ts, weight: point_cb(op, pts, n_ts, weight, snapshot))

        if self.distance < 40:
            p1 = Graphene.Point().init(self.point.x + self.tangent1[0] * 40, self.point.y + self.tangent1[1] * 40)
            p2 = Graphene.Point().init(self.point.x + self.tangent2[0] * 40, self.point.y + self.tangent2[1] * 40)

            builder = Gsk.PathBuilder.new()

            builder.move_to(p1.x, p1.y)
            builder.line_to(self.point.x, self.point.y)
            builder.line_to(p2.x, p2.y)

            path = builder.to_path()

            stroke = Gsk.Stroke.new(1.0)
            snapshot.push_stroke(path, stroke)

            snapshot.append_color(rgba(0, 0, 0, 1), Graphene.Rect().init(0, 0, width, height))

            snapshot.pop()

            builder = Gsk.PathBuilder.new()

            builder.add_circle(self.point, 5)
            builder.add_circle(p1, 2.5)
            builder.add_circle(p2, 2.5)

            path = builder.to_path()

            snapshot.push_fill(path, Gsk.FillRule.WINDING)
            snapshot.append_color(rgba(1, 0, 0, 1), Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()

            stroke = Gsk.Stroke.new(1.0)
            snapshot.push_stroke(path, stroke)

            snapshot.append_color(rgba(0, 0, 0, 1), Graphene.Rect().init(0, 0, width, height))

            snapshot.pop()

            if self.curvature != 0:
                builder = Gsk.PathBuilder.new()
                builder.add_circle(self.center, abs(1 / self.curvature))
                builder.add_circle(self.center, 3)

                path = builder.to_path()

                stroke = Gsk.Stroke.new(1.0)
                snapshot.push_stroke(path, stroke)

                snapshot.append_color(rgba(1, 0, 1, 1), Graphene.Rect().init(0, 0, width, height))

                snapshot.pop()

        snapshot.restore()


def path_explorer_new() -> Gtk.Widget:
    return PathExplorer()
