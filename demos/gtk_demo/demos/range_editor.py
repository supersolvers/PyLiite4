"""RangeEditor: a slider with two handles selecting a range, used by the Path Explorer demo.

Ported from GTK Demo's range-editor.c and range-editor.h.

Copyright © 2025 Red Hat, Inc. Authors: Matthias Clasen <mclasen@redhat.com>
"""

from collections.abc import Callable

from PyLiite4 import Gdk, GLib, GObject, Gtk

# Gizmo

GizmoMeasureFunc = Callable[["Gizmo", Gtk.Orientation, int], tuple[int, int, int, int]]
GizmoAllocateFunc = Callable[["Gizmo", int, int, int], None]
GizmoSnapshotFunc = Callable[["Gizmo", Gtk.Snapshot], None]


class Gizmo(Gtk.Widget):
    __gtype_name__ = "Gizmo"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        self.measure_func: GizmoMeasureFunc | None = None
        self.allocate_func: GizmoAllocateFunc | None = None
        self.snapshot_func: GizmoSnapshotFunc | None = None

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        if self.measure_func:
            return self.measure_func(self, orientation, for_size)
        return 0, 0, -1, -1

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        if self.allocate_func:
            self.allocate_func(self, width, height, baseline)

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        if self.snapshot_func:
            self.snapshot_func(self, snapshot)
        else:
            Gtk.Widget.do_snapshot(self, snapshot)

    # C unparents the gizmo's children when it is finalized; the range editor's dispose already does.


def gizmo_new(css_name: str, measure_func: GizmoMeasureFunc | None, allocate_func: GizmoAllocateFunc | None,
              snapshot_func: GizmoSnapshotFunc | None) -> Gtk.Widget:
    gizmo = Gizmo(css_name=css_name, accessible_role=Gtk.AccessibleRole.NONE)

    gizmo.measure_func = measure_func
    gizmo.allocate_func = allocate_func
    gizmo.snapshot_func = snapshot_func

    return gizmo


# Utilities


def measure_widget(widget: Gtk.Widget, orientation: Gtk.Orientation) -> tuple[int, int]:
    min, nat, _, _ = widget.measure(orientation, -1)
    return min, nat


def allocation(x: float, y: float, width: float, height: float) -> Gdk.Rectangle:
    """A GtkAllocation; its fields are ints, as in C."""
    alloc = Gdk.Rectangle()
    alloc.x, alloc.y, alloc.width, alloc.height = int(x), int(y), int(width), int(height)
    return alloc


# Trough


