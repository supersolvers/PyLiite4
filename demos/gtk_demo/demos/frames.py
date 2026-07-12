"""Benchmark/Frames

This demo is intentionally as simple as possible, to see what
framerate the windowing system can deliver on its own.

It does nothing but change the drawn color, for every frame.
"""

import random

from PyLiite4 import Gdk, GLib, Graphene, Gtk

TIME_SPAN = 3.0 * GLib.TIME_SPAN_SECOND


class ColorWidget(Gtk.Widget):
    __gtype_name__ = "ColorWidget"

    def __init__(self) -> None:
        super().__init__()
        self.color1 = Gdk.RGBA()
        self.color2 = Gdk.RGBA()
        self.time2 = 0
        self.t = 0.0
        self.add_tick_callback(change_color)
        self.set_hexpand(True)
        self.set_vexpand(True)

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        w = self.get_width()
        h = self.get_height()

        c = Gdk.RGBA()
        c.red = (1 - self.t) * self.color1.red + self.t * self.color2.red
        c.green = (1 - self.t) * self.color1.green + self.t * self.color2.green
        c.blue = (1 - self.t) * self.color1.blue + self.t * self.color2.blue
        c.alpha = 1

        snapshot.append_color(c, Graphene.Rect().init(0, 0, w, h))


def change_color(widget: ColorWidget, frame_clock: Gdk.FrameClock) -> bool:
    color = widget
    time = frame_clock.get_frame_time()

    if time >= color.time2:
        color.time2 = time + TIME_SPAN

        color.color1 = color.color2
        color.color2 = Gdk.RGBA()
        color.color2.red = random.uniform(0, 1)
        color.color2.green = random.uniform(0, 1)
        color.color2.blue = random.uniform(0, 1)
        color.color2.alpha = 1

    color.t = 1 - (color.time2 - time) / TIME_SPAN

    widget.queue_draw()

    return GLib.SOURCE_CONTINUE


def color_widget_new() -> Gtk.Widget:
    return ColorWidget()


def update_fps_label(label: Gtk.Label) -> bool:
    frame_clock = label.get_frame_clock()

    if frame_clock:
        label.set_label(f"{frame_clock.get_fps():.2f} fps")
    else:
        label.set_label("")

    return GLib.SOURCE_CONTINUE


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window
    if window is None:
        builder = Gtk.Builder.new_from_resource("/frames/frames.ui")
        window = builder.get_object("window")
        window.close_request.connect(close_request)
        window.set_display(do_widget.get_display())

        label = builder.get_object("fps")
        box = builder.get_object("box")

        box.append(color_widget_new())

        source_id = GLib.timeout_add(500, update_fps_label, label)
        label.unrealize.connect(lambda label: GLib.source_remove(source_id))

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
