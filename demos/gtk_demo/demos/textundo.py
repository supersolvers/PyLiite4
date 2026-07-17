"""Text View/Undo and Redo

The GtkTextView supports undo and redo through the use of a
GtkTextBuffer. You can enable or disable undo support using
gtk_text_buffer_set_enable_undo().

Use Control+z to undo and Control+Shift+z or Control+y to
redo previously undone operations.
"""

from PyLiite4 import Gtk

window: Gtk.Window | None = None


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window
    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_default_size(330, 330)
        window.set_resizable(False)
        window.destroy.connect(destroyed)

        window.set_title("Undo and Redo")

        view = Gtk.TextView()
        view.set_wrap_mode(Gtk.WrapMode.WORD)
        view.set_pixels_below_lines(10)
        view.set_left_margin(20)
        view.set_right_margin(20)
        view.set_top_margin(20)
        view.set_bottom_margin(20)

        buffer = view.get_buffer()
        buffer.set_enable_undo(True)

        # this text cannot be undone
        buffer.begin_irreversible_action()
        iter = buffer.get_start_iter()
        buffer.insert(iter,
                      "The GtkTextView supports undo and redo through the use of a "
                      "GtkTextBuffer. You can enable or disable undo support using "
                      "gtk_text_buffer_set_enable_undo().\n"
                      "Type to add more text.\n"
                      "Use Control+z to undo and Control+Shift+z or Control+y to "
                      "redo previously undone operations.")
        buffer.end_irreversible_action()

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        window.set_child(sw)
        sw.set_child(view)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
