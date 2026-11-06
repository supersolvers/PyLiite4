"""Image Filtering
#Keywords: brightness, contrast, saturation, sepia, blur, color, posterize, graph

Show some image filters.

This includes both TV-style brightness and contrast controls, as well
as more complex effects such as sepia. All of the filters are applied
on the GPU.

Also demonstrate how to use GskPath for drawing simple graphs.
"""

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk

from .component_filter import ComponentFilter
from .filter_paintable import GtkFilterPaintable

window: Gtk.Window | None = None


def set_wait_cursor(widget: Gtk.Widget) -> None:
    widget.get_root().set_cursor_from_name("wait")


def unset_wait_cursor(widget: Gtk.Widget) -> None:
    widget.get_root().set_cursor(None)


def texture_loaded(source: Gtk.Picture, result: Gio.Task, data: object) -> None:
    try:
        texture = result.propagate_value().value
    except GLib.Error as error:
        print(error.message)
        return

    source.get_paintable().set_property("texture", texture)

    unset_wait_cursor(source)


def load_texture(task: Gio.Task, source_object: GObject.Object, file: Gio.File,
                 cancellable: Gio.Cancellable | None) -> None:
    try:
        texture = Gdk.Texture.new_from_file(file)
    except GLib.Error as error:
        task.return_error(error)
    else:
        task.return_value(texture)


def open_file_async(file: Gio.File, picture: Gtk.Picture) -> None:
    set_wait_cursor(picture)

    task = Gio.Task.new(picture, None, texture_loaded, None)
    # g_task_set_task_data() takes a pointer, which PyGObject can't pass, so the thread function gets the file
    # from a closure instead.
    task.run_in_thread(lambda task, source, data, cancellable: load_texture(task, source, file, cancellable))


def file_opened(source: Gtk.FileDialog, result: Gio.AsyncResult, picture: Gtk.Picture) -> None:
    try:
        file = source.open_finish(result)
    except GLib.Error as error:
        print(error.message)
        return

    open_file_async(file, picture)


def open_file(picture: Gtk.Picture) -> None:
    parent = picture.get_root()

    dialog = Gtk.FileDialog()

    filter = Gtk.FileFilter()
    filter.set_name("Images")
    filter.add_pixbuf_formats()
    filters = Gio.ListStore(item_type=Gtk.FileFilter)
    filters.append(filter)

    dialog.set_filters(filters)

    dialog.open(parent, None, file_opened, picture)


css_provider: Gtk.CssProvider | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global css_provider, window

    if css_provider is None:
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/image_filtering/image_filtering.css")

        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    if window is None:
        GObject.type_ensure(GtkFilterPaintable)
        GObject.type_ensure(ComponentFilter)

        # The UI file connects open_file with object="picture", which makes it a swapped handler, and PyGObject's
        # builder scope can't connect swapped handlers. Unswapped, the scope passes the picture as swap_data.
        builder = Gtk.Builder({"open_file": lambda button, swap_data: open_file(swap_data)})

        data = Gio.resources_lookup_data("/image_filtering/image_filtering.ui", Gio.ResourceLookupFlags.NONE)
        try:
            builder.add_from_string(data.get_data().decode().replace('object="picture"',
                                                                     'object="picture" swapped="no"'))
        except GLib.Error as error:
            print(error.message, end="")

        window = builder.get_object("window")
        window.close_request.connect(close_request)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
