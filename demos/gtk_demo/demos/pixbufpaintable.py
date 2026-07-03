"""A paintable that plays a GdkPixbufAnimation, used by images."""

from PyLiite4 import Gdk, GdkPixbuf, GLib, GObject


class PixbufPaintable(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "PixbufPaintable"

    def __init__(self, **properties: object) -> None:
        self._resource_path: str | None = None
        self.anim: GdkPixbuf.PixbufAnimation | None = None
        self.iter: GdkPixbuf.PixbufAnimationIter | None = None
        self.timeout = 0
        super().__init__(**properties)

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        self.iter.advance(None)
        pixbuf = self.iter.get_pixbuf()
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)

        texture.snapshot(snapshot, width, height)

    def do_get_intrinsic_width(self) -> int:
        return self.anim.get_width()

    def do_get_intrinsic_height(self) -> int:
        return self.anim.get_height()

    def set_resource_path(self, resource_path: str) -> None:
        self._resource_path = resource_path

        self.anim = GdkPixbuf.PixbufAnimation.new_from_resource(resource_path)
        self.iter = self.anim.get_iter(None)

        delay = self.iter.get_delay_time()
        self.timeout = GLib.timeout_add(delay, delay_cb, self)

        self.invalidate_contents()

        self.notify("resource-path")

    @GObject.Property(type=str)
    def resource_path(self) -> str | None:
        return self._resource_path

    @resource_path.setter
    def resource_path(self, value: str) -> None:
        self.set_resource_path(value)

    def do_dispose(self) -> None:
        self._resource_path = None
        self.anim = None
        self.iter = None
        if self.timeout:
            GLib.source_remove(self.timeout)
            self.timeout = 0

        GObject.Object.do_dispose(self)


def delay_cb(self: PixbufPaintable) -> bool:
    # In C, the timeout doesn't keep the paintable alive, and disposing the paintable removes it. Here the
    # timeout holds the paintable, so it stops once nothing else does, and lets it go.
    if self.__grefcount__ <= 1:
        self.timeout = 0
        return GLib.SOURCE_REMOVE

    delay = self.iter.get_delay_time()
    self.timeout = GLib.timeout_add(delay, delay_cb, self)

    self.invalidate_contents()

    return GLib.SOURCE_REMOVE


def pixbuf_paintable_new_from_resource(path: str) -> Gdk.Paintable:
    return PixbufPaintable(resource_path=path)
