"""Paintable/Animated Paintable

GdkPaintable also allows paintables to change.

This demo code gives an example of how this could work. It builds
on the previous simple example.

Paintables can also change their size, this works similarly, but
we will not demonstrate this here as our icon does not have any size.
"""

import weakref

from PyLiite4 import Gdk, GLib, GObject, Gtk

from .paintable import gtk_nuclear_icon_new, gtk_nuclear_snapshot, rgba

window: Gtk.Window | None = None

# A full rotation takes 5 seconds: the timeout does a single step every 10ms, so 500 steps take 5s.
MAX_PROGRESS = 500


class GtkNuclearAnimation(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "GtkNuclearAnimation"

    def __init__(self) -> None:
        super().__init__()
        self.draw_background = False

        # The progress of the animation. It counts upwards until it hits MAX_PROGRESS, then starts from scratch.
        self.progress = 0

        # A timer updates the animation, often enough for it to look smooth.
        #
        # Ideally this would attach to the frame clock, but a paintable has none, so a regular timeout stands in
        # and should trigger often enough to be smooth.
        #
        # C removes the timeout when the paintable is finalized. Python can't hook finalization, so the
        # timeout holds the paintable weakly and removes itself once the paintable is gone.
        self.source_id = GLib.timeout_add(10, gtk_nuclear_animation_step, weakref.ref(self))

    # The GdkPaintable interface

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        # The drawing function from the previous example.
        gtk_nuclear_snapshot(snapshot,
                             rgba(0, 0, 0, 1),  # black
                             rgba(0.9, 0.75, 0.15, 1.0) if self.draw_background  # yellow
                             else rgba(0, 0, 0, 0),  # transparent
                             width, height,
                             360 * self.progress // MAX_PROGRESS)

    def do_get_current_image(self) -> Gdk.Paintable:
        # Non-static paintables must implement this. It returns a static paintable with the same contents as this
        # one has now: the nuclear icon has a rotation property, so an instance of it does.
        return gtk_nuclear_icon_new(360 * self.progress // MAX_PROGRESS)

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # The animation changes the contents, so the static contents flag can't be set; the size still doesn't
        # change, so that flag can.
        return Gdk.PaintableFlags.STATIC_SIZE


def gtk_nuclear_animation_step(data: weakref.ref) -> bool:
    nuclear = data()
    if nuclear is None:
        return GLib.SOURCE_REMOVE

    # The progress resets at the maximum value: at MAX_PROGRESS the icon has rotated by 360 degrees, so it looks
    # identical to the unrotated one.
    nuclear.progress = (nuclear.progress + 1) % MAX_PROGRESS

    # Tells all listeners that the contents changed, so they redraw the paintable.
    nuclear.invalidate_contents()

    # Keeps the timeout running. A single-shot timeout would return GLib.SOURCE_REMOVE instead.
    return GLib.SOURCE_CONTINUE


def gtk_nuclear_animation_new(draw_background: bool) -> Gdk.Paintable:
    """And finally, we add the simple constructor, for the other demos."""
    nuclear = GtkNuclearAnimation()

    nuclear.draw_background = draw_background

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
        window.set_title("Nuclear Animation")
        window.set_default_size(300, 200)
        window.close_request.connect(close_request)

        nuclear = gtk_nuclear_animation_new(True)
        image = Gtk.Image.new_from_paintable(nuclear)
        image.set_pixel_size(256)
        window.set_child(image)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
