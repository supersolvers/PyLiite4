from PyLiite4 import Gdk, Gio, Gtk

from demos.workbench import workbench

color_dialog_button: Gtk.ColorDialogButton = workbench.builder.get_object("color_dialog_button")
custom_button: Gtk.Button = workbench.builder.get_object("custom_button")

color = Gdk.RGBA()
color.parse("red")

dialog_standard = Gtk.ColorDialog(
    title="Select a color",
    modal=True,
    with_alpha=True,
)

color_dialog_button.set_dialog(dialog_standard)
color_dialog_button.set_rgba(color)

color_dialog_button.notify["rgba"].connect(
    lambda *_: print(
        f"Color Dialog Button: The color selected is {color_dialog_button.get_rgba().to_string()}",
    ),
)

dialog_custom = Gtk.ColorDialog(
    title="Select a color",
    modal=True,
    with_alpha=False,
)


def on_color_selected(_dialog: Gtk.ColorDialog, _result: Gio.AsyncResult) -> None:
    color = _dialog.choose_rgba_finish(_result)
    print(f"Custom Button: The color selected is {color.to_string()}")


def on_clicked(_button: Gtk.Button) -> None:
    dialog_custom.choose_rgba(workbench.window, None, None, on_color_selected)


custom_button.clicked.connect(on_clicked)
