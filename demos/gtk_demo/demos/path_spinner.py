"""Path/Spinner

This demo shows how to use GskPath to draw a simple animation
that could be used as a spinner.
"""

import ctypes
import math

from PyLiite4 import Gdk, GLib, GObject, Graphene, Gsk, Gtk

# PyGObject can't allocate a GskPathPoint (its fields are in an anonymous union), so gsk_path_get_closest_point()
# fails with "Could not caller allocate argument". Call it, and gsk_path_builder_add_segment() that takes its
# result, through ctypes instead; a boxed type's hash is its C pointer.
_gtk = ctypes.CDLL("libgtk-4.so.1")


class GskPathPoint(ctypes.Structure):
    _fields_ = [("padding", ctypes.c_void_p * 8)]


class graphene_point_t(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]


_gtk.gsk_path_get_closest_point.argtypes = [ctypes.c_void_p, ctypes.POINTER(graphene_point_t), ctypes.c_float,
                                            ctypes.POINTER(GskPathPoint), ctypes.POINTER(ctypes.c_float)]
_gtk.gsk_path_get_closest_point.restype = ctypes.c_int
_gtk.gsk_path_builder_add_segment.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(GskPathPoint),
                                              ctypes.POINTER(GskPathPoint)]
_gtk.gsk_path_builder_add_segment.restype = None


def gsk_path_get_closest_point(path: Gsk.Path, point: Graphene.Point, threshold: float,
                               result: GskPathPoint) -> bool:
    return bool(_gtk.gsk_path_get_closest_point(hash(path), ctypes.byref(graphene_point_t(point.x, point.y)),
                                                threshold, ctypes.byref(result), None))


def gsk_path_builder_add_segment(builder: Gsk.PathBuilder, path: Gsk.Path, start: GskPathPoint,
                                 end: GskPathPoint) -> None:
    _gtk.gsk_path_builder_add_segment(hash(builder), hash(path), ctypes.byref(start), ctypes.byref(end))


# C has code to also draw the path's control points, disabled with #undef SHOW_CONTROLS; it isn't ported.


class GtkSpinnerPaintable(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "GtkSpinnerPaintable"

    def __init__(self) -> None:
        super().__init__()
        self.start_time = 0

        self.width = 0
        self.angle = 0.0
        self.completion = 0.0

        self.circle: Gsk.Path | None = None
        self.path: Gsk.Path | None = None
        self.stroke: Gsk.Stroke | None = None
        self.color = Gdk.RGBA()
        self.circle_color = Gdk.RGBA()

    def do_get_intrinsic_width(self) -> int:
        return self.width

    def do_get_intrinsic_height(self) -> int:
        return self.width

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        snapshot.append_stroke(self.circle, self.stroke, self.circle_color)
        snapshot.append_stroke(self.path, self.stroke, self.color)

    def do_get_flags(self) -> Gdk.PaintableFlags:
        return Gdk.PaintableFlags.STATIC_SIZE

    def update_path(self) -> None:
        start = GskPathPoint()
        end = GskPathPoint()

        start_angle = self.angle
        end_angle = math.fmod(self.angle + 360 * self.completion / 100, 360)

        p0 = Graphene.Point().init(50 + 40 * math.cos(math.pi * start_angle / 180),
                                   50 + 40 * math.sin(math.pi * start_angle / 180))
        p1 = Graphene.Point().init(50 + 40 * math.cos(math.pi * end_angle / 180),
                                   50 + 40 * math.sin(math.pi * end_angle / 180))

        self.path = None

        gsk_path_get_closest_point(self.circle, p0, math.inf, start)
        gsk_path_get_closest_point(self.circle, p1, math.inf, end)

        builder = Gsk.PathBuilder.new()
        gsk_path_builder_add_segment(builder, self.circle, start, end)
        self.path = builder.to_path()

        self.invalidate_contents()

    def set_completion(self, completion: float) -> None:
        self.completion = min(max(completion, 0), 100)
        self.update_path()

    def get_completion(self) -> float:
        return self.completion

    def set_frame_time(self, time: int) -> None:
        if self.start_time == 0:
            self.start_time = time

        delta = (time - self.start_time) / GLib.TIME_SPAN_SECOND
        self.angle = math.fmod(60 * delta, 360)
        self.update_path()


def gtk_spinner_paintable_new() -> Gdk.Paintable:
    self = GtkSpinnerPaintable()

    builder = Gsk.PathBuilder.new()
    builder.add_circle(Graphene.Point().init(50, 50), 40)
    self.circle = builder.to_path()

    self.width = 100
    self.angle = 0
    self.completion = 1
    self.color.parse("green")
    self.circle_color.parse("lightgray")
    self.stroke = Gsk.Stroke.new(5)

    return self


def tick_cb(widget: Gtk.Widget, clock: Gdk.FrameClock, data: GtkSpinnerPaintable) -> bool:
    self = data

    self.set_frame_time(clock.get_frame_time())
    return GLib.SOURCE_CONTINUE


progress_delta = 0.5


def progress_timeout(data: GtkSpinnerPaintable) -> bool:
    global progress_delta
    self = data

    progress = self.get_completion()
    if progress >= 100 or progress <= 0:
        progress_delta = -progress_delta

    self.set_completion(progress + progress_delta)

    return GLib.SOURCE_CONTINUE


def unset_timeout(data: int) -> None:
    GLib.source_remove(data)


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        window = Gtk.Window()
        window.set_resizable(True)
        window.set_title("Spinner")
        window.close_request.connect(close_request)

        paintable = gtk_spinner_paintable_new()
        picture = Gtk.Picture.new_for_paintable(paintable)
        picture.set_halign(Gtk.Align.CENTER)
        picture.set_valign(Gtk.Align.CENTER)
        picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        picture.set_can_shrink(False)

        picture.add_tick_callback(tick_cb, paintable)
        timeout_id = GLib.timeout_add(100, progress_timeout, paintable)

        # C removes the timeout with g_object_set_data_full() when the picture goes away.
        picture.weak_ref(unset_timeout, timeout_id)

        window.set_child(picture)

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
