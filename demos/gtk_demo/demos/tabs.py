"""Text View/Tabs

GtkTextView can position text at fixed positions, using tabs.
Tabs can specify alignment, and also allow aligning numbers
on the decimal point.

The example here has three tabs, with left, numeric and right
alignment.
"""

from PyLiite4 import Gtk, Pango

window: Gtk.Window | None = None


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_title("Tabs")
        window.set_display(do_widget.get_display())
        window.set_default_size(330, 130)
        window.set_resizable(False)
        window.destroy.connect(destroyed)

        view = Gtk.TextView()
        view.set_wrap_mode(Gtk.WrapMode.WORD)
        view.set_top_margin(20)
        view.set_bottom_margin(20)
        view.set_left_margin(20)
        view.set_right_margin(20)

        tabs = Pango.TabArray.new(3, True)
        tabs.set_tab(0, Pango.TabAlign.LEFT, 0)
        tabs.set_tab(1, Pango.TabAlign.DECIMAL, 150)
        tabs.set_decimal_point(1, ".")
        tabs.set_tab(2, Pango.TabAlign.RIGHT, 290)
        view.set_tabs(tabs)

        buffer = view.get_buffer()
        buffer.set_text("one\t2.0\tthree\nfour\t5.555\tsix\nseven\t88.88\tnine", -1)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        window.set_child(sw)
        sw.set_child(view)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
