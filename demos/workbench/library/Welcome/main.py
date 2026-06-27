from PyLiite4 import Adw, Gtk

from demos.workbench import workbench


def greet(_button: Gtk.Button) -> None:
    dialog = Adw.AlertDialog(body="Hello World!")
    dialog.add_response("ok", "Ok")
    dialog.response.connect(dialog_response)
    dialog.present(workbench.window)


def dialog_response(dialog: Adw.AlertDialog, response: str) -> None:
    print(response)
    dialog.close()


subtitle_box: Gtk.Box = workbench.builder.get_object("subtitle")

button = Gtk.Button(label="Press me", margin_top=6, css_classes=["suggested-action"])
button.clicked.connect(greet)

subtitle_box.append(button)

print("Welcome to Workbench!")
