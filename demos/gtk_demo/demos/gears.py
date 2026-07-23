"""OpenGL/Gears

This is a classic OpenGL demo, running in a GtkGLArea.
"""

from collections.abc import Callable

from PyLiite4 import Gtk

from .gtkgears import GTK_GEARS_N_AXIS, GTK_GEARS_X_AXIS, GTK_GEARS_Y_AXIS, GTK_GEARS_Z_AXIS, GtkGears, gtk_gears_new


def on_axis_value_change(adjustment: Gtk.Adjustment, data: Callable[[], GtkGears]) -> None:
    gears = data()
    axis = adjustment.axis

    gears.set_axis(axis, adjustment.get_value())


def create_axis_slider(gears: GtkGears, axis: int) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    if axis == GTK_GEARS_X_AXIS:
        text = "X"
    elif axis == GTK_GEARS_Y_AXIS:
        text = "Y"
    elif axis == GTK_GEARS_Z_AXIS:
        text = "Z"
    else:
        raise AssertionError("not reached")

    label = Gtk.Label(label=text)
    box.append(label)

    adj = Gtk.Adjustment(value=gears.get_axis(axis), lower=0.0, upper=360.0, step_increment=1.0,
                         page_increment=12.0, page_size=0.0)
    adj.axis = axis
    # Passed weakly: the window holds the adjustment, so a strong reference would keep it alive after it's destroyed.
    adj.value_changed.connect(on_axis_value_change, gears.weak_ref())
    slider = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=adj)
    slider.set_draw_value(False)
    box.append(slider)
    slider.set_vexpand(True)

    return box


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref

    window = window_ref()
    if window is None:
        window = Gtk.Window()
        window_ref = window.weak_ref()
        window.set_title("Gears")
        window.set_resizable(True)
        window.set_default_size(640, 640)

        overlay = Gtk.Overlay()
        overlay.set_margin_start(12)
        overlay.set_margin_end(12)
        overlay.set_margin_top(12)
        overlay.set_margin_bottom(12)

        window.set_child(overlay)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.START)
        frame.set_valign(Gtk.Align.START)
        frame.add_css_class("app-notification")
        overlay.add_overlay(frame)

        fps_label = Gtk.Label(label="")
        fps_label.set_halign(Gtk.Align.START)
        frame.set_child(fps_label)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_spacing(6)
        overlay.set_child(box)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.set_spacing(6)
        box.append(hbox)

        gears = gtk_gears_new()
        gears.set_hexpand(True)
        gears.set_vexpand(True)
        hbox.append(gears)

        for i in range(GTK_GEARS_N_AXIS):
            hbox.append(create_axis_slider(gears, i))

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hbox.set_spacing(6)
        box.append(hbox)

        gears.set_fps_label(fps_label)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
