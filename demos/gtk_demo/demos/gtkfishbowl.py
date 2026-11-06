"""GtkFishbowl, a widget moving its children around, used by the Fishbowl demo."""

from collections.abc import Callable
from dataclasses import dataclass

from PyLiite4 import Gdk, GLib, GObject, Gtk

GtkFishCreationFunc = Callable[[], Gtk.Widget]


@dataclass
class GtkFishbowlChild:
    widget: Gtk.Widget
    x: float
    y: float
    dx: float
    dy: float


def new_speed() -> float:
    # 5 to 50 seconds to cross the screen.
    return GLib.random_double_range(0.02, 0.2)


def guess_refresh_interval(frame_clock: Gdk.FrameClock) -> int:
    interval = GLib.MAXINT64

    for i in range(frame_clock.get_history_start(), frame_clock.get_frame_counter()):
        t = frame_clock.get_timings(i)
        before = frame_clock.get_timings(i - 1)
        if t is None or before is None:
            continue

        ts = t.get_frame_time()
        before_ts = before.get_frame_time()
        if ts == 0 or before_ts == 0:
            continue

        interval = min(interval, ts - before_ts)

    if interval == GLib.MAXINT64:
        return 0

    return interval


class GtkFishbowl(Gtk.Widget):
    __gtype_name__ = "GtkFishbowl"

    def __init__(self, **properties: object) -> None:
        self.creation_func: GtkFishCreationFunc | None = None
        self.children: dict[Gtk.Widget, GtkFishbowlChild] = {}
        self._count = 0
        self.last_frame_time = 0
        self._update_delay = GLib.USEC_PER_SEC
        self.tick_id = 0
        self._framerate = 0.0
        self.last_benchmark_change = 0
        self._benchmark = False
        super().__init__(**properties)

    @GObject.Property(type=bool, default=False, nick="animating", blurb="Whether children are moving around")
    def animating(self) -> bool:
        return self.get_animating()

    @animating.setter
    def animating(self, value: bool) -> None:
        self.set_animating(value)

    @GObject.Property(type=bool, default=False, nick="Benchmark",
                      blurb="Adapt the count property to hit the maximum framerate")
    def benchmark(self) -> bool:
        return self.get_benchmark()

    @benchmark.setter
    def benchmark(self, value: bool) -> None:
        self.set_benchmark(value)

    @GObject.Property(type=GObject.TYPE_UINT, default=0, minimum=0, maximum=GLib.MAXUINT32, nick="Count",
                      blurb="Number of widgets")
    def count(self) -> int:
        return self.get_count()

    @count.setter
    def count(self, value: int) -> None:
        self.set_count(value)

    @GObject.Property(type=float, default=0, minimum=0, maximum=GLib.MAXDOUBLE, nick="Framerate",
                      blurb="Framerate of this widget in frames per second", flags=GObject.ParamFlags.READABLE)
    def framerate(self) -> float:
        return self.get_framerate()

    @GObject.Property(type=GObject.TYPE_INT64, default=GLib.USEC_PER_SEC, minimum=0, maximum=GLib.MAXINT64,
                      nick="Update delay", blurb="Number of usecs between updates")
    def update_delay(self) -> int:
        return self.get_update_delay()

    @update_delay.setter
    def update_delay(self, value: int) -> None:
        self.set_update_delay(value)

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        minimum = 0
        natural = 0

        for child in self.children.values():
            if orientation == Gtk.Orientation.HORIZONTAL:
                child_min, child_nat, _, _ = child.widget.measure(orientation, -1)
            else:
                min_width, _, _, _ = child.widget.measure(Gtk.Orientation.HORIZONTAL, -1)
                child_min, child_nat, _, _ = child.widget.measure(orientation, min_width)

            minimum = max(minimum, child_min)
            natural = max(natural, child_nat)

        return minimum, natural, -1, -1

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        for child in self.children.values():
            child_requisition, _ = child.widget.get_preferred_size()
            child_allocation = Gdk.Rectangle()
            child_allocation.x = round(child.x * (width - child_requisition.width))
            child_allocation.y = round(child.y * (height - child_requisition.height))
            child_allocation.width = child_requisition.width
            child_allocation.height = child_requisition.height

            child.widget.size_allocate(child_allocation, -1)

    def add(self, widget: Gtk.Widget) -> None:
        child_info = GtkFishbowlChild(widget=widget, x=0, y=0, dx=new_speed(), dy=new_speed())

        widget.set_parent(self)
        widget.update_state([Gtk.AccessibleState.HIDDEN], [True])

        self.children[widget] = child_info
        self._count += 1
        self.notify("count")

    def remove(self, widget: Gtk.Widget) -> None:
        if self.children.pop(widget, None) is not None:
            widget.unparent()

            self._count -= 1
            self.notify("count")

    def do_dispose(self) -> None:
        self.set_animating(False)
        self.set_count(0)

        Gtk.Widget.do_dispose(self)

    def get_count(self) -> int:
        return self._count

    def set_count(self, count: int) -> None:
        if self._count == count:
            return

        self.freeze_notify()

        while self._count > count:
            self.remove(self.get_first_child())

        while self._count < count:
            new_widget = self.creation_func()

            self.add(new_widget)

        self.thaw_notify()

    def get_benchmark(self) -> bool:
        return self._benchmark

    def set_benchmark(self, benchmark: bool) -> None:
        if self._benchmark == benchmark:
            return

        self._benchmark = benchmark
        if not benchmark:
            self.last_benchmark_change = 0

        self.notify("benchmark")

    def get_animating(self) -> bool:
        return self.tick_id != 0

    def do_update(self) -> None:
        frame_clock = self.get_frame_clock()
        if frame_clock is None:
            return

        fps = frame_clock.get_fps()
        if fps <= 0.0:
            return

        self._framerate = fps
        self.notify("framerate")

        if not self._benchmark:
            return

        end_counter = frame_clock.get_frame_counter()
        end = frame_clock.get_timings(end_counter)
        while end is not None and not end.get_complete():
            end_counter -= 1
            end = frame_clock.get_timings(end_counter)
        if end is None:
            return

        interval = end.get_refresh_interval()
        if interval == 0:
            interval = guess_refresh_interval(frame_clock)
            if interval == 0:
                return
        expected_fps = GLib.USEC_PER_SEC / interval

        if fps > (expected_fps - 1):
            if self.last_benchmark_change > 0:
                self.last_benchmark_change *= 2
            else:
                self.last_benchmark_change = 1
        elif 0.95 * fps < expected_fps:
            if self.last_benchmark_change < 0:
                self.last_benchmark_change -= 1
            else:
                self.last_benchmark_change = -1
        else:
            self.last_benchmark_change = 0

        self.set_count(max(1, self._count + self.last_benchmark_change))

    def tick(self, widget: Gtk.Widget, frame_clock: Gdk.FrameClock) -> bool:
        frame_time = widget.get_frame_clock().get_frame_time()
        elapsed = frame_time - self.last_frame_time
        do_update = frame_time // self._update_delay != self.last_frame_time // self._update_delay
        self.last_frame_time = frame_time

        # The last frame time was 0, so the animation is only starting.
        if elapsed == frame_time:
            return GLib.SOURCE_CONTINUE

        for child in self.children.values():
            child.x += child.dx * (elapsed / GLib.USEC_PER_SEC)
            child.y += child.dy * (elapsed / GLib.USEC_PER_SEC)

            if child.x <= 0:
                child.x = 0
                child.dx = new_speed()
            elif child.x >= 1:
                child.x = 1
                child.dx = - new_speed()

            if child.y <= 0:
                child.y = 0
                child.dy = new_speed()
            elif child.y >= 1:
                child.y = 1
                child.dy = - new_speed()

        widget.queue_allocate()

        if do_update:
            self.do_update()

        return GLib.SOURCE_CONTINUE

    def set_animating(self, animating: bool) -> None:
        if self.get_animating() == animating:
            return

        if animating:
            self.tick_id = self.add_tick_callback(self.tick)
        else:
            self.last_frame_time = 0
            self.remove_tick_callback(self.tick_id)
            self.tick_id = 0
            self._framerate = 0
            self.notify("framerate")

        self.notify("animating")

    def get_framerate(self) -> float:
        return self._framerate

    def get_update_delay(self) -> int:
        return self._update_delay

    def set_update_delay(self, update_delay: int) -> None:
        if self._update_delay == update_delay:
            return

        self._update_delay = update_delay

        self.notify("update-delay")

    def set_creation_func(self, creation_func: GtkFishCreationFunc) -> None:
        self.freeze_notify()

        self.set_count(0)
        self.last_benchmark_change = 0

        self.creation_func = creation_func

        self.set_count(1)

        self.thaw_notify()


GtkFishbowl.set_accessible_role(Gtk.AccessibleRole.PRESENTATION)


def gtk_fishbowl_new() -> Gtk.Widget:
    return GtkFishbowl()
