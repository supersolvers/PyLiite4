"""Path/Walk

This demo draws a world map and shows how to animate objects along a GskPath.

The world map that is used here is a path with 211 lines and 1569 cubic
Bėzier segments in 121 contours.
"""

import ctypes
import math

from PyLiite4 import Gdk, Gio, GLib, GObject, Graphene, Gsk, Gtk

POINT_SIZE = 8

# PyGObject can't allocate a GskPathPoint (its fields are in an anonymous union), so gsk_path_measure_get_point()
# and friends fail with "Could not caller allocate argument". Call them through ctypes instead; a boxed type's hash
# is its C pointer.
_gtk = ctypes.CDLL("libgtk-4.so.1")


class GskPathPoint(ctypes.Structure):
    _fields_ = [("padding", ctypes.c_void_p * 8)]


class graphene_point_t(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]


_gtk.gsk_path_measure_get_point.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.POINTER(GskPathPoint)]
_gtk.gsk_path_measure_get_point.restype = ctypes.c_int
_gtk.gsk_path_point_get_position.argtypes = [ctypes.POINTER(GskPathPoint), ctypes.c_void_p,
                                             ctypes.POINTER(graphene_point_t)]
_gtk.gsk_path_point_get_position.restype = None
_gtk.gsk_path_point_get_rotation.argtypes = [ctypes.POINTER(GskPathPoint), ctypes.c_void_p, ctypes.c_int]
_gtk.gsk_path_point_get_rotation.restype = ctypes.c_float


def gsk_path_measure_get_point(measure: Gsk.PathMeasure, distance: float, point: GskPathPoint) -> bool:
    return bool(_gtk.gsk_path_measure_get_point(hash(measure), distance, ctypes.byref(point)))


def gsk_path_point_get_position(point: GskPathPoint, path: Gsk.Path) -> Graphene.Point:
    position = graphene_point_t()
    _gtk.gsk_path_point_get_position(ctypes.byref(point), hash(path), ctypes.byref(position))
    return Graphene.Point().init(position.x, position.y)


def gsk_path_point_get_rotation(point: GskPathPoint, path: Gsk.Path, direction: Gsk.PathDirection) -> float:
    return _gtk.gsk_path_point_get_rotation(ctypes.byref(point), hash(path), int(direction))


def rgba_init_from_hsla(hue: float, saturation: float, lightness: float, alpha: float) -> Gdk.RGBA:
    rgba = Gdk.RGBA()

    if lightness <= 0.5:
        m2 = lightness * (1 + saturation)
    else:
        m2 = lightness + saturation - lightness * saturation
    m1 = 2 * lightness - m2

    rgba.alpha = alpha

    if saturation == 0:
        rgba.red = lightness
        rgba.green = lightness
        rgba.blue = lightness
    else:
        hue = hue + 120
        while hue > 360:
            hue -= 360
        while hue < 0:
            hue += 360

        if hue < 60:
            rgba.red = m1 + (m2 - m1) * hue / 60
        elif hue < 180:
            rgba.red = m2
        elif hue < 240:
            rgba.red = m1 + (m2 - m1) * (240 - hue) / 60
        else:
            rgba.red = m1

        hue -= 120
        if hue < 0:
            hue += 360

        if hue < 60:
            rgba.green = m1 + (m2 - m1) * hue / 60
        elif hue < 180:
            rgba.green = m2
        elif hue < 240:
            rgba.green = m1 + (m2 - m1) * (240 - hue) / 60
        else:
            rgba.green = m1

        hue -= 120
        if hue < 0:
            hue += 360

        if hue < 60:
            rgba.blue = m1 + (m2 - m1) * hue / 60
        elif hue < 180:
            rgba.blue = m2
        elif hue < 240:
            rgba.blue = m1 + (m2 - m1) * (240 - hue) / 60
        else:
            rgba.blue = m1

    return rgba


