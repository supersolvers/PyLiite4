"""The gtk4-demo-application program, which the Application Class demo runs as its own process.

Run it with ``python -m demos.gtk_demo.demos.application``.
"""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from PyLiite4 import Gio, GLib, Gtk

from demos import gtk_demo

gtk_demo.register_resources()


def show_action_dialog(action: Gio.SimpleAction) -> None:
    dialog = Gtk.AlertDialog(message=f'You activated action: "{action.get_name()}"')
    dialog.show(None)


def show_action_infobar(action: Gio.SimpleAction, parameter: GLib.Variant,
                        data: "Callable[[], DemoApplicationWindow]") -> None:
    window = data()
    name = action.get_name()
    value = parameter.get_string()

    text = f'You activated radio action: "{name}".\nCurrent value: {value}'
    window.message.set_text(text)
    window.infobar.set_visible(True)


def activate_action(action: Gio.SimpleAction, parameter: GLib.Variant | None, user_data: object) -> None:
    show_action_dialog(action)


def activate_new(action: Gio.SimpleAction, parameter: GLib.Variant | None, app: Gio.Application) -> None:
    window = create_demo_window(app, None)
    window.present()


def open_response_cb(dialog: Gtk.FileDialog, result: Gio.AsyncResult, app: Gio.Application) -> None:
    error = None
    try:
        file = dialog.open_finish(result)
        if file:
            ok, contents, _etag = file.load_contents(None)
            window = create_demo_window(app, contents.decode("utf-8", "replace"))
            window.present()
    except GLib.Error as e:
        error = e

    if error:
        alert = Gtk.AlertDialog(message=f'Error loading file: "{error.message}"')
        alert.show(None)


def activate_open(action: Gio.SimpleAction, parameter: GLib.Variant | None, app: Gio.Application) -> None:
    dialog = Gtk.FileDialog()
    dialog.open(None, None, open_response_cb, app)


def activate_toggle(action: Gio.SimpleAction, parameter: GLib.Variant | None, user_data: object) -> None:
    show_action_dialog(action)

    state = action.get_state()
    action.change_state(GLib.Variant.new_boolean(not state.get_boolean()))


def activate_radio(action: Gio.SimpleAction, parameter: GLib.Variant,
                   user_data: "Callable[[], DemoApplicationWindow]") -> None:
    show_action_infobar(action, parameter, user_data)

    action.change_state(parameter)


def show_about_dialog(parent: Gtk.Window, **properties: object) -> None:
    # gtk_show_about_dialog() takes varargs, so it isn't in the bindings: this does what it does.
    dialog = getattr(parent, "_about_dialog", None)
    if dialog is None:
        dialog = Gtk.AboutDialog(hide_on_close=True, modal=True, transient_for=parent, destroy_with_parent=True,
                                 **properties)
        parent._about_dialog = dialog
    dialog.present()


def activate_about(action: Gio.SimpleAction, parameter: GLib.Variant | None,
                   user_data: Callable[[], Gtk.Window]) -> None:
    window = user_data()
    authors = [
        "Peter Mattis",
        "Spencer Kimball",
        "Josh MacDonald",
        "and many more...",
    ]

    documentors = [
        "Owen Taylor",
        "Tony Gale",
        "Matthias Clasen <mclasen@redhat.com>",
        "and many more...",
    ]

    package_version = f"{Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}"
    show_about_dialog(window,
                      program_name="GTK Code Demos",
                      version=f"{package_version},\nRunning against GTK "
                              f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}",
                      copyright="(C) 1997-2013 The GTK Team",
                      license_type=Gtk.License.LGPL_2_1,
                      website="http://www.gtk.org",
                      comments="Program to demonstrate GTK functions.",
                      authors=authors,
                      documenters=documentors,
                      logo_icon_name="org.gtk.Demo4",
                      title="About GTK Code Demos")


def activate_quit(action: Gio.SimpleAction, parameter: GLib.Variant | None, app: Gtk.Application) -> None:
    for win in list(app.get_windows()):
        win.destroy()


def pop_message(status: Gtk.Label) -> None:
    messages: list[str] = getattr(status, "messages", [])

    if messages:
        message = messages.pop(0)
        status.set_label(message)


def push_message(status: Gtk.Label, message: str) -> None:
    messages: list[str] = getattr(status, "messages", [])

    status.set_label(message)
    messages.insert(0, message)
    status.messages = messages


def change_theme_state(action: Gio.SimpleAction, state: GLib.Variant, user_data: object) -> None:
    settings = Gtk.Settings.get_default()

    settings.set_property("gtk-application-prefer-dark-theme", state.get_boolean())

    action.set_state(state)


