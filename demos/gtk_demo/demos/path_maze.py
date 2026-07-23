"""Path/Maze

This demo shows how to use a GskPath to create a maze and use
gsk_path_get_closest_point() to check the mouse stays
on the path.

It also shows off the performance of GskPath (or not) as this
is a rather complex path.
"""

import ctypes
import math
import os
import random

from PyLiite4 import Gdk, GLib, Graphene, Gsk, Gtk

from .paintable_mediastream import gtk_nuclear_media_stream_new

# PyGObject can't allocate a GskPathPoint (its fields are in an anonymous union), so gsk_path_get_closest_point()
# fails with "Could not caller allocate argument". Call it through ctypes instead; a boxed type's hash is its C
# pointer.
_gtk = ctypes.CDLL("libgtk-4.so.1")


class GskPathPoint(ctypes.Structure):
    _fields_ = [("padding", ctypes.c_void_p * 8)]


class graphene_point_t(ctypes.Structure):
    _fields_ = [("x", ctypes.c_float), ("y", ctypes.c_float)]


_gtk.gsk_path_get_closest_point.argtypes = [ctypes.c_void_p, ctypes.POINTER(graphene_point_t), ctypes.c_float,
                                            ctypes.POINTER(GskPathPoint), ctypes.POINTER(ctypes.c_float)]
_gtk.gsk_path_get_closest_point.restype = ctypes.c_int


def gsk_path_get_closest_point(path: Gsk.Path, point: Graphene.Point,
                               threshold: float) -> tuple[bool, GskPathPoint, float]:
    result = GskPathPoint()
    distance = ctypes.c_float()
    found = _gtk.gsk_path_get_closest_point(hash(path), ctypes.byref(graphene_point_t(point.x, point.y)), threshold,
                                            ctypes.byref(result), ctypes.byref(distance))
    return bool(found), result, distance.value


MAZE_GRID_SIZE = 20
MAZE_STROKE_SIZE_ACTIVE = MAZE_GRID_SIZE - 4
MAZE_STROKE_SIZE_INACTIVE = MAZE_GRID_SIZE - 12
MAZE_WIDTH = 31
MAZE_HEIGHT = 21


def color_stop(offset: float, red: float, green: float, blue: float, alpha: float) -> Gsk.ColorStop:
    stop = Gsk.ColorStop()
    stop.offset = offset
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = red, green, blue, alpha
    stop.color = color
    return stop


class GtkMaze(Gtk.Widget):
    __gtype_name__ = "GtkMaze"

    def __init__(self) -> None:
        super().__init__()
        self.width = 0
        self.height = 0
        self.path: Gsk.Path | None = None
        self.measure: Gsk.PathMeasure | None = None
        self.background: Gdk.Paintable | None = None

        controller = Gtk.EventControllerMotion()
        controller.motion.connect(pointer_motion, self)
        controller.leave.connect(pointer_leave, self)
        self.add_controller(controller)

        self.active = True

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        if orientation == Gtk.Orientation.HORIZONTAL:
            return self.width, self.width, -1, -1
        else:
            return self.height, self.height, -1, -1

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        stroke = Gsk.Stroke.new(MAZE_STROKE_SIZE_INACTIVE)
        if self.active:
            stroke.set_line_width(MAZE_STROKE_SIZE_ACTIVE)
        stroke.set_line_join(Gsk.LineJoin.ROUND)
        stroke.set_line_cap(Gsk.LineCap.ROUND)
        snapshot.push_stroke(self.path, stroke)

        if self.background:
            self.background.snapshot(snapshot, width, height)
        else:
            snapshot.append_linear_gradient(Graphene.Rect().init(0, 0, width, height),
                                            Graphene.Point().init(0, 0),
                                            Graphene.Point().init(width, height),
                                            [
                                                color_stop(0.0, 1.0, 0.0, 0.0, 1.0),
                                                color_stop(0.2, 1.0, 0.0, 0.0, 1.0),
                                                color_stop(0.3, 1.0, 1.0, 0.0, 1.0),
                                                color_stop(0.4, 0.0, 1.0, 0.0, 1.0),
                                                color_stop(0.6, 0.0, 1.0, 1.0, 1.0),
                                                color_stop(0.7, 0.0, 0.0, 1.0, 1.0),
                                                color_stop(0.8, 1.0, 0.0, 1.0, 1.0),
                                                color_stop(1.0, 1.0, 0.0, 1.0, 1.0),
                                            ])

        snapshot.pop()

    def set_path(self, path: Gsk.Path) -> None:
        self.path = path
        self.measure = Gsk.PathMeasure.new(path)

        self.queue_draw()

    # C connects gtk_widget_queue_draw() and gtk_widget_queue_resize() swapped, and disconnects them in
    # dispose; bound methods end their connections when the maze goes away.
    def background_invalidated_contents(self, background: Gdk.Paintable) -> None:
        self.queue_draw()

    def background_invalidated_size(self, background: Gdk.Paintable) -> None:
        self.queue_resize()


# GTK_DATADIR in C: the data directory GTK was installed into.
GTK_DATADIR = next((path for path in GLib.get_system_data_dirs()
                    if os.path.isdir(os.path.join(path, "sounds", "freedesktop"))), "/usr/share")

# The streams that are playing; C keeps them alive with a reference until they end.
playing_streams: set[Gtk.MediaStream] = set()


