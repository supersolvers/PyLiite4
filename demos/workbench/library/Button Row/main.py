from PyLiite4 import Adw

from demos.workbench import workbench

button_row_suggested: Adw.ButtonRow = workbench.builder.get_object("button_row_suggested")
button_row_destructive: Adw.ButtonRow = workbench.builder.get_object("button_row_destructive")


def on_suggested_activated(*_args: object) -> None:
    print("Suggested button row activated")


def on_destructive_activated(*_args: object) -> None:
    print("Destructive button row activated")


button_row_suggested.activated.connect(on_suggested_activated)
button_row_destructive.activated.connect(on_destructive_activated)