class GtkPathWalk(Gtk.Widget):
    __gtype_name__ = "GtkPathWalk"

    def __init__(self, **properties) -> None:
        self._path: Gsk.Path | None = None
        self.measure: Gsk.PathMeasure | None = None
        self.bounds = Graphene.Rect().init(0, 0, 0, 0)
        self.arrow_path: Gsk.Path | None = None
        self._n_points = 500

        super().__init__(**properties)

        # The data is taken from
        # https://commons.wikimedia.org/wiki/Maps_of_the_world#/media/File:Simplified_blank_world_map_without_Antartica_(no_borders).svg
        data = Gio.resources_lookup_data("/path_walk/path_world.txt", Gio.ResourceLookupFlags.NONE)
        path = Gsk.Path.parse(data.get_data().decode())
        self.set_path(path)
        self.arrow_path = Gsk.Path.parse("M 5 0 L 0 -5. 0 -2, -5 -2, -5 2, 0 2, 0 5 Z")
        self._n_points = 500
        self.add_tick_callback(tick_tick_tick)

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        if self._path is None:
            return

        snapshot.save()

        stroke = Gsk.Stroke.new(2.0)
        snapshot.push_stroke(self._path, stroke)
        snapshot.append_color(Gdk.RGBA(red=0, green=0, blue=0, alpha=1), Graphene.Rect().init(0, 0, width, height))
        snapshot.pop()

        length = self.measure.get_length()
        progress = 25.0 * self.get_frame_clock().get_frame_time() / GLib.USEC_PER_SEC

        stroke = Gsk.Stroke.new(1.0)
        black = Gdk.RGBA(red=0, green=0, blue=0, alpha=1)
        for i in range(self._n_points):
            distance = i * length / self._n_points
            distance = math.fmod(distance + progress, length)

            point = GskPathPoint()
            gsk_path_measure_get_point(self.measure, distance, point)
            position = gsk_path_point_get_position(point, self._path)
            angle = gsk_path_point_get_rotation(point, self._path, Gsk.PathDirection.FROM_START)
            color = rgba_init_from_hsla(360.0 * i / self._n_points, 1, 0.5, 1)

            snapshot.save()
            snapshot.translate(position)
            snapshot.rotate(angle)
            snapshot.append_fill(self.arrow_path, Gsk.FillRule.EVEN_ODD, color)
            snapshot.append_stroke(self.arrow_path, stroke, black)
            snapshot.restore()

        snapshot.restore()

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        if orientation == Gtk.Orientation.HORIZONTAL:
            size = math.ceil(self.bounds.get_width())
        else:
            size = math.ceil(self.bounds.get_height())
        return size, size, -1, -1

    def set_n_points(self, n_points: int) -> None:
        if self._n_points == n_points:
            return

        self._n_points = n_points

        self.queue_draw()

        self.notify("n-points")

    def set_path(self, path: Gsk.Path | None) -> None:
        if self._path is path:
            return

        self._path = None
        self.bounds = Graphene.Rect().init(0, 0, 0, 0)
        if path is not None:
            self._path = path
            stroke = Gsk.Stroke.new(2.0)
            _, self.bounds = path.get_stroke_bounds(stroke)
            self.measure = Gsk.PathMeasure.new(self._path)

        self.queue_resize()

        self.notify("path")

    @GObject.Property(type=GObject.TYPE_UINT, minimum=1, maximum=GLib.MAXUINT32, default=500,
                      flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.EXPLICIT_NOTIFY)
    def n_points(self) -> int:
        return self._n_points

    @n_points.setter
    def n_points(self, value: int) -> None:
        self.set_n_points(value)

    @GObject.Property(type=Gsk.Path, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.EXPLICIT_NOTIFY)
    def path(self) -> Gsk.Path | None:
        return self._path

    @path.setter
    def path(self, value: Gsk.Path | None) -> None:
        self.set_path(value)


def tick_tick_tick(self: Gtk.Widget, frame_clock: Gdk.FrameClock) -> bool:
    self.queue_draw()

    return GLib.SOURCE_CONTINUE


def gtk_path_walk_new() -> GtkPathWalk:
    return GtkPathWalk()


window: Gtk.Window | None = None


def window_destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        builder = Gtk.Builder.new_from_resource("/path_walk/path_walk.ui")
        window = builder.get_object("window")
        window.set_display(do_widget.get_display())
        window.destroy.connect(window_destroyed)

    result = window
    if not result.get_visible():
        result.present()
    else:
        result.destroy()

    return result
