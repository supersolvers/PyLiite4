from PyLiite4 import Gtk

from demos.workbench import workbench

list_view: Gtk.ListView = workbench.builder.get_object("list_view")
item_factory: Gtk.SignalListItemFactory = workbench.builder.get_object("item_factory")
header_factory: Gtk.SignalListItemFactory = workbench.builder.get_object("header_factory")


class CustomModel(Gtk.StringList, Gtk.SectionModel):
    def do_get_section(self, position: int) -> tuple[int, int]:
        start = position
        end = start + 5
        return (start, end)


def on_setup_item(_: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    list_item.set_child(Gtk.Label(margin_start=12, halign=Gtk.Align.START))


def on_bind_item(_: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    item: Gtk.StringObject = list_item.get_item()
    label: Gtk.Label = list_item.get_child()

    label.set_label(item.get_string())


def on_setup_header(_: Gtk.SignalListItemFactory, list_item: Gtk.ListHeader) -> None:
    list_item.set_child(Gtk.Label(label="Header", halign=Gtk.Align.START))


custom_model = CustomModel()

for i in range(1, 201):
    custom_model.append(f"Item {i}")

item_factory.setup.connect(on_setup_item)
item_factory.bind.connect(on_bind_item)

header_factory.setup.connect(on_setup_header)

selection_model = Gtk.NoSelection(model=custom_model)

list_view.set_model(selection_model)
