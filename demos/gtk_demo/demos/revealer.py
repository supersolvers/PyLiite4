"""Revealer

GtkRevealer is a container that animates showing and hiding
of its sole child with nice transitions.
"""

from PyLiite4 import GLib, GObject, Gtk

count = 0
timeout = 0
revealers: list[Gtk.Revealer] = []


def change_direction(revealer: Gtk.Revealer, pspec: GObject.ParamSpec) -> None:
    if revealer.get_mapped():
        revealed = revealer.get_child_revealed()
        revealer.set_reveal_child(not revealed)


def reveal_one(window: Gtk.Window) -> bool:
    global count, timeout

    revealer = revealers[count]

    revealer.set_reveal_child(True)

    revealer.notify["child-revealed"].connect(change_direction)
    count += 1

    if count >= 9:
        timeout = 0
        return GLib.SOURCE_REMOVE
    else:
        return GLib.SOURCE_CONTINUE


window: Gtk.Window | None = None


def on_destroy(widget: Gtk.Window) -> None:
    global window, timeout
    window = None
    if timeout != 0:
        GLib.source_remove(timeout)
        timeout = 0


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, count, timeout

    if window is None:
        builder = Gtk.Builder.new_from_resource("/revealer/revealer.ui")
        window = builder.get_object("window")
        # Where C keeps the revealers as data on the window, keep them in a list
        revealers[:] = [builder.get_object(f"revealer{i}") for i in range(10)]
        window.set_display(do_widget.get_display())
        window.destroy.connect(on_destroy)

    if not window.get_visible():
        count = 0
        timeout = GLib.timeout_add(690, reveal_one, window)
        window.set_visible(True)
    else:
        window.destroy()

    return window
