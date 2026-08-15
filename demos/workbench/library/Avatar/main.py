from PyLiite4 import Adw, Gdk, Gio, Gly, Gtk

from demos.workbench import workbench

file_filter = Gtk.FileFilter(name="Images", mime_types=Gly.Loader.get_mime_types())

file_dialog = Gtk.FileDialog(
    title="Select an Avatar",
    modal=True,
    default_filter=file_filter,
)

avatar_image: Adw.Avatar = workbench.builder.get_object("avatar_image")
button: Gtk.Button = workbench.builder.get_object("button")

button.clicked.connect(lambda *_: on_clicked())


def on_selected(file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
    file = file_dialog.open_finish(result)
    texture = Gdk.Texture.new_from_file(file)
    avatar_image.set_custom_image(texture)


def on_clicked() -> None:
    file_dialog.open(workbench.window, None, on_selected)
