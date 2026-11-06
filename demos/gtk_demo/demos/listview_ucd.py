"""Lists/Characters

This demo shows a multi-column representation of some parts
of the Unicode Character Database, or UCD. It also demonstrates
the use of sections with headings to group items.

The dataset used here has 33 796 items.
"""

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk

from .script_names import get_script_name
from .unicode_names import get_break_type_name, get_combining_class_name, get_unicode_type_name


def is_surrogate(codepoint: int) -> bool:
    # PyGObject passes a gunichar as a one-character str, which can't hold a surrogate: for those, the GLib functions
    # below are answered here, as GLib answers them.
    return 0xD800 <= codepoint <= 0xDFFF


def unichar_get_script(codepoint: int) -> GLib.UnicodeScript:
    if is_surrogate(codepoint):
        return GLib.UnicodeScript.UNKNOWN
    return GLib.unichar_get_script(chr(codepoint))


def unichar_type(codepoint: int) -> GLib.UnicodeType:
    if is_surrogate(codepoint):
        return GLib.UnicodeType.SURROGATE
    return GLib.unichar_type(chr(codepoint))


def unichar_break_type(codepoint: int) -> GLib.UnicodeBreakType:
    if is_surrogate(codepoint):
        return GLib.UnicodeBreakType.SURROGATE
    return GLib.unichar_break_type(chr(codepoint))


def unichar_combining_class(codepoint: int) -> int:
    if is_surrogate(codepoint):
        return 0
    return GLib.unichar_combining_class(chr(codepoint))


def unichar_isprint(codepoint: int) -> bool:
    if is_surrogate(codepoint):
        return False
    return GLib.unichar_isprint(chr(codepoint))


class UcdItem(GObject.Object):
    __gtype_name__ = "UcdItem"

    def __init__(self, codepoint: int, name: str) -> None:
        super().__init__()
        self._codepoint = codepoint
        self._name = name
        self._script = unichar_get_script(codepoint)

    @GObject.Property(type=GObject.TYPE_UINT, flags=GObject.ParamFlags.READABLE)
    def codepoint(self) -> int:
        return self._codepoint

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def name(self) -> str:
        return self._name

    @GObject.Property(type=GObject.TYPE_UINT, flags=GObject.ParamFlags.READABLE)
    def script(self) -> int:
        return int(self._script)


def ucd_item_new(codepoint: int, name: str) -> UcdItem:
    return UcdItem(codepoint, name)


def ucd_item_get_codepoint(item: UcdItem) -> int:
    return item._codepoint


def ucd_item_get_name(item: UcdItem) -> str:
    return item._name


def ucd_item_get_script(item: UcdItem) -> GLib.UnicodeScript:
    return item._script


def ucd_model_new() -> Gio.ListModel:
    data = Gio.resources_lookup_data("/listview_ucd_data/ucdnames.data", Gio.ResourceLookupFlags.NONE)
    v = GLib.Variant.new_from_bytes(GLib.VariantType.new("a(us)"), data, True)

    store = Gio.ListStore(item_type=GObject.Object)
    items = []
    for u, name in v.unpack():
        if u == 0:
            continue

        items.append(ucd_item_new(u, name))
    store.splice(0, 0, items)

    expression = Gtk.PropertyExpression.new(UcdItem, None, "codepoint")
    sorter = Gtk.NumericSorter.new(expression)
    sort = Gtk.SortListModel.new(store, sorter)

    expression = Gtk.PropertyExpression.new(UcdItem, None, "script")
    sorter = Gtk.NumericSorter.new(expression)
    sort.set_section_sorter(sorter)

    return sort


def printable(codepoint: int) -> str:
    # g_unichar_to_utf8() of the character, if g_unichar_isprint().
    return chr(codepoint) if unichar_isprint(codepoint) else ""


