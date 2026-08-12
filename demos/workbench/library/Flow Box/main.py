from PyLiite4 import Adw, Gtk

from demos.workbench import workbench

flowbox: Gtk.FlowBox = workbench.builder.get_object("flowbox")


def add_emoji(_flowbox: Gtk.FlowBox, unicode: str) -> None:
    item = Adw.Bin(
        child=Gtk.Label(
            vexpand=True,
            hexpand=True,
            label=unicode,
            css_classes=["emoji"],
        ),
        width_request=100,
        height_request=100,
        css_classes=["card"],
    )
    _flowbox.append(item)


for code in range(128513, 128591):
    add_emoji(flowbox, chr(code))


def on_item_selected(_flowbox: Gtk.FlowBox, item: Gtk.FlowBoxChild) -> None:
    # FlowBoxChild -> AdwBin -> Label
    emoji = item.get_child().get_child().get_label()
    print("Unicode:", emoji.encode("unicode-escape"))


flowbox.child_activated.connect(on_item_selected)
