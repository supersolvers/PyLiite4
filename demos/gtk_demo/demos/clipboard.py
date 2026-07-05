"""Clipboard
#Keywords: drag-and-drop, dnd

GdkClipboard is used for clipboard handling. This demo shows how to
copy and paste text, images, colors or files to and from the clipboard.

You can also use Drag-And-Drop to copy the data from the source to the
target.
"""

from collections.abc import Callable

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk

from . import demoimage  # noqa: F401  (C includes demoimage.h)


def copy_button_clicked(source_stack: Gtk.Stack, button: Gtk.Button) -> None:
    clipboard = source_stack.get_clipboard()

    visible_child = source_stack.get_visible_child()
    visible_child_name = source_stack.get_visible_child_name()

    if visible_child_name == "Text":
        clipboard.set(GObject.Value(str, visible_child.get_text()))
    elif visible_child_name == "Image":
        child = visible_child.get_first_child()
        while child:
            if child.get_active():
                image = child.get_first_child()
                paintable = image.get_paintable()

                # gdk_clipboard_set() takes varargs: set() takes the value with its type.
                if isinstance(paintable, Gdk.Texture):
                    clipboard.set(GObject.Value(Gdk.Texture, paintable))
                else:
                    clipboard.set(GObject.Value(Gdk.Paintable, paintable))
                break
            child = child.get_next_sibling()
    elif visible_child_name == "Color":
        color = visible_child.get_rgba()
        clipboard.set(GObject.Value(Gdk.RGBA, color))
    elif visible_child_name == "File":
        clipboard.set(GObject.Value(Gio.File, getattr(visible_child, "file", None)))
    else:
        print("TODO", end="")


def present_value(dest_stack: Gtk.Stack, value: object) -> None:
    # The value comes unboxed from its GValue, so its Python type tells which GType it held.
    if isinstance(value, Gio.File):
        dest_stack.set_visible_child_name("File")
        child = dest_stack.get_visible_child()

        file = value
        child.set_property("label", file.peek_path())
    elif isinstance(value, Gdk.RGBA):
        dest_stack.set_visible_child_name("Color")
        child = dest_stack.get_visible_child().get_first_child()

        color = value
        child.set_property("rgba", color)
    elif isinstance(value, Gdk.Paintable):
        dest_stack.set_visible_child_name("Image")
        child = dest_stack.get_visible_child()

        paintable = value
        child.set_property("paintable", paintable)
    elif isinstance(value, str):
        dest_stack.set_visible_child_name("Text")
        child = dest_stack.get_visible_child()

        child.set_label(value)


def paste_received(clipboard: Gdk.Clipboard, result: Gio.AsyncResult, dest_stack: Gtk.Stack) -> None:
    try:
        value = clipboard.read_value_finish(result)
    except GLib.Error as error:
        print(error.message)
    else:
        present_value(dest_stack, value)


def paste_button_clicked(dest_stack: Gtk.Stack, button: Gtk.Button) -> None:
    clipboard = dest_stack.get_clipboard()
    formats = clipboard.get_formats()

    if formats.contain_gtype(Gdk.Texture.__gtype__):
        clipboard.read_value_async(Gdk.Texture.__gtype__, 0, None, paste_received, dest_stack)
    elif formats.contain_gtype(Gdk.Paintable.__gtype__):
        clipboard.read_value_async(Gdk.Paintable.__gtype__, 0, None, paste_received, dest_stack)
    elif formats.contain_gtype(Gdk.RGBA.__gtype__):
        clipboard.read_value_async(Gdk.RGBA.__gtype__, 0, None, paste_received, dest_stack)
    elif formats.contain_gtype(Gio.File.__gtype__):
        clipboard.read_value_async(Gio.File.__gtype__, 0, None, paste_received, dest_stack)
    elif formats.contain_gtype(GObject.TYPE_STRING):
        clipboard.read_value_async(GObject.TYPE_STRING, 0, None, paste_received, dest_stack)


def update_copy_button_sensitivity(source_stack: Gtk.Stack) -> None:
    copy_button: Gtk.Button = source_stack.copy_button

    visible_child = source_stack.get_visible_child()
    visible_child_name = source_stack.get_visible_child_name()
    if visible_child_name == "Text":
        sensitive = len(visible_child.get_text()) > 0
    elif visible_child_name in ("Color", "Image"):
        sensitive = True
    elif visible_child_name == "File":
        sensitive = getattr(visible_child, "file", None) is not None
    else:
        sensitive = False

    copy_button.set_sensitive(sensitive)


def source_changed_cb(copy_button: Gtk.Button, pspec: GObject.ParamSpec, source_stack: Gtk.Stack) -> None:
    update_copy_button_sensitivity(source_stack)


def text_changed_cb(copy_button: Gtk.Button, pspec: GObject.ParamSpec, entry: Gtk.Entry) -> None:
    update_copy_button_sensitivity(entry.get_ancestor(Gtk.Stack))


