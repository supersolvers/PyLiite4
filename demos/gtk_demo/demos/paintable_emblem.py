"""Paintable/Emblems

This demo shows how GdkPaintable can be used to
overlay an emblem on top of an icon. The emblem
can either be another icon, or an arbitrary
paintable.
"""

from PyLiite4 import Gdk, GObject, Graphene, Gtk

from .paintable_animated import gtk_nuclear_animation_new

window: Gtk.Window | None = None


class DemoIcon(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "DemoIcon"

    def __init__(self) -> None:
        super().__init__()
        self.icon: Gdk.Paintable | None = None
        self.emblem: Gdk.Paintable | None = None
        self.flags = Gdk.PaintableFlags.STATIC_SIZE | Gdk.PaintableFlags.STATIC_CONTENTS

    def do_snapshot(self, snapshot: Gtk.Snapshot, width: float, height: float) -> None:
        self.icon.snapshot(snapshot, width, height)
        snapshot.save()
        snapshot.translate(Graphene.Point().init(0.5 * width, 0))
        self.emblem.snapshot(snapshot, 0.5 * width, 0.5 * height)
        snapshot.restore()

    def do_get_flags(self) -> Gdk.PaintableFlags:
        return self.flags

    def emblem_invalidated(self, emblem: Gdk.Paintable) -> None:
        # C connects gdk_paintable_invalidate_contents() swapped; a bound method, unlike a lambda, ends its
        # connection when the icon goes away, as C's dispose does.
        self.invalidate_contents()


def demo_icon_new_with_paintable(icon_name: str, emblem: Gdk.Paintable) -> Gdk.Paintable:
    theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
    icon = theme.lookup_icon(icon_name, None, 128, 1, Gtk.TextDirection.LTR, 0)

    self = DemoIcon()
    self.icon = icon
    self.emblem = emblem

    if (emblem.get_flags() & Gdk.PaintableFlags.STATIC_CONTENTS) == 0:
        self.flags &= ~Gdk.PaintableFlags.STATIC_CONTENTS
        emblem.invalidate_contents.connect(self.emblem_invalidated)

    return self


def demo_icon_new(icon_name: str, emblem_name: str) -> Gdk.Paintable:
    theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
    emblem = theme.lookup_icon(emblem_name, None, 128, 1, Gtk.TextDirection.LTR, 0)

    return demo_icon_new_with_paintable(icon_name, emblem)


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Paintable — Emblems")
        window.set_default_size(300, 200)
        window.close_request.connect(close_request)

        grid = Gtk.Grid()

        icon = demo_icon_new("folder", "starred")
        image = Gtk.Image.new_from_paintable(icon)
        image.set_pixel_size(256)
        image.set_hexpand(True)
        image.set_vexpand(True)
        grid.attach(image, 0, 0, 1, 1)

        icon = demo_icon_new_with_paintable("drive-multidisk", gtk_nuclear_animation_new(False))
        image = Gtk.Image.new_from_paintable(icon)
        image.set_pixel_size(256)
        image.set_hexpand(True)
        image.set_vexpand(True)
        grid.attach(image, 1, 0, 1, 1)

        window.set_child(grid)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
