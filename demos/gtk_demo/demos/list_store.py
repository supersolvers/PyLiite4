"""Tree View/List Store

The GtkListStore is used to store data in list form, to be used
later on by a GtkTreeView to display it. This demo builds a
simple GtkListStore and displays it.
"""

from dataclasses import dataclass

from PyLiite4 import GLib, GObject, Gtk

window: Gtk.Window | None = None
model: Gtk.TreeModel | None = None
timeout = 0

G_MAXUINT = 0xFFFFFFFF


@dataclass(frozen=True)
class Bug:
    fixed: bool
    number: int
    severity: str
    description: str


(COLUMN_FIXED, COLUMN_NUMBER, COLUMN_SEVERITY, COLUMN_DESCRIPTION, COLUMN_PULSE, COLUMN_ICON, COLUMN_ACTIVE,
 COLUMN_SENSITIVE, NUM_COLUMNS) = range(9)

bugs = [
    Bug(False, 60482, "Normal",     "scrollable notebooks and hidden tabs"),
    Bug(False, 60620, "Critical",   "gdk_surface_clear_area (gdksurface-win32.c) is not thread-safe"),
    Bug(False, 50214, "Major",      "Xft support does not clean up correctly"),
    Bug(True,  52877, "Major",      "GtkFileSelection needs a refresh method. "),
    Bug(False, 56070, "Normal",     "Can't click button after setting in sensitive"),
    Bug(True,  56355, "Normal",     "GtkLabel - Not all changes propagate correctly"),
    Bug(False, 50055, "Normal",     "Rework width/height computations for TreeView"),
    Bug(False, 58278, "Normal",     "gtk_dialog_set_response_sensitive () doesn't work"),
    Bug(False, 55767, "Normal",     "Getters for all setters"),
    Bug(False, 56925, "Normal",     "Gtkcalender size"),
    Bug(False, 56221, "Normal",     "Selectable label needs right-click copy menu"),
    Bug(True,  50939, "Normal",     "Add shift clicking to GtkTextView"),
    Bug(False, 6112,  "Enhancement", "netscape-like collapsible toolbars"),
    Bug(False, 1,     "Normal",     "First bug :=)"),
]


def spinner_timeout() -> bool:
    if model is None:
        return GLib.SOURCE_REMOVE

    iter = model.get_iter_first()
    pulse = model.get_value(iter, COLUMN_PULSE)
    if pulse == G_MAXUINT:
        pulse = 0
    else:
        pulse += 1

    model.set(iter, COLUMN_PULSE, pulse, COLUMN_ACTIVE, True)

    return GLib.SOURCE_CONTINUE


def create_model() -> Gtk.TreeModel:
    store = Gtk.ListStore(bool, GObject.TYPE_UINT, str, str, GObject.TYPE_UINT, str, bool, bool)

    for i, bug in enumerate(bugs):
        if i == 1 or i == 3:
            icon_name = "battery-level-10-charging-symbolic"
        else:
            icon_name = None
        if i == 3:
            sensitive = False
        else:
            sensitive = True
        store.append([bug.fixed, bug.number, bug.severity, bug.description, 0, icon_name, False, sensitive])

    return store


def fixed_toggled(cell: Gtk.CellRendererToggle, path_str: str, tree_model: Gtk.ListStore) -> None:
    path = Gtk.TreePath.new_from_string(path_str)

    iter = tree_model.get_iter(path)
    fixed = tree_model.get_value(iter, COLUMN_FIXED)

    fixed ^= True

    tree_model.set(iter, COLUMN_FIXED, fixed)


def add_columns(treeview: Gtk.TreeView) -> None:
    # Fixed toggles
    renderer = Gtk.CellRendererToggle()
    renderer.toggled.connect(fixed_toggled, model)

    column = Gtk.TreeViewColumn("Fixed?", renderer, active=COLUMN_FIXED)

    column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
    column.set_fixed_width(50)
    treeview.append_column(column)

    # Bug numbers
    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Bug number", renderer, text=COLUMN_NUMBER)
    column.set_sort_column_id(COLUMN_NUMBER)
    treeview.append_column(column)

    # Severities
    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Severity", renderer, text=COLUMN_SEVERITY)
    column.set_sort_column_id(COLUMN_SEVERITY)
    treeview.append_column(column)

    # Descriptions
    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Description", renderer, text=COLUMN_DESCRIPTION)
    column.set_sort_column_id(COLUMN_DESCRIPTION)
    treeview.append_column(column)

    # Spinners
    renderer = Gtk.CellRendererSpinner()
    column = Gtk.TreeViewColumn("Spinning", renderer, pulse=COLUMN_PULSE, active=COLUMN_ACTIVE)
    column.set_sort_column_id(COLUMN_PULSE)
    treeview.append_column(column)

    # Symbolic icons
    renderer = Gtk.CellRendererPixbuf()
    column = Gtk.TreeViewColumn("Symbolic icon", renderer, icon_name=COLUMN_ICON, sensitive=COLUMN_SENSITIVE)
    column.set_sort_column_id(COLUMN_ICON)
    treeview.append_column(column)


def window_closed(widget: Gtk.Widget) -> bool:
    global model, window, timeout

    model = None
    window = None
    if timeout != 0:
        GLib.source_remove(timeout)
        timeout = 0
    return False


def close_request(win: Gtk.Window) -> bool:
    win.destroy()
    window_closed(win)
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, model, timeout

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("List Store")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        window.set_child(vbox)

        label = Gtk.Label(label="This is the bug list (note: not based on real data, it would be nice to have a "
                                "nice ODBC interface to bugzilla or so, though).")
        vbox.append(label)

        sw = Gtk.ScrolledWindow()
        sw.set_has_frame(True)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.append(sw)

        model = create_model()

        treeview = Gtk.TreeView.new_with_model(model)
        treeview.set_vexpand(True)
        treeview.set_search_column(COLUMN_DESCRIPTION)

        sw.set_child(treeview)

        add_columns(treeview)

        window.set_default_size(280, 250)
        # A Python reference keeps the window alive past gtk_window_destroy(), so "destroy" would come too late.
        window.close_request.connect(close_request)

    if not window.get_visible():
        window.set_visible(True)
        if timeout == 0:
            # FIXME: This should use the animation-duration instead.
            timeout = GLib.timeout_add(80, spinner_timeout)
    else:
        close_request(window)

    return window
