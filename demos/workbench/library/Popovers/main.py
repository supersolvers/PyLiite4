from PyLiite4 import Gtk

from demos.workbench import workbench


def on_closed(popover: Gtk.Popover) -> None:
    name = popover.get_name()
    print(f"{name} closed.")


popover_ids = ("plain_popover", "popover_menu")

for id in popover_ids:
    popover: Gtk.Popover = workbench.builder.get_object(id)
    popover.closed.connect(on_closed)
