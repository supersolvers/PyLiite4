"""Paint
#Keywords: GdkDrawingArea, GtkGesture

Demonstrates practical handling of drawing tablets in a real world
usecase.
"""

from PyLiite4 import Gdk, GLib, GObject, Gio, Graphene, Gtk, cairo


def pad_action_entry(type: Gtk.PadActionType, index: int, mode: int, label: str,
                     action_name: str) -> Gtk.PadActionEntry:
    entry = Gtk.PadActionEntry()
    entry.type, entry.index, entry.mode, entry.label, entry.action_name = type, index, mode, label, action_name
    return entry


pad_actions = [
    (Gtk.PadActionType.BUTTON, 1, -1, "Black", "pad.black"),
    (Gtk.PadActionType.BUTTON, 2, -1, "Pink", "pad.pink"),
    (Gtk.PadActionType.BUTTON, 3, -1, "Green", "pad.green"),
    (Gtk.PadActionType.BUTTON, 4, -1, "Red", "pad.red"),
    (Gtk.PadActionType.BUTTON, 5, -1, "Purple", "pad.purple"),
    (Gtk.PadActionType.BUTTON, 6, -1, "Orange", "pad.orange"),
    (Gtk.PadActionType.STRIP, -1, -1, "Brush size", "pad.brush_size"),
    (Gtk.PadActionType.DIAL, -1, -1, "Brush size", "pad.change_brush_size"),
]

pad_colors = [
    "black",
    "pink",
    "green",
    "red",
    "purple",
    "orange",
]


def rgba(red: float, green: float, blue: float, alpha: float) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = red, green, blue, alpha
    return color


class DrawingArea(Gtk.Widget):
    __gtype_name__ = "DrawingArea"

    color_set = GObject.Signal("color-set", flags=GObject.SignalFlags.RUN_FIRST, arg_types=(Gdk.RGBA,))

    def __init__(self) -> None:
        super().__init__()
        self.surface: cairo.ImageSurface | None = None
        self.cr: cairo.Context | None = None
        self.pad_controller: Gtk.PadController | None = None

        gesture = Gtk.GestureStylus()
        gesture.down.connect(stylus_gesture_down, self)
        gesture.motion.connect(stylus_gesture_motion, self)
        self.add_controller(gesture)

        self.draw_color = rgba(0, 0, 0, 1)
        self.brush_size = 1.0

        self.gesture = gesture

    def ensure_surface(self, width: int, height: int) -> None:
        if not self.surface or self.surface.get_width() != width or self.surface.get_height() != height:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
            if self.surface:
                cr = cairo.Context(surface)
                cr.set_source_surface(self.surface, 0, 0)
                cr.paint()

            self.surface = surface
            self.cr = cairo.Context(surface)

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        self.ensure_surface(width, height)

        Gtk.Widget.do_size_allocate(self, width, height, baseline)

    def do_map(self) -> None:
        Gtk.Widget.do_map(self)

        self.ensure_surface(self.get_width(), self.get_height())

    def do_unmap(self) -> None:
        self.cr = None
        self.surface = None

        Gtk.Widget.do_unmap(self)

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        cr = snapshot.append_cairo(Graphene.Rect().init(0, 0, width, height))

        cr.set_source_rgb(1, 1, 1)
        cr.paint()

        cr.set_source_surface(self.surface, 0, 0)
        cr.paint()

        cr.set_source_rgb(0.6, 0.6, 0.6)
        cr.rectangle(0, 0, width, height)
        cr.stroke()

    def do_unroot(self) -> None:
        toplevel = self.get_root()

        if self.pad_controller:
            toplevel.remove_controller(self.pad_controller)
            self.pad_controller = None

        Gtk.Widget.do_unroot(self)

    def do_root(self) -> None:
        Gtk.Widget.do_root(self)

        toplevel = self.get_root()

        action_group = Gio.SimpleActionGroup()
        self.pad_controller = Gtk.PadController.new(action_group, None)

        for i, (type, _index, _mode, _label, action_name) in enumerate(pad_actions):
            if type == Gtk.PadActionType.BUTTON:
                action = Gio.SimpleAction.new(action_name, None)
                action.activate.connect(on_pad_button_activate, self, pad_colors[i])
            elif type == Gtk.PadActionType.DIAL:
                action = Gio.SimpleAction.new_stateful(action_name, GLib.VariantType.new("d"),
                                                       GLib.Variant.new_double(0))
                action.activate.connect(on_pad_dial_change, self)
            else:
                action = Gio.SimpleAction.new_stateful(action_name, GLib.VariantType.new("d"),
                                                       GLib.Variant.new_double(0))
                action.activate.connect(on_pad_knob_change, self)

            action_group.add_action(action)

        self.pad_controller.set_action_entries([pad_action_entry(*entry) for entry in pad_actions])

        toplevel.add_controller(self.pad_controller)

    def apply_stroke(self, tool: Gdk.DeviceTool | None, x: float, y: float, pressure: float) -> None:
        if tool and tool.get_tool_type() == Gdk.DeviceToolType.ERASER:
            self.cr.set_line_width(10 * pressure * self.brush_size)
            self.cr.set_operator(cairo.OPERATOR_DEST_OUT)
        else:
            self.cr.set_line_width(4 * pressure * self.brush_size)
            self.cr.set_operator(cairo.OPERATOR_SATURATE)

        self.cr.set_source_rgba(self.draw_color.red, self.draw_color.green, self.draw_color.blue,
                                self.draw_color.alpha * pressure)

        self.cr.line_to(x, y)
        self.cr.stroke()
        self.cr.move_to(x, y)

    def set_color(self, color: Gdk.RGBA) -> None:
        if self.draw_color.equal(color):
            return

        self.draw_color = color.copy()
        self.color_set.emit(self.draw_color)

    def get_gesture(self) -> Gtk.Gesture:
        return self.gesture


