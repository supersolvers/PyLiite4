from PyLiite4 import Gtk

from demos.workbench import workbench

radio_button_1: Gtk.CheckButton = workbench.builder.get_object("radio_button_1")
radio_button_2: Gtk.CheckButton = workbench.builder.get_object("radio_button_2")

radio_button_1.toggled.connect(lambda widget: on_toggled(widget, "Force Light Mode"))
radio_button_2.toggled.connect(lambda widget: on_toggled(widget, "Force Dark Mode"))


def on_toggled(radio_button: Gtk.CheckButton, message: str) -> None:
    if radio_button.get_active():
        print(message)
