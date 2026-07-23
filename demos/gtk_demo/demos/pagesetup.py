"""Printing/Page Setup
#Keywords: GtkPageSetup

GtkPageSetupUnixDialog can be used if page setup is needed
independent of a full printing dialog.
"""

from PyLiite4 import Gtk

window: Gtk.Window | None = None


def done_cb(dialog: Gtk.Dialog, response: int) -> None:
    dialog.destroy()


def window_destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        window = Gtk.PageSetupUnixDialog.new("Page Setup", do_widget)
        window.destroy.connect(window_destroyed)
        window.response.connect(done_cb)

    result = window
    if not result.get_visible():
        result.set_visible(True)
    else:
        result.destroy()

    return result
