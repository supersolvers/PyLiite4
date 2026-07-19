"""Image Scaling
#Keywords: zoom, scale, filter, action, menu

The custom widget we create here is similar to a GtkPicture,
but allows setting a zoom level and filtering mode for the
displayed paintable.

It also demonstrates how to add a context menu to a custom
widget and connect it with widget actions.

The context menu has items to change the zoom level.
"""

import math

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk

from .imageview import image_view_new

window: Gtk.Window | None = None
cancellable: Gio.Cancellable | None = None


def load_texture(task: Gio.Task, source_object: GObject.Object, file: Gio.File,
                 cancellable: Gio.Cancellable | None) -> None:
    try:
        texture = Gdk.Texture.new_from_file(file)
    except GLib.Error as error:
        task.return_error(error)
    else:
        task.return_value(texture)


def set_wait_cursor(widget: Gtk.Widget) -> None:
    widget.get_root().set_cursor_from_name("wait")


def unset_wait_cursor(widget: Gtk.Widget) -> None:
    widget.get_root().set_cursor(None)


def texture_loaded(source: Gtk.Widget, result: Gio.Task, data: Gtk.Widget) -> None:
    try:
        texture = result.propagate_value().value
    except GLib.Error as error:
        print(error.message)
        return

    if window is None:
        return

    unset_wait_cursor(data)

    data.set_property("texture", texture)


def open_file_async(file: Gio.File, demo: Gtk.Widget) -> None:
    set_wait_cursor(demo)

    task = Gio.Task.new(demo, cancellable, texture_loaded, demo)
    # g_task_set_task_data() takes a pointer, which PyGObject can't pass, so the thread function gets the file
    # from a closure instead
    task.run_in_thread(lambda task, source, data, cancellable: load_texture(task, source, file, cancellable))


def open_portland_rose(button: Gtk.Button, demo: Gtk.Widget) -> None:
    file = Gio.File.new_for_uri("resource:///transparent/portland-rose.jpg")
    open_file_async(file, demo)


def open_large_image(button: Gtk.Button, demo: Gtk.Widget) -> None:
    file = Gio.File.new_for_uri("resource:///org/gtk/Demo4/large-image.png")
    open_file_async(file, demo)


def file_opened(source: Gtk.FileDialog, result: Gio.AsyncResult, data: Gtk.Widget) -> None:
    try:
        file = source.open_finish(result)
    except GLib.Error as error:
        print(error.message)
        return

    open_file_async(file, data)


def open_file(picker: Gtk.Widget, demo: Gtk.Widget) -> None:
    parent = picker.get_root()

    dialog = Gtk.FileDialog()

    filter = Gtk.FileFilter()
    filter.set_name("Images")
    filter.add_pixbuf_formats()
    filters = Gio.ListStore(item_type=Gtk.FileFilter)
    filters.append(filter)

    dialog.set_filters(filters)

    dialog.open(parent, None, file_opened, demo)


def rotate(button: Gtk.Button, demo: Gtk.Widget) -> None:
    angle = demo.get_property("angle")

    angle = math.fmod(angle + 90, 360)

    demo.set_property("angle", angle)


def transform_to(binding: GObject.Binding, from_: float) -> float:
    return math.pow(2, from_)


def transform_from(binding: GObject.Binding, to: float) -> float:
    return math.log2(to)


def free_cancellable() -> None:
    global cancellable
    cancellable.cancel()
    cancellable = None


def cancel_load(widget: Gtk.Widget, args: GLib.Variant | None, cancellable: Gio.Cancellable) -> bool:
    unset_wait_cursor(widget)
    cancellable.cancel()
    return True


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    free_cancellable()
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, cancellable

    if window is None:
        window = Gtk.Window()
        window.set_title("Image Scaling")
        window.set_default_size(600, 400)
        window.set_display(do_widget.get_display())
        window.close_request.connect(close_request)

        cancellable = Gio.Cancellable()

        controller = Gtk.ShortcutController()
        controller.add_shortcut(Gtk.Shortcut.new(Gtk.KeyvalTrigger.new(Gdk.KEY_Escape, 0),
                                                 Gtk.CallbackAction.new(cancel_load, cancellable)))
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        window.add_controller(controller)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        window.set_child(box)

        sw = Gtk.ScrolledWindow()
        sw.set_vexpand(True)
        box.append(sw)

        widget = image_view_new("/transparent/portland-rose.jpg")
        vp = Gtk.Viewport()
        vp.set_scroll_to_focus(False)

        vp.set_child(widget)
        sw.set_child(vp)

        box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.append(box2)

        button = Gtk.Button.new_from_icon_name("document-open-symbolic")
        button.set_tooltip_text("Open File")
        button.clicked.connect(open_file, widget)
        box2.append(button)

        button = Gtk.Button()
        button.set_child(Gtk.Image.new_from_resource("/org/gtk/Demo4/portland-rose-thumbnail.png"))
        button.add_css_class("image-button")
        button.set_tooltip_text("Portland Rose")
        button.clicked.connect(open_portland_rose, widget)
        box2.append(button)

        button = Gtk.Button()
        button.set_child(Gtk.Image.new_from_resource("/org/gtk/Demo4/large-image-thumbnail.png"))
        button.add_css_class("image-button")
        button.set_tooltip_text("Large image")
        button.clicked.connect(open_large_image, widget)
        box2.append(button)

        button = Gtk.Button.new_from_icon_name("object-rotate-right-symbolic")
        button.set_tooltip_text("Rotate")
        button.clicked.connect(rotate, widget)
        box2.append(button)

        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, -10., 10., 0.1)
        scale.add_mark(0., Gtk.PositionType.TOP, None)
        scale.set_tooltip_text("Zoom")
        scale.update_property([Gtk.AccessibleProperty.LABEL], ["Zoom"])
        scale.set_value(0.)
        scale.set_hexpand(True)
        box2.append(scale)

        dropdown = Gtk.DropDown(model=Gtk.StringList.new(["Linear", "Nearest", "Trilinear"]))
        dropdown.set_tooltip_text("Filter")
        dropdown.update_property([Gtk.AccessibleProperty.LABEL], ["Filter"])
        box2.append(dropdown)

        dropdown.bind_property("selected", widget, "filter", GObject.BindingFlags.DEFAULT)

        scale.get_adjustment().bind_property("value", widget, "scale", GObject.BindingFlags.BIDIRECTIONAL,
                                             transform_to, transform_from)

    if not window.get_visible():
        window.set_visible(True)
    else:
        close_request(window)

    return window
