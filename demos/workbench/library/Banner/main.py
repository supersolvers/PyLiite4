from PyLiite4 import Adw, Gtk

from demos.workbench import workbench

banner: Adw.Banner = workbench.builder.get_object("banner")
overlay: Adw.ToastOverlay = workbench.builder.get_object("overlay")
button_show_banner: Gtk.Button = workbench.builder.get_object("button_show_banner")


def alert(_banner: Adw.Banner) -> None:
    _banner.set_revealed(False)

    toast = Adw.Toast(
        title="Troubleshoot successful!",
        timeout=3,
    )
    overlay.add_toast(toast)


banner.button_clicked.connect(alert)

button_show_banner.clicked.connect(lambda *_: banner.set_revealed(True))
