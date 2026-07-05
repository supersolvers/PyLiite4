"""Shortcuts Window

GtkShortcutsWindow is a window that provides a help overlay
for shortcuts and gestures in an application.
"""

from collections.abc import Callable

from PyLiite4 import Gio, GObject, Gtk


def show_shortcuts(window: Gtk.Window, id: str, view: str | None) -> None:
    builder = Gtk.Builder.new_from_resource(f"/shortcuts/{id}.ui")
    overlay = builder.get_object(id)
    overlay.set_transient_for(window)
    overlay.set_property("view-name", view)
    overlay.present()


def shortcuts_builder_shortcuts(window: Gtk.Window, *args: object) -> None:
    show_shortcuts(window, "shortcuts-builder", None)


def shortcuts_gedit_shortcuts(window: Gtk.Window, *args: object) -> None:
    show_shortcuts(window, "shortcuts-gedit", None)


def shortcuts_clocks_shortcuts(window: Gtk.Window, *args: object) -> None:
    show_shortcuts(window, "shortcuts-clocks", None)


def shortcuts_clocks_shortcuts_stopwatch(window: Gtk.Window, *args: object) -> None:
    show_shortcuts(window, "shortcuts-clocks", "stopwatch")


def shortcuts_boxes_shortcuts(window: Gtk.Window, *args: object) -> None:
    show_shortcuts(window, "shortcuts-boxes", None)


def shortcuts_boxes_shortcuts_wizard(window: Gtk.Window, *args: object) -> None:
    show_shortcuts(window, "shortcuts-boxes", "wizard")


def shortcuts_boxes_shortcuts_display(window: Gtk.Window, *args: object) -> None:
    show_shortcuts(window, "shortcuts-boxes", "display")


class ShortcutsScope(GObject.Object, Gtk.BuilderScope):
    """Finds the handlers that C exports from the module.

    shortcuts.ui connects them swapped, to its window, which PyGObject's own builder scope refuses.
    """

    def do_create_closure(self, builder: Gtk.Builder, function_name: str, flags: Gtk.BuilderClosureFlags,
                          object: GObject.Object | None) -> Callable[..., object]:
        handler = globals()[function_name]
        if flags & Gtk.BuilderClosureFlags.SWAPPED:
            return lambda *args: handler(object, *args)
        return handler


window: Gtk.Window | None = None
icons_added = False


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, icons_added

    if not icons_added:
        icons_added = True
        Gtk.IconTheme.get_for_display(do_widget.get_display()).add_resource_path("/icons")

    GObject.type_ensure(Gio.FileIcon.__gtype__)

    if window is None:
        builder = Gtk.Builder()
        builder.set_scope(ShortcutsScope())
        builder.add_from_resource("/shortcuts/shortcuts.ui")
        window = builder.get_object("window1")
        window.set_display(do_widget.get_display())
        window.destroy.connect(destroyed)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
