"""Tree View/Editable Cells

This demo demonstrates the use of editable cells in a GtkTreeView. If
you're new to the GtkTreeView widgets and associates, look into
the GtkListStore example first. It also shows how to use the
GtkCellRenderer::editing-started signal to do custom setup of the
editable widget.

The cell renderers used in this demo are GtkCellRendererText,
GtkCellRendererCombo and GtkCellRendererProgress.
"""

from dataclasses import dataclass

from collections.abc import Callable

from PyLiite4 import Gtk


@dataclass
class Item:
    number: int
    product: str
    yummy: int


COLUMN_ITEM_NUMBER = 0
COLUMN_ITEM_PRODUCT = 1
COLUMN_ITEM_YUMMY = 2
NUM_ITEM_COLUMNS = 3

COLUMN_NUMBER_TEXT = 0
NUM_NUMBER_COLUMNS = 1

articles: list[Item] | None = None


def add_items() -> None:
    assert articles is not None

    articles.append(Item(3, "bottles of coke", 20))
    articles.append(Item(5, "packages of noodles", 50))
    articles.append(Item(2, "packages of chocolate chip cookies", 90))
    articles.append(Item(1, "can vanilla ice cream", 60))
    articles.append(Item(6, "eggs", 10))


def create_items_model() -> Gtk.TreeModel:
    global articles

    # create array
    articles = []

    add_items()

    # create list store
    model = Gtk.ListStore(int, str, int)

    # add items
    for item in articles:
        iter = model.append()

        model.set(iter,
                  COLUMN_ITEM_NUMBER, item.number,
                  COLUMN_ITEM_PRODUCT, item.product,
                  COLUMN_ITEM_YUMMY, item.yummy)

    return model


N_NUMBERS = 10


def create_numbers_model() -> Gtk.TreeModel:
    # create list store
    model = Gtk.ListStore(str, int)

    # add numbers
    for i in range(N_NUMBERS):
        str_ = chr(ord("0") + i)

        iter = model.append()

        model.set(iter, COLUMN_NUMBER_TEXT, str_)

    return model


def add_item(button: Gtk.Button, treeview: Gtk.TreeView) -> None:
    assert articles is not None

    foo = Item(0, "Description here", 50)
    articles.append(foo)

    # Insert a new row below the current one
    path, _column = treeview.get_cursor()
    model = treeview.get_model()
    if path:
        current = model.get_iter(path)
        iter = model.insert_after(current)
    else:
        iter = model.insert(-1)

    # Set the data for the new row
    model.set(iter,
              COLUMN_ITEM_NUMBER, foo.number,
              COLUMN_ITEM_PRODUCT, foo.product,
              COLUMN_ITEM_YUMMY, foo.yummy)

    # Move focus to the new row
    path = model.get_path(iter)
    column = treeview.get_column(0)
    treeview.set_cursor(path, column, False)


def remove_item(widget: Gtk.Button, treeview: Gtk.TreeView) -> None:
    model = treeview.get_model()
    selection = treeview.get_selection()

    _model, iter = selection.get_selected()
    if iter is not None:
        path = model.get_path(iter)
        i = path.get_indices()[0]
        model.remove(iter)

        del articles[i]


def separator_row(model: Gtk.TreeModel, iter: Gtk.TreeIter) -> bool:
    path = model.get_path(iter)
    idx = path.get_indices()[0]

    return idx == 5


def editing_started(cell: Gtk.CellRenderer, editable: Gtk.CellEditable, path: str) -> None:
    editable.set_row_separator_func(separator_row)


def cell_edited(cell: Gtk.CellRendererText, path_string: str, new_text: str, model: Gtk.ListStore) -> None:
    path = Gtk.TreePath.new_from_string(path_string)

    column = cell.column

    iter = model.get_iter(path)

    if column == COLUMN_ITEM_NUMBER:
        i = path.get_indices()[0]
        try:
            articles[i].number = int(new_text)
        except ValueError:
            # As atoi()
            articles[i].number = 0

        model.set(iter, column, articles[i].number)

    elif column == COLUMN_ITEM_PRODUCT:
        i = path.get_indices()[0]
        articles[i].product = new_text

        model.set(iter, column, articles[i].product)

    else:
        raise AssertionError("not reached")


def add_columns(treeview: Gtk.TreeView, items_model: Gtk.TreeModel, numbers_model: Gtk.TreeModel) -> None:
    # number column
    renderer = Gtk.CellRendererCombo(model=numbers_model,
                                     text_column=COLUMN_NUMBER_TEXT,
                                     has_entry=False,
                                     editable=True)
    renderer.edited.connect(cell_edited, items_model)
    renderer.editing_started.connect(editing_started)
    renderer.column = COLUMN_ITEM_NUMBER

    treeview.insert_column_with_attributes(-1, "Number", renderer, text=COLUMN_ITEM_NUMBER)

    # product column
    renderer = Gtk.CellRendererText(editable=True)
    renderer.edited.connect(cell_edited, items_model)
    renderer.column = COLUMN_ITEM_PRODUCT

    treeview.insert_column_with_attributes(-1, "Product", renderer, text=COLUMN_ITEM_PRODUCT)

    # yummy column
    renderer = Gtk.CellRendererProgress()
    renderer.column = COLUMN_ITEM_YUMMY

    treeview.insert_column_with_attributes(-1, "Yummy", renderer, value=COLUMN_ITEM_YUMMY)


# The window, held weakly as g_object_add_weak_pointer() holds it in C: GTK keeps a window until it is
# destroyed, so a strong reference here would keep a destroyed window around.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Editable Cells")
        window_ref = window.weak_ref()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        window.set_child(vbox)

        vbox.append(Gtk.Label(label="Shopping list (you can edit the cells!)"))

        sw = Gtk.ScrolledWindow()
        sw.set_has_frame(True)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.append(sw)

        # create models
        items_model = create_items_model()
        numbers_model = create_numbers_model()

        # create tree view
        treeview = Gtk.TreeView.new_with_model(items_model)
        treeview.set_vexpand(True)
        treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        add_columns(treeview, items_model, numbers_model)

        sw.set_child(treeview)

        # some buttons
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        hbox.set_homogeneous(True)
        vbox.append(hbox)

        button = Gtk.Button.new_with_label("Add item")
        button.clicked.connect(add_item, treeview)
        hbox.append(button)

        button = Gtk.Button.new_with_label("Remove item")
        button.clicked.connect(remove_item, treeview)
        hbox.append(button)

        window.set_default_size(320, 200)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