def measure_trough(gizmo: Gizmo, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
    self = gizmo.get_parent()

    minimum, natural = measure_widget(self.highlight, orientation)
    min, nat = measure_widget(self.slider1, orientation)

    if orientation == Gtk.Orientation.HORIZONTAL:
        minimum += min
        natural += nat
    else:
        minimum = max(minimum, min)
        natural = max(natural, nat)

    min, nat = measure_widget(self.slider2, orientation)

    if orientation == Gtk.Orientation.HORIZONTAL:
        minimum += min
        natural += nat
    else:
        minimum = max(minimum, min)
        natural = max(natural, nat)

    return minimum, natural, -1, -1


def allocate_trough(gizmo: Gizmo, width: int, height: int, baseline: int) -> None:
    self = gizmo.get_parent()

    x1 = width * (self.value1 - self.lower) / (self.upper - self.lower)
    x2 = width * (self.value2 - self.lower) / (self.upper - self.lower)

    self.highlight.size_allocate(allocation(x1, 0, x2 - x1, height), -1)

    slider_width, _ = measure_widget(self.slider1, Gtk.Orientation.HORIZONTAL)
    slider_height, _ = measure_widget(self.slider1, Gtk.Orientation.VERTICAL)

    self.slider1.size_allocate(allocation(x1 - slider_width, (height - slider_height) / 2,
                                          slider_width, slider_height), -1)

    slider_width, _ = measure_widget(self.slider2, Gtk.Orientation.HORIZONTAL)
    slider_height, _ = measure_widget(self.slider2, Gtk.Orientation.VERTICAL)

    self.slider2.size_allocate(allocation(x2, (height - slider_height) / 2, slider_width, slider_height), -1)


def render_trough(gizmo: Gizmo, snapshot: Gtk.Snapshot) -> None:
    self = gizmo.get_parent()

    self.trough.snapshot_child(self.highlight, snapshot)
    self.trough.snapshot_child(self.slider1, snapshot)
    self.trough.snapshot_child(self.slider2, snapshot)


# Input


def drag_gesture_begin(gesture: Gtk.GestureDrag, offset_x: float, offset_y: float, self: "RangeEditor") -> None:
    self.mouse_location = self.pick(offset_x, offset_y, Gtk.PickFlags.DEFAULT)

    if self.mouse_location == self.slider1 or self.mouse_location == self.slider2:
        self.drag_gesture.set_state(Gtk.EventSequenceState.CLAIMED)


def drag_gesture_end(gesture: Gtk.GestureDrag, offset_x: float, offset_y: float, self: "RangeEditor") -> None:
    self.mouse_location = None


def drag_gesture_update(gesture: Gtk.GestureDrag, offset_x: float, offset_y: float, self: "RangeEditor") -> None:
    if self.mouse_location == self.slider1 or self.mouse_location == self.slider2:
        _, start_x, start_y = gesture.get_start_point()
        mouse_x = int(start_x + offset_x)

        ok, bounds = self.trough.compute_bounds(self)
        assert ok

        v = self.lower + (mouse_x - bounds.origin.x) / bounds.size.width * (self.upper - self.lower)

        if self.mouse_location == self.slider1:
            v = min(max(v, self.lower), self.upper)
            self.set_values(min(v, self.value2), self.value2)
        elif self.mouse_location == self.slider2:
            v = min(max(v, self.lower), self.upper)
            self.set_values(self.value1, max(self.value1, v))


_FLOAT_FLAGS = GObject.ParamFlags.READWRITE | GObject.ParamFlags.EXPLICIT_NOTIFY


class RangeEditor(Gtk.Widget):
    __gtype_name__ = "RangeEditor"

    def __init__(self, **properties: object) -> None:
        self._lower = 0.0
        self._upper = 0.0
        self._value1 = 0.0
        self._value2 = 0.0

        self.mouse_location: Gtk.Widget | None = None

        self.trough = gizmo_new("trough", measure_trough, allocate_trough, render_trough)
        self.highlight = gizmo_new("highlight", None, None, None)
        self.slider1 = gizmo_new("slider", None, None, None)
        self.slider2 = gizmo_new("slider", None, None, None)

        super().__init__()

        self.trough.set_parent(self)
        self.highlight.set_parent(self.trough)
        self.slider1.set_parent(self.trough)
        self.slider1.add_css_class("left")
        self.slider2.set_parent(self.trough)
        self.slider2.add_css_class("right")

        self.drag_gesture = Gtk.GestureDrag()
        self.drag_gesture.set_button(0)
        self.drag_gesture.drag_begin.connect(drag_gesture_begin, self)
        self.drag_gesture.drag_update.connect(drag_gesture_update, self)
        self.drag_gesture.drag_end.connect(drag_gesture_end, self)

        self.add_controller(self.drag_gesture)

        for name, value in properties.items():
            self.set_property(name, value)

    # Properties

    @GObject.Property(type=GObject.TYPE_FLOAT, minimum=-GLib.MAXFLOAT, maximum=GLib.MAXFLOAT, default=0,
                      flags=_FLOAT_FLAGS)
    def lower(self) -> float:
        return self._lower

    @lower.setter
    def lower(self, v: float) -> None:
        self.set_limits(v, max(v, self._upper))

    @GObject.Property(type=GObject.TYPE_FLOAT, minimum=-GLib.MAXFLOAT, maximum=GLib.MAXFLOAT, default=0,
                      flags=_FLOAT_FLAGS)
    def upper(self) -> float:
        return self._upper

    @upper.setter
    def upper(self, v: float) -> None:
        self.set_limits(min(v, self._lower), v)

    @GObject.Property(type=GObject.TYPE_FLOAT, minimum=-GLib.MAXFLOAT, maximum=GLib.MAXFLOAT, default=0,
                      flags=_FLOAT_FLAGS)
    def value1(self) -> float:
        return self._value1

    @value1.setter
    def value1(self, v: float) -> None:
        self.set_values(v, max(v, self._value2))

    @GObject.Property(type=GObject.TYPE_FLOAT, minimum=-GLib.MAXFLOAT, maximum=GLib.MAXFLOAT, default=0,
                      flags=_FLOAT_FLAGS)
    def value2(self) -> float:
        return self._value2

    @value2.setter
    def value2(self, v: float) -> None:
        self.set_values(min(v, self._value1), v)

    # Setters

    def set_values(self, value1: float, value2: float) -> None:
        # C's g_return_if_fail() checks
        if not (self._lower <= value1 <= value2 <= self._upper):
            return

        if self._value1 == value1 and self._value2 == value2:
            return

        self.freeze_notify()

        if self._value1 != value1:
            self._value1 = value1
            self.notify("value1")

        if self._value2 != value2:
            self._value2 = value2
            self.notify("value2")

        self.thaw_notify()
        self.highlight.queue_resize()
        self.slider1.queue_resize()
        self.slider2.queue_resize()

    def set_limits(self, lower: float, upper: float) -> None:
        if not lower <= upper:
            return

        if self._lower == lower and self._upper == upper:
            return

        self.freeze_notify()

        if self._lower != lower:
            self._lower = lower
            self.notify("lower")

        if self._upper != upper:
            self._upper = upper
            self.notify("upper")

        self.set_values(min(max(self._value1, self._lower), self._upper),
                        min(max(self._value2, self._lower), self._upper))

        self.thaw_notify()
        self.highlight.queue_resize()

    # GtkWidget implementation

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        minimum, natural = measure_widget(self.trough, orientation)
        return minimum, natural, -1, -1

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        slider1_width, _ = measure_widget(self.slider1, Gtk.Orientation.HORIZONTAL)
        slider2_width, _ = measure_widget(self.slider2, Gtk.Orientation.HORIZONTAL)
        min_height, _ = measure_widget(self.trough, Gtk.Orientation.VERTICAL)

        self.trough.size_allocate(allocation(slider1_width, (height - min_height) / 2,
                                             width - slider1_width - slider2_width, min_height), -1)

    def do_dispose(self) -> None:
        for name in ("highlight", "slider1", "slider2", "trough"):
            child = getattr(self, name, None)
            if child is not None:
                child.unparent()
                setattr(self, name, None)

        Gtk.Widget.do_dispose(self)

    # Public API

    def get_limits(self) -> tuple[float, float]:
        return self._lower, self._upper

    def get_values(self) -> tuple[float, float]:
        return self._value1, self._value2

    def configure(self, lower: float, upper: float, value1: float, value2: float) -> None:
        if not (lower <= value1 <= value2 <= upper):
            return

        self.freeze_notify()

        if self._lower != lower:
            self._lower = lower
            self.notify("lower")

        if self._upper != upper:
            self._upper = upper
            self.notify("upper")

        if self._value1 != value1:
            self._value1 = value1
            self.notify("value1")

        if self._value2 != value2:
            self._value2 = value2
            self.notify("value2")

        self.thaw_notify()

        self.highlight.queue_resize()
        self.slider1.queue_resize()
        self.slider2.queue_resize()


RangeEditor.set_css_name("rangeeditor")


def range_editor_new() -> RangeEditor:
    return RangeEditor()
