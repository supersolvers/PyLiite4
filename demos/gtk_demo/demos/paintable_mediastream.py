"""Paintable/Media Stream

GdkPaintable is also used by the GtkMediaStream class.

This demo code turns the nuclear media_stream into the object
GTK uses for videos. This allows treating the icon like a
regular video, so we can for example attach controls to it.

After all, what good is a media_stream if one cannot pause
it.
"""

import weakref

from PyLiite4 import Gdk, GLib, Gtk

from .paintable import gtk_nuclear_icon_new, gtk_nuclear_snapshot, rgba

window: Gtk.Window | None = None

# A full rotation takes 5 seconds.
#
# This stream keeps real timestamps rather than steps, in microseconds as GtkMediaStream does.
DURATION = 5 * GLib.USEC_PER_SEC


class GtkNuclearMediaStream(Gtk.MediaStream):
    """This time, we inherit from GtkMediaStream, which is already a GdkPaintable."""

    __gtype_name__ = "GtkNuclearMediaStream"

    def __init__(self) -> None:
        super().__init__()
        # The progress of the video.
        self.progress = 0

        # When the progress was last updated while the video plays. The progress is computed from it, so it stays
        # accurate even if the timeout doesn't fire exactly on time.
        self.last_time = 0

        # The ID of the timer that updates the progress, as in the previous example.
        self.source_id = 0

        # Media streams start paused, so no timer is added here. They do need to tell GTK once they are
        # initialized.
        self.stream_prepared(False, True, True, DURATION)

    # GtkMediaStream is a GdkPaintable, so displaying video means implementing that interface, as in the
    # animation example.

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        # The drawing function from the previous example.
        gtk_nuclear_snapshot(snapshot,
                             rgba(0, 0, 0, 1),  # black
                             rgba(0.9, 0.75, 0.15, 1.0),  # yellow
                             width, height,
                             360 * self.progress // DURATION)

    def do_get_current_image(self) -> Gdk.Paintable:
        # As in the animation.
        return gtk_nuclear_icon_new(360 * self.progress // DURATION)

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # As in the animation.
        return Gdk.PaintableFlags.STATIC_SIZE

    def do_play(self) -> bool:
        # A stream that is already at its end doesn't start playing.
        if self.progress >= DURATION:
            return False

        # The source is added only when playing starts.
        # C removes it when the stream is finalized; the timeout only holds the stream weakly instead.
        self.source_id = GLib.timeout_add(10, gtk_nuclear_media_stream_step, weakref.ref(self))

        # The start time, which the updates measure from.
        self.last_time = GLib.get_monotonic_time()

        # Playing started.
        return True

    def do_pause(self) -> None:
        # Called when a playing stream is paused. It removes the updating source and sets its ID back to 0, so
        # nothing tries to remove it again.
        GLib.source_remove(self.source_id)
        self.source_id = 0
        self.last_time = 0

    def do_seek(self, timestamp: int) -> None:
        # Seeking is optional for media streams, but trivial to implement here.
        self.progress = timestamp

        # Media streams are asynchronous, so seeking can take a while. This one seeks at once, so it reports
        # success straight away.
        self.seek_success()

        # The stream's timestamp and the paintable both need to know about the seek.
        self.update(self.progress)
        self.invalidate_contents()


def gtk_nuclear_media_stream_step(data: weakref.ref) -> bool:
    nuclear = data()
    if nuclear is None:
        return GLib.SOURCE_REMOVE

    # The time elapsed since the last call adds to the progress.
    current_time = GLib.main_current_source().get_time()
    nuclear.progress += current_time - nuclear.last_time

    if nuclear.progress > DURATION:
        if nuclear.get_loop():
            # A looping stream wraps the progress around.
            nuclear.progress %= DURATION
        else:
            # Otherwise the progress stops at the end rather than run past it.
            nuclear.progress = DURATION

    nuclear.last_time = current_time

    # The media stream's timestamp.
    nuclear.update(nuclear.progress)

    # The contents change too: this is a video, not just an audio stream.
    nuclear.invalidate_contents()

    # A stream that has finished playing tells the media stream, which then calls do_pause() to pause it.
    if nuclear.progress >= DURATION:
        nuclear.stream_ended()

    # do_pause() removes the timeout, so it can always continue here.
    return GLib.SOURCE_CONTINUE


def gtk_nuclear_media_stream_new() -> Gtk.MediaStream:
    """And finally, we add the simple constructor, for the other demos."""
    return GtkNuclearMediaStream()


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
        window.set_title("Nuclear MediaStream")
        window.set_default_size(300, 200)
        window.close_request.connect(close_request)

        nuclear = gtk_nuclear_media_stream_new()
        nuclear.set_loop(True)

        video = Gtk.Video.new_for_media_stream(nuclear)
        window.set_child(video)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
