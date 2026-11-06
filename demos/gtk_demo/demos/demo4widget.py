"""Demo4Widget: text used as a mask for an animated gradient, used by the Masking demo.

Ported from GTK Demo's demo4widget.c and demo4widget.h.
"""

from PyLiite4 import Gdk, GObject, Graphene, Gsk, Gtk, Pango

from .hsla import GdkHSLA, _gdk_hsla_init_from_rgba, _gdk_rgba_init_from_hsla


def rotate_color(rgba: Gdk.RGBA) -> None:
    hsla = GdkHSLA()

    _gdk_hsla_init_from_rgba(hsla, rgba)
    hsla.hue -= 1
    _gdk_rgba_init_from_hsla(rgba, hsla)


def color_stop(offset: float, color: Gdk.RGBA) -> Gsk.ColorStop:
    stop = Gsk.ColorStop()
    stop.offset = offset
    stop.color = color
    return stop


def rgba(red: float, green: float, blue: float, alpha: float) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = red, green, blue, alpha
    return color


class Demo4Widget(Gtk.Widget):
    __gtype_name__ = "Demo4Widget"

    def __init__(self) -> None:
        super().__init__()
        self._progress = 0.5

        self.n_stops = 8
        # The stops' colours; C keeps them in GskColorStops.
        self.colors = [rgba(1, 0, 0, 1)]
        self.offsets = [0.0]

        for i in range(1, self.n_stops):
            hsla = GdkHSLA()

            self.offsets.append(i / (self.n_stops - 1))
            _gdk_hsla_init_from_rgba(hsla, self.colors[i - 1])
            hsla.hue += 360.0 / (self.n_stops - 1)
            color = Gdk.RGBA()
            _gdk_rgba_init_from_hsla(color, hsla)
            self.colors.append(color)

        self.layout = self.create_pango_layout("123")
        context = self.layout.get_context()
        desc = context.get_font_description().copy()
        desc.set_weight(Pango.Weight.BOLD)
        desc.set_size(210 * Pango.SCALE)
        self.layout.set_font_description(desc)

        self.tick = self.add_tick_callback(self.rotate_colors)

    @GObject.Property(type=float, minimum=0.0, maximum=1.0, default=0.5)
    def progress(self) -> float:
        return self._progress

    @progress.setter
    def progress(self, value: float) -> None:
        self._progress = value
        self.queue_draw()

    def rotate_colors(self, widget: Gtk.Widget, clock: Gdk.FrameClock) -> bool:
        for i in range(self.n_stops):
            rotate_color(self.colors[i])

        widget.queue_draw()

        return True  # GLib.SOURCE_CONTINUE

    def do_dispose(self) -> None:
        if self.tick:
            self.remove_tick_callback(self.tick)
            self.tick = 0

        Gtk.Widget.do_dispose(self)

    def snapshot_content(self, snapshot: Gtk.Snapshot, mode: Gsk.MaskMode) -> None:
        width = self.get_width()
        height = self.get_height()

        snapshot.push_mask(mode)
        layout_width, layout_height = self.layout.get_pixel_size()
        scale = min(width / layout_width, height / layout_height)
        snapshot.translate(Graphene.Point().init((width - scale * layout_width) / 2,
                                                 (height - scale * layout_height) / 2))
        snapshot.scale(scale, scale)
        snapshot.append_layout(self.layout, rgba(0, 0, 0, 1))
        snapshot.pop()

        snapshot.append_linear_gradient(Graphene.Rect().init(0, 0, width, height),
                                        Graphene.Point().init(0, 0),
                                        Graphene.Point().init(width, height),
                                        [color_stop(offset, color) for offset, color in zip(self.offsets, self.colors)])
        snapshot.pop()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = self.get_width()
        height = self.get_height()

        snapshot.push_mask(Gsk.MaskMode.INVERTED_LUMINANCE)
        snapshot.append_linear_gradient(Graphene.Rect().init(0, 0, width, height),
                                        Graphene.Point().init(0, 0),
                                        Graphene.Point().init(width, 0),
                                        [color_stop(max(0.0, self._progress - 5.0 / width), rgba(1, 1, 1, 1)),
                                         color_stop(min(1.0, self._progress + 5.0 / width), rgba(0, 0, 0, 1))])
        snapshot.pop()
        self.snapshot_content(snapshot, Gsk.MaskMode.INVERTED_ALPHA)
        snapshot.pop()

        snapshot.push_mask(Gsk.MaskMode.LUMINANCE)
        snapshot.append_linear_gradient(Graphene.Rect().init(0, 0, width, height),
                                        Graphene.Point().init(0, 0),
                                        Graphene.Point().init(width, 0),
                                        [color_stop(max(0.0, self._progress - 5.0 / width), rgba(1, 1, 1, 1)),
                                         color_stop(min(1.0, self._progress + 5.0 / width), rgba(0, 0, 0, 1))])
        snapshot.pop()
        self.snapshot_content(snapshot, Gsk.MaskMode.ALPHA)
        snapshot.pop()


def demo4_widget_new() -> Gtk.Widget:
    return Demo4Widget()
