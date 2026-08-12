from PyLiite4 import GObject, Gtk

from demos.workbench import workbench

grid_view: Gtk.GridView = workbench.builder.get_object("grid_view")
add: Gtk.Button = workbench.builder.get_object("add")
remove: Gtk.Button = workbench.builder.get_object("remove")

item = 1

string_model = Gtk.StringList.new(
    ["Default Item 1", "Default Item 2", "Default Item 3"]
)

model = Gtk.SingleSelection(model=string_model)

factory_for_grid_view = Gtk.SignalListItemFactory()


def on_factory_for_grid_view_setup(_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    list_box = Gtk.Box(width_request=160, height_request=160, css_classes=["card"])
    label = Gtk.Label(halign=Gtk.Align.CENTER, hexpand=True, valign=Gtk.Align.CENTER)
    list_box.append(label)
    list_item.set_child(list_box)


def on_factory_for_grid_view_bind(_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    list_box: Gtk.Box = list_item.get_child()
    model_item: Gtk.StringObject = list_item.get_item()
    label_widget: Gtk.Label = list_box.get_last_child()

    label_widget.set_label(model_item.get_string())


factory_for_grid_view.setup.connect(on_factory_for_grid_view_setup)
factory_for_grid_view.bind.connect(on_factory_for_grid_view_bind)

grid_view.set_model(model)
grid_view.set_factory(factory_for_grid_view)


def on_item_changed(_list: Gtk.StringList, position: int, removed: int, added: int) -> None:
    print(
        f"position: {position}, Item removed? {removed != 0}, Item added? {added != 0}"
    )


def on_selection_changed(*_: object) -> None:
    selected_item = model.get_selected()
    print(f"Model item selected from view: {string_model.get_string(selected_item)}")


string_model.items_changed.connect(on_item_changed)
model.selection_changed.connect(on_selection_changed)


def on_add_clicked(*_: object) -> None:
    global item
    new_item = f"New item {item}"
    string_model.append(new_item)
    item += 1


def on_remove_clicked(*_: object) -> None:
    selected_item = model.get_selected()
    string_model.remove(selected_item)


add.clicked.connect(on_add_clicked)
remove.clicked.connect(on_remove_clicked)