def celebrate(win: bool) -> None:
    if win:
        path = os.path.join(GTK_DATADIR, "sounds", "freedesktop", "stereo", "complete.oga")
    else:
        path = os.path.join(GTK_DATADIR, "sounds", "freedesktop", "stereo", "suspend-error.oga")
    stream = Gtk.MediaFile.new_for_filename(path)
    stream.set_volume(1.0)
    stream.play()

    playing_streams.add(stream)
    stream.notify["ended"].connect(lambda stream, _pspec: playing_streams.discard(stream))


def pointer_motion(controller: Gtk.EventControllerMotion, x: float, y: float, self: GtkMaze) -> None:
    if not self.active:
        return

    found, point, distance = gsk_path_get_closest_point(self.path, Graphene.Point().init(x, y), math.inf)
    if found:
        if distance < MAZE_STROKE_SIZE_ACTIVE / 2:
            return

    celebrate(False)

    self.active = False
    self.queue_draw()


def pointer_leave(controller: Gtk.EventControllerMotion, self: GtkMaze) -> None:
    if not self.active:
        self.active = True
        self.queue_draw()


def gtk_maze_new(path: Gsk.Path, background: Gdk.Paintable | None, width: int, height: int) -> Gtk.Widget:
    self = GtkMaze()

    self.set_path(path)
    self.background = background
    if self.background:
        self.background.invalidate_contents.connect(self.background_invalidated_contents)
        self.background.invalidate_size.connect(self.background_invalidated_size)
    self.width = width
    self.height = height

    return self


def add_point_to_maze(maze: Gtk.Bitset, builder: Gsk.PathBuilder, x: int, y: int) -> None:
    set = [False, False, False, False]

    maze.add(y * MAZE_WIDTH + x)

    while True:
        set[0] = set[0] or x == 0 or maze.contains(y * MAZE_WIDTH + x - 1)
        set[1] = set[1] or y == 0 or maze.contains((y - 1) * MAZE_WIDTH + x)
        set[2] = set[2] or x + 1 == MAZE_WIDTH or maze.contains(y * MAZE_WIDTH + x + 1)
        set[3] = set[3] or y + 1 == MAZE_HEIGHT or maze.contains((y + 1) * MAZE_WIDTH + x)

        if set[0] and set[1] and set[2] and set[3]:
            return

        dir = random.randrange(4)
        while set[dir]:
            dir = random.randrange(4)

        if dir == 0:
            builder.move_to((x + 0.5) * MAZE_GRID_SIZE, (y + 0.5) * MAZE_GRID_SIZE)
            builder.line_to((x - 0.5) * MAZE_GRID_SIZE, (y + 0.5) * MAZE_GRID_SIZE)
            add_point_to_maze(maze, builder, x - 1, y)
        elif dir == 1:
            builder.move_to((x + 0.5) * MAZE_GRID_SIZE, (y + 0.5) * MAZE_GRID_SIZE)
            builder.line_to((x + 0.5) * MAZE_GRID_SIZE, (y - 0.5) * MAZE_GRID_SIZE)
            add_point_to_maze(maze, builder, x, y - 1)
        elif dir == 2:
            builder.move_to((x + 0.5) * MAZE_GRID_SIZE, (y + 0.5) * MAZE_GRID_SIZE)
            builder.line_to((x + 1.5) * MAZE_GRID_SIZE, (y + 0.5) * MAZE_GRID_SIZE)
            add_point_to_maze(maze, builder, x + 1, y)
        elif dir == 3:
            builder.move_to((x + 0.5) * MAZE_GRID_SIZE, (y + 0.5) * MAZE_GRID_SIZE)
            builder.line_to((x + 0.5) * MAZE_GRID_SIZE, (y + 1.5) * MAZE_GRID_SIZE)
            add_point_to_maze(maze, builder, x, y + 1)
        else:
            raise AssertionError("not reached")


def create_path_for_maze(widget: Gtk.Widget) -> Gsk.Path:
    builder = Gsk.PathBuilder.new()
    maze = Gtk.Bitset.new_empty()
    # make sure the outer lines are unreachable:
    # Set the full range, then remove the center again.
    maze.add_range(0, MAZE_WIDTH * MAZE_HEIGHT)
    maze.remove_rectangle(MAZE_WIDTH + 1, MAZE_WIDTH - 2, MAZE_HEIGHT - 2, MAZE_WIDTH)

    # Fill the maze
    add_point_to_maze(maze, builder, MAZE_WIDTH // 2, MAZE_HEIGHT // 2)

    # Add start and stop lines
    builder.move_to(1.5 * MAZE_GRID_SIZE, -0.5 * MAZE_GRID_SIZE)
    builder.line_to(1.5 * MAZE_GRID_SIZE, 1.5 * MAZE_GRID_SIZE)
    builder.move_to((MAZE_WIDTH - 1.5) * MAZE_GRID_SIZE, (MAZE_HEIGHT - 1.5) * MAZE_GRID_SIZE)
    builder.line_to((MAZE_WIDTH - 1.5) * MAZE_GRID_SIZE, (MAZE_HEIGHT + 0.5) * MAZE_GRID_SIZE)

    return builder.to_path()


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
        window.set_resizable(False)
        window.set_title("Follow the maze with the mouse")
        window.close_request.connect(close_request)

        # C has the alternative, disabled with #if 0, of Gtk.MediaFile.new_for_resource("/images/gtk-logo.webm")
        stream = gtk_nuclear_media_stream_new()
        stream.play()
        stream.set_loop(True)

        path = create_path_for_maze(window)

        maze = gtk_maze_new(path, stream, MAZE_WIDTH * MAZE_GRID_SIZE, MAZE_HEIGHT * MAZE_GRID_SIZE)

        window.set_child(maze)

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
