from collections.abc import Callable

from PyLiite4 import GObject, Gtk

from demos.workbench import workbench

buttons = {
    "button_no_look": "Don't look",
    "button_look": "Look",
    "button_camera": "Camera",
    "button_flashlight": "Flashlight",
    "button_console": "Console",
}


def on_active(name: str) -> Callable[[Gtk.ToggleButton, GObject.ParamSpec], None]:
    return lambda button, _: print(f'{name} {"On" if button.get_active() else "Off"}')


for id, name in buttons.items():
    button: Gtk.ToggleButton = workbench.builder.get_object(id)
    button.notify["active"].connect(on_active(name))
