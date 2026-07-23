"""Path/Sweep

This demo shows how path intersections can be used.

The world map that is used here is a path with 211 lines and 1569 cubic
Bėzier segments in 121 contours.
"""

import math

from PyLiite4 import Gdk, Gio, GObject, Graphene, Gsk, Gtk

POINT_SIZE = 8


def rgba(red: float, green: float, blue: float, alpha: float) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = red, green, blue, alpha
    return color


def intersection_cb(path1: Gsk.Path, point1: Gsk.PathPoint, path2: Gsk.Path, point2: Gsk.PathPoint,
                    kind: Gsk.PathIntersection, data: Gsk.PathBuilder) -> bool:
    builder = data

    p = point1.get_position(path1)
    builder.add_circle(p, 4)

    return True


def get_intersection_path(path1: Gsk.Path, path2: Gsk.Path) -> Gsk.Path:
    builder = Gsk.PathBuilder.new()

    path1.foreach_intersection(path2, intersection_cb, builder)

    return builder.to_path()


class GtkPathSweep(Gtk.Widget):
    __gtype_name__ = "GtkPathSweep"

    def __init__(self, **properties: object) -> None:
        self._path: Gsk.Path | None = None
        self.bounds = Graphene.Rect().init(0, 0, 0, 0)
        self.y_pos = 0.0
        self.in_ = False

        super().__init__(**properties)

        # Data taken from
        # https://commons.wikimedia.org/wiki/Maps_of_the_world#/media/File:Simplified_blank_world_map_without_Antartica_(no_borders).svg
        data = Gio.resources_lookup_data("/path_sweep/path_world.txt", Gio.ResourceLookupFlags.NONE)
        path = Gsk.Path.parse(data.get_data().decode())
        self.set_path(path)

        controller = Gtk.EventControllerMotion()
        controller.motion.connect(motion_cb, self)
        controller.enter.connect(enter_cb, self)
        controller.leave.connect(leave_cb, self)
        self.add_controller(controller)

    @GObject.Property(type=Gsk.Path, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.EXPLICIT_NOTIFY)
    def path(self) -> Gsk.Path | None:
        return self._path

    @path.setter
    def path(self, value: Gsk.Path | None) -> None:
        self.set_path(value)

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        if self._path is None:
            return

        snapshot.save()

        stroke = Gsk.Stroke.new(2.0)

        snapshot.append_stroke(self._path, stroke, rgba(0, 0, 0, 1))

        if self.in_:
            _, bounds = self._path.get_stroke_bounds(stroke)

            builder = Gsk.PathBuilder.new()
            builder.move_to(bounds.origin.x, bounds.origin.y + self.y_pos)
            builder.line_to(bounds.origin.x + bounds.size.width, bounds.origin.y + self.y_pos)
            line = builder.to_path()

            snapshot.append_stroke(line, stroke, rgba(0, 0, 0, 1))

            isecs = get_intersection_path(self._path, line)

            snapshot.append_fill(isecs, Gsk.FillRule.WINDING, rgba(1, 0, 0, 1))
            snapshot.append_stroke(isecs, stroke, rgba(0, 0, 0, 1))

        snapshot.restore()

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        if orientation == Gtk.Orientation.HORIZONTAL:
            size = math.ceil(self.bounds.size.width)
        else:
            size = math.ceil(self.bounds.size.height)
        return size, size, -1, -1

    def set_path(self, path: Gsk.Path | None) -> None:
        if self._path == path:
            return

        self._path = None
        self.bounds = Graphene.Rect().init(0, 0, 0, 0)
        if path:
            self._path = path
            stroke = Gsk.Stroke.new(2.0)
            _, self.bounds = path.get_stroke_bounds(stroke)

        self.queue_resize()

        self.notify("path")


def motion_cb(controller: Gtk.EventControllerMotion, x: float, y: float, data: GtkPathSweep) -> None:
    self = data

    self.y_pos = y
    self.queue_draw()


def enter_cb(controller: Gtk.EventControllerMotion, x: float, y: float, data: GtkPathSweep) -> None:
    self = data

    self.in_ = True
    self.y_pos = y
    self.queue_draw()


def leave_cb(controller: Gtk.EventControllerMotion, data: GtkPathSweep) -> None:
    self = data

    self.in_ = False
    self.queue_draw()


def gtk_path_sweep_new() -> Gtk.Widget:
    return GtkPathSweep()


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        builder = Gtk.Builder.new_from_resource("/path_sweep/path_sweep.ui")
        window = builder.get_object("window")
        window.set_display(do_widget.get_display())
        window.close_request.connect(close_request)

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
