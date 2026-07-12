"""Stack Sidebar

GtkStackSidebar provides an automatic sidebar widget to control
navigation of a GtkStack object. This widget automatically updates
its content based on what is presently available in the GtkStack
object, and using the "title" child property to set the display labels.
"""

from PyLiite4 import Gtk

window: Gtk.Window | None = None


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    pages = [
        "Welcome to GTK",
        "GtkStackSidebar Widget",
        "Automatic navigation",
        "Consistent appearance",
        "Scrolling",
        "Page 6",
        "Page 7",
        "Page 8",
        "Page 9",
    ]

    if window is None:
        window = Gtk.Window()
        window.set_resizable(True)

        header = Gtk.HeaderBar()
        window.set_titlebar(header)
        window.set_title("Stack Sidebar")
        window.destroy.connect(destroyed)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        sidebar = Gtk.StackSidebar()
        box.append(sidebar)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        sidebar.set_stack(stack)
        stack.set_hexpand(True)

        box.append(stack)

        for i, c in enumerate(pages):
            if i == 0:
                widget = Gtk.Image.new_from_icon_name("org.gtk.Demo4")
                widget.add_css_class("icon-dropshadow")
                widget.set_pixel_size(256)
            else:
                widget = Gtk.Label(label=c)
            stack.add_named(widget, c)
            stack.get_page(widget).set_property("title", c)

        window.set_child(box)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
