from PyLiite4 import Gdk, Gio, Gtk, Xdp, XdpGtk4

from demos.workbench import workbench

portal = Xdp.Portal()
parent = XdpGtk4.parent_new_gtk(workbench.window)
button: Gtk.Button = workbench.builder.get_object("button")


def on_selected(_portal: Xdp.Portal, task: Gio.AsyncResult) -> None:
    color = Gdk.RGBA()

    color.red, color.green, color.blue = _portal.pick_color_finish(task)
    color.alpha = 1

    print(f"Selected color is: {color.to_string()}")


def on_clicked(_button: Gtk.Button) -> None:
    # result is a GVariant of the form (ddd), containing red, green and blue components in the range [0,1]
    portal.pick_color(parent, None, on_selected)


button.clicked.connect(on_clicked)
