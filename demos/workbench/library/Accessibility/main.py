from PyLiite4 import Adw, Gdk, GObject, Gtk

from demos.workbench import workbench

custom_button: Adw.Bin = workbench.builder.get_object("custom_button")


def toggle_button(button: Gtk.Widget) -> None:
    checked = button.get_state_flags() & Gtk.StateFlags.CHECKED != 0

    # Invert the current state
    checked = not checked
    pressed = Gtk.AccessibleTristate.TRUE if checked else Gtk.AccessibleTristate.FALSE

    # Update the accessible state
    state = GObject.Value()
    state.init(GObject.TYPE_INT)
    state.set_int(pressed)
    button.update_state([Gtk.AccessibleState.PRESSED], [state])

    # Update the widget state (i.e. CSS pseudo-class)
    if checked:
        button.set_state_flags(Gtk.StateFlags.CHECKED, False)
    else:
        button.unset_state_flags(Gtk.StateFlags.CHECKED)

    # Grab the focus
    button.grab_focus()


clicker = Gtk.GestureClick()
clicker.released.connect(lambda _clicker, _n_press, _x, _y: toggle_button(custom_button))
custom_button.add_controller(clicker)


def on_key_released(_controller: Gtk.EventControllerKey, keyval: int, _keycode: int,
                    _state: Gdk.ModifierType) -> None:
    keyvals = [
        Gdk.KEY_space,
        Gdk.KEY_KP_Space,
        Gdk.KEY_Return,
        Gdk.KEY_ISO_Enter,
        Gdk.KEY_KP_Enter,
    ]

    if keyval in keyvals:
        toggle_button(custom_button)


key_controller = Gtk.EventControllerKey()
key_controller.key_released.connect(on_key_released)
custom_button.add_controller(key_controller)
