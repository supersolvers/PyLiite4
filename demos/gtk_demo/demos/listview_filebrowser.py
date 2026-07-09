"""Lists/File browser
#Keywords: GListModel

This demo shows off the different layouts that are quickly achievable
with GtkListview and GtkGridView by implementing a file browser with
different views.
"""

import os

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk

window: Gtk.Window | None = None


class FileBrowserView(GObject.Object):
    """A simple object that holds the data for the different views."""

    __gtype_name__ = "FileBrowserView"

    factory = GObject.Property(type=Gtk.ListItemFactory, nick="factory", blurb="factory to use in the main view")
    icon_name = GObject.Property(type=str, nick="icon name", blurb="icon to display for selecting this view")
    title = GObject.Property(type=str, nick="title", blurb="title to display for selecting this view")
    orientation = GObject.Property(type=Gtk.Orientation, default=Gtk.Orientation.VERTICAL, nick="orientation",
                                   blurb="orientation of the view")


def filebrowser_get_display_name(object: GObject.Object, info: Gio.FileInfo | None) -> str | None:
    if not info:
        return None
    return info.get_attribute_string("standard::display-name")


def filebrowser_get_content_type(object: GObject.Object, info: Gio.FileInfo | None) -> str | None:
    if not info:
        return None
    return info.get_attribute_string("standard::content-type")


def filebrowser_get_size(object: GObject.Object, info: Gio.FileInfo | None) -> str | None:
    if not info:
        return None
    return GLib.format_size(info.get_attribute_uint64("standard::size"))


def filebrowser_get_icon(object: GObject.Object, info: Gio.FileInfo | None) -> Gio.Icon | None:
    if info:
        return info.get_attribute_object("standard::icon")
    return None


def filebrowser_up_clicked_cb(button: Gtk.Button, list: Gtk.DirectoryList) -> None:
    file = list.get_file().get_parent()
    if file is None:
        return
    list.set_file(file)


def filebrowser_view_activated_cb(view: Gtk.GridView, pos: int, list: Gtk.DirectoryList) -> None:
    info = view.get_model().get_item(pos)
    if info.get_file_type() == Gio.FileType.DIRECTORY:
        list.set_file(info.get_attribute_object("standard::file"))


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window
    if window is None:
        provider = Gtk.CssProvider()
        provider.load_from_resource("/listview_filebrowser/listview_filebrowser.css")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)

        # PyGObject's builder scope passes a signal's "object" in place of the emitter rather than after its
        # arguments, and not at all when it is an empty list model, so the handlers look it up themselves.
        builder = Gtk.Builder()
        builder.set_scope(Gtk.Builder.BuilderScope({
            "filebrowser_get_display_name": filebrowser_get_display_name,
            "filebrowser_get_content_type": filebrowser_get_content_type,
            "filebrowser_get_size": filebrowser_get_size,
            "filebrowser_get_icon": filebrowser_get_icon,
            "filebrowser_up_clicked_cb": lambda button: filebrowser_up_clicked_cb(
                button, builder.get_object("dirlist")),
            "filebrowser_view_activated_cb": lambda view, pos: filebrowser_view_activated_cb(
                view, pos, builder.get_object("dirlist")),
        }))
        builder.add_from_resource("/listview_filebrowser/listview_filebrowser.ui")
        window = builder.get_object("window")
        window.set_display(do_widget.get_display())

        window.close_request.connect(close_request)

        # Create the model and fill it with the contents of the current directory
        file = Gio.File.new_for_path(os.getcwd())
        dirlist = builder.get_object("dirlist")
        dirlist.set_file(file)

        # grab focus in the view
        view = builder.get_object("view")
        view.grab_focus()

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
    return window
