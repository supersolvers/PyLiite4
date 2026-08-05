from collections.abc import Callable
from gettext import gettext as _

from PyLiite4 import Adw, Gio, GLib, Gtk

from . import register_resources
from .adw_demo_debug_info import adw_demo_generate_debug_info
from .adw_demo_preferences_dialog import adw_demo_preferences_dialog_new
from .adw_demo_window import adw_demo_window_new


def show_inspector(action: Gio.SimpleAction, state: GLib.Variant | None, app: Gtk.Application) -> None:
    Gtk.Window.set_interactive_debugging(True)


def show_preferences(action: Gio.SimpleAction, state: GLib.Variant | None, app: Gtk.Application) -> None:
    window = app.get_active_window()

    adw_demo_preferences_dialog_new().present(window)


def show_about(action: Gio.SimpleAction, state: GLib.Variant | None, app: Gtk.Application) -> None:
    developers = [
        "Adrien Plazas",
        "Alice Mikhaylenko",
        "Andrei Lișiță",
        "Guido Günther",
        "Jamie Murphy",
        "Julian Sparber",
        "Manuel Genovés",
        "Zander Brown",
    ]

    designers = [
        "GNOME Design Team",
    ]

    window = app.get_active_window()

    debug_info = adw_demo_generate_debug_info()

    about = Adw.AboutDialog.new_from_appdata("/org/gnome/Adwaita1/Demo/org.gnome.Adwaita1.Demo.metainfo.xml", None)
    assert isinstance(about, Adw.AboutDialog)
    about.set_version(Adw.VERSION_S)
    about.set_debug_info(debug_info)
    about.set_debug_info_filename("adwaita-1-demo-debug-info.txt")
    about.set_copyright("© 2017–2022 Purism SPC\n© 2023-2024 GNOME Foundation Inc.")
    about.set_developers(developers)
    about.set_designers(designers)
    about.set_artists(designers)
    about.set_translator_credits(_("translator-credits"))

    about.add_link(_("_Documentation"),
                   "https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/")
    about.add_link(_("_Chat"),
                   "https://matrix.to/#/#libadwaita:gnome.org")

    about.present(window)


def quit_app(action: Gio.SimpleAction, state: GLib.Variant | None, app: Gtk.Application) -> None:
    app.quit()


def show_window(app: Gtk.Application) -> Gtk.Window:
    window = adw_demo_window_new(app)
    window.present()
    return window


app_entries: list[tuple[str, Callable[[Gio.SimpleAction, GLib.Variant | None, Gtk.Application], None]]] = [
    ("inspector", show_inspector),
    ("preferences", show_preferences),
    ("about", show_about),
    ("quit", quit_app),
]


def add_actions(app: Gtk.Application) -> None:
    """g_action_map_add_action_entries() and the accelerators, as main() sets them up."""
    for name, activate in app_entries:
        action = Gio.SimpleAction(name=name)
        action.activate.connect(activate, app)
        app.add_action(action)

    app.set_accels_for_action("app.preferences", ["<Ctrl>comma"])
    app.set_accels_for_action("app.quit", ["<Ctrl>Q"])


def main(argv: list[str]) -> int:
    register_resources()

    app = Adw.Application(application_id="org.gnome.Adwaita1.Demo", flags=Gio.ApplicationFlags.NON_UNIQUE)
    add_actions(app)

    app.activate.connect(show_window)
    return app.run(argv)
