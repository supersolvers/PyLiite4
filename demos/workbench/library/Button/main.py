from PyLiite4 import Gtk

from demos.workbench import workbench

button_ids = [
    "regular",
    "flat",
    "suggested",
    "destructive",
    "custom",
    "disabled",
    "circular-plus",
    "circular-minus",
    "pill",
    "osd-left",
    "osd-right",
]


def on_clicked(button: Gtk.Button) -> None:
    print(f"{button.get_name()} clicked")


for id in button_ids:
    button: Gtk.Button = workbench.builder.get_object(id)
    button.clicked.connect(on_clicked)
