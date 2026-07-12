"""Overlay/Interactive Overlay
#Keywords: GtkOverlay

Shows widgets in static positions over a main widget.

The overlaid widgets can be interactive controls such
as the entry in this example, or just decorative, like
the big blue label.
"""

from PyLiite4 import Gtk


def do_number(button: Gtk.Button, entry: Gtk.Entry) -> None:
    entry.set_text(button.get_label())


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
        window.set_default_size(500, 510)
        window.set_title("Interactive Overlay")

        overlay = Gtk.Overlay()
        grid = Gtk.Grid()
        overlay.set_child(grid)

        entry = Gtk.Entry()

        for j in range(5):
            for i in range(5):
                text = f"{5 * j + i}"
                button = Gtk.Button.new_with_label(text)
                button.set_hexpand(True)
                button.set_vexpand(True)
                button.clicked.connect(do_number, entry)
                grid.attach(button, i, j, 1, 1)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_can_target(False)
        overlay.add_overlay(vbox)
        vbox.set_halign(Gtk.Align.CENTER)
        vbox.set_valign(Gtk.Align.START)

        label = Gtk.Label(label="<span foreground='blue' weight='ultrabold' font='40'>Numbers</span>")
        label.set_use_markup(True)
        label.set_can_target(False)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        vbox.append(label)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        overlay.add_overlay(vbox)
        vbox.set_halign(Gtk.Align.CENTER)
        vbox.set_valign(Gtk.Align.CENTER)

        entry.set_placeholder_text("Your Lucky Number")
        entry.set_margin_top(8)
        entry.set_margin_bottom(8)
        vbox.append(entry)

        window.set_child(overlay)

        window.close_request.connect(close_request)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