def setup_centered_label(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = Gtk.Inscription.new("")
    listitem.set_child(label)


def setup_label(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = Gtk.Inscription.new("")
    label.set_xalign(0)
    listitem.set_child(label)


def setup_ellipsizing_label(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = Gtk.Inscription.new("")
    label.set_xalign(0)
    label.set_text_overflow(Gtk.InscriptionOverflow.ELLIPSIZE_END)
    label.set_nat_chars(20)
    listitem.set_child(label)


def bind_codepoint(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = listitem.get_child()
    item = listitem.get_item()
    codepoint = ucd_item_get_codepoint(item)

    label.set_text(f"{codepoint:#06x}")


def bind_char(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = listitem.get_child()
    item = listitem.get_item()
    codepoint = ucd_item_get_codepoint(item)

    label.set_text(printable(codepoint))


def bind_name(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = listitem.get_child()
    item = listitem.get_item()
    name = ucd_item_get_name(item)

    label.set_text(name)


def bind_type(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = listitem.get_child()
    item = listitem.get_item()
    codepoint = ucd_item_get_codepoint(item)

    label.set_text(get_unicode_type_name(unichar_type(codepoint)))


def bind_break_type(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = listitem.get_child()
    item = listitem.get_item()
    codepoint = ucd_item_get_codepoint(item)

    label.set_text(get_break_type_name(unichar_break_type(codepoint)))


def bind_combining_class(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListItem) -> None:
    label = listitem.get_child()
    item = listitem.get_item()
    codepoint = ucd_item_get_codepoint(item)

    label.set_text(get_combining_class_name(unichar_combining_class(codepoint)))


def setup_header(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListHeader) -> None:
    label = Gtk.Inscription.new("")
    label.add_css_class("heading")
    label.set_margin_start(20)
    label.set_margin_end(20)
    label.set_margin_top(10)
    label.set_margin_bottom(10)
    label.set_xalign(0)
    listitem.set_child(label)


def bind_header(factory: Gtk.SignalListItemFactory, listitem: Gtk.ListHeader) -> None:
    label = listitem.get_child()
    item = listitem.get_item()
    script = ucd_item_get_script(item)

    label.set_text(get_script_name(script))


def selection_changed(selection: Gtk.SingleSelection, pspec: GObject.ParamSpec, label: Gtk.Label) -> None:
    item = selection.get_selected_item()
    codepoint = ucd_item_get_codepoint(item)

    label.set_text(printable(codepoint))


def create_ucd_view(label: Gtk.Widget | None) -> Gtk.Widget:
    ucd_model = ucd_model_new()

    selection = Gtk.SingleSelection.new(ucd_model)
    selection.set_autoselect(True)
    selection.set_can_unselect(False)
    if label:
        selection.notify["selected"].connect(selection_changed, label)

    cv = Gtk.ColumnView.new(selection)
    cv.set_show_column_separators(True)

    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_centered_label)
    factory.bind.connect(bind_codepoint)
    column = Gtk.ColumnViewColumn.new("Codepoint", factory)
    cv.append_column(column)

    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_centered_label)
    factory.bind.connect(bind_char)
    column = Gtk.ColumnViewColumn.new("Char", factory)
    cv.append_column(column)

    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_ellipsizing_label)
    factory.bind.connect(bind_name)
    column = Gtk.ColumnViewColumn.new("Name", factory)
    column.set_resizable(True)
    cv.append_column(column)

    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_ellipsizing_label)
    factory.bind.connect(bind_type)
    column = Gtk.ColumnViewColumn.new("Type", factory)
    column.set_resizable(True)
    cv.append_column(column)

    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_ellipsizing_label)
    factory.bind.connect(bind_break_type)
    column = Gtk.ColumnViewColumn.new("Break Type", factory)
    column.set_resizable(True)
    cv.append_column(column)

    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_label)
    factory.bind.connect(bind_combining_class)
    column = Gtk.ColumnViewColumn.new("Combining Class", factory)
    column.set_resizable(True)
    cv.append_column(column)

    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_header)
    factory.bind.connect(bind_header)
    cv.set_header_factory(factory)

    return cv


window: Gtk.Window | None = None


def remove_provider(provider: Gtk.StyleProvider) -> None:
    Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), provider)


def destroyed(win: Gtk.Window) -> None:
    global window
    # g_object_set_data_full() with remove_provider() as the destroy notify.
    remove_provider(win.provider)
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_default_size(800, 400)
        window.set_title("Characters")
        window.set_display(do_widget.get_display())
        # The C demo clears its window with a weak pointer. A Python global keeps the window alive after
        # gtk_window_destroy(), so that "destroy" would only come later: unrealizing is what destroying does at once.
        window.unrealize.connect(destroyed)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        label = Gtk.Label(label="")
        label.set_width_chars(2)
        label.add_css_class("enormous")
        provider = Gtk.CssProvider()
        provider.load_from_string("label.enormous { font-size: 80px; }")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)
        label.set_hexpand(True)
        box.append(label)

        sw = Gtk.ScrolledWindow()
        sw.set_propagate_natural_width(True)
        listview = create_ucd_view(label)
        sw.set_child(listview)
        box.prepend(sw)
        window.set_child(box)

        window.provider = provider

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
