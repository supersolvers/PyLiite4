"""Spin Buttons
#Keywords: GtkEntry

GtkSpinButton provides convenient ways to input data
that can be seen as a value in a range. The examples
here show that this does not necessarily mean numeric
values, and it can include custom formatting.
"""

import ctypes
import math
import re
from collections.abc import Callable

from PyLiite4 import Gio, GObject, Gtk

# GtkSpinButton::input hands its handler a double to fill in, which PyGObject can't pass to Python: it reads the
# pointer as a double and can't take the value back. So the input handlers are connected through ctypes, with the
# C signature, and get the new value back from Python as (result, new_val).
_gobject = ctypes.CDLL("libgobject-2.0.so.0")
_INPUT_FUNC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_double), ctypes.c_void_p)
_gobject.g_signal_connect_data.argtypes = [ctypes.c_void_p, ctypes.c_char_p, _INPUT_FUNC, ctypes.c_void_p,
                                           ctypes.c_void_p, ctypes.c_int]
_gobject.g_signal_connect_data.restype = ctypes.c_ulong
_input_closures: list[object] = []


def connect_input(spin_button: Gtk.SpinButton, handler: Callable[[Gtk.SpinButton], tuple[int, float]]) -> None:
    def input(_instance: int, new_val: ctypes.POINTER(ctypes.c_double), _data: int) -> int:
        result, new_val[0] = handler(spin_button)
        return result

    callback = _INPUT_FUNC(input)
    _input_closures.append(callback)
    _gobject.g_signal_connect_data(hash(spin_button), b"input", callback, None, None, 0)


def spinbutton_hex_spin_input(spin_button: Gtk.SpinButton) -> tuple[int, float]:
    buf = spin_button.get_text()
    # As strtol (buf, &err, 16): the longest hexadecimal prefix, and an error if anything follows it
    match = re.match(r"\s*([+-]?)(?:0[xX](?=[0-9a-fA-F]))?([0-9a-fA-F]*)", buf)
    res = float(int(match[1] + match[2], 16)) if match[2] else 0.0
    if match.end() < len(buf):
        return Gtk.INPUT_ERROR, res
    else:
        return True, res


def spinbutton_hex_spin_output(spin_button: Gtk.SpinButton) -> bool:
    adjustment = spin_button.get_adjustment()
    val = adjustment.get_value()
    if abs(val) < 1e-5:
        buf = "0x00"
    else:
        buf = f"0x{int(val):02X}"
    if buf != spin_button.get_text():
        spin_button.set_text(buf)

    return True


def spinbutton_time_spin_input(spin_button: Gtk.SpinButton) -> tuple[int, float]:
    text = spin_button.get_text()
    str = text.split(":", 1)

    if len(str) == 2 and re.fullmatch(r"\s*[+-]?\d+", str[0]) and re.fullmatch(r"\s*[+-]?\d+", str[1]):
        hours = int(str[0])
        minutes = int(str[1])
        if 0 <= hours < 24 and 0 <= minutes < 60:
            return True, hours * 60 + minutes

    return Gtk.INPUT_ERROR, 0.0


def spinbutton_time_spin_output(spin_button: Gtk.SpinButton) -> bool:
    adjustment = spin_button.get_adjustment()
    hours = adjustment.get_value() / 60.0
    minutes = (hours - math.floor(hours)) * 60.0
    buf = f"{math.floor(hours):02.0f}:{math.floor(minutes + 0.5):02.0f}"
    if buf != spin_button.get_text():
        spin_button.set_text(buf)

    return True


month = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def spinbutton_month_spin_input(spin_button: Gtk.SpinButton) -> tuple[int, float]:
    for i in range(1, 13):
        if month[i - 1].upper().startswith(spin_button.get_text().upper()):
            return True, float(i)

    return Gtk.INPUT_ERROR, 0.0


def spinbutton_month_spin_output(spin_button: Gtk.SpinButton) -> bool:
    adjustment = spin_button.get_adjustment()
    value = adjustment.get_value()
    for i in range(1, 13):
        if abs(value - i) < 1e-5:
            if month[i - 1] != spin_button.get_text():
                spin_button.set_text(month[i - 1])

    return True


def value_to_label(binding: GObject.Binding, value: float) -> str:
    return f"{value:g}"


window: Gtk.Window | None = None


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None
    _input_closures.clear()


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        builder = Gtk.Builder({
            "spinbutton_hex_spin_output": spinbutton_hex_spin_output,
            "spinbutton_time_spin_output": spinbutton_time_spin_output,
            "spinbutton_month_spin_output": spinbutton_month_spin_output,
        })
        # The input handlers can't be connected from Python by the builder (see connect_input above), so they are
        # taken out of the UI file and connected below.
        ui = Gio.resources_lookup_data("/spinbutton/spinbutton.ui", Gio.ResourceLookupFlags.NONE).get_data().decode()
        inputs = re.findall(r'<object class="GtkSpinButton" id="(\w+)">(?:(?!</object>).)*?'
                            r'<signal name="input" handler="(\w+)"/>', ui, re.S)
        builder_ui = re.sub(r'\s*<signal name="input" handler="\w+"/>', "", ui)
        builder.add_from_string(builder_ui)
        for id, handler in inputs:
            connect_input(builder.get_object(id), globals()[handler])

        window = builder.get_object("window")
        window.set_display(do_widget.get_display())
        window.set_title("Spin Buttons")
        window.set_resizable(False)
        window.destroy.connect(destroyed)

        for name in ("basic", "hex", "time", "month"):
            adj = builder.get_object(f"{name}_adjustment")
            label = builder.get_object(f"{name}_label")
            adj.bind_property("value", label, "label", GObject.BindingFlags.SYNC_CREATE, value_to_label)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window

