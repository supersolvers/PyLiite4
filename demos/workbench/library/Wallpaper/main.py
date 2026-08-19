from PyLiite4 import Gio, GLib, Gtk, Xdp, XdpGtk4

from demos.workbench import workbench

portal = Xdp.Portal()
parent = XdpGtk4.parent_new_gtk(workbench.window)
button: Gtk.Button = workbench.builder.get_object("button")

uri = workbench.resolve("./wallpaper.png")


def on_wallpaper_set(_portal: Xdp.Portal, result: Gio.AsyncResult) -> None:
    try:
        success = _portal.set_wallpaper_finish(result)
    except GLib.Error:
        success = False
    if success:
        print("Wallpaper set successfully")
    else:
        print("Could not set wallpaper")


def on_clicked(_button: Gtk.Button) -> None:
    portal.set_wallpaper(
        parent,
        uri,
        Xdp.WallpaperFlags.PREVIEW | Xdp.WallpaperFlags.BACKGROUND | Xdp.WallpaperFlags.LOCKSCREEN,
        None,
        on_wallpaper_set,
    )


button.clicked.connect(on_clicked)
