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

# Do a full rotation in 5 seconds.
#
# We do not save steps here but real timestamps.
# GtkMediaStream uses microseconds, so we will do so, too.
DURATION = 5 * GLib.USEC_PER_SEC


class GtkNuclearMediaStream(Gtk.MediaStream):
    """This time, we inherit from GtkMediaStream, which is already a GdkPaintable."""

    __gtype_name__ = "GtkNuclearMediaStream"

    def __init__(self) -> None:
        super().__init__()
        # This variable stores the progress of our video.
        self.progress = 0

        # This variable stores the timestamp of the last
        # time we updated the progress variable when the
        # video is currently playing.
        # This is so that we can always accurately compute the
        # progress we've had, even if the timeout does not
        # exactly work.
        self.last_time = 0

        # This variable again holds the ID of the timer that
        # updates our progress variable. Nothing changes about
        # how this works compared to the previous example.
        self.source_id = 0

        # This time, we don't have to add a timer here, because media
        # streams start paused.
        #
        # However, media streams need to tell GTK once they are initialized,
        # so we do that here.
        self.stream_prepared(False, True, True, DURATION)

    # GtkMediaStream is a GdkPaintable. So when we want to display video,
    # we have to implement the interface, just like in the animation example.

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        # We call the function from the previous example here.
        gtk_nuclear_snapshot(snapshot,
                             rgba(0, 0, 0, 1),  # black
                             rgba(0.9, 0.75, 0.15, 1.0),  # yellow
                             width, height,
                             360 * self.progress // DURATION)

    def do_get_current_image(self) -> Gdk.Paintable:
        # Same thing as with the animation
        return gtk_nuclear_icon_new(360 * self.progress // DURATION)

    def do_get_flags(self) -> Gdk.PaintableFlags:
        # And same thing as with the animation over here, too.
        return Gdk.PaintableFlags.STATIC_SIZE

    def do_play(self) -> bool:
        # If we're already at the end of the stream, we don't want
        # to start playing and exit early.
        if self.progress >= DURATION:
            return False

        # This time, we add the source only when we start playing.
        # C removes it when the stream is finalized; the timeout only holds the stream weakly instead.
        self.source_id = GLib.timeout_add(10, gtk_nuclear_media_stream_step, weakref.ref(self))

        # We also want to initialize our time, so that we can
        # do accurate updates.
        self.last_time = GLib.get_monotonic_time()

        # We successfully started playing, so we return TRUE here.
        return True

    def do_pause(self) -> None:
        # This function will be called when a playing stream
        # gets paused.
        # So we remove the updating source here and set it
        # back to 0 so that the finalize function doesn't try
        # to remove it again.
        GLib.source_remove(self.source_id)
        self.source_id = 0
        self.last_time = 0

    def do_seek(self, timestamp: int) -> None:
        # This is optional functionality for media streams,
        # but not being able to seek is kinda boring.
        # And it's trivial to implement, so let's go for it.
        self.progress = timestamp

        # Media streams are asynchronous, so seeking can take a while.
        # We however don't need that functionality, so we can just
        # report success.
        self.seek_success()

        # We also have to update our timestamp and tell the
        # paintable interface about the seek
        self.update(self.progress)
        self.invalidate_contents()


def gtk_nuclear_media_stream_step(data: weakref.ref) -> bool:
    nuclear = data()
    if nuclear is None:
        return GLib.SOURCE_REMOVE

    # Compute the time that has elapsed since the last time we were called
    # and add it to our current progress.
    current_time = GLib.main_current_source().get_time()
    nuclear.progress += current_time - nuclear.last_time

    # Check if we've ended
    if nuclear.progress > DURATION:
        if nuclear.get_loop():
            # We're looping. So make the progress loop using modulo
            nuclear.progress %= DURATION
        else:
            # Just make sure we don't overflow
            nuclear.progress = DURATION

    # Update the last time to the current timestamp.
    nuclear.last_time = current_time

    # Update the timestamp of the media stream
    nuclear.update(nuclear.progress)

    # We also need to invalidate our contents again.
    # After all, we are a video and not just an audio stream.
    nuclear.invalidate_contents()

    # Now check if we have finished playing and if so,
    # tell the media stream. The media stream will then
    # call our pause function to pause the stream.
    if nuclear.progress >= DURATION:
        nuclear.stream_ended()

    # The timeout function is removed by the pause function,
    # so we can just always return this value.
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
