"""Path/Text

This demo shows how to use GskPath to transform a path along another path.

It also demonstrates that paths can be filled with more interesting
content than just plain colors.
"""

import ctypes
import math
from dataclasses import dataclass

from PyLiite4 import Gdk, GObject, Graphene, Gsk, Gtk, Pango

# PyGObject can't allocate a GskPathPoint (its fields are in an anonymous union), so gsk_path_measure_get_point()
# and gsk_path_get_closest_point() fail with "Could not caller allocate argument". Call them, and the functions
# reading their result, through ctypes instead; a boxed type's hash is its C pointer.
_gtk = ctypes.CDLL("libgtk-4.so.1")


class GskPathPoint(ctypes.Structure):
    _fields_ = [("padding", ctypes.c_void_p * 8)]


class graphene_point_t(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]


_gtk.gsk_path_measure_get_point.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.POINTER(GskPathPoint)]
_gtk.gsk_path_measure_get_point.restype = ctypes.c_int
_gtk.gsk_path_get_closest_point.argtypes = [ctypes.c_void_p, ctypes.POINTER(graphene_point_t), ctypes.c_float,
                                            ctypes.POINTER(GskPathPoint), ctypes.POINTER(ctypes.c_float)]
_gtk.gsk_path_get_closest_point.restype = ctypes.c_int
_gtk.gsk_path_point_get_position.argtypes = [ctypes.POINTER(GskPathPoint), ctypes.c_void_p,
                                             ctypes.POINTER(graphene_point_t)]
_gtk.gsk_path_point_get_position.restype = None
_gtk.gsk_path_point_get_tangent.argtypes = [ctypes.POINTER(GskPathPoint), ctypes.c_void_p, ctypes.c_int,
                                            ctypes.c_void_p]
_gtk.gsk_path_point_get_tangent.restype = None


def gsk_path_measure_get_point(measure: Gsk.PathMeasure, distance: float, point: GskPathPoint) -> bool:
    return bool(_gtk.gsk_path_measure_get_point(hash(measure), distance, ctypes.byref(point)))


def gsk_path_get_closest_point(path: Gsk.Path, point: Graphene.Point, threshold: float,
                               result: GskPathPoint) -> bool:
    return bool(_gtk.gsk_path_get_closest_point(hash(path), ctypes.byref(graphene_point_t(point.x, point.y)),
                                                threshold, ctypes.byref(result), None))


def gsk_path_point_get_position(point: GskPathPoint, path: Gsk.Path) -> Graphene.Point:
    position = graphene_point_t()
    _gtk.gsk_path_point_get_position(ctypes.byref(point), hash(path), ctypes.byref(position))
    return Graphene.Point().init(position.x, position.y)


def gsk_path_point_get_tangent(point: GskPathPoint, path: Gsk.Path,
                               direction: Gsk.PathDirection) -> tuple[float, float]:
    # graphene_vec2_t is a 16-byte aligned SIMD value
    buffer = (ctypes.c_float * 8)()
    address = (ctypes.addressof(buffer) + 15) & ~15
    _gtk.gsk_path_point_get_tangent(ctypes.byref(point), hash(path), int(direction), address)
    tangent = (ctypes.c_float * 2).from_address(address)
    return tangent[0], tangent[1]


POINT_SIZE = 8


def rgba(red: float, green: float, blue: float, alpha: float) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = red, green, blue, alpha
    return color


def create_path_from_text(widget: Gtk.Widget, text: str) -> tuple[Gsk.Path, Graphene.Point]:
    """Returns the path, and C's out_offset."""
    layout = widget.create_pango_layout(text)
    desc = Pango.FontDescription.from_string("sans bold 36")
    layout.set_font_description(desc)

    builder = Gsk.PathBuilder.new()
    builder.add_layout(layout)
    result = builder.to_path()

    out_offset = Graphene.Point().init(0, - layout.get_baseline() / Pango.SCALE)

    return result, out_offset


@dataclass
class GtkPathTransform:
    measure: Gsk.PathMeasure
    builder: Gsk.PathBuilder
    offset: Graphene.Point
    scale: float


def gtk_path_transform_point(measure: Gsk.PathMeasure, pt: Graphene.Point, offset: Graphene.Point,
                             scale: float) -> Graphene.Point:
    point = GskPathPoint()
    res = Graphene.Point().init(0, 0)

    if gsk_path_measure_get_point(measure, (pt.x + offset.x) * scale, point):
        path = measure.get_path()

        res = gsk_path_point_get_position(point, path)
        tangent_x, tangent_y = gsk_path_point_get_tangent(point, path, Gsk.PathDirection.TO_END)

        res.x -= (pt.y + offset.y) * scale * tangent_y
        res.y += (pt.y + offset.y) * scale * tangent_x

    return res


