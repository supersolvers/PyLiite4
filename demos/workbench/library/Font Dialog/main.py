from PyLiite4 import GObject, Gio, Gtk, Pango

from demos.workbench import workbench

font_dialog_button: Gtk.FontDialogButton = workbench.builder.get_object("font_dialog_button")
custom_button: Gtk.Button = workbench.builder.get_object("custom_button")

dialog_standard = Gtk.FontDialog(title="Select a Font", modal=True)
font_dialog_button.set_dialog(dialog_standard)


def on_font_description_changed(_button: Gtk.FontDialogButton, _description: GObject.ParamSpec) -> None:
    font_name = font_dialog_button.get_font_desc().to_string()
    print(f"Font: {font_name}")


def on_clicked(_button: Gtk.Button) -> None:
    dialog_custom.choose_family(workbench.window, None, None, on_family_chosen)


def on_family_chosen(_dialog: Gtk.FontDialog, result: Gio.AsyncResult) -> None:
    family: Pango.FontFamily = dialog_custom.choose_family_finish(result)
    print(f"Font Family: {family.get_name()}")


font_dialog_button.notify["font-desc"].connect(on_font_description_changed)

dialog_custom = Gtk.FontDialog(
    title="Select a Font Family",
    modal=True,
)

custom_button.clicked.connect(on_clicked)
