from PyLiite4 import Gtk

from demos.workbench import workbench

list_view: Gtk.ListView = workbench.builder.get_object("list_view")
add: Gtk.Button = workbench.builder.get_object("add")
remove: Gtk.Button = workbench.builder.get_object("remove")

string_model = Gtk.StringList.new(
    ["Default Item 1", "Default Item 2", "Default Item 3"]
)

item = 1

model = Gtk.SingleSelection(model=string_model)


def on_item_changed(_list: Gtk.StringList, position: int, removed: int, added: int) -> None:
    print(
        f"position: {position}, Item removed? {removed != 0}, Item added? {added != 0}"
    )


def on_selection_changed(*_: object) -> None:
    selected_item = model.get_selected()
    print(f"Model item selected from view: {string_model.get_string(selected_item)}")


string_model.items_changed.connect(on_item_changed)
model.selection_changed.connect(on_selection_changed)

list_view.set_model(model)


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
