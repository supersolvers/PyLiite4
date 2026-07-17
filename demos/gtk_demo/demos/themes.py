"""Benchmark/Themes

This demo continuously switches themes, like some of you.

Warning: This demo involves rapidly flashing changes and may
be hazardous to photosensitive viewers.
"""

from dataclasses import dataclass

from PyLiite4 import Gdk, GLib, GObject, Gtk

window: Gtk.Window | None = None
tick_cb = 0


@dataclass
class Theme:
    name: str
    dark: bool


themes = [
    Theme("Adwaita", False),
    Theme("Adwaita", True),
    Theme("HighContrast", False),
    Theme("HighContrastInverse", False),
]

theme = 0


def change_theme(widget: Gtk.Widget, frame_clock: Gdk.FrameClock | None, label: Gtk.Label) -> bool:
    global theme
    next = themes[theme % len(themes)]
    theme += 1

    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-theme-name", next.name)
    settings.set_property("gtk-application-prefer-dark-theme", next.dark)

    name = next.name + (" (dark)" if next.dark else "")
    widget.set_title(name)

    if frame_clock is not None:
        label.set_label(f"{frame_clock.get_fps():.2f} fps")
    else:
        label.set_label("")

    return GLib.SOURCE_CONTINUE


def toggle_cycle(button: Gtk.ToggleButton, pspec: GObject.ParamSpec, warning: Gtk.Window) -> None:
    global tick_cb

    active = button.get_active()

    window = button.get_ancestor(Gtk.Window)

    if active and not tick_cb:
        warning.present()
    elif not active and tick_cb:
        window.remove_tick_callback(tick_cb)
        tick_cb = 0


def warning_closed(warning: Gtk.Dialog, response_id: int, label: Gtk.Label) -> None:
    global tick_cb

    warning.set_visible(False)

    window = label.get_ancestor(Gtk.Window)
    button = window.button

    if response_id == Gtk.ResponseType.OK:
        tick_cb = window.add_tick_callback(change_theme, label)
    else:
        button.set_active(False)


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        builder = Gtk.Builder.new_from_resource("/themes/themes.ui")
        window = builder.get_object("window")
        window.destroy.connect(destroyed)
        window.set_display(do_widget.get_display())

        label = builder.get_object("fps")
        warning = builder.get_object("warning")
        warning.response.connect(warning_closed, label)

        button = builder.get_object("toggle")
        window.button = button
        button.notify["active"].connect(toggle_cycle, warning)
        window.realize()

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
