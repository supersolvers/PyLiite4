"""The parent widget of the layout manager transformation demo, which rotates its Demo2Layout."""

from PyLiite4 import Gdk, GLib, Gtk

from .demo2layout import Demo2Layout


def ease_out_cubic(t: float) -> float:
    """From clutter-easing.c, based on Robert Penner's
    infamous easing equations, MIT license.
    """
    p = t - 1

    return p * p * p + 1


class Demo2Widget(Gtk.Widget):
    __gtype_name__ = "Demo2Widget"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        # here is where we use our custom layout manager. C sets it with gtk_widget_class_set_layout_manager_type(),
        # but when GTK creates a Python layout manager during the widget's construction, PyGObject gives it the
        # widget's Python wrapper, so it is set per instance instead.
        self.set_layout_manager(Demo2Layout())

        self.start_time = 0
        self.end_time = 0
        self.start_position = 0.0
        self.end_position = 0.0
        self.start_offset = 0.0
        self.end_offset = 0.0
        self.animating = False

        self.set_focusable(True)

    def do_dispose(self) -> None:
        while (child := self.get_first_child()) is not None:
            child.unparent()

        Gtk.Widget.do_dispose(self)

    def update_position(self, widget: Gtk.Widget, clock: Gdk.FrameClock) -> bool:
        layout = self.get_layout_manager()

        now = clock.get_frame_time()

        if now >= self.end_time:
            self.animating = False

            return GLib.SOURCE_REMOVE

        t = (now - self.start_time) / (self.end_time - self.start_time)

        t = ease_out_cubic(t)

        layout.set_position(self.start_position + t * (self.end_position - self.start_position))
        layout.set_offset(self.start_offset + t * (self.end_offset - self.start_offset))
        self.queue_allocate()

        return GLib.SOURCE_CONTINUE

    def rotate_sphere(self, action: str, parameters: GLib.Variant) -> None:
        layout = self.get_layout_manager()

        orientation, direction = parameters.unpack()

        self.end_position = self.start_position = layout.get_position()
        self.end_offset = self.start_offset = layout.get_offset()
        if orientation == Gtk.Orientation.HORIZONTAL:
            self.end_position += 10 * direction
        else:
            self.end_offset += 10 * direction
        self.start_time = GLib.get_monotonic_time()
        self.end_time = self.start_time + 0.5 * GLib.TIME_SPAN_SECOND

        if not self.animating:
            self.add_tick_callback(self.update_position)
            self.animating = True

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        child = self.get_first_child()
        while child is not None:
            # our layout manager sets this for children that are out of view
            if child.get_child_visible():
                self.snapshot_child(child, snapshot)
            child = child.get_next_sibling()

    def add_child(self, child: Gtk.Widget) -> None:
        child.set_parent(self)


Demo2Widget.install_action("rotate", "(ii)", Demo2Widget.rotate_sphere)


def add_binding_action(keyval: int, mods: Gdk.ModifierType, action_name: str, format: str, *args: object) -> None:
    # gtk_widget_class_add_binding_action() is variadic, so it is done with the shortcut it adds
    Demo2Widget.add_shortcut(Gtk.Shortcut(trigger=Gtk.KeyvalTrigger.new(keyval, mods),
                                          action=Gtk.NamedAction.new(action_name),
                                          arguments=GLib.Variant(format, args)))


add_binding_action(Gdk.KEY_Left, 0, "rotate", "(ii)", Gtk.Orientation.HORIZONTAL, -1)
add_binding_action(Gdk.KEY_Right, 0, "rotate", "(ii)", Gtk.Orientation.HORIZONTAL, 1)
add_binding_action(Gdk.KEY_Up, 0, "rotate", "(ii)", Gtk.Orientation.VERTICAL, 1)
add_binding_action(Gdk.KEY_Down, 0, "rotate", "(ii)", Gtk.Orientation.VERTICAL, -1)


def demo2_widget_new() -> Gtk.Widget:
    return Demo2Widget()
