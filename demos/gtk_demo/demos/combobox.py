"""Combo Boxes
#Keywords: GtkCellRenderer

The GtkComboBox widget allows to select one option out of a list.
The GtkComboBoxEntry additionally allows the user to enter a value
that is not in the list of options.

How the options are displayed is controlled by cell renderers.
"""

from collections.abc import Callable
from gettext import gettext as _

from PyLiite4 import GLib, GObject, Gtk, Pango

ICON_NAME_COL = 0
TEXT_COL = 1


def N_(message: str) -> str:
    return message


def create_icon_store() -> Gtk.TreeModel:
    icon_names = [
        "dialog-warning",
        "process-stop",
        "document-new",
        "edit-clear",
        None,
        "document-open",
    ]
    labels = [
        N_("Warning"),
        N_("Stop"),
        N_("New"),
        N_("Clear"),
        None,
        N_("Open"),
    ]

    store = Gtk.ListStore.new([str, str])

    for i in range(len(icon_names)):
        if icon_names[i]:
            store.append([icon_names[i], _(labels[i])])
        else:
            store.append([None, "separator"])

    return store


def set_sensitive(cell_layout: Gtk.CellLayout, cell: Gtk.CellRenderer, tree_model: Gtk.TreeModel,
                  iter: Gtk.TreeIter, data: object) -> None:
    """A GtkCellLayoutDataFunc that demonstrates how one can control
    sensitivity of rows. This particular function does nothing
    useful and just makes the second row insensitive.
    """
    path = tree_model.get_path(iter)
    indices = path.get_indices()
    sensitive = indices[0] != 1

    cell.set_property("sensitive", sensitive)


def is_separator(model: Gtk.TreeModel, iter: Gtk.TreeIter, data: object) -> bool:
    """A GtkTreeViewRowSeparatorFunc that demonstrates how rows can be
    rendered as separators. This particular function does nothing
    useful and just turns the fourth row into a separator.
    """
    path = model.get_path(iter)
    result = path.get_indices()[0] == 4

    return result


def create_capital_store() -> Gtk.TreeModel:
    capitals = [
        ("A - B", None),
        (None, "Albany"),
        (None, "Annapolis"),
        (None, "Atlanta"),
        (None, "Augusta"),
        (None, "Austin"),
        (None, "Baton Rouge"),
        (None, "Bismarck"),
        (None, "Boise"),
        (None, "Boston"),
        ("C - D", None),
        (None, "Carson City"),
        (None, "Charleston"),
        (None, "Cheyenne"),
        (None, "Columbia"),
        (None, "Columbus"),
        (None, "Concord"),
        (None, "Denver"),
        (None, "Des Moines"),
        (None, "Dover"),
        ("E - J", None),
        (None, "Frankfort"),
        (None, "Harrisburg"),
        (None, "Hartford"),
        (None, "Helena"),
        (None, "Honolulu"),
        (None, "Indianapolis"),
        (None, "Jackson"),
        (None, "Jefferson City"),
        (None, "Juneau"),
        ("K - O", None),
        (None, "Lansing"),
        (None, "Lincoln"),
        (None, "Little Rock"),
        (None, "Madison"),
        (None, "Montgomery"),
        (None, "Montpelier"),
        (None, "Nashville"),
        (None, "Oklahoma City"),
        (None, "Olympia"),
        ("P - S", None),
        (None, "Phoenix"),
        (None, "Pierre"),
        (None, "Providence"),
        (None, "Raleigh"),
        (None, "Richmond"),
        (None, "Sacramento"),
        (None, "Salem"),
        (None, "Salt Lake City"),
        (None, "Santa Fe"),
        (None, "Springfield"),
        (None, "St. Paul"),
        ("T - Z", None),
        (None, "Tallahassee"),
        (None, "Topeka"),
        (None, "Trenton"),
    ]

    store = Gtk.TreeStore.new([str])

    iter = None
    for group, capital in capitals:
        if group:
            iter = store.append(None, [group])
        elif capital:
            store.append(iter, [capital])

    return store