def on_pad_button_activate(action: Gio.SimpleAction, parameter: GLib.Variant | None, area: DrawingArea,
                           color: str) -> None:
    # C keeps the colour name on the action with g_object_set_data()
    rgba = Gdk.RGBA()
    rgba.parse(color)
    area.set_color(rgba)


def on_pad_knob_change(action: Gio.SimpleAction, parameter: GLib.Variant, area: DrawingArea) -> None:
    value = parameter.get_double()

    area.brush_size = value


def on_pad_dial_change(action: Gio.SimpleAction, parameter: GLib.Variant, area: DrawingArea) -> None:
    value = parameter.get_double()

    area.brush_size += value / 120.0


def stylus_gesture_down(gesture: Gtk.GestureStylus, x: float, y: float, area: DrawingArea) -> None:
    area.cr.new_path()


def stylus_gesture_motion(gesture: Gtk.GestureStylus, x: float, y: float, area: DrawingArea) -> None:
    tool = gesture.get_device_tool()

    ok, backlog = gesture.get_backlog()
    if ok:
        for coord in backlog:
            area.apply_stroke(tool,
                              coord.axes[Gdk.AxisUse.X],
                              coord.axes[Gdk.AxisUse.Y],
                              coord.axes[Gdk.AxisUse.PRESSURE] if coord.flags & Gdk.AxisFlags.PRESSURE else 1)
    else:
        ok, pressure = gesture.get_axis(Gdk.AxisUse.PRESSURE)
        if not ok:
            pressure = 1

        area.apply_stroke(tool, x, y, pressure)

    area.queue_draw()


def drawing_area_new() -> DrawingArea:
    return DrawingArea()


def color_button_color_set(button: Gtk.ColorDialogButton, pspec: GObject.ParamSpec, draw_area: DrawingArea) -> None:
    color = button.get_rgba()
    draw_area.set_color(color)


def drawing_area_color_set(area: DrawingArea, color: Gdk.RGBA, button: Gtk.ColorDialogButton) -> None:
    button.set_rgba(color)


def drawing_area_clear(button: Gtk.Button, area: DrawingArea) -> None:
    area.cr = None
    area.surface = None

    width = area.get_width()
    height = area.get_height()

    area.ensure_surface(width, height)
    area.queue_draw()


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(toplevel: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        window = Gtk.Window()

        draw_area = drawing_area_new()
        window.set_child(draw_area)

        headerbar = Gtk.HeaderBar()

        button = Gtk.ColorDialogButton.new(Gtk.ColorDialog())
        button.notify["rgba"].connect(color_button_color_set, draw_area)
        draw_area.color_set.connect(drawing_area_color_set, button)
        button.set_rgba(rgba(0, 0, 0, 1))

        headerbar.pack_end(button)

        button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        button.clicked.connect(drawing_area_clear, draw_area)

        headerbar.pack_end(button)

        button = Gtk.CheckButton.new_with_label("Stylus only")
        button.bind_property("active", draw_area.get_gesture(), "stylus-only", GObject.BindingFlags.SYNC_CREATE)
        headerbar.pack_start(button)

        window.set_titlebar(headerbar)
        window.set_title("Paint")
        window.close_request.connect(close_request)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
