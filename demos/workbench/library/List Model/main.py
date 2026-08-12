from PyLiite4 import Adw, GObject, Gtk

from demos.workbench import workbench

stack: Gtk.Stack = workbench.builder.get_object("stack")
list_box: Gtk.ListBox = workbench.builder.get_object("list_box")
flow_box: Gtk.FlowBox = workbench.builder.get_object("flow_box")
add: Gtk.Button = workbench.builder.get_object("add")
remove: Gtk.Button = workbench.builder.get_object("remove")
list_box_editable: Gtk.ListBox = workbench.builder.get_object("list_box_editable")
search_entry: Gtk.SearchEntry = workbench.builder.get_object("search_entry")

# Model
model = Gtk.StringList(strings=["Default Item 1", "Default Item 2", "Default Item 3"])
item = 1

model.items_changed.connect(
    lambda _self, position, removed, added: print(
        f"position: {position}, Item removed? {bool(removed)}, Item added? {bool(added)}",
    ),
)

# Filter-Model
search_expression = Gtk.PropertyExpression.new(
    Gtk.StringObject,
    None,
    "string",
)
filter = Gtk.StringFilter(
    expression=search_expression,
    ignore_case=True,
    match_mode=Gtk.StringFilterMatchMode.SUBSTRING,
)
filter_model = Gtk.FilterListModel(
    model=model,
    filter=filter,
    incremental=True,
)


def create_item_for_list_box(list_item: Gtk.StringObject) -> Gtk.Widget:
    list_row = Adw.ActionRow(
        title=list_item.get_string(),
    )
    return list_row


def create_item_for_flow_box(list_item: Gtk.StringObject) -> Gtk.Widget:
    list_box = Adw.Bin(
        width_request=160,
        height_request=160,
        css_classes=["card"],
        valign=Gtk.Align.START,
        child=Gtk.Label(
            label=list_item.get_string(),
            halign=Gtk.Align.CENTER,
            hexpand=True,
            valign=Gtk.Align.CENTER,
        ),
    )
    return list_box


def create_item_for_filter_model(list_item: Gtk.StringObject) -> Gtk.Widget:
    list_row = Adw.ActionRow(
        title=list_item.get_string(),
    )
    return list_row


def on_add_clicked(_button: Gtk.Button) -> None:
    global item
    new_item = f"Item {item}"
    model.append(new_item)
    item += 1


def on_remove_clicked(_button: Gtk.Button) -> None:
    selected_row = list_box_editable.get_selected_row()
    index = selected_row.get_index()
    model.remove(index)


list_box.bind_model(model, create_item_for_list_box)
flow_box.bind_model(model, create_item_for_flow_box)
list_box_editable.bind_model(filter_model, create_item_for_filter_model)


# Controller
add.clicked.connect(on_add_clicked)

remove.clicked.connect(on_remove_clicked)

search_entry.search_changed.connect(lambda _: filter.set_search(search_entry.get_text()))

# View
stack.notify["visible-child"].connect(lambda *_: print("View changed"))

list_box_editable.row_selected.connect(
    lambda *_: remove.set_sensitive(list_box_editable.get_selected_row() is not None),
)