def file_button_set_file(button: Gtk.Button, file: Gio.File) -> None:
    button.get_child().set_label(file.peek_path())
    button.file = file


def file_chooser_response(dialog: Gtk.FileDialog, result: Gio.AsyncResult, button: Gtk.Button) -> None:
    try:
        file = dialog.open_finish(result)
    except GLib.Error:
        file = None
    if file:
        file_button_set_file(button, file)

        update_copy_button_sensitivity(button.get_ancestor(Gtk.Stack))


def open_file_cb(button: Gtk.Button) -> None:
    dialog = Gtk.FileDialog()

    dialog.open(button.get_ancestor(Gtk.Window),
                None,
                file_chooser_response, button)


def folder_chooser_response(dialog: Gtk.FileDialog, result: Gio.AsyncResult, button: Gtk.Button) -> None:
    try:
        file = dialog.select_folder_finish(result)
    except GLib.Error:
        file = None
    if file:
        file_button_set_file(button, file)

        update_copy_button_sensitivity(button.get_ancestor(Gtk.Stack))


def open_folder_cb(button: Gtk.Button) -> None:
    dialog = Gtk.FileDialog()

    dialog.select_folder(button.get_ancestor(Gtk.Window),
                         None,
                         folder_chooser_response, button)


def update_paste_button_sensitivity(clipboard: Gdk.Clipboard, paste_button: Gtk.Widget) -> None:
    sensitive = False

    formats = clipboard.get_formats()

    if (formats.contain_gtype(Gio.File.__gtype__) or
            formats.contain_gtype(Gdk.RGBA.__gtype__) or
            formats.contain_gtype(Gdk.Texture.__gtype__) or
            formats.contain_gtype(Gdk.Paintable.__gtype__) or
            formats.contain_gtype(GObject.TYPE_STRING)):
        sensitive = True

    paste_button.set_sensitive(sensitive)


def unset_clipboard_handler(paste_button: Gtk.Widget) -> None:
    clipboard = paste_button.get_clipboard()

    clipboard.changed.disconnect(paste_button.clipboard_handler)


def on_drop(dest_stack: Gtk.Stack, value: object, x: float, y: float, target: Gtk.DropTarget) -> bool:
    present_value(dest_stack, value)
    return True


def drag_prepare(drag_source: Gtk.DragSource, x: float, y: float) -> Gdk.ContentProvider | None:
    button = drag_source.get_widget()

    if isinstance(button, Gtk.ToggleButton):
        image = button.get_first_child()
        paintable = image.get_paintable()

        if isinstance(paintable, Gdk.Texture):
            value = GObject.Value(Gdk.Texture, paintable)
        else:
            value = GObject.Value(Gdk.Paintable, paintable)
    else:
        file = getattr(button, "file", None)

        if file:
            value = GObject.Value(Gio.File, file)
        else:
            return None

    return Gdk.ContentProvider.new_for_value(value)


class BuilderCScope(GObject.Object, Gtk.BuilderScope):
    """What gtk_builder_cscope_new() and gtk_builder_cscope_add_callback() do: callbacks by name.

    PyGObject's own Gtk.Builder scope passes only the object to handlers with object="...", dropping the signal's
    arguments, and clipboard.ui uses object= on four signals.
    """

    __gtype_name__ = "PyDemoClipboardBuilderCScope"

    def __init__(self) -> None:
        super().__init__()
        self.callbacks: dict[str, Callable[..., object]] = {}

    def add_callback(self, callback: Callable[..., object]) -> None:
        self.callbacks[callback.__name__] = callback

    def do_create_closure(self, builder: Gtk.Builder, function_name: str, flags: Gtk.BuilderClosureFlags,
                          object: GObject.Object | None) -> Callable[..., object]:
        callback = self.callbacks[function_name]
        if object is None:
            return callback
        if flags & Gtk.BuilderClosureFlags.SWAPPED:
            return lambda instance, *args: callback(object, *args, instance)
        return lambda instance, *args: callback(instance, *args, object)


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        scope = BuilderCScope()
        scope.add_callback(copy_button_clicked)
        scope.add_callback(paste_button_clicked)
        scope.add_callback(source_changed_cb)
        scope.add_callback(text_changed_cb)
        scope.add_callback(open_file_cb)
        scope.add_callback(open_folder_cb)
        scope.add_callback(on_drop)
        scope.add_callback(drag_prepare)
        builder = Gtk.Builder()
        builder.set_scope(scope)
        builder.add_from_resource("/clipboard/clipboard.ui")

        window = builder.get_object("window")
        window_ref = window.weak_ref()
        window.set_display(do_widget.get_display())

        button = builder.get_object("copy_button")
        builder.get_object("source_stack").copy_button = button

        button = builder.get_object("paste_button")
        button.clipboard_handler = button.get_clipboard().changed.connect(update_paste_button_sensitivity, button)
        button.destroy.connect(unset_clipboard_handler)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
