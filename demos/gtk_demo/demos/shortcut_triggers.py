"""Shortcuts
#Keywords: GtkShortcutController

GtkShortcut is the abstraction used by GTK to handle shortcuts from
keyboard or other input devices.

Shortcut triggers can be used to weave complex sequences of key
presses into sophisticated mechanisms to activate shortcuts.

This demo code shows creative ways to do that.
"""

from collections.abc import Callable

from PyLiite4 import Gdk, GLib, Gtk

window: Gtk.Window | None = None


def shortcut_activated(widget: Gtk.Widget, unused: GLib.Variant | None, row: Gtk.Label) -> bool:
    print(f"activated {row.get_label()}")
    return True


def create_ctrl_g() -> Gtk.ShortcutTrigger:
    return Gtk.KeyvalTrigger.new(Gdk.KEY_g, Gdk.ModifierType.CONTROL_MASK)


def create_x() -> Gtk.ShortcutTrigger:
    return Gtk.KeyvalTrigger.new(Gdk.KEY_x, 0)


shortcuts: list[tuple[str, Callable[[], Gtk.ShortcutTrigger]]] = [
    ("Press Ctrl-G", create_ctrl_g),
    ("Press X", create_x),
]


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Shortcuts")
        window.set_default_size(200, -1)
        window.set_resizable(False)
        window.destroy.connect(destroyed)

        list = Gtk.ListBox()
        list.set_margin_top(6)
        list.set_margin_bottom(6)
        list.set_margin_start(6)
        list.set_margin_end(6)
        window.set_child(list)

        for description, create_trigger_func in shortcuts:
            row = Gtk.Label(label=description)
            list.insert(row, -1)

            controller = Gtk.ShortcutController()
            controller.set_scope(Gtk.ShortcutScope.GLOBAL)
            row.add_controller(controller)

            shortcut = Gtk.Shortcut.new(create_trigger_func(), Gtk.CallbackAction.new(shortcut_activated, row))
            controller.add_shortcut(shortcut)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
