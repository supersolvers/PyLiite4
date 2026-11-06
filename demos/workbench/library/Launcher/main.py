from PyLiite4 import Gio, GLib, GObject, Gtk

from demos.workbench import workbench

launch_file: Gtk.Button = workbench.builder.get_object("launch_file")
file_name: Gtk.Label = workbench.builder.get_object("file_name")
file_location: Gtk.Button = workbench.builder.get_object("file_location")
change_file: Gtk.Button = workbench.builder.get_object("change_file")
uri_launch: Gtk.Button = workbench.builder.get_object("uri_launch")
uri_details: Gtk.Entry = workbench.builder.get_object("uri_details")

# File launcher

file = Gio.File.new_for_uri(workbench.resolve("workbench.txt"))
file_launcher = Gtk.FileLauncher(
    always_ask=True,
    file=file,
)


def on_file_changed(_launcher: Gtk.FileLauncher, _file: GObject.ParamSpec) -> None:
    details = file_launcher.get_file().query_info(
        "standard::display-name",
        Gio.FileQueryInfoFlags.NONE,
        None,
    )
    file_name.set_label(details.get_display_name())


def on_uri_changed(_entry: Gtk.Entry) -> None:
    text = uri_details.get_text()

    try:
        uri_launch.set_sensitive(GLib.Uri.is_valid(text, GLib.UriFlags.NONE))
    except Exception:
        uri_launch.set_sensitive(False)


def on_file_opened(dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    file = dialog.open_finish(result)
    file_launcher.set_file(file)


launch_file.clicked.connect(lambda _: file_launcher.launch(workbench.window, None))

file_launcher.notify["file"].connect(on_file_changed)

file_location.clicked.connect(
    lambda _: file_launcher.open_containing_folder(workbench.window, None)
)

change_file.clicked.connect(
    lambda _: Gtk.FileDialog().open(workbench.window, None, on_file_opened)
)

# URI launcher

uri_launch.clicked.connect(
    lambda _: Gtk.UriLauncher(uri=uri_details.get_text()).launch(
        workbench.window, None
    ),
)

uri_details.changed.connect(on_uri_changed)
