"""Text View/Automatic Scrolling
#Keywords: GtkTextView, GtkScrolledWindow

This example demonstrates how to use the gravity of
GtkTextMarks to keep a text view scrolled to the bottom
while appending text.
"""

from PyLiite4 import GLib, Gtk

window: Gtk.Window | None = None

scroll_to_end_count = 0
scroll_to_bottom_count = 0


def scroll_to_end(textview: Gtk.TextView) -> bool:
    """Scroll to the end of the buffer."""
    global scroll_to_end_count

    buffer = textview.get_buffer()

    # Get "end" mark. It's located at the end of buffer because
    # of right gravity
    mark = buffer.get_mark("end")
    iter = buffer.get_iter_at_mark(mark)

    # and insert some text at its position, the iter will be
    # revalidated after insertion to point to the end of inserted text
    spaces = " " * scroll_to_end_count
    scroll_to_end_count += 1
    buffer.insert(iter, "\n")
    buffer.insert(iter, spaces)
    buffer.insert(iter, f"Scroll to end scroll to end scroll to end scroll to end {scroll_to_end_count}")

    # Now scroll the end mark onscreen.
    textview.scroll_mark_onscreen(mark)

    # Emulate typewriter behavior, shift to the left if we
    # are far enough to the right.
    if scroll_to_end_count > 150:
        scroll_to_end_count = 0

    return GLib.SOURCE_CONTINUE


def scroll_to_bottom(textview: Gtk.TextView) -> bool:
    """Scroll to the bottom of the buffer."""
    global scroll_to_bottom_count

    buffer = textview.get_buffer()

    # Get end iterator
    iter = buffer.get_end_iter()

    # and insert some text at it, the iter will be revalidated
    # after insertion to point to the end of inserted text
    spaces = " " * scroll_to_bottom_count
    scroll_to_bottom_count += 1
    buffer.insert(iter, "\n")
    buffer.insert(iter, spaces)
    buffer.insert(iter, "Scroll to bottom scroll to bottom scroll "
                        f"to bottom scroll to bottom {scroll_to_bottom_count}")

    # Move the iterator to the beginning of line, so we don't scroll
    # in horizontal direction
    iter.set_line_offset(0)

    # and place the mark at iter. the mark will stay there after we
    # insert some text at the end because it has left gravity.
    mark = buffer.get_mark("scroll")
    buffer.move_mark(mark, iter)

    # Scroll the mark onscreen.
    textview.scroll_mark_onscreen(mark)

    # Shift text back if we got enough to the right.
    if scroll_to_bottom_count > 40:
        scroll_to_bottom_count = 0

    return GLib.SOURCE_CONTINUE


def setup_scroll(textview: Gtk.TextView, to_end: bool) -> int:
    buffer = textview.get_buffer()
    iter = buffer.get_end_iter()

    if to_end:
        # If we want to scroll to the end, including horizontal scrolling,
        # then we just create a mark with right gravity at the end of the
        # buffer. It will stay at the end unless explicitly moved with
        # gtk_text_buffer_move_mark.
        buffer.create_mark("end", iter, False)

        # Add scrolling timeout.
        return GLib.timeout_add(50, scroll_to_end, textview)
    else:
        # If we want to scroll to the bottom, but not scroll horizontally,
        # then an end mark won't do the job. Just create a mark so we can
        # use it with gtk_text_view_scroll_mark_onscreen, we'll position it
        # explicitly when needed. Use left gravity so the mark stays where
        # we put it after inserting new text.
        buffer.create_mark("scroll", iter, True)

        # Add scrolling timeout.
        return GLib.timeout_add(100, scroll_to_bottom, textview)


def remove_timeout(window: Gtk.Widget, timeout: int) -> None:
    GLib.source_remove(timeout)


def create_text_view(hbox: Gtk.Box, to_end: bool) -> None:
    swindow = Gtk.ScrolledWindow()
    hbox.append(swindow)
    textview = Gtk.TextView()
    swindow.set_child(textview)

    timeout = setup_scroll(textview, to_end)

    # Remove the timeout in destroy handler, so we don't try to
    # scroll destroyed widget.
    textview.destroy.connect(remove_timeout, timeout)


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window
    if window is None:
        window = Gtk.Window()
        window.set_title("Automatic Scrolling")
        window.destroy.connect(destroyed)
        window.set_default_size(600, 400)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.set_homogeneous(True)
        window.set_child(hbox)

        create_text_view(hbox, True)
        create_text_view(hbox, False)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
