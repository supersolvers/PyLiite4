"""Pickers and Launchers
#Keywords: GtkColorDialog, GtkFontDialog, GtkFileDialog, GtkPrintDialog, GtkFileLauncher, GtkUriLauncher

The dialogs are mainly intended for use in preference dialogs.
They allow to select colors, fonts and files. There is also a
print dialog.

The launchers let you open files or URIs in applications that
can handle them.
"""

from PyLiite4 import Gdk, Gio, GLib, Gtk, Pango

app_picker: Gtk.Button
open_folder_button: Gtk.Button
print_button: Gtk.Button

# The files the buttons act on, as g_object_set_data (button, "file", ...) keeps them in C.
files: dict[Gtk.Widget, Gio.File] = {}


def set_file(file: Gio.File | None, data: Gtk.Label) -> None:
    if file is None:
        app_picker.set_sensitive(False)
        files.pop(app_picker, None)
        open_folder_button.set_sensitive(False)
        files.pop(open_folder_button, None)
        return

    name = file.get_basename()
    data.set_label(name)

    app_picker.set_sensitive(True)
    files[app_picker] = file
    open_folder_button.set_sensitive(True)
    files[open_folder_button] = file

    info = file.query_info("standard::content-type", Gio.FileQueryInfoFlags.NONE, None)
    if info.get_content_type() == "application/pdf":
        print_button.set_sensitive(True)
        files[print_button] = file


def file_opened(source: Gtk.FileDialog, result: Gio.AsyncResult, data: Gtk.Label) -> None:
    try:
        file = source.open_finish(result)
    except GLib.Error as error:
        file = None
        print(error.message)
        app_picker.set_sensitive(False)
        files.pop(app_picker, None)
        print_button.set_sensitive(False)
        files.pop(print_button, None)

    set_file(file, data)


def abort_mission(cancellable: Gio.Cancellable) -> bool:
    cancellable.cancel()

    return GLib.SOURCE_REMOVE


def open_file(picker: Gtk.Button, label: Gtk.Label) -> None:
    parent = picker.get_root()

    dialog = Gtk.FileDialog()

    cancellable = Gio.Cancellable()

    GLib.timeout_add_seconds(20, abort_mission, cancellable)

    dialog.open(parent, cancellable, file_opened, label)


def open_app_done(launcher: Gtk.FileLauncher, result: Gio.AsyncResult, data: object) -> None:
    try:
        launcher.launch_finish(result)
    except GLib.Error as error:
        print(error.message)


def open_app(picker: Gtk.Button) -> None:
    parent = picker.get_root()

    file = files.get(picker)
    launcher = Gtk.FileLauncher.new(file)

    launcher.launch(parent, None, open_app_done, None)


def open_folder_done(launcher: Gtk.FileLauncher, result: Gio.AsyncResult, data: object) -> None:
    try:
        launcher.open_containing_folder_finish(result)
    except GLib.Error as error:
        print(error.message)


def open_folder(picker: Gtk.Button) -> None:
    parent = picker.get_root()

    file = files.get(picker)
    launcher = Gtk.FileLauncher.new(file)

    launcher.open_containing_folder(parent, None, open_folder_done, None)


# The timeouts that cancel the print operations, as g_object_set_data (cancellable, "timeout", ...) keeps them in C.
timeouts: dict[Gio.Cancellable, int] = {}


def print_file_done(dialog: Gtk.PrintDialog, result: Gio.AsyncResult, cancellable: Gio.Cancellable) -> None:
    id = timeouts.pop(cancellable, 0)
    if id:
        GLib.source_remove(id)

    try:
        dialog.print_file_finish(result)
    except GLib.Error as error:
        print(error.message)


def print_file(picker: Gtk.Button) -> None:
    parent = picker.get_root()

    file = files.get(picker)
    dialog = Gtk.PrintDialog()

    cancellable = Gio.Cancellable()

    def abort(cancellable: Gio.Cancellable) -> bool:
        timeouts.pop(cancellable, None)
        return abort_mission(cancellable)

    id = GLib.timeout_add_seconds(20, abort, cancellable)
    timeouts[cancellable] = id

    dialog.print_file(parent, None, file, cancellable, print_file_done, cancellable)


