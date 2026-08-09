from PyLiite4 import Adw, GObject, Gtk

from demos.workbench import workbench

circular_switch: Adw.SwitchRow = workbench.builder.get_object("circular_switch")
secondary_button: Gtk.MenuButton = workbench.builder.get_object("secondary")


def update_css(_widget: Adw.SwitchRow, _params: GObject.ParamSpec) -> None:
    if circular_switch.get_active():
        secondary_button.add_css_class("circular")
    else:
        secondary_button.remove_css_class("circular")


circular_switch.notify["active"].connect(update_css)
