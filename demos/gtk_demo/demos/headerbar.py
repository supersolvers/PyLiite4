"""Header Bar
#Keywords: GtkWindowHandle, GtkWindowControls

GtkHeaderBar is a container that is suitable for implementing
window titlebars. One of its features is that it can position
a title centered with regard to the full width, regardless of
variable-width content at the left or right.

It is commonly used with gtk_window_set_titlebar()
"""

from PyLiite4 import Gtk

window: Gtk.Window | None = None


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
        window.set_title("Welcome to the Hotel California")
        window.close_request.connect(close_request)

        window.set_default_size(600, 400)

        header = Gtk.HeaderBar()

        button = Gtk.Button.new_from_icon_name("mail-send-receive-symbolic")
        button.set_tooltip_text("Check out")
        header.pack_end(button)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.add_css_class("linked")
        button = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        button.set_tooltip_text("Back")
        box.append(button)
        button = Gtk.Button.new_from_icon_name("go-next-symbolic")
        button.set_tooltip_text("Forward")
        box.append(button)

        header.pack_start(box)
        switch = Gtk.Switch()
        switch.update_property([Gtk.AccessibleProperty.LABEL], ["Change something"])
        header.pack_start(switch)

        window.set_titlebar(header)

        content = Gtk.TextView()
        content.update_property([Gtk.AccessibleProperty.LABEL], ["Content"])
        window.set_child(content)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