def is_capital_sensitive(cell_layout: Gtk.CellLayout, cell: Gtk.CellRenderer, tree_model: Gtk.TreeModel,
                         iter: Gtk.TreeIter, data: object) -> None:
    sensitive = not tree_model.iter_has_child(iter)

    cell.set_property("sensitive", sensitive)


def fill_combo_entry(combo: Gtk.ComboBoxText) -> None:
    combo.append_text("One")
    combo.append_text("Two")
    combo.append_text("2½")
    combo.append_text("Three")


class MaskEntry(Gtk.Entry, Gtk.Editable):
    """A simple validating entry"""

    __gtype_name__ = "MaskEntry"

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)
        self.mask: str | None = None

    def set_background(self) -> None:
        if self.mask:
            if not GLib.Regex.match_simple(self.mask, self.get_text(), 0, 0):
                attrs = Pango.AttrList()
                attrs.insert(Pango.attr_foreground_new(65535, 32767, 32767))
                self.set_attributes(attrs)
                return

        # gtk_entry_set_attributes() isn't annotated as taking NULL, so this clears the property instead.
        self.set_property("attributes", None)

    def do_changed(self) -> None:
        self.set_background()


def set_attributes(cell_layout: Gtk.CellLayout, cell: Gtk.CellRenderer, attributes: dict[str, int]) -> None:
    # gtk_cell_layout_set_attributes() takes varargs, so it isn't in the bindings: this does what it does.
    cell_layout.clear_attributes(cell)
    for attribute, column in attributes.items():
        cell_layout.add_attribute(cell, attribute, column)


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Combo Boxes")
        window_ref = window.weak_ref()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        window.set_child(vbox)

        # A combobox demonstrating cell renderers, separators and insensitive rows
        frame = Gtk.Frame(label="Items with icons")
        vbox.append(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(5)
        box.set_margin_end(5)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        frame.set_child(box)

        model = create_icon_store()
        combo = Gtk.ComboBox.new_with_model(model)
        box.append(combo)

        renderer = Gtk.CellRendererPixbuf()
        combo.pack_start(renderer, False)
        set_attributes(combo, renderer, {"icon-name": ICON_NAME_COL})

        combo.set_cell_data_func(renderer, set_sensitive, None)

        renderer = Gtk.CellRendererText()
        combo.pack_start(renderer, True)
        set_attributes(combo, renderer, {"text": TEXT_COL})

        combo.set_cell_data_func(renderer, set_sensitive, None)

        combo.set_row_separator_func(is_separator, None)

        combo.set_active(0)

        # A combobox demonstrating trees
        frame = Gtk.Frame(label="Where are we ?")
        vbox.append(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(5)
        box.set_margin_end(5)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        frame.set_child(box)

        model = create_capital_store()
        combo = Gtk.ComboBox.new_with_model(model)
        box.append(combo)

        renderer = Gtk.CellRendererText()
        combo.pack_start(renderer, True)
        set_attributes(combo, renderer, {"text": 0})
        combo.set_cell_data_func(renderer, is_capital_sensitive, None)

        path = Gtk.TreePath.new_from_indices([0, 8])
        iter = model.get_iter(path)
        combo.set_active_iter(iter)

        # A combobox with an entry, with validation
        frame = Gtk.Frame(label="Editable")
        vbox.append(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(5)
        box.set_margin_end(5)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        frame.set_child(box)

        combo = Gtk.ComboBoxText.new_with_entry()
        fill_combo_entry(combo)
        box.append(combo)

        entry = MaskEntry()
        entry.mask = "^([0-9]*|One|Two|2½|Three)$"

        combo.set_child(entry)

        # A combobox with string IDs
        frame = Gtk.Frame(label="String IDs")
        vbox.append(frame)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_margin_start(5)
        box.set_margin_end(5)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        frame.set_child(box)

        combo = Gtk.ComboBoxText()
        combo.append("never", "Not visible")
        combo.append("when-active", "Visible when active")
        combo.append("always", "Always visible")
        box.append(combo)

        entry = Gtk.Entry()
        combo.bind_property("active-id",
                            entry, "text",
                            GObject.BindingFlags.BIDIRECTIONAL)
        box.append(entry)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
