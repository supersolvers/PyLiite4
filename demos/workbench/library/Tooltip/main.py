from PyLiite4 import Gtk

from demos.workbench import workbench

button: Gtk.Button = workbench.builder.get_object("button")


def on_query_tooltip(_button: Gtk.Button, _x: int, _y: int, _mode: bool, tooltip: Gtk.Tooltip) -> bool:
    custom_tooltip = Gtk.Box(spacing=6)
    label = Gtk.Label(label="This is a custom tooltip")
    icon = Gtk.Image(icon_name="emoji-body-symbolic")
    custom_tooltip.append(label)
    custom_tooltip.append(icon)

    tooltip.set_custom(custom_tooltip)
    return True


button.query_tooltip.connect(on_query_tooltip)
