"""Tree View/Filter Model
#Keywords: GtkTreeView

This example demonstrates how GtkTreeModelFilter can be used not
just to show a subset of the rows, but also to compute columns
that are not actually present in the underlying model.
"""

from collections.abc import Callable

from PyLiite4 import GObject, Gtk

WIDTH_COLUMN = 0
HEIGHT_COLUMN = 1
AREA_COLUMN = 2
SQUARE_COLUMN = 3


def format_number(col: Gtk.TreeViewColumn, cell: Gtk.CellRenderer, model: Gtk.TreeModel, iter: Gtk.TreeIter,
                  column: int) -> None:
    num = model.get_value(iter, column)
    text = f"{num}"
    cell.set_property("text", text)


def filter_modify_func(model: Gtk.TreeModelFilter, iter: Gtk.TreeIter, column: int,
                       data: object) -> int | bool:
    filter_model = model

    child_model = filter_model.get_model()
    child_iter = filter_model.convert_iter_to_child_iter(iter)

    width, height = child_model.get(child_iter, WIDTH_COLUMN, HEIGHT_COLUMN)

    if column == WIDTH_COLUMN:
        return width
    elif column == HEIGHT_COLUMN:
        return height
    elif column == AREA_COLUMN:
        return width * height
    elif column == SQUARE_COLUMN:
        return width == height
    else:
        raise AssertionError("not reached")


def visible_func(model: Gtk.TreeModel, iter: Gtk.TreeIter, data: object) -> bool:
    width = model.get_value(iter, WIDTH_COLUMN)

    return width < 10


def cell_edited(cell: Gtk.CellRendererSpin, path_string: str, new_text: str, store: Gtk.ListStore) -> None:
    path = Gtk.TreePath.new_from_string(path_string)
    iter = store.get_iter(path)

    column = cell.column

    try:
        val = int(new_text)
    except ValueError:
        # As with atoi(), text that isn't a number gives 0.
        val = 0

    store.set(iter, column, val)


# The window, held weakly as g_object_add_weak_pointer() holds it in C: GTK keeps a window until it is
# destroyed, so a strong reference here would keep a destroyed window around.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        builder = Gtk.Builder.new_from_resource("/filtermodel/filtermodel.ui")
        window = builder.get_object("window1")
        window.set_display(do_widget.get_display())
        window_ref = window.weak_ref()

        store = builder.get_object("liststore1")

        column = builder.get_object("treeviewcolumn1")
        cell = builder.get_object("cellrenderertext1")
        column.set_cell_data_func(cell, format_number, WIDTH_COLUMN)
        cell.column = WIDTH_COLUMN
        cell.edited.connect(cell_edited, store)

        column = builder.get_object("treeviewcolumn2")
        cell = builder.get_object("cellrenderertext2")
        column.set_cell_data_func(cell, format_number, HEIGHT_COLUMN)
        cell.column = HEIGHT_COLUMN
        cell.edited.connect(cell_edited, store)

        column = builder.get_object("treeviewcolumn3")
        cell = builder.get_object("cellrenderertext3")
        column.set_cell_data_func(cell, format_number, WIDTH_COLUMN)

        column = builder.get_object("treeviewcolumn4")
        cell = builder.get_object("cellrenderertext4")
        column.set_cell_data_func(cell, format_number, HEIGHT_COLUMN)

        column = builder.get_object("treeviewcolumn5")
        cell = builder.get_object("cellrenderertext5")
        column.set_cell_data_func(cell, format_number, AREA_COLUMN)

        column = builder.get_object("treeviewcolumn6")
        cell = builder.get_object("cellrendererpixbuf1")
        column.add_attribute(cell, "visible", SQUARE_COLUMN)

        tree = builder.get_object("treeview2")

        types = [GObject.TYPE_INT, GObject.TYPE_INT, GObject.TYPE_INT, GObject.TYPE_BOOLEAN]
        model = Gtk.TreeModelFilter(child_model=store)
        model.set_modify_func(types, filter_modify_func, None)

        tree.set_model(model)

        column = builder.get_object("treeviewcolumn7")
        cell = builder.get_object("cellrenderertext6")
        column.set_cell_data_func(cell, format_number, WIDTH_COLUMN)

        column = builder.get_object("treeviewcolumn8")
        cell = builder.get_object("cellrenderertext7")
        column.set_cell_data_func(cell, format_number, HEIGHT_COLUMN)

        tree = builder.get_object("treeview3")

        model = Gtk.TreeModelFilter(child_model=store)
        model.set_visible_func(visible_func, None)
        tree.set_model(model)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
