"""List Box/Controls

GtkListBox is well-suited for creating “button strips” — lists of
controls for use in preference dialogs or settings panels. To create
this style of list, use the .rich-list style class.
"""

from PyLiite4 import Gtk

window: Gtk.Window | None = None
switch_widget: Gtk.Switch | None = None
check: Gtk.CheckButton | None = None
image: Gtk.Image | None = None


def row_activated(list: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
    if switch_widget.is_ancestor(row):
        switch_widget.set_active(not switch_widget.get_active())
    elif check.is_ancestor(row):
        check.set_active(not check.get_active())
    elif image.is_ancestor(row):
        image.set_opacity(1.0 - image.get_opacity())


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, switch_widget, check, image

    if window is None:
        builder = Gtk.Builder({"row_activated": row_activated})

        builder.add_from_resource("/listbox_controls/listbox_controls.ui")

        window = builder.get_object("window")
        window.set_display(do_widget.get_display())
        window.close_request.connect(close_request)

        switch_widget = builder.get_object("switch")
        check = builder.get_object("check")
        image = builder.get_object("image")

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
