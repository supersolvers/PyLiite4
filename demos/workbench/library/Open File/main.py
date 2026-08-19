from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

button_single: Gtk.Button = workbench.builder.get_object("button_single")
button_image: Gtk.Button = workbench.builder.get_object("button_image")
button_multiple: Gtk.Button = workbench.builder.get_object("button_multiple")
file_filter_image: Gtk.FileFilter = workbench.builder.get_object("file_filter_image")


def on_file_opened(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    file = file_dialog.open_finish(result)
    print(f"Selected File: {get_file_name(file)}")


def open_file() -> None:
    dialog = Gtk.FileDialog()
    dialog.open(workbench.window, None, on_file_opened)


def on_image_opened(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    file = file_dialog.open_finish(result)
    print(f"Selected Image: {get_file_name(file)}")


def open_image() -> None:
    file_dialog = Gtk.FileDialog(default_filter=file_filter_image)
    file_dialog.open(workbench.window, None, on_image_opened)


def on_multiple_files_opened(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    files = file_dialog.open_multiple_finish(result)
    print(f"Selected Files ({files.get_n_items()}):")
    for file in files:
        print(f"  {get_file_name(file)}")


def open_multiple_files() -> None:
    file_dialog = Gtk.FileDialog()
    file_dialog.open_multiple(workbench.window, None, on_multiple_files_opened)


def get_file_name(file: Gio.File) -> str:
    info = file.query_info("standard::name", Gio.FileQueryInfoFlags.NONE, None)
    return info.get_name()


button_single.clicked.connect(lambda *_: open_file())
button_image.clicked.connect(lambda *_: open_image())
button_multiple.clicked.connect(lambda *_: open_multiple_files())