def gtk_path_transform_op(op: Gsk.PathOperation, pts: list[Graphene.Point], n_pts: int, weight: float,
                          data: GtkPathTransform) -> bool:
    transform = data

    if op == Gsk.PathOperation.MOVE:
        res = gtk_path_transform_point(transform.measure, pts[0], transform.offset, transform.scale)
        transform.builder.move_to(res.x, res.y)
    elif op == Gsk.PathOperation.LINE:
        res = gtk_path_transform_point(transform.measure, pts[1], transform.offset, transform.scale)
        transform.builder.line_to(res.x, res.y)
    elif op == Gsk.PathOperation.QUAD:
        res = [gtk_path_transform_point(transform.measure, pts[1], transform.offset, transform.scale),
               gtk_path_transform_point(transform.measure, pts[2], transform.offset, transform.scale)]
        transform.builder.quad_to(res[0].x, res[0].y, res[1].x, res[1].y)
    elif op == Gsk.PathOperation.CUBIC:
        res = [gtk_path_transform_point(transform.measure, pts[1], transform.offset, transform.scale),
               gtk_path_transform_point(transform.measure, pts[2], transform.offset, transform.scale),
               gtk_path_transform_point(transform.measure, pts[3], transform.offset, transform.scale)]
        transform.builder.cubic_to(res[0].x, res[0].y, res[1].x, res[1].y, res[2].x, res[2].y)
    elif op == Gsk.PathOperation.CONIC:
        res = [gtk_path_transform_point(transform.measure, pts[1], transform.offset, transform.scale),
               gtk_path_transform_point(transform.measure, pts[3], transform.offset, transform.scale)]
        transform.builder.conic_to(res[0].x, res[0].y, res[1].x, res[1].y, weight)
    elif op == Gsk.PathOperation.CLOSE:
        transform.builder.close()
    else:
        raise AssertionError("not reached")

    return True


# C passes -1: every operation
ALL_OPERATIONS = Gsk.PathForeachFlags.QUAD | Gsk.PathForeachFlags.CUBIC | Gsk.PathForeachFlags.CONIC


def gtk_path_transform(line_path: Gsk.Path, path: Gsk.Path, offset: Graphene.Point) -> Gsk.Path | None:
    ok, bounds = path.get_bounds()
    if not ok:
        return None

    transform = GtkPathTransform(Gsk.PathMeasure.new(line_path), Gsk.PathBuilder.new(), offset, 1.0)

    if bounds.origin.x + bounds.size.width > 0:
        transform.scale = transform.measure.get_length() / (bounds.origin.x + bounds.size.width)
    else:
        transform.scale = 1.0

    path.foreach(ALL_OPERATIONS, lambda op, pts, n_pts, weight: gtk_path_transform_op(op, pts, n_pts, weight,
                                                                                         transform))

    return transform.builder.to_path()


_PROPERTY_FLAGS = GObject.ParamFlags.READWRITE | GObject.ParamFlags.EXPLICIT_NOTIFY


