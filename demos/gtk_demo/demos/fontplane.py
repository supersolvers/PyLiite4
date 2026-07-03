"""GtkFontPlane, a widget for picking a font's weight and width at once, for the Font Features demo."""

from PyLiite4 import Gdk, GObject, Graphene, Gtk


def adjustment_get_normalized_value(adj: Gtk.Adjustment) -> float:
    return (adj.get_value() - adj.get_lower()) / (adj.get_upper() - adj.get_lower())


def adjustment_set_normalized_value(adj: Gtk.Adjustment, val: float) -> None:
    adj.set_value(adj.get_lower() + val * (adj.get_upper() - adj.get_lower()))


def clamp(x: float, low: float, high: float) -> float:
    return min(max(x, low), high)


def set_cross_cursor(widget: Gtk.Widget, enabled: bool) -> None:
    if enabled:
        widget.set_cursor_from_name("crosshair")
    else:
        widget.set_cursor(None)


class GtkFontPlane(Gtk.Widget):
    __gtype_name__ = "GtkFontPlane"

    def __init__(self, **properties: object) -> None:
        self.weight_adj: Gtk.Adjustment | None = None
        self.width_adj: Gtk.Adjustment | None = None
        super().__init__(**properties)

        gesture = Gtk.GestureDrag()
        gesture.drag_begin.connect(self.plane_drag_gesture_begin)
        gesture.drag_update.connect(self.plane_drag_gesture_update)
        gesture.drag_end.connect(self.plane_drag_gesture_end)
        gesture.set_button(0)
        self.add_controller(gesture)

    def _set_weight_adjustment(self, adjustment: Gtk.Adjustment | None) -> None:
        if adjustment:
            self.weight_adj = adjustment
            adjustment.value_changed.connect(self.adj_changed)

    def _set_width_adjustment(self, adjustment: Gtk.Adjustment | None) -> None:
        if adjustment:
            self.width_adj = adjustment
            adjustment.value_changed.connect(self.adj_changed)

    weight_adjustment = GObject.Property(type=Gtk.Adjustment, setter=_set_weight_adjustment,
                                         flags=GObject.ParamFlags.WRITABLE | GObject.ParamFlags.CONSTRUCT_ONLY)
    width_adjustment = GObject.Property(type=Gtk.Adjustment, setter=_set_width_adjustment,
                                        flags=GObject.ParamFlags.WRITABLE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def val_to_xy(self) -> tuple[int, int]:
        width = self.get_width()
        height = self.get_height()

        u = adjustment_get_normalized_value(self.width_adj)
        v = adjustment_get_normalized_value(self.weight_adj)

        x = int(clamp(width * u, 0, width - 1))
        y = int(clamp(height * (1 - v), 0, height - 1))
        return x, y

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        x, y = self.val_to_xy()
        width = self.get_width()
        height = self.get_height()

        cr = snapshot.append_cairo(Graphene.Rect().init(0, 0, width, height))

        cr.set_source_rgb(0, 0, 0)
        cr.rectangle(0, 0, width, height)
        cr.paint()

        cr.move_to(0, y + 0.5)
        cr.line_to(width, y + 0.5)

        cr.move_to(x + 0.5, 0)
        cr.line_to(x + 0.5, height)

        if self.has_visible_focus():
            cr.set_line_width(3.0)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.6)
            cr.stroke_preserve()

            cr.set_line_width(1.0)
            cr.set_source_rgba(0.0, 0.0, 0.0, 0.8)
            cr.stroke()
        else:
            cr.set_line_width(1.0)
            cr.set_source_rgba(0.8, 0.8, 0.8, 0.8)
            cr.stroke()

    def adj_changed(self, adjustment: Gtk.Adjustment) -> None:
        self.queue_draw()

    def update_value(self, x: float, y: float) -> None:
        u = clamp(x * (1.0 / self.get_width()), 0, 1)
        v = clamp(1 - y * (1.0 / self.get_height()), 0, 1)

        adjustment_set_normalized_value(self.width_adj, u)
        adjustment_set_normalized_value(self.weight_adj, v)

        self.queue_draw()

    def plane_drag_gesture_begin(self, gesture: Gtk.GestureDrag, start_x: float, start_y: float) -> None:
        button = gesture.get_current_button()

        if button != Gdk.BUTTON_PRIMARY:
            gesture.set_state(Gtk.EventSequenceState.DENIED)
            return

        set_cross_cursor(self, True)
        self.update_value(start_x, start_y)
        self.grab_focus()
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def plane_drag_gesture_update(self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float) -> None:
        _, start_x, start_y = gesture.get_start_point()
        self.update_value(start_x + offset_x, start_y + offset_y)

    def plane_drag_gesture_end(self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float) -> None:
        set_cross_cursor(self, False)


def gtk_font_plane_new(weight_adj: Gtk.Adjustment, width_adj: Gtk.Adjustment) -> GtkFontPlane:
    return GtkFontPlane(weight_adjustment=weight_adj, width_adjustment=width_adj)
