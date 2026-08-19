from PyLiite4 import Adw, Gio, GLib, Gtk, Xdp, XdpGtk4

from demos.workbench import workbench

portal = Xdp.Portal()
parent = XdpGtk4.parent_new_gtk(workbench.window)

button: Gtk.Button = workbench.builder.get_object("button")
picture: Gtk.Picture = workbench.builder.get_object("picture")

button.clicked.connect(lambda _: take_screenshot())


def take_screenshot() -> None:
    flags = Xdp.ScreenshotFlags.NONE
    portal.take_screenshot(parent, flags, None, on_finished)


def on_finished(portal: Xdp.Portal, result: Gio.AsyncResult) -> None:
    try:
        uri = portal.take_screenshot_finish(result)
    except GLib.Error:
        show_permission_error()
        return
    file = Gio.File.new_for_uri(uri)
    picture.set_file(file)


def show_permission_error() -> None:
    dialog = Adw.AlertDialog(
        heading="Permission Error",
        body="Ensure Screenshot permission is enabled in\nSettings → Apps → Workbench",
        close_response="ok",
    )

    dialog.add_response("ok", "OK")
    dialog.present(workbench.window)
