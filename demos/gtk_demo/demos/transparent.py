"""Overlay/Transparency
#Keywords: GtkOverlay, GtkSnapshot, blur, backdrop-filter

Blur the background behind an overlay.
"""

from PyLiite4 import Gdk, Gtk

window: Gtk.Window | None = None
css_provider: Gtk.CssProvider | None = None


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window, css_provider

    if css_provider is None:
        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/transparent/transparent.css")

        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_default_size(450, 450)
        window.destroy.connect(destroyed)

        window.set_title("Transparency")

        overlay = Gtk.Overlay()
        window.set_child(overlay)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.set_hexpand(True)
        box.set_homogeneous(True)
        box.add_css_class("floating-controls")

        box.set_halign(Gtk.Align.FILL)
        box.set_valign(Gtk.Align.END)

        overlay.add_overlay(box)

        button = Gtk.Button.new_with_label("Don't click this button!")
        button.add_css_class("blur-overlay")

        box.append(button)

        button = Gtk.Button.new_with_label("Maybe this one?")
        button.add_css_class("blur-overlay")

        box.append(button)

        picture = Gtk.Picture.new_for_resource("/transparent/portland-rose.jpg")
        picture.set_content_fit(Gtk.ContentFit.COVER)
        overlay.set_child(picture)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