class GtkPathWidget(Gtk.Widget):
    __gtype_name__ = "GtkPathWidget"

    def __init__(self, **properties: object) -> None:
        self._text: str | None = None
        self._editable = False

        self.points = [Graphene.Point().init(0, 0) for _ in range(4)]

        self.active_point = 0

        self.line_path: Gsk.Path | None = None
        self.text_path: Gsk.Path | None = None

        self.background: Gdk.Paintable | None = None

        super().__init__(**properties)

        controller = Gtk.GestureDrag()
        controller.drag_begin.connect(drag_begin, self)
        controller.drag_update.connect(drag_update, self)
        controller.drag_end.connect(drag_update, self)
        self.add_controller(controller)

        controller = Gtk.EventControllerMotion()
        controller.enter.connect(pointer_motion, self)
        controller.motion.connect(pointer_motion, self)
        controller.leave.connect(pointer_leave, self)
        self.add_controller(controller)

        self.points[0] = Graphene.Point().init(0.1, 0.9)
        self.points[1] = Graphene.Point().init(0.3, 0.1)
        self.points[2] = Graphene.Point().init(0.7, 0.1)
        self.points[3] = Graphene.Point().init(0.9, 0.9)

        self.background = Gdk.Texture.new_from_resource("/sliding_puzzle/portland-rose.jpg")

        self.set_text("It's almost working")

    @GObject.Property(type=str, nick="text", blurb="Text transformed along a path", flags=_PROPERTY_FLAGS)
    def text(self) -> str | None:
        return self._text

    @text.setter
    def text(self, value: str | None) -> None:
        self.set_text(value)

    @GObject.Property(type=bool, default=False, nick="editable", blurb="If the path can be edited by the user",
                      flags=_PROPERTY_FLAGS)
    def editable(self) -> bool:
        return self._editable

    @editable.setter
    def editable(self, value: bool) -> None:
        self.set_editable(value)

    def clear_text_path(self) -> None:
        self.text_path = None

    def clear_paths(self) -> None:
        self.clear_text_path()

        self.line_path = None

    def create_text_path(self) -> None:
        self.clear_text_path()

        path, offset = create_path_from_text(self, self._text)
        self.text_path = gtk_path_transform(self.line_path, path, offset)

    def create_paths(self) -> None:
        width = self.get_width()
        height = self.get_height()

        self.clear_paths()

        if width <= 0 or height <= 0:
            return

        builder = Gsk.PathBuilder.new()
        builder.move_to(self.points[0].x * width, self.points[0].y * height)
        builder.cubic_to(self.points[1].x * width, self.points[1].y * height,
                         self.points[2].x * width, self.points[2].y * height,
                         self.points[3].x * width, self.points[3].y * height)
        self.line_path = builder.to_path()

        self.create_text_path()

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        Gtk.Widget.do_size_allocate(self, width, height, baseline)

        self.create_paths()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        # frosted glass the background
        snapshot.push_blur(100)
        self.background.snapshot(snapshot, width, height)
        snapshot.append_color(rgba(1, 1, 1, 0.6), Graphene.Rect().init(0, 0, width, height))
        snapshot.pop()

        # draw the text
        if self.text_path:
            snapshot.push_fill(self.text_path, Gsk.FillRule.WINDING)
            self.background.snapshot(snapshot, width, height)

            # ... with an emboss effect
            stroke = Gsk.Stroke.new(2.0)
            snapshot.translate(Graphene.Point().init(1, 1))
            snapshot.push_stroke(self.text_path, stroke)
            snapshot.append_color(rgba(0, 0, 0, 0.2), Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()

            snapshot.pop()

        if self._editable and self.line_path:
            # draw the control line
            stroke = Gsk.Stroke.new(1.0)
            snapshot.push_stroke(self.line_path, stroke)
            snapshot.append_color(rgba(0, 0, 0, 1), Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()

            # draw the points
            builder = Gsk.PathBuilder.new()
            for i in range(4):
                builder.add_circle(Graphene.Point().init(self.points[i].x * width, self.points[i].y * height),
                                   POINT_SIZE)
            path = builder.to_path()

            snapshot.push_fill(path, Gsk.FillRule.WINDING)
            snapshot.append_color(rgba(1, 1, 1, 1), Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()

            stroke = Gsk.Stroke.new(1.0)
            snapshot.push_stroke(path, stroke)
            snapshot.append_color(rgba(0, 0, 0, 1), Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()

    def set_text(self, text: str | None) -> None:
        if self._text == text:
            return

        self._text = text

        self.create_paths()

        self.queue_draw()

        self.notify("text")

    def set_editable(self, editable: bool) -> None:
        if self._editable == editable:
            return

        self._editable = editable

        self.queue_draw()

        self.notify("editable")


def drag_begin(gesture: Gtk.GestureDrag, x: float, y: float, self: GtkPathWidget) -> None:
    mouse = Graphene.Point().init(x, y)
    width = self.get_width()
    height = self.get_height()

    for i in range(4):
        point = Graphene.Point().init(self.points[i].x * width, self.points[i].y * height)
        if point.distance(mouse)[0] <= POINT_SIZE:
            self.active_point = i
            break
    else:
        gesture.set_state(Gtk.EventSequenceState.DENIED)
        return

    self.queue_draw()


def drag_update(drag: Gtk.GestureDrag, offset_x: float, offset_y: float, self: GtkPathWidget) -> None:
    width = self.get_width()
    height = self.get_height()

    _, start_x, start_y = drag.get_start_point()

    self.points[self.active_point] = Graphene.Point().init((start_x + offset_x) / width,
                                                           (start_y + offset_y) / height)
    self.points[self.active_point].x = min(max(self.points[self.active_point].x, 0), 1)
    self.points[self.active_point].y = min(max(self.points[self.active_point].y, 0), 1)

    self.create_paths()

    self.queue_draw()


def pointer_motion(controller: Gtk.EventControllerMotion, x: float, y: float, self: GtkPathWidget) -> None:
    point = GskPathPoint()

    if gsk_path_get_closest_point(self.line_path, Graphene.Point().init(x, y), math.inf, point):
        self.queue_draw()


def pointer_leave(controller: Gtk.EventControllerMotion, self: GtkPathWidget) -> None:
    self.queue_draw()


def gtk_path_widget_new() -> Gtk.Widget:
    return GtkPathWidget()


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        builder = Gtk.Builder.new_from_resource("/path_text/path_text.ui")
        window = builder.get_object("window")
        window.set_display(do_widget.get_display())
        window.close_request.connect(close_request)

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
