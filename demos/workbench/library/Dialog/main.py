from PyLiite4 import Adw, Gio, Gtk

from demos.workbench import workbench

dialog: Adw.Dialog = workbench.builder.get_object("dialog")
button: Gtk.Button = workbench.builder.get_object("button")
image: Gtk.Image = workbench.builder.get_object("image")

image.set_from_file(Gio.File.new_for_uri(workbench.resolve("image.svg")).get_path())


def on_button_clicked(_button: Gtk.Button) -> None:
    dialog.present(workbench.window)


def on_dialog_close_attempt(_dialog: Adw.Dialog) -> None:
    print("Close Attempt")
    dialog.force_close()


def on_dialog_closed(_dialog: Adw.Dialog) -> None:
    print("Closed")


button.clicked.connect(on_button_clicked)
dialog.close_attempt.connect(on_dialog_close_attempt)
dialog.closed.connect(on_dialog_closed)
