import sys

from PyLiite4 import Gio, GLib, Gtk

from demos.workbench import workbench

button_single: Gtk.Button = workbench.builder.get_object("button_single")
button_multiple: Gtk.Button = workbench.builder.get_object("button_multiple")


def on_single_selected(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    try:
        file = file_dialog.select_folder_finish(result)
    except GLib.Error as error:
        print(error, file=sys.stderr)
        return
    print(f"Selected Folder: {get_file_name(file)}")


def select_folder(_button: Gtk.Button) -> None:
    file_dialog = Gtk.FileDialog()
    file_dialog.select_folder(workbench.window, None, on_single_selected)


def on_multiple_selected(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    try:
        files = file_dialog.select_multiple_folders_finish(result)
    except GLib.Error as error:
        print(error, file=sys.stderr)
        return
    print(f"Selected Folders ({files.get_n_items()}):")
    for file in files:
        print(f"  {get_file_name(file)}")


def select_multiple_folders(_button: Gtk.Button) -> None:
    file_dialog = Gtk.FileDialog()
    file_dialog.select_multiple_folders(workbench.window, None, on_multiple_selected)


def get_file_name(file: Gio.File) -> str:
    info = file.query_info("standard::name", Gio.FileQueryInfoFlags.NONE, None)
    return info.get_name()


button_single.clicked.connect(select_folder)
button_multiple.clicked.connect(select_multiple_folders)
