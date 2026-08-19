from PyLiite4 import Adw, Gio, Gtk

from demos.workbench import workbench

banner: Adw.Banner = workbench.builder.get_object("banner")
network_monitor = Gio.NetworkMonitor.get_default()
level_bar: Gtk.LevelBar = workbench.builder.get_object("level_bar")


def set_network_status() -> None:
    banner.set_revealed(network_monitor.get_network_metered())
    level_bar.set_value(network_monitor.get_connectivity())


set_network_status()
network_monitor.network_changed.connect(lambda *_: set_network_status())

banner.button_clicked.connect(lambda _: banner.set_revealed(False))
