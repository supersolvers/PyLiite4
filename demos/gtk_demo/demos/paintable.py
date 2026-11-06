"""Paintable/Simple Paintable

GdkPaintable is an interface used by GTK for drawings of any sort
that do not require layouting or positioning.

This demo code gives a simple example on how a paintable can
be created.

Paintables can be used in many places inside GTK widgets, but the
most common usage is inside GtkImage and that's what we're going
to do here.
"""

import math

from PyLiite4 import Gdk, GObject, Graphene, Gsk, Gtk

window: Gtk.Window | None = None


def rgba(red: float, green: float, blue: float, alpha: float) -> Gdk.RGBA:
    """A GdkRGBA, as C writes (GdkRGBA) { red, green, blue, alpha }."""
    color = Gdk.RGBA()
    color.red, color.green, color.blue, color.alpha = red, green, blue, alpha
    return color


RADIUS = 0.3


def gtk_nuclear_snapshot(snapshot: Gtk.Snapshot, foreground: Gdk.RGBA, background: Gdk.RGBA,
                         width: float, height: float, rotation: float) -> None:
    """The function that draws the actual icon.

    We make it a custom function so that it can be called from all the other demos, too.
    """
    snapshot.append_color(background, Graphene.Rect().init(0, 0, width, height))

    size = min(width, height)

    snapshot.save()

    snapshot.translate(Graphene.Point().init(width / 2.0, height / 2.0))
    snapshot.scale(size, size)
    snapshot.rotate(rotation)

    builder = Gsk.PathBuilder.new()
    builder.add_circle(Graphene.Point.zero(), 0.1)
    path = builder.to_path()
    snapshot.append_fill(path, Gsk.FillRule.WINDING, foreground)

    stroke = Gsk.Stroke.new(RADIUS)
    stroke.set_dash([RADIUS * math.pi / 3])
    builder = Gsk.PathBuilder.new()
    builder.add_circle(Graphene.Point.zero(), RADIUS)
    path = builder.to_path()
    snapshot.append_stroke(path, stroke, foreground)

    snapshot.restore()


class GtkNuclearIcon(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "GtkNuclearIcon"

    def __init__(self) -> None:
        super().__init__()
        # The rotation. Nothing here uses it, but the follow-up demos do.
        self.rotation = 0.0

    # The GdkPaintable interface

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        # The only function a paintable has to implement: it does the actual drawing.
        gtk_nuclear_snapshot(snapshot,
                             rgba(0, 0, 0, 1),  # black
                             rgba(0.9, 0.75, 0.15, 1.0),  # yellow
                             width, height,
                             self.rotation)

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # The flags tell GTK that this image never changes. That allows many optimizations, so a paintable should
        # always set them when they apply.
        return Gdk.PaintableFlags.STATIC_CONTENTS | Gdk.PaintableFlags.STATIC_SIZE


def gtk_nuclear_icon_new(rotation: float) -> Gdk.Paintable:
    """And finally, we add a simple constructor, so that the other examples can use it."""
    nuclear = GtkNuclearIcon()
    nuclear.rotation = rotation

    return nuclear


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
        window.set_title("Nuclear Icon")
        window.set_default_size(300, 200)
        window.close_request.connect(close_request)

        nuclear = gtk_nuclear_icon_new(0.0)
        image = Gtk.Image.new_from_paintable(nuclear)
        image.set_pixel_size(256)
        window.set_child(image)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
