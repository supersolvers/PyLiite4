"""Benchmark/Fishbowl

This demo models the fishbowl demos seen on the web in a GTK way.
It's also a neat little tool to see how fast your computer (or
your GTK version) is.
"""

from collections.abc import Callable

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk

from .graphwidget import graph_widget_new
from .gtkfishbowl import GtkFishbowl
from .gtkgears import gtk_gears_new
from .nodewidget import node_widget_new

css = (".blurred-button {"
       "  box-shadow: 0px 0px 5px 10px rgba(0, 0, 0, 0.5);"
       "}"
       "")

icon_names: list[str] | None = None
n_icon_names = 0


def init_icon_names(theme: Gtk.IconTheme) -> None:
    global icon_names, n_icon_names
    if icon_names:
        return

    icon_names = theme.get_icon_names()
    n_icon_names = len(icon_names)


# Also used in iconscroll.py
def create_icon_by_id(icon_index: int) -> Gtk.Widget:
    image = Gtk.Image()

    init_icon_names(Gtk.IconTheme.get_for_display(image.get_display()))

    icon_index %= n_icon_names

    image.set_icon_size(Gtk.IconSize.LARGE)
    image.set_from_icon_name(icon_names[icon_index])

    return image


def create_icon() -> Gtk.Widget:
    if n_icon_names == 0:
        n = 0
    else:
        n = GLib.random_int_range(0, n_icon_names)

    return create_icon_by_id(n)


def create_symbolic() -> Gtk.Widget:
    # Defined in iconscroll, which uses create_icon_by_id() from here.
    from .iconscroll import create_symbolic
    return create_symbolic()


def create_svg() -> Gtk.Widget:
    from .iconscroll import create_svg
    return create_svg()


def create_button() -> Gtk.Widget:
    return Gtk.Button.new_with_label("Button")


def create_blurred_button() -> Gtk.Widget:
    w = Gtk.Button()

    w.add_css_class("blurred-button")

    return w


def create_font_button() -> Gtk.Widget:
    return Gtk.FontDialogButton.new(Gtk.FontDialog())


def create_level_bar() -> Gtk.Widget:
    w = Gtk.LevelBar.new_for_interval(0, 100)

    w.set_value(50)

    # Force them to be a bit larger
    w.set_size_request(200, -1)

    return w


def create_spinner() -> Gtk.Widget:
    w = Gtk.Spinner()

    w.start()

    return w


def create_spinbutton() -> Gtk.Widget:
    w = Gtk.SpinButton.new_with_range(0, 10, 1)

    return w


def create_label() -> Gtk.Widget:
    w = Gtk.Label(label="Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor "
                        "invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua.")

    w.set_wrap(True)
    w.set_max_width_chars(100)

    return w


def create_video() -> Gtk.Widget:
    w = Gtk.Video()

    w.set_size_request(64, 64)
    w.set_loop(True)
    w.set_autoplay(True)
    w.set_resource("/images/gtk-logo.webm")

    return w


def create_gears() -> Gtk.Widget:
    w = gtk_gears_new()

    w.set_size_request(100, 100)

    return w


def create_switch() -> Gtk.Widget:
    w = Gtk.Switch()

    w.set_state(True)

    return w


def mapped(w: Gtk.MenuButton) -> None:
    w.popup()


def create_menu_button() -> Gtk.Widget:
    w = Gtk.MenuButton()
    popover = Gtk.Popover()

    popover.set_child(Gtk.Button.new_with_label("Hey!"))
    popover.set_autohide(False)
    w.set_popover(popover)
    w.map.connect(mapped)

    return w


def create_tiger() -> Gtk.Widget:
    return node_widget_new("/fishbowl/tiger.node")


def create_graph() -> Gtk.Widget:
    return graph_widget_new()


widget_types: list[tuple[str, Callable[[], Gtk.Widget], Callable[[GtkFishbowl], bool] | None]] = [
    ("Icon",       create_icon,           None),
    ("Button",     create_button,         None),
    ("Blurbutton", create_blurred_button, None),
    ("Fontbutton", create_font_button,    None),
    ("Levelbar",   create_level_bar,      None),
    ("Label",      create_label,          None),
    ("Spinner",    create_spinner,        None),
    ("Spinbutton", create_spinbutton,     None),
    ("Video",      create_video,          None),
    ("Gears",      create_gears,          None),
    ("Switch",     create_switch,         None),
    ("Menubutton", create_menu_button,    None),
    ("Tiger",      create_tiger,          None),
    ("Graph",      create_graph,          None),
    ("Symbolic",   create_symbolic,       None),
    ("SVG",        create_svg,            None),
]

selected_widget_type = -1
N_WIDGET_TYPES = len(widget_types)


def set_widget_type(fishbowl: GtkFishbowl, widget_type_index: int) -> bool:
    global selected_widget_type

    if widget_type_index == selected_widget_type:
        return True

    name, create_func, check = widget_types[widget_type_index]
    if check is not None and not check(fishbowl):
        return False

    selected_widget_type = widget_type_index

    fishbowl.set_creation_func(create_func)

    window = fishbowl.get_root()
    window.set_title(name)

    return True


def fishbowl_next_button_clicked_cb(source: Gtk.Button | None, fishbowl: GtkFishbowl) -> None:
    new_index = selected_widget_type

    while True:
        if new_index + 1 >= N_WIDGET_TYPES:
            new_index = 0
        else:
            new_index = new_index + 1

        if set_widget_type(fishbowl, new_index):
            break


def fishbowl_prev_button_clicked_cb(source: Gtk.Button | None, fishbowl: GtkFishbowl) -> None:
    new_index = selected_widget_type

    while True:
        if new_index - 1 < 0:
            new_index = N_WIDGET_TYPES - 1
        else:
            new_index = new_index - 1

        if set_widget_type(fishbowl, new_index):
            break


def fishbowl_changes_toggled_cb(button: Gtk.ToggleButton, pspec: GObject.ParamSpec) -> None:
    if button.get_active():
        file = Gio.File.new_for_uri("resource:///org/gtk/libgtk/icons/changes-prevent-symbolic.svg")
    else:
        file = Gio.File.new_for_uri("resource:///org/gtk/libgtk/icons/changes-allow-symbolic.svg")

    paintable = Gtk.IconPaintable.new_for_file(file, 16, 1)
    image = button.get_child()
    image.set_from_paintable(paintable)


def format_header_cb(object: GObject.Object | None, count: int, fps: float) -> str:
    return f"{count} Icons, {fps:.2f} fps"


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None
provider: Gtk.CssProvider | None = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref, provider, selected_widget_type

    if provider is None:
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    window = window_ref()
    if window is None:
        GObject.type_ensure(GtkFishbowl.__gtype__)

        # PyGObject's builder scope calls a handler with object="bowl" with the bowl alone, as if it were swapped,
        # rather than with the button and the bowl as GTK does.
        scope = {
            "fishbowl_prev_button_clicked_cb": lambda bowl: fishbowl_prev_button_clicked_cb(None, bowl),
            "fishbowl_next_button_clicked_cb": lambda bowl: fishbowl_next_button_clicked_cb(None, bowl),
            "fishbowl_changes_toggled_cb": fishbowl_changes_toggled_cb,
            "format_header_cb": format_header_cb,
        }

        builder = Gtk.Builder(scope)
        builder.add_from_resource("/fishbowl/fishbowl.ui")
        window = builder.get_object("window")
        window_ref = window.weak_ref()

        bowl = builder.get_object("bowl")
        selected_widget_type = -1
        set_widget_type(bowl, 0)
        window.set_display(do_widget.get_display())

        window.realize()

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
