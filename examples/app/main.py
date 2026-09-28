"""A starting point for a libadwaita application.

It shows an Adw.Application with a window, a header bar with a primary menu, Gio.SimpleActions with keyboard
accelerators, an about dialog, and a window size that is saved with Gio.Settings.

Run it from the repository root:

    python examples/app/main.py

GSettings needs a compiled schema, here org.example.PyLiite4App.gschema.xml. An installed application puts it in
$prefix/share/glib-2.0/schemas and runs glib-compile-schemas there. For development, compile it next to this file:

    glib-compile-schemas examples/app

The application looks for the schema among the installed ones first, then in this directory. Without it, the
application still runs, but opens at its default size every time.
"""

import sys
from pathlib import Path

from PyLiite4 import Adw, Gio, GLib, Gtk

APP_ID = "org.example.PyLiite4App"


def load_settings() -> Gio.Settings | None:
    """The application's settings, or None when the schema can't be found."""
    installed = Gio.SettingsSchemaSource.get_default()
    schema = installed.lookup(APP_ID, True) if installed else None
    here = Path(__file__).resolve().parent
    if schema is None and (here / "gschemas.compiled").exists():
        source = Gio.SettingsSchemaSource.new_from_directory(str(here), installed, False)
        schema = source.lookup(APP_ID, False)
    if schema is None:
        return None
    return Gio.Settings.new_full(schema, None, None)


class Window(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, settings: Gio.Settings | None) -> None:
        super().__init__(application=application, title="PyLiite4 App", default_width=640, default_height=480)
        if settings is not None:
            # Bound properties take the stored values now, and store each change from here on.
            settings.bind("window-width", self, "default-width", Gio.SettingsBindFlags.DEFAULT)
            settings.bind("window-height", self, "default-height", Gio.SettingsBindFlags.DEFAULT)
            settings.bind("window-maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT)

        menu = Gio.Menu()
        menu.append("_New Window", "app.new-window")
        menu.append("_About PyLiite4 App", "app.about")
        menu.append("_Quit", "app.quit")
        header = Adw.HeaderBar()
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu, primary=True,
                                       tooltip_text="Main Menu"))

        self.toasts = Adw.ToastOverlay()
        self.toasts.set_child(Adw.StatusPage(
            icon_name="face-smile-symbolic", title="Hello",
            description="Press Ctrl+G to greet, F10 for the menu",
            child=Gtk.Button(label="_Greet", use_underline=True, action_name="win.greet", halign=Gtk.Align.CENTER,
                             css_classes=["pill", "suggested-action"])))
        view = Adw.ToolbarView(content=self.toasts)
        view.add_top_bar(header)
        self.set_content(view)

        # A window action ("win.greet") belongs to one window; application actions ("app.quit") to all of them.
        greet = Gio.SimpleAction(name="greet")
        greet.activate.connect(self.on_greet)
        self.add_action(greet)

    def on_greet(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        self.toasts.add_toast(Adw.Toast(title="Hello from PyLiite4", timeout=2))


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.settings = load_settings()
        if self.settings is None:
            print(f"The {APP_ID} schema isn't installed, so the window size won't be saved", file=sys.stderr)
        self.activate.connect(self.on_activate)

        for name, callback in [("new-window", self.on_new_window), ("about", self.on_about), ("quit", self.on_quit)]:
            action = Gio.SimpleAction(name=name)
            action.activate.connect(callback)
            self.add_action(action)
        self.set_accels_for_action("app.new-window", ["<Control>n"])
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("win.greet", ["<Control>g"])
        self.set_accels_for_action("window.close", ["<Control>w"])

    def on_activate(self, application: Gio.Application) -> None:
        # Activating again, for example by starting a second copy, raises the open window.
        window = self.get_active_window() or Window(self, self.settings)
        window.present()

    def on_new_window(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        Window(self, self.settings).present()

    def on_about(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        about = Adw.AboutDialog(application_name="PyLiite4 App", application_icon="face-smile-symbolic",
                                developer_name="The PyLiite4 developers", version="0.1.0",
                                website="https://example.org", license_type=Gtk.License.LGPL_3_0_ONLY,
                                developers=["A Developer https://example.org"], copyright="© 2026 A Developer")
        about.present(self.get_active_window())

    def on_quit(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        self.quit()


if __name__ == "__main__":
    sys.exit(Application().run(sys.argv))
