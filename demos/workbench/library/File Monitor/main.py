from PyLiite4 import Adw, Gio, GLib, Gtk

from demos.workbench import workbench

edit_entry: Gtk.TextView = workbench.builder.get_object("edit_entry")
view_file: Gtk.Button = workbench.builder.get_object("view_file")
delete_file: Gtk.Button = workbench.builder.get_object("delete_file")
edit_file: Gtk.Button = workbench.builder.get_object("edit_file")
file_name: Gtk.Label = workbench.builder.get_object("file_name")
buffer = edit_entry.get_buffer()
file = Gio.File.new_for_uri(workbench.resolve("workbench.txt"))
file_dir = file.get_parent()
overlay: Adw.ToastOverlay = workbench.builder.get_object("overlay")
file_launcher = Gtk.FileLauncher(always_ask=True, file=file)
details = file.query_info(
    "standard::display-name",
    Gio.FileQueryInfoFlags.NONE,
    None,
)
file_name.set_label(details.get_display_name())
buffer.set_text("Start editing ... ", -1)

monitor_for_dir = file_dir.monitor(
    Gio.FileMonitorFlags.WATCH_MOVES,
    None,
)
monitor_for_file = file.monitor(Gio.FileMonitorFlags.NONE, None)


def on_file_changed(_self: Gio.FileMonitor, _file: Gio.File, _other_file: Gio.File | None,
                    event: Gio.FileMonitorEvent) -> None:
    if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
        toast = Adw.Toast(title="File modified", timeout=2)
        overlay.add_toast(toast)


def on_dir_changed(_self: Gio.FileMonitor, child: Gio.File, other_file: Gio.File | None,
                   event: Gio.FileMonitorEvent) -> None:
    toast = Adw.Toast(
        timeout=2,
    )

    match event:
        case Gio.FileMonitorEvent.RENAMED:
            toast.set_title(
                f"{child.get_basename()} was renamed to {other_file.get_basename()}"
            )
        case Gio.FileMonitorEvent.DELETED:
            toast.set_title(f"{child.get_basename()} was deleted from the directory")
        case Gio.FileMonitorEvent.CREATED:
            toast.set_title(f"{child.get_basename()} created in the directory")

    if toast.get_title():
        overlay.add_toast(toast)


def on_edit_clicked(_button: Gtk.Button) -> None:
    bytes = GLib.Bytes(buffer.props.text.encode())
    # Workbench's Python version passes bytes.unref_to_array() to replace_contents_async(), but that writes from a
    # copy that's freed when the call returns, so the file gets garbage. The GBytes variant keeps its data alive.
    file.replace_contents_bytes_async(
        bytes,
        None,
        False,
        Gio.FileCreateFlags.REPLACE_DESTINATION,
        None,
        None,
    )


delete_file.clicked.connect(lambda _: file.delete_async(GLib.PRIORITY_DEFAULT, None))

view_file.clicked.connect(lambda _: file_launcher.launch(workbench.window, None))

monitor_for_file.changed.connect(on_file_changed)

monitor_for_dir.changed.connect(on_dir_changed)

edit_file.clicked.connect(on_edit_clicked)
