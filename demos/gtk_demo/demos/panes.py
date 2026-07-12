"""Paned Widgets

The GtkPaned Widget divides its content area into two panes
with a divider in between that the user can adjust. A separate
child is placed into each pane. GtkPaned widgets can be split
horizontally or vertically. This test contains both a horizontal
and a vertical GtkPaned widget.

There are a number of options that can be set for each pane.
You can use the Inspector to adjust the options for each side
of each widget.
"""

from PyLiite4 import Gtk

window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        window = Gtk.Window()
        window.set_title("Paned Widgets")
        window.set_default_size(330, 250)
        window.set_resizable(False)
        window.set_display(do_widget.get_display())

        window.close_request.connect(close_request)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        window.set_child(vbox)

        frame = Gtk.Frame()
        vbox.append(frame)

        vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        frame.set_child(vpaned)

        hpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        vpaned.set_start_child(hpaned)
        vpaned.set_shrink_start_child(False)

        label = Gtk.Label(label="Hi there")
        label.set_margin_start(4)
        label.set_margin_end(4)
        label.set_margin_top(4)
        label.set_margin_bottom(4)
        label.set_hexpand(True)
        label.set_vexpand(True)
        hpaned.set_start_child(label)
        hpaned.set_shrink_start_child(False)

        label = Gtk.Label(label="Hello")
        label.set_margin_start(4)
        label.set_margin_end(4)
        label.set_margin_top(4)
        label.set_margin_bottom(4)
        label.set_hexpand(True)
        label.set_vexpand(True)
        hpaned.set_end_child(label)
        hpaned.set_shrink_end_child(False)

        label = Gtk.Label(label="Goodbye")
        label.set_margin_start(4)
        label.set_margin_end(4)
        label.set_margin_top(4)
        label.set_margin_bottom(4)
        label.set_hexpand(True)
        label.set_vexpand(True)
        vpaned.set_end_child(label)
        vpaned.set_shrink_end_child(False)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
