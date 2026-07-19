"""Cursors

Demonstrates a useful set of available cursors. The cursors shown here are the
ones defined by CSS, which we assume to be available. The example shows creating
cursors by name or from an image, with or without a fallback.
"""

import math
from collections.abc import Callable

from PyLiite4 import Gdk, GdkPixbuf, GLib, Gtk

# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
# (C also clears it from a "destroy" handler; the weak reference covers that.)
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def cursor_callback(cursor: Gdk.Cursor, cursor_size: int, scale: float,
                    data: object = None) -> tuple[Gdk.Texture | None, int, int, int, int]:
    # The out arguments width, height, hotspot_x and hotspot_y are returned after the texture.
    scaled_size = math.ceil(cursor_size * scale)

    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_resource_at_scale("/cursors/images/gtk-logo.svg",
                                                             scaled_size, scaled_size,
                                                             True)
    except GLib.Error as error:
        print(error.message)
        return None, 0, 0, 0, 0

    texture = Gdk.Texture.new_for_pixbuf(pixbuf)

    width = cursor_size
    height = cursor_size
    hotspot_x = int(18 * cursor_size / 32.0)
    hotspot_y = int(2 * cursor_size / 32.0)

    return texture, width, height, hotspot_x, hotspot_y


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        provider = Gtk.CssProvider()
        provider.load_from_resource("/cursors/cursors.css")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),
                                                  provider,
                                                  800)

        builder = Gtk.Builder.new_from_resource("/cursors/cursors.ui")
        window = builder.get_object("window")
        window_ref = window.weak_ref()
        window.set_display(do_widget.get_display())
        logo_callback = builder.get_object("logo_callback")
        cursor = Gdk.Cursor.new_from_callback(cursor_callback, None)
        logo_callback.set_cursor(cursor)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
