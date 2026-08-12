from PyLiite4 import Gio, GObject, Gtk

from demos.workbench import workbench

list_view: Gtk.ListView = workbench.builder.get_object("list_view")
factory: Gtk.SignalListItemFactory = workbench.builder.get_object("factory")


class TreeNode(GObject.Object):
    def __init__(self, _title: str, _children: list["TreeNode"] | None = None) -> None:
        super().__init__()
        self.children = _children or []
        self.title = _title


class TreeWidget(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(
            spacing=6, margin_start=6, margin_end=12, margin_top=6, margin_bottom=6
        )

        self.expander = Gtk.TreeExpander.new()

        self.label = Gtk.Label(halign=Gtk.Align.START)

        self.append(self.expander)
        self.append(self.label)


def create_model_func(item: TreeNode) -> Gio.ListModel | None:
    if item.children == []:
        return None
    child_model = Gio.ListStore.new(TreeNode)
    for child in item.children:
        child_model.append(child)
    return child_model


def on_setup(_: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    list_item.set_child(TreeWidget())


def on_bind(_: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    list_row: Gtk.TreeListRow = list_item.get_item()
    widget: TreeWidget = list_item.get_child()
    item: TreeNode = list_row.get_item()

    widget.expander.set_list_row(list_row)
    widget.label.set_label(item.title)


factory.setup.connect(on_setup)
factory.bind.connect(on_bind)

root_model = TreeNode(
    "Root",
    [
        TreeNode("Child 1", [TreeNode("Child 1.1", []), TreeNode("Child 1.2", [])]),
        TreeNode(
            "Child 2",
            [
                TreeNode("Child 2.1", []),
                TreeNode("Child 2.2", []),
                TreeNode("Child 2.3", [TreeNode("Child 3.1", [])]),
            ],
        ),
    ],
)

tree_model = Gio.ListStore.new(TreeNode)
tree_model.append(root_model)

tree_list_model = Gtk.TreeListModel.new(tree_model, False, True, create_model_func)
tree_list_model.set_autoexpand(False)

selection_model = Gtk.NoSelection(model=tree_list_model)

list_view.set_model(selection_model)