def open_uri_done(launcher: Gtk.UriLauncher, result: Gio.AsyncResult, data: object) -> None:
    try:
        launcher.launch_finish(result)
    except GLib.Error as error:
        print(error.message)


def launch_uri(picker: Gtk.Button) -> None:
    parent = picker.get_root()

    launcher = Gtk.UriLauncher.new("http://www.gtk.org")

    launcher.launch(parent, None, open_uri_done, None)


def on_drop(target: Gtk.DropTarget, value: object, x: float, y: float, data: Gtk.Label) -> bool:
    if isinstance(value, Gio.File):
        set_file(value, data)
        return True

    return False


window: Gtk.Window | None = None


def window_destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window, app_picker, open_folder_button, print_button

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Pickers and Launchers")
        window.destroy.connect(window_destroyed)

        table = Gtk.Grid()
        table.set_margin_start(20)
        table.set_margin_end(20)
        table.set_margin_top(20)
        table.set_margin_bottom(20)
        table.set_row_spacing(6)
        table.set_column_spacing(6)
        window.set_child(table)

        label = Gtk.Label.new_with_mnemonic("_Color:")
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_hexpand(True)
        table.attach(label, 0, 0, 1, 1)

        picker = Gtk.ColorDialogButton.new(Gtk.ColorDialog())
        label.set_mnemonic_widget(picker)
        table.attach(picker, 1, 0, 1, 1)

        label = Gtk.Label.new_with_mnemonic("_Font:")
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_hexpand(True)
        table.attach(label, 0, 1, 1, 1)

        picker = Gtk.FontDialogButton.new(Gtk.FontDialog())
        label.set_mnemonic_widget(picker)
        table.attach(picker, 1, 1, 1, 1)

        label = Gtk.Label.new_with_mnemonic("_File:")
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_hexpand(True)
        table.attach(label, 0, 2, 1, 1)

        picker = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button = Gtk.Button.new_from_icon_name("document-open-symbolic")
        label.set_mnemonic_widget(button)
        button.update_property([Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.HAS_POPUP],
                               ["Select File", True])

        label = Gtk.Label(label="None")

        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.drop.connect(on_drop, label)
        button.add_controller(drop_target)

        label.set_xalign(0.)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_hexpand(True)
        button.clicked.connect(open_file, label)
        picker.append(label)
        picker.append(button)
        app_picker = Gtk.Button.new_from_icon_name("system-run-symbolic")
        app_picker.set_halign(Gtk.Align.END)
        app_picker.update_property([Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.HAS_POPUP],
                                   ["Open File", True])
        app_picker.set_sensitive(False)
        app_picker.clicked.connect(open_app)
        picker.append(app_picker)
        open_folder_button = Gtk.Button.new_from_icon_name("folder-symbolic")
        open_folder_button.set_halign(Gtk.Align.END)
        open_folder_button.update_property([Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.HAS_POPUP],
                                           ["Open in Folder", True])
        open_folder_button.set_sensitive(False)
        open_folder_button.clicked.connect(open_folder)
        picker.append(open_folder_button)

        print_button = Gtk.Button.new_from_icon_name("printer-symbolic")
        print_button.set_tooltip_text("Print File")
        print_button.set_sensitive(False)
        print_button.update_property([Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.HAS_POPUP],
                                     ["Print File", True])
        print_button.clicked.connect(print_file)
        picker.append(print_button)

        table.attach(picker, 1, 2, 1, 1)

        label = Gtk.Label.new_with_mnemonic("_URI:")
        label.set_halign(Gtk.Align.START)
        label.set_valign(Gtk.Align.CENTER)
        label.set_hexpand(True)
        table.attach(label, 0, 3, 1, 1)

        picker = Gtk.Button(label="www.gtk.org")
        label.set_mnemonic_widget(picker)
        picker.update_property([Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.HAS_POPUP],
                               ["Open www.gtk.org", True])
        picker.clicked.connect(launch_uri)
        table.attach(picker, 1, 3, 1, 1)

    result = window
    if not result.get_visible():
        result.present()
    else:
        result.destroy()

    return result

