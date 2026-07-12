"""Aspect Frame

GtkAspectFrame makes sure its child gets a specific aspect ratio.
"""

from collections.abc import Callable

from PyLiite4 import GObject, Gtk

# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def setup_ui(window: Gtk.Window) -> None:
    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.2, 5.0, 0.1)
    scale.set_draw_value(True)
    scale.set_digits(2)
    scale.set_value(1.5)

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    box.set_vexpand(True)

    label = Gtk.Label(label="This wrapping label is always given a specific aspect ratio by the aspect frame. The "
                            "specific aspect ratio can be controlled by dragging the slider. The picture is always "
                            "given its natural aspect ratio. Try resizing the window to see how the two aspect "
                            "frames react to different available sizes, and how the box distributes space between "
                            "them.")
    label.set_wrap(True)
    label.set_max_width_chars(50)
    aspect_frame = Gtk.AspectFrame.new(0.5, 0.5, 1.5, False)
    scale.get_adjustment().bind_property("value", aspect_frame, "ratio", GObject.BindingFlags.DEFAULT)
    aspect_frame.set_child(label)
    aspect_frame.set_hexpand(True)
    box.append(aspect_frame)

    aspect_frame = Gtk.AspectFrame.new(0.5, 0.5, 0, True)
    aspect_frame.set_child(Gtk.Picture.new_for_resource("/aspect_frame/ducky.png"))
    box.append(aspect_frame)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    vbox.append(scale)
    vbox.append(box)

    window.set_child(vbox)


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()
    if window is None:
        window = Gtk.Window()
        window_ref = window.weak_ref()
        window.set_display(do_widget.get_display())

        window.set_title("Aspect Frame")
        window.add_css_class("aspect-frame-demo")

        provider = Gtk.CssProvider()
        provider.load_from_resource("/aspect_frame/aspect_frame.css")
        Gtk.StyleContext.add_provider_for_display(do_widget.get_display(), provider, 800)

        setup_ui(window)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