def change_radio_state(action: Gio.SimpleAction, state: GLib.Variant, user_data: object) -> None:
    action.set_state(state)


app_entries = [
    ("new", activate_new, None, None, None),
    ("open", activate_open, None, None, None),
    ("save", activate_action, None, None, None),
    ("save-as", activate_action, None, None, None),
    ("quit", activate_quit, None, None, None),
    ("dark", activate_toggle, None, "false", change_theme_state),
]

win_entries = [
    ("shape", activate_radio, "s", "'oval'", change_radio_state),
    ("bold", activate_toggle, None, "false", None),
    ("about", activate_about, None, None, None),
    ("file1", activate_action, None, None, None),
    ("logo", activate_action, None, None, None),
]


def settings_new(schema_id: str) -> Gio.Settings:
    # The C program finds its schema installed with GTK. Here it's compiled from data/ into the cache.
    directory = Path(GLib.get_user_cache_dir()) / "PyLiite4" / "gtk-demo" / "schemas"
    directory.mkdir(parents=True, exist_ok=True)
    source_file = gtk_demo.DATA / "org.gtk.Demo4.gschema.xml"
    (directory / source_file.name).write_bytes(source_file.read_bytes())
    subprocess.run(["glib-compile-schemas", str(directory)], check=True)
    source = Gio.SettingsSchemaSource.new_from_directory(str(directory), Gio.SettingsSchemaSource.get_default(),
                                                         False)
    return Gio.Settings.new_full(source.lookup(schema_id, False), None, None)


class DemoApplication(Gtk.Application):
    __gtype_name__ = "DemoApplication"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)

        settings = settings_new("org.gtk.Demo4.Application")

        self.add_action_entries(app_entries, self)

        action = settings.create_action("color")

        self.add_action(action)

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

        builder = Gtk.Builder()
        builder.add_from_resource("/application_demo/menus.ui")

        self.set_menubar(builder.get_object("menubar"))

    def do_activate(self) -> None:
        # GTK 4.22.4's C version only creates the window, left from the window-restoring API that was taken out
        # before 4.22, so its window never shows. The port presents it.
        create_demo_window(self, None).present()


def template_ui() -> str:
    # GTK 4.22.4's application.ui sets a "session-id" property that GtkWindow doesn't have in 4.22, which fails the
    # whole template, so it's loaded without that line.
    data = Gio.resources_lookup_data("/application_demo/application.ui", Gio.ResourceLookupFlags.NONE)
    return "\n".join(line for line in data.get_data().decode().splitlines() if '"session-id"' not in line)


@Gtk.Template(string=template_ui())
class DemoApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "DemoApplicationWindow"

    message: Gtk.Label = Gtk.Template.Child()
    infobar: Gtk.InfoBar = Gtk.Template.Child()
    status: Gtk.Label = Gtk.Template.Child()
    menubutton: Gtk.MenuButton = Gtk.Template.Child()
    toolmenu: Gio.MenuModel = Gtk.Template.Child()
    buffer: Gtk.TextBuffer = Gtk.Template.Child()

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)

        popover = Gtk.PopoverMenu.new_from_model(self.toolmenu)
        self.menubutton.set_popover(popover)

        # The window is passed weakly: it holds its actions, so a strong reference would keep it alive after it's
        # destroyed.
        self.add_action_entries(win_entries, self.weak_ref())

    @Gtk.Template.Callback()
    def clicked_cb(self, widget: Gtk.Button) -> None:
        self.infobar.set_visible(False)

    @Gtk.Template.Callback()
    def update_statusbar(self, buffer: Gtk.TextBuffer) -> None:
        # clear any previous message, underflow is allowed
        pop_message(self.status)

        count = buffer.get_char_count()

        iter = buffer.get_iter_at_mark(buffer.get_insert())

        row = iter.get_line()
        col = iter.get_line_offset()

        msg = f"Cursor at row {row} column {col} - {count} chars in document"

        push_message(self.status, msg)

    @Gtk.Template.Callback()
    def mark_set_callback(self, buffer: Gtk.TextBuffer, new_location: Gtk.TextIter, mark: Gtk.TextMark) -> None:
        self.update_statusbar(buffer)


def create_demo_window(app: Gio.Application, content: str | None) -> DemoApplicationWindow:
    window = DemoApplicationWindow(application=app, show_menubar=True)
    if content:
        window.buffer.set_text(content, -1)

    return window


def main() -> int:
    app = DemoApplication(application_id="org.gtk.Demo4.App", flags=Gio.ApplicationFlags.HANDLES_OPEN,
                          register_session=True)

    return app.run(sys.argv[:1])


if __name__ == "__main__":
    sys.exit(main())
