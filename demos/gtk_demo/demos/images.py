"""Images
#Keywords: GdkPaintable, GtkWidgetPaintable

GtkImage and GtkPicture are used to display an image; the image can be
in a number of formats.

GtkImage is the widget used to display icons or images that should be
sized and styled like an icon, while GtkPicture is used for images
that should be displayed as-is.

This demo code shows some of the more obscure cases, in the simple
case a call to gtk_picture_new_for_file() or
gtk_image_new_from_icon_name() is all you need.
"""

from PyLiite4 import Gio, GObject, Gtk

from .pixbufpaintable import pixbuf_paintable_new_from_resource

window: Gtk.Window | None = None


def toggle_sensitivity_callback(togglebutton: Gtk.ToggleButton, user_data: Gtk.Widget) -> None:
    child = user_data.get_first_child()
    while child is not None:
        # don't disable our toggle
        if child != togglebutton:
            child.set_sensitive(not togglebutton.get_active())
        child = child.get_next_sibling()


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Images")
        window.close_request.connect(close_request)

        base_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        base_vbox.set_margin_start(16)
        base_vbox.set_margin_end(16)
        base_vbox.set_margin_top(16)
        base_vbox.set_margin_bottom(16)
        window.set_child(base_vbox)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        base_vbox.append(hbox)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hbox.append(vbox)

        label = Gtk.Label(label="Image from a resource")
        label.add_css_class("heading")
        vbox.append(label)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        vbox.append(frame)

        image = Gtk.Image.new_from_resource("/images/org.gtk.Demo4.svg")
        image.set_icon_size(Gtk.IconSize.LARGE)

        frame.set_child(image)

        # Animation

        label = Gtk.Label(label="Animation from a resource")
        label.add_css_class("heading")
        vbox.append(label)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        vbox.append(frame)

        paintable = pixbuf_paintable_new_from_resource("/images/floppybuddy.gif")
        picture = Gtk.Picture.new_for_paintable(paintable)

        frame.set_child(picture)

        # Symbolic icon

        label = Gtk.Label(label="Symbolic themed icon")
        label.add_css_class("heading")
        vbox.append(label)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        vbox.append(frame)

        gicon = Gio.ThemedIcon.new_with_default_fallbacks("battery-level-10-charging-symbolic")
        image = Gtk.Image.new_from_gicon(gicon)
        image.set_icon_size(Gtk.IconSize.LARGE)

        frame.set_child(image)

        # Stateful

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hbox.append(vbox)

        label = Gtk.Label(label="Stateful icon")
        label.add_css_class("heading")
        vbox.append(label)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        vbox.append(frame)

        paintable = Gtk.Svg.new_from_resource("/images/stateful.gpa")
        paintable.play()
        paintable.set_state(0)
        image = Gtk.Image.new_from_paintable(paintable)
        image.set_pixel_size(128)

        frame.set_child(image)

        state = Gtk.Switch()
        state.set_halign(Gtk.Align.START)
        state.bind_property("active", paintable, "state", GObject.BindingFlags.DEFAULT)
        vbox.append(state)

        # Animations

        label = Gtk.Label(label="Path animation")
        label.add_css_class("heading")
        vbox.append(label)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        vbox.append(frame)

        paintable = Gtk.Svg.new_from_resource("/images/animated.gpa")
        paintable.play()
        paintable.set_state(0)
        image = Gtk.Image.new_from_paintable(paintable)
        image.set_pixel_size(128)

        frame.set_child(image)

        # Video

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hbox.append(vbox)

        label = Gtk.Label(label="Displaying video")
        label.add_css_class("heading")
        vbox.append(label)

        frame = Gtk.Frame()
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        vbox.append(frame)

        video = Gtk.Video.new_for_resource("/images/gtk-logo.webm")
        video.get_media_stream().set_loop(True)
        frame.set_child(video)

        # Widget paintables
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hbox.append(vbox)

        label = Gtk.Label(label="GtkWidgetPaintable")
        label.add_css_class("heading")
        vbox.append(label)

        paintable = Gtk.WidgetPaintable.new(do_widget)
        picture = Gtk.Picture.new_for_paintable(paintable)
        picture.set_size_request(100, 100)
        picture.set_valign(Gtk.Align.START)
        vbox.append(picture)

        # Sensitivity control
        button = Gtk.ToggleButton.new_with_mnemonic("_Insensitive")
        button.set_halign(Gtk.Align.END)
        button.set_valign(Gtk.Align.END)
        button.set_vexpand(True)
        base_vbox.append(button)

        button.toggled.connect(toggle_sensitivity_callback, base_vbox)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
