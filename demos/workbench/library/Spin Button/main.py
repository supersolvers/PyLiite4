from PyLiite4 import Gtk

from demos.workbench import workbench

hours: Gtk.SpinButton = workbench.builder.get_object("hours")
minutes: Gtk.SpinButton = workbench.builder.get_object("minutes")

hours.set_text("00")
minutes.set_text("00")


def tell_time(hours: Gtk.SpinButton, minutes: Gtk.SpinButton) -> str:
    return f"The time selected is {hours.get_text()}:{minutes.get_text()}"


def on_value_changed(spin_button: Gtk.SpinButton) -> bool:
    value = spin_button.get_adjustment().get_value()
    spin_button.set_text(f"{int(value):02}")
    return True


hours.value_changed.connect(lambda *_args: print(tell_time(hours, minutes)))
minutes.value_changed.connect(lambda *_args: print(tell_time(hours, minutes)))


hours.output.connect(on_value_changed)

minutes.output.connect(on_value_changed)


# This only works for one direction
# Add any extra logic to account for wrapping in both directions
minutes.wrapped.connect(lambda *_args: hours.spin(Gtk.SpinType.STEP_FORWARD, 1))
