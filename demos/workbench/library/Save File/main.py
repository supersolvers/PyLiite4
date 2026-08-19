import sys

from PyLiite4 import Gio, GLib, Gtk

from demos.workbench import workbench

button: Gtk.Button = workbench.builder.get_object("button")


def save_file(_button: Gtk.Button) -> None:
    file_dialog = Gtk.FileDialog(initial_name="Workbench.txt")
    file_dialog.save(workbench.window, None, on_save)


def on_save(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    # "save_finish" returns a Gio.File you can write to
    try:
        file = file_dialog.save_finish(result)
    except GLib.Error as error:
        print(error, file=sys.stderr)
        return
    contents = "Hello from Workbench!".encode("UTF-8")
    file.replace_contents_async(contents, None, False, Gio.FileCreateFlags.NONE, None, on_replace_contents)


def on_replace_contents(file: Gio.File, result: Gio.AsyncResult) -> None:
    file.replace_contents_finish(result)
    print(f"File {file.get_basename()} saved")


# Handle button click
button.clicked.connect(save_file)
