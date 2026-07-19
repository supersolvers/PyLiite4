"""Paintable/SVG

This demo shows using GtkSvg to display an SVG image in
a GtkPicture that can be scaled by resizing the window.
"""

from PyLiite4 import Gio, GLib, Gtk


def image_clicked(click: Gtk.GestureClick, n_press: int, x: float, y: float, image: Gtk.Picture) -> None:
    # C calls gtk_image_get_paintable() on what is really a GtkPicture.
    paintable = image.get_paintable()
    state = paintable.get_state()

    if state < 63:
        paintable.set_state(state + 1)
    else:
        paintable.set_state(0)


def open_response_cb(dialog: Gtk.FileDialog, result: Gio.AsyncResult, window: Gtk.Window) -> None:
    try:
        file = dialog.open_finish(result)
    except GLib.Error:
        file = None

    if file:
        bytes, _etag = file.load_bytes(None)
        paintable = Gtk.Svg.new_from_bytes(bytes)

        image = Gtk.Picture()
        window.set_child(image)
        controller = Gtk.GestureClick()
        controller.pressed.connect(image_clicked, image)
        image.add_controller(controller)
        image.set_paintable(paintable)


def show_file_open(button: Gtk.Widget, window: Gtk.Window) -> None:
    dialog = Gtk.FileDialog()
    dialog.set_title("Open svg image")

    filter = Gtk.FileFilter()
    filter.add_mime_type("image/svg+xml")
    filter.add_mime_type("image/x-gtk-path-animation")
    filter.add_pattern("*.gpa")
    filters = Gio.ListStore(item_type=Gtk.FileFilter)
    filters.append(filter)
    dialog.set_filters(filters)

    dialog.open(button.get_root(), None, open_response_cb, window)


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
        header = Gtk.HeaderBar()
        window.set_titlebar(header)
        window.set_default_size(330, 330)
        window.set_title("Paintable — SVG")
        window.close_request.connect(close_request)

        button = Gtk.Button.new_with_mnemonic("_Open")
        header.pack_start(button)

        image = Gtk.Picture()
        image.set_size_request(16, 16)

        button.clicked.connect(show_file_open, window)

        window.set_child(image)

        paintable = Gtk.Svg.new_from_resource("/paintable_svg/org.gtk.gtk4.NodeEditor.Devel.svg")
        image.set_paintable(paintable)

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
