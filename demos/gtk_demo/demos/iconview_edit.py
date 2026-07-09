"""Icon View/Editing and Drag-and-Drop
#Keywords: dnd

The GtkIconView widget supports Editing and Drag-and-Drop.
This example also demonstrates using the generic GtkCellLayout
interface to set up cell renderers in an icon view.
"""

from PyLiite4 import Gdk, GdkPixbuf, Gtk

COL_TEXT, NUM_COLS = range(2)


def fill_store(store: Gtk.ListStore) -> None:
    text = ["Red", "Green", "Blue", "Yellow"]

    # First clear the store
    store.clear()

    for i in range(4):
        store.append([text[i]])


def create_store() -> Gtk.ListStore:
    store = Gtk.ListStore(str)

    return store


def set_cell_color(cell_layout: Gtk.CellLayout, cell: Gtk.CellRenderer, tree_model: Gtk.TreeModel,
                   iter: Gtk.TreeIter, data: object) -> None:
    pixel = 0

    text = tree_model.get_value(iter, COL_TEXT)
    if not text:
        return

    color = Gdk.RGBA()
    if color.parse(text):
        pixel = (int(color.red * 255) << 24
                 | int(color.green * 255) << 16
                 | int(color.blue * 255) << 8
                 | int(color.alpha * 255))

    pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 24, 24)
    pixbuf.fill(pixel)

    cell.set_property("pixbuf", pixbuf)


def edited(cell: Gtk.CellRendererText, path_string: str, text: str, icon_view: Gtk.IconView) -> None:
    model = icon_view.get_model()
    path = Gtk.TreePath.new_from_string(path_string)

    iter = model.get_iter(path)
    model.set(iter, COL_TEXT, text)


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        window = Gtk.Window()

        window.set_display(do_widget.get_display())
        window.set_title("Editing and Drag-and-Drop")
        window.close_request.connect(close_request)

        store = create_store()
        fill_store(store)

        icon_view = Gtk.IconView.new_with_model(store)

        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        icon_view.set_item_orientation(Gtk.Orientation.HORIZONTAL)
        icon_view.set_columns(2)
        icon_view.set_reorderable(True)

        renderer = Gtk.CellRendererPixbuf()
        icon_view.pack_start(renderer, True)
        icon_view.set_cell_data_func(renderer, set_cell_color, None)

        renderer = Gtk.CellRendererText()
        icon_view.pack_start(renderer, True)
        renderer.set_property("editable", True)
        renderer.edited.connect(edited, icon_view)
        icon_view.add_attribute(renderer, "text", COL_TEXT)

        window.set_child(icon_view)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
