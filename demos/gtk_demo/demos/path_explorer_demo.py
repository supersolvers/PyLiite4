"""Path/Path Explorer

This demo lets you explore some of the features of GskPath.
"""

from PyLiite4 import Gdk, GObject, Gsk, Gtk

from .path_explorer import PathExplorer  # noqa: F401  (registers the type the .ui file uses)
from .range_editor import RangeEditor  # noqa: F401  (registers the type the .ui file uses)


def text_to_path(binding: GObject.Binding, text: str) -> Gsk.Path | None:
    return Gsk.Path.parse(text)


def path_to_text(binding: GObject.Binding, path: Gsk.Path) -> str:
    return path.to_string()


window: Gtk.Window | None = None
css_provider: Gtk.CssProvider | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window, css_provider

    if not css_provider:
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/path_explorer_demo/path_explorer_demo.css")

        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    if not window:
        builder = Gtk.Builder()

        builder.add_from_resource("/path_explorer_demo/path_explorer_demo.ui")

        window = builder.get_object("window")
        window.close_request.connect(close_request)

        demo = builder.get_object("demo")
        entry = builder.get_object("entry")
        demo.bind_property("path", entry, "text",
                           GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
                           path_to_text, text_to_path)

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
