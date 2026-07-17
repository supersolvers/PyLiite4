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

# Do a full rotation in 5 seconds.
# We will register the timeout for doing a single step to
# be executed every 10ms, which means after 1000 steps
# 10s will have elapsed.
MAX_PROGRESS = 500


class GtkNuclearAnimation(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "GtkNuclearAnimation"

    def __init__(self) -> None:
        super().__init__()
        self.draw_background = False

        # This variable stores the progress of our animation.
        # We just count upwards until we hit MAX_PROGRESS and
        # then start from scratch.
        self.progress = 0

        # Add a timer here that constantly updates our animations.
        # We want to update it often enough to guarantee a smooth animation.
        #
        # Ideally, we'd attach to the frame clock, but because we do
        # not have it available here, we just use a regular timeout
        # that hopefully triggers often enough to be smooth.
        #
        # C removes the timeout when the paintable is finalized. Python can't hook finalization, so the
        # timeout holds the paintable weakly and removes itself once the paintable is gone.
        self.source_id = GLib.timeout_add(10, gtk_nuclear_animation_step, weakref.ref(self))

    # Again, we implement the functionality required by the GdkPaintable interface

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        # We call the function from the previous example here.
        gtk_nuclear_snapshot(snapshot,
                             rgba(0, 0, 0, 1),  # black
                             rgba(0.9, 0.75, 0.15, 1.0) if self.draw_background  # yellow
                             else rgba(0, 0, 0, 0),  # transparent
                             width, height,
                             360 * self.progress // MAX_PROGRESS)

    def do_get_current_image(self) -> Gdk.Paintable:
        # For non-static paintables, this function needs to be implemented.
        # It must return a static paintable with the same contents
        # as this one currently has.
        #
        # Luckily we added the rotation property to the nuclear icon
        # object previously, so we can just return an instance of that one.
        return gtk_nuclear_icon_new(360 * self.progress // MAX_PROGRESS)

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # This time, we cannot set the static contents flag because our animation
        # changes the contents.
        # However, our size still doesn't change, so report that flag.
        return Gdk.PaintableFlags.STATIC_SIZE


def gtk_nuclear_animation_step(data: weakref.ref) -> bool:
    nuclear = data()
    if nuclear is None:
        return GLib.SOURCE_REMOVE

    # Add 1 to the progress and reset it when we've reached
    # the maximum value.
    # The animation will rotate by 360 degrees at MAX_PROGRESS
    # so it will be identical to the original unrotated one.
    nuclear.progress = (nuclear.progress + 1) % MAX_PROGRESS

    # Now we need to tell all listeners that we've changed out contents
    # so that they can redraw this paintable.
    nuclear.invalidate_contents()

    # We want this timeout function to be called repeatedly,
    # so we return this value here.
    # If this was a single-shot timeout, we could also
    # return G_SOURCE_REMOVE here to get rid of it.
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
