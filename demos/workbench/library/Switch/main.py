from PyLiite4 import Gtk

from demos.workbench import workbench

switch_on: Gtk.Switch = workbench.builder.get_object("switch_on")
label_on: Gtk.Label = workbench.builder.get_object("label_on")

switch_off: Gtk.Switch = workbench.builder.get_object("switch_off")
label_off: Gtk.Label = workbench.builder.get_object("label_off")


def on_switch_on_activated(*_args: object) -> None:
    label_on.set_label("On" if switch_on.get_active() else "Off")
    switch_off.set_active(not switch_on.get_active())


def on_switch_off_activated(*_args: object) -> None:
    label_off.set_label("On" if switch_off.get_active() else "Off")
    switch_on.set_active(not switch_off.get_active())


switch_on.notify["active"].connect(on_switch_on_activated)

switch_off.notify["active"].connect(on_switch_off_activated)
