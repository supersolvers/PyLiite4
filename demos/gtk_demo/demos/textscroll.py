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

    # The "end" mark stays at the end of the buffer because it has right gravity.
    mark = buffer.get_mark("end")
    iter = buffer.get_iter_at_mark(mark)

    # Text inserted at the mark's position revalidates the iter to point to the end of the inserted text.
    spaces = " " * scroll_to_end_count
    scroll_to_end_count += 1
    buffer.insert(iter, "\n")
    buffer.insert(iter, spaces)
    buffer.insert(iter, f"Scroll to end scroll to end scroll to end scroll to end {scroll_to_end_count}")

    textview.scroll_mark_onscreen(mark)

    # Like a typewriter, the text shifts back to the left once it is far enough to the right.
    if scroll_to_end_count > 150:
        scroll_to_end_count = 0

    return GLib.SOURCE_CONTINUE


def scroll_to_bottom(textview: Gtk.TextView) -> bool:
    """Scroll to the bottom of the buffer."""
    global scroll_to_bottom_count

    buffer = textview.get_buffer()

    iter = buffer.get_end_iter()

    # Text inserted at the iter revalidates it to point to the end of the inserted text.
    spaces = " " * scroll_to_bottom_count
    scroll_to_bottom_count += 1
    buffer.insert(iter, "\n")
    buffer.insert(iter, spaces)
    buffer.insert(iter, "Scroll to bottom scroll to bottom scroll "
                        f"to bottom scroll to bottom {scroll_to_bottom_count}")

    # The iter moves to the beginning of the line, so the view doesn't scroll horizontally.
    iter.set_line_offset(0)

    # The mark has left gravity, so it stays at the iter when more text is inserted at the end.
    mark = buffer.get_mark("scroll")
    buffer.move_mark(mark, iter)

    textview.scroll_mark_onscreen(mark)

    # The text shifts back once it is far enough to the right.
    if scroll_to_bottom_count > 40:
        scroll_to_bottom_count = 0

    return GLib.SOURCE_CONTINUE


def setup_scroll(textview: Gtk.TextView, to_end: bool) -> int:
    buffer = textview.get_buffer()
    iter = buffer.get_end_iter()

    if to_end:
        # Scrolling to the end, horizontally too, takes a mark with right gravity at the end of the buffer. It
        # stays at the end unless move_mark() moves it.
        buffer.create_mark("end", iter, False)

        return GLib.timeout_add(50, scroll_to_end, textview)
    else:
        # Scrolling to the bottom without scrolling horizontally can't use an end mark. This mark is only there
        # for scroll_mark_onscreen(), and is positioned explicitly when needed; it has left gravity, so it stays
        # where it was put when new text is inserted.
        buffer.create_mark("scroll", iter, True)

        return GLib.timeout_add(100, scroll_to_bottom, textview)


def remove_timeout(window: Gtk.Widget, timeout: int) -> None:
    GLib.source_remove(timeout)


def create_text_view(hbox: Gtk.Box, to_end: bool) -> None:
    swindow = Gtk.ScrolledWindow()
    hbox.append(swindow)
    textview = Gtk.TextView()
    swindow.set_child(textview)

    timeout = setup_scroll(textview, to_end)

    # The destroy handler removes the timeout, so nothing tries to scroll a destroyed widget.
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
