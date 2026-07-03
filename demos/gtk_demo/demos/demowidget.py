"""The parent widget of the layout manager demo, which animates its DemoLayout."""

from PyLiite4 import Gdk, GLib, Gtk

from .demolayout import DemoLayout

# The widget is controlling the transition by calling
# demo_layout_set_position() in a tick callback.
#
# We take half a second to go from one layout to the other.

DURATION = 0.5 * GLib.TIME_SPAN_SECOND


class DemoWidget(Gtk.Widget):
    __gtype_name__ = "DemoWidget"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        # here is where we use our custom layout manager. C sets it with gtk_widget_class_set_layout_manager_type(),
        # but when GTK creates a Python layout manager during the widget's construction, PyGObject gives it the
        # widget's Python wrapper, so it is set per instance instead.
        self.set_layout_manager(DemoLayout())

        self.backward = False  # whether we go 0 -> 1 or 1 -> 0
        self.start_time = 0    # time the transition started
        self.tick_id = 0       # our tick cb

        gesture = Gtk.GestureClick()
        gesture.pressed.connect(self.clicked)
        self.add_controller(gesture)

    def transition(self, widget: Gtk.Widget, frame_clock: Gdk.FrameClock) -> bool:
        demo_layout = self.get_layout_manager()
        now = frame_clock.get_frame_time()

        self.queue_allocate()

        if self.backward:
            demo_layout.set_position(1.0 - (now - self.start_time) / DURATION)
        else:
            demo_layout.set_position((now - self.start_time) / DURATION)

        if now - self.start_time >= DURATION:
            self.backward = not self.backward
            demo_layout.set_position(1.0 if self.backward else 0.0)
            # keep things interesting by shuffling the positions
            if not self.backward:
                demo_layout.shuffle()
            self.tick_id = 0

            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE

    def clicked(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if self.tick_id != 0:
            return

        frame_clock = self.get_frame_clock()
        self.start_time = frame_clock.get_frame_time()
        self.tick_id = self.add_tick_callback(self.transition)

    def do_dispose(self) -> None:
        while (child := self.get_first_child()) is not None:
            child.unparent()

        Gtk.Widget.do_dispose(self)

    def add_child(self, child: Gtk.Widget) -> None:
        child.set_parent(self)



def demo_widget_new() -> Gtk.Widget:
    return DemoWidget()
