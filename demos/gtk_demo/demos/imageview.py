"""A widget that shows a texture with a zoom level, rotation and filter, used by image_scaling."""

import math

from PyLiite4 import Gdk, GLib, GObject, Graphene, Gsk, Gtk

FLT_EPSILON = 1.1920929e-07


def approx_value(a: float, b: float, epsilon: float) -> bool:
    return abs(a - b) < epsilon


@Gtk.Template(resource_path="/menu/imageview.ui")
class ImageView(Gtk.Widget):
    __gtype_name__ = "ImageView"

    menu: Gtk.PopoverMenu = Gtk.Template.Child()

    def __init__(self, **properties: object) -> None:
        self._texture: Gdk.Texture | None = None
        self._scale = 1.0
        self._angle = 0.0
        self._filter = Gsk.ScalingFilter.LINEAR
        self.start_scale = 0.0
        self.start_angle = 0.0
        super().__init__(**properties)

    # Named so that it doesn't hide the widget's query-tooltip signal
    @Gtk.Template.Callback("query_tooltip")
    def query_tooltip_cb(self, widget: Gtk.Widget, x: int, y: int, keyboard_mode: bool, tooltip: Gtk.Tooltip) -> bool:
        filter = ["Linear", "Nearest", "Trilinear"]

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(6)
        label = Gtk.Label(label="Texture")
        label.set_xalign(0)
        grid.attach(label, 0, 0, 1, 1)
        s = f"{self._texture.get_width()} × {self._texture.get_height()}"
        label = Gtk.Label(label=s)
        label.set_xalign(1)
        grid.attach(label, 1, 0, 1, 1)

        label = Gtk.Label(label="Rotation")
        label.set_xalign(0)
        grid.attach(label, 0, 1, 1, 1)
        s = f"{self._angle:.1f}"
        if s.endswith(".0"):
            s = s[:-2]
        s2 = s + "°"
        label = Gtk.Label(label=s2)
        label.set_xalign(1)
        grid.attach(label, 1, 1, 1, 1)

        label = Gtk.Label(label="Scale")
        label.set_xalign(0)
        grid.attach(label, 0, 2, 1, 1)

        precision = 1
        while True:
            s = f"{self._scale:.{precision}f}"
            s = s.rstrip("0")
            if s.endswith("."):
                s = s[:-1]
            precision += 1
            if s != "0":
                break

        label = Gtk.Label(label=s)
        label.set_xalign(1)
        grid.attach(label, 1, 2, 1, 1)

        label = Gtk.Label(label="Filter")
        label.set_xalign(0)
        grid.attach(label, 0, 3, 1, 1)
        label = Gtk.Label(label=filter[self._filter])
        label.set_xalign(1)
        grid.attach(label, 1, 3, 1, 1)

        tooltip.set_custom(grid)

        return True

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        w2 = w = self._scale * self._texture.get_width()
        h2 = h = self._scale * self._texture.get_height()

        if approx_value(self._angle, 90, FLT_EPSILON) or approx_value(self._angle, 270, FLT_EPSILON):
            w2, h2 = h2, w2

        x = int((width - math.ceil(w2)) / 2)
        y = int((height - math.ceil(h2)) / 2)

        snapshot.push_clip(Graphene.Rect().init(0, 0, width, height))
        snapshot.save()
        snapshot.translate(Graphene.Point().init(x, y))
        snapshot.translate(Graphene.Point().init(w2 / 2, h2 / 2))
        snapshot.rotate(self._angle)
        snapshot.translate(Graphene.Point().init(-w / 2, -h / 2))
        snapshot.append_scaled_texture(self._texture, self._filter, Graphene.Rect().init(0, 0, w, h))
        snapshot.restore()
        snapshot.pop()

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        width = self._texture.get_width()
        height = self._texture.get_height()

        if approx_value(self._angle, 90, FLT_EPSILON) or approx_value(self._angle, 270, FLT_EPSILON):
            width, height = height, width

        if orientation == Gtk.Orientation.HORIZONTAL:
            size = width
        else:
            size = height

        minimum = natural = int(math.ceil(self._scale * size))
        return minimum, natural, -1, -1

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        # Since we are not using a layout manager (who would do this
        # for us), we need to allocate a size for our menu by calling
        # gtk_popover_present().
        self.menu.present()

    @GObject.Property(type=Gdk.Texture)
    def texture(self) -> Gdk.Texture | None:
        return self._texture

    @texture.setter
    def texture(self, value: Gdk.Texture) -> None:
        self._texture = value
        self._scale = 1.0
        self._angle = 0.0
        self._filter = Gsk.ScalingFilter.LINEAR
        self.update_actions()
        self.queue_resize()
        self.notify("scale")
        self.notify("angle")
        self.notify("filter")

    @GObject.Property(type=float, minimum=1 / 1024, maximum=1024, default=1.0)
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        self._scale = value
        self.update_actions()
        self.queue_resize()

    @GObject.Property(type=float, minimum=0, maximum=360, default=0)
    def angle(self) -> float:
        return self._angle

    @angle.setter
    def angle(self, value: float) -> None:
        self._angle = math.fmod(value, 360)
        self.queue_resize()

    @GObject.Property(type=Gsk.ScalingFilter, default=Gsk.ScalingFilter.LINEAR)
    def filter(self) -> Gsk.ScalingFilter:
        return self._filter

    @filter.setter
    def filter(self, value: Gsk.ScalingFilter) -> None:
        self._filter = Gsk.ScalingFilter(value)
        self.queue_resize()

    @Gtk.Template.Callback()
    def pressed_cb(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        # We are placing our menu at the point where
        # the click happened, before popping it up.
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self.menu.set_pointing_to(rect)
        self.menu.popup()

    def update_actions(self) -> None:
        self.action_set_enabled("zoom.in", self._scale < 1024)
        self.action_set_enabled("zoom.out", self._scale > 1 / 1024)
        self.action_set_enabled("zoom.reset", self._scale != 1)

    def zoom_cb(self, action_name: str, parameter: GLib.Variant | None) -> None:
        if action_name == "zoom.in":
            scale = min(1024, self._scale * math.sqrt(2))
        elif action_name == "zoom.out":
            scale = max(1 / 1024, self._scale / math.sqrt(2))
        elif action_name == "zoom.reset":
            scale = 1.0
        else:
            raise AssertionError("not reached")

        self.set_property("scale", scale)

    def rotate_cb(self, action_name: str, parameter: GLib.Variant) -> None:
        angle = parameter.get_int32()

        self.set_property("angle", math.fmod(self._angle + angle, 360))

    @Gtk.Template.Callback()
    def scale_begin_cb(self, gesture: Gtk.Gesture, sequence: Gdk.EventSequence | None) -> None:
        self.start_scale = self._scale

    @Gtk.Template.Callback()
    def scale_changed_cb(self, gesture: Gtk.GestureZoom, scale: float) -> None:
        self.set_property("scale", self.start_scale * scale)

    @Gtk.Template.Callback()
    def rotate_begin_cb(self, gesture: Gtk.Gesture, sequence: Gdk.EventSequence | None) -> None:
        self.start_angle = self._angle

    @Gtk.Template.Callback()
    def angle_changed_cb(self, gesture: Gtk.GestureRotate, angle: float, delta: float) -> None:
        a = 90 * round(math.degrees(delta) / 10)

        self.set_property("angle", math.fmod(self.start_angle + a, 360))


# These are the actions that we are using in the menu
ImageView.install_action("zoom.in", None, ImageView.zoom_cb)
ImageView.install_action("zoom.out", None, ImageView.zoom_cb)
ImageView.install_action("zoom.reset", None, ImageView.zoom_cb)
ImageView.install_action("rotate", "i", ImageView.rotate_cb)

ImageView.set_accessible_role(Gtk.AccessibleRole.IMG)


def image_view_new(resource: str) -> Gtk.Widget:
    texture = Gdk.Texture.new_from_resource(resource)

    return ImageView(texture=texture)
