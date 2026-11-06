"""Icon View/Icon View Basics

The GtkIconView widget is used to display and manipulate icons.
It uses a GtkTreeModel for data storage, so the list store
example might be helpful.
"""

import os

from PyLiite4 import GdkPixbuf, GLib, Gtk

window: Gtk.Window | None = None

FOLDER_NAME = "/iconview/gnome-fs-directory.png"
FILE_NAME = "/iconview/gnome-fs-regular.png"

COL_PATH, COL_DISPLAY_NAME, COL_PIXBUF, COL_IS_DIRECTORY, NUM_COLS = range(5)


file_pixbuf: GdkPixbuf.Pixbuf | None = None
folder_pixbuf: GdkPixbuf.Pixbuf | None = None
parent = ""
up_button: Gtk.Button | None = None


def load_pixbufs() -> None:
    """Loads the images for the demo and returns whether the operation succeeded"""
    global file_pixbuf, folder_pixbuf

    if file_pixbuf:
        return  # Already loaded earlier.

    file_pixbuf = GdkPixbuf.Pixbuf.new_from_resource(FILE_NAME)
    # The demo's own resources must load.
    assert file_pixbuf

    folder_pixbuf = GdkPixbuf.Pixbuf.new_from_resource(FOLDER_NAME)
    assert folder_pixbuf


def fill_store(store: Gtk.ListStore) -> None:
    store.clear()

    try:
        dir = GLib.Dir.open(parent, 0)
    except GLib.Error:
        return

    name = dir.read_name()
    while name is not None:
        # Hidden files, which start with a '.', are left out.
        if name[0] != '.':
            path = os.path.join(parent, name)

            is_dir = GLib.file_test(path, GLib.FileTest.IS_DIR)

            display_name = GLib.filename_display_name(name)

            store.append([path, display_name, folder_pixbuf if is_dir else file_pixbuf, is_dir])

        name = dir.read_name()
    dir.close()


def sort_func(model: Gtk.TreeModel, a: Gtk.TreeIter, b: Gtk.TreeIter, user_data: object) -> int:
    # Sorts folders before files, which the default sort wouldn't.

    is_dir_a, name_a = model.get(a, COL_IS_DIRECTORY, COL_DISPLAY_NAME)
    is_dir_b, name_b = model.get(b, COL_IS_DIRECTORY, COL_DISPLAY_NAME)

    if not is_dir_a and is_dir_b:
        ret = 1
    elif is_dir_a and not is_dir_b:
        ret = -1
    else:
        ret = GLib.utf8_collate(name_a, name_b)

    return ret


def create_store() -> Gtk.ListStore:
    store = Gtk.ListStore(str, str, GdkPixbuf.Pixbuf, bool)

    store.set_default_sort_func(sort_func, None)
    store.set_sort_column_id(Gtk.TREE_SORTABLE_DEFAULT_SORT_COLUMN_ID, Gtk.SortType.ASCENDING)

    return store


def item_activated(icon_view: Gtk.IconView, tree_path: Gtk.TreePath, store: Gtk.ListStore) -> None:
    global parent

    iter = store.get_iter(tree_path)
    path, is_dir = store.get(iter, COL_PATH, COL_IS_DIRECTORY)

    if not is_dir:
        return

    parent = path

    fill_store(store)

    up_button.set_sensitive(True)


def up_clicked(item: Gtk.Button, store: Gtk.ListStore) -> None:
    global parent

    dir_name = os.path.dirname(parent)

    parent = dir_name

    fill_store(store)

    # There's no going up from the root.
    up_button.set_sensitive(parent != "/")


def home_clicked(item: Gtk.Button, store: Gtk.ListStore) -> None:
    global parent

    parent = GLib.get_home_dir()

    fill_store(store)

    up_button.set_sensitive(True)


def close_window(*args: object) -> bool:
    global window, file_pixbuf, folder_pixbuf

    window.destroy()
    window = None

    file_pixbuf = None

    folder_pixbuf = None

    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, parent, up_button

    if window is None:
        window = Gtk.Window()
        window.set_default_size(650, 400)

        window.set_display(do_widget.get_display())
        window.set_title("Icon View Basics")

        window.close_request.connect(close_window)

        load_pixbufs()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        window.set_child(vbox)

        tool_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        vbox.append(tool_bar)

        up_button = Gtk.Button.new_with_mnemonic("_Up")
        up_button.set_sensitive(False)
        tool_bar.append(up_button)

        home_button = Gtk.Button.new_with_mnemonic("_Home")
        tool_bar.append(home_button)

        sw = Gtk.ScrolledWindow()
        sw.set_has_frame(True)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_vexpand(True)

        vbox.append(sw)

        # The view starts at '/'.
        parent = "/"
        store = create_store()
        fill_store(store)

        icon_view = Gtk.IconView.new_with_model(store)
        icon_view.set_selection_mode(Gtk.SelectionMode.MULTIPLE)

        up_button.clicked.connect(up_clicked, store)

        home_button.clicked.connect(home_clicked, store)

        # The model columns that hold each item's text and pixbuf.
        icon_view.set_text_column(COL_DISPLAY_NAME)
        icon_view.set_pixbuf_column(COL_PIXBUF)

        icon_view.item_activated.connect(item_activated, store)
        sw.set_child(icon_view)

        icon_view.grab_focus()

    if not window.get_visible():
        window.set_visible(True)
    else:
        close_window()

    return window
