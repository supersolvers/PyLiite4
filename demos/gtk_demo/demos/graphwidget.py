"""GraphWidget, a widget drawing a wobbling curve, used by the Fishbowl demo."""

import math

from PyLiite4 import Gdk, GLib, Graphene, Gsk, Gtk


class GraphWidget(Gtk.Widget):
    __gtype_name__ = "GraphWidget"

    def __init__(self) -> None:
        super().__init__()

        self.color = Gdk.RGBA()
        self.color.red = GLib.random_double_range(0, 1)
        self.color.green = GLib.random_double_range(0, 1)
        self.color.blue = GLib.random_double_range(0, 1)
        self.color.alpha = 1

        self.period = GLib.random_double_range(0.5, 1)
        self.amplitude = GLib.random_double_range(10, 25)

        self.stroke = Gsk.Stroke.new(2)

        self.path: Gsk.Path | None = None
        self.update_path(0)

        self.start_time = 0
        self.tick_cb_id = self.add_tick_callback(self.tick_cb)

    def update_path(self, amplitude: float) -> None:
        p = [Graphene.Point() for _ in range(20)]

        for i in range(20):
            p[i].x = 10 * i
            p[i].y = 50

            if i % 4 == 1 or i % 4 == 2:
                if i % 8 < 4:
                    p[i].y += amplitude
                else:
                    p[i].y -= amplitude

        builder = Gsk.PathBuilder.new()
        builder.move_to(p[0].x, p[0].y)

        for i in range(0, 20, 4):
            builder.cubic_to(p[i + 1].x, p[i + 1].y,
                             p[i + 2].x, p[i + 2].y,
                             p[i + 3].x, p[i + 3].y)

        self.path = builder.to_path()

    def tick_cb(self, widget: Gtk.Widget, frame_clock: Gdk.FrameClock) -> bool:
        now = frame_clock.get_frame_time()

        if self.start_time == 0:
            self.start_time = now

        angle = 360 * (now - self.start_time) / (self.period * GLib.TIME_SPAN_MINUTE)
        self.update_path(math.sin(angle) * self.amplitude)

        widget.queue_draw()

        return GLib.SOURCE_CONTINUE

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        snapshot.append_stroke(self.path, self.stroke, self.color)

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        if orientation == Gtk.Orientation.HORIZONTAL:
            return 200, 200, -1, -1
        else:
            return 100, 100, -1, -1


def graph_widget_new() -> Gtk.Widget:
    return GraphWidget()
