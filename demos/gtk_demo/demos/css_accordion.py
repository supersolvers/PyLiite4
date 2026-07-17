"""Theming/CSS Accordion

A simple accordion demo written using CSS transitions and multiple backgrounds
"""

from collections.abc import Callable

from PyLiite4 import Gtk


def destroy_provider(window: Gtk.Widget, provider: Gtk.StyleProvider) -> None:
    Gtk.StyleContext.remove_provider_for_display(window.get_display(), provider)


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()
    if window is None:
        window = Gtk.Window()
        window.set_title("CSS Accordion")
        window.set_transient_for(do_widget)
        window.set_default_size(600, 300)
        window_ref = window.weak_ref()

        styled_box = Gtk.Frame()
        window.set_child(styled_box)
        styled_box.add_css_class("accordion")
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        container.set_halign(Gtk.Align.CENTER)
        container.set_valign(Gtk.Align.CENTER)
        styled_box.set_child(container)

        child = Gtk.Button.new_with_label("This")
        container.append(child)

        child = Gtk.Button.new_with_label("Is")
        container.append(child)

        child = Gtk.Button.new_with_label("A")
        container.append(child)

        child = Gtk.Button.new_with_label("CSS")
        container.append(child)

        child = Gtk.Button.new_with_label("Accordion")
        container.append(child)

        child = Gtk.Button.new_with_label(":-)")
        container.append(child)

        provider = Gtk.CssProvider()
        provider.load_from_resource("/css_accordion/css_accordion.css")

        Gtk.StyleContext.add_provider_for_display(window.get_display(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        window.destroy.connect(destroy_provider, provider)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
