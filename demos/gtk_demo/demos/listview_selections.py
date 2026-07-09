"""Lists/Selections
#Keywords: suggestion, completion

The GtkDropDown widget is a modern alternative to GtkComboBox.
It uses list models instead of tree models, and the content is
displayed using widgets instead of cell renderers.

This example also shows a custom widget that can replace
GtkEntryCompletion or GtkComboBoxText. It is not currently
part of GTK.
"""

import os

from PyLiite4 import Gio, GLib, GObject, Gtk, Pango

from .suggestionentry import MatchObject, suggestion_entry_new


class StringHolder(GObject.Object):
    __gtype_name__ = "StringHolder"

    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self.icon: str | None = None
        self.description: str | None = None


def string_holder_new(title: str, icon: str | None, description: str | None) -> StringHolder:
    holder = StringHolder()
    holder.title = title
    holder.icon = icon
    holder.description = description
    return holder


# C keeps these with g_object_set_data() on the list item.
class ItemWidgets:
    def __init__(self, title: Gtk.Label, image: Gtk.Image, checkmark: Gtk.Image,
                 description: Gtk.Label | None = None) -> None:
        self.title = title
        self.image = image
        self.description = description
        self.checkmark = checkmark
        self.handler = 0


item_widgets: dict[Gtk.ListItem, ItemWidgets] = {}


def strings_setup_item_single_line(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem,
                                   data: Gtk.DropDown) -> None:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

    image = Gtk.Image()
    title = Gtk.Label(label="")
    title.set_xalign(0.0)
    checkmark = Gtk.Image.new_from_icon_name("object-select-symbolic")

    box.append(image)
    box.append(title)
    box.append(checkmark)

    item_widgets[item] = ItemWidgets(title, image, checkmark)

    item.set_child(box)


def strings_setup_item_full(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem, data: Gtk.DropDown) -> None:
    image = Gtk.Image()
    title = Gtk.Label(label="")
    title.set_xalign(0.0)
    description = Gtk.Label(label="")
    description.set_xalign(0.0)
    description.add_css_class("dim-label")
    checkmark = Gtk.Image.new_from_icon_name("object-select-symbolic")

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    box2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

    box.append(image)
    box.append(box2)
    box2.append(title)
    box2.append(description)
    box.append(checkmark)

    item_widgets[item] = ItemWidgets(title, image, checkmark, description)

    item.set_child(box)


def selected_item_changed(dropdown: Gtk.DropDown, pspec: GObject.ParamSpec | None, item: Gtk.ListItem) -> None:
    checkmark = item_widgets[item].checkmark

    if dropdown.get_selected_item() == item.get_item():
        checkmark.set_opacity(1.0)
    else:
        checkmark.set_opacity(0.0)


def strings_bind_item(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem, data: Gtk.DropDown) -> None:
    dropdown = data

    holder = item.get_item()

    widgets = item_widgets[item]
    title = widgets.title
    image = widgets.image
    description = widgets.description
    checkmark = widgets.checkmark

    title.set_label(holder.title)
    if image:
        image.set_from_icon_name(holder.icon)
        image.set_visible(holder.icon is not None)
    if description:
        description.set_label(holder.description)
        description.set_visible(holder.description is not None)

    popup = title.get_ancestor(Gtk.Popover)
    if popup and popup.is_ancestor(dropdown):
        checkmark.set_visible(True)
        widgets.handler = dropdown.notify["selected-item"].connect(selected_item_changed, item)
        selected_item_changed(dropdown, None, item)
    else:
        checkmark.set_visible(False)


def strings_unbind_item(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem, data: Gtk.DropDown) -> None:
    dropdown = data

    widgets = item_widgets[list_item]
    if widgets.handler:
        dropdown.notify["selected-item"].disconnect(widgets.handler)
        widgets.handler = 0


def strings_factory_new(data: Gtk.DropDown, full: bool) -> Gtk.ListItemFactory:
    factory = Gtk.SignalListItemFactory()
    if full:
        factory.setup.connect(strings_setup_item_full, data)
    else:
        factory.setup.connect(strings_setup_item_single_line, data)
    factory.bind.connect(strings_bind_item, data)
    factory.unbind.connect(strings_unbind_item, data)

    return factory


def strings_model_new(titles: list[str], icons: list[str] | None,
                      descriptions: list[str] | None) -> Gio.ListModel:
    store = Gio.ListStore(item_type=StringHolder)
    for i, title in enumerate(titles):
        holder = string_holder_new(title,
                                   icons[i] if icons else None,
                                   descriptions[i] if descriptions else None)
        store.append(holder)

    return store


def drop_down_new_from_strings(titles: list[str], icons: list[str] | None,
                               descriptions: list[str] | None) -> Gtk.DropDown:
    assert titles is not None
    assert icons is None or len(icons) == len(titles)
    assert descriptions is None or len(icons) == len(descriptions)

    model = strings_model_new(titles, icons, descriptions)
    widget = Gtk.DropDown(model=model)

    factory = strings_factory_new(widget, False)
    if icons is not None or descriptions is not None:
        list_factory = strings_factory_new(widget, True)
    else:
        list_factory = None

    widget.set_property("factory", factory)
    widget.set_property("list-factory", list_factory)

    return widget


def get_family_name(item: Pango.FontFamily) -> str:
    return item.get_name()


def get_file_name(item: Gio.FileInfo) -> str:
    return item.get_display_name()


def setup_item(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    icon = Gtk.Image()
    label = Gtk.Label(label="")
    label.set_xalign(0)
    box.append(icon)
    box.append(label)
    item.set_child(box)


def bind_item(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
    match = item.get_item()
    info = match.get_item()
    box = item.get_child()
    icon = box.get_first_child()
    label = box.get_last_child()

    icon.set_from_gicon(info.get_icon())
    label.set_label(info.get_display_name())


def setup_highlight_item(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
    label = Gtk.Label(label="")
    label.set_xalign(0)
    item.set_child(label)


def bind_highlight_item(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
    obj = item.get_item()
    label = item.get_child()

    str = obj.get_string()

    label.set_label(str)
    attrs = Pango.AttrList()
    attr = Pango.attr_weight_new(Pango.Weight.BOLD)
    attr.start_index = obj.get_match_start()
    attr.end_index = obj.get_match_end()
    attrs.insert(attr)
    label.set_attributes(attrs)


def match_func(obj: MatchObject, search: str, user_data: object) -> None:
    tmp1 = GLib.utf8_normalize(obj.get_string(), -1, GLib.NormalizeMode.ALL)
    tmp2 = GLib.utf8_normalize(search, -1, GLib.NormalizeMode.ALL)

    # C's strstr() gives a byte offset
    p = tmp1.encode().find(tmp2.encode())
    if p != -1:
        obj.set_match(p, p + len(search), 1)
    else:
        obj.set_match(0, 0, 0)


def setup_header(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListHeader) -> None:
    self = list_item

    child = Gtk.Label(label="")
    child.set_xalign(0)
    child.set_use_markup(True)
    child.set_margin_top(10)
    child.set_margin_bottom(10)

    self.set_child(child)


def bind_header(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListHeader) -> None:
    self = list_item
    child = self.get_child()
    item = self.get_item()

    if "hour" in item.get_string():
        child.set_label("<big><b>Hours</b></big>")
    else:
        child.set_label("<big><b>Minutes</b></big>")


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window
    times = ["1 minute", "2 minutes", "5 minutes", "20 minutes"]
    minutes = [
        "1 minute", "2 minutes", "5 minutes", "10 minutes", "15 minutes", "20 minutes",
        "25 minutes", "30 minutes", "35 minutes", "40 minutes", "45 minutes", "50 minutes",
        "55 minutes",
    ]
    hours = ["1 hour", "2 hours", "3 hours", "5 hours", "6 hours", "7 hours",
             "8 hours", "9 hours", "10 hours", "11 hours", "12 hours"]
    device_titles = ["Digital Output", "Headphones", "Digital Output", "Analog Output"]
    device_icons = ["audio-card-symbolic", "audio-headphones-symbolic", "audio-card-symbolic",
                    "audio-card-symbolic"]
    device_descriptions = [
        "Built-in Audio", "Built-in audio", "Thinkpad Tunderbolt 3 Dock USB Audio",
        "Thinkpad Tunderbolt 3 Dock USB Audio",
    ]

    if not window:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Selections")
        window.set_resizable(False)

        window.close_request.connect(close_request)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)

        hbox.set_margin_start(20)
        hbox.set_margin_end(20)
        hbox.set_margin_top(20)
        hbox.set_margin_bottom(20)
        window.set_child(hbox)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hbox.append(box)

        label = Gtk.Label(label="Dropdowns")
        label.add_css_class("title-4")
        box.append(label)

        # A basic dropdown
        button = drop_down_new_from_strings(times, None, None)
        box.append(button)

        # A dropdown using an expression to obtain strings
        minutes_model = Gtk.StringList.new(minutes)
        hours_model = Gtk.StringList.new(hours)
        store = Gio.ListStore(item_type=Gio.ListModel)
        store.append(minutes_model)
        store.append(hours_model)
        flat = Gtk.FlattenListModel.new(store)
        expression = Gtk.PropertyExpression.new(Gtk.StringObject, None, "string")
        button = Gtk.DropDown.new(flat, expression)
        button.set_enable_search(True)
        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_header)
        factory.bind.connect(bind_header)
        button.set_header_factory(factory)
        box.append(button)

        button = Gtk.DropDown.new(None, None)

        # C uses pango_cairo_font_map_get_default(); PyLiite4 has no PangoCairo, and this is the same font map.
        model = window.get_pango_context().get_font_map()
        button.set_model(model)
        button.set_selected(0)

        expression = Gtk.ClosureExpression.new(GObject.TYPE_STRING, get_family_name, None)
        button.set_expression(expression)
        box.append(button)

        spin = Gtk.SpinButton.new_with_range(-1, model.get_n_items(), 1)
        spin.set_halign(Gtk.Align.START)
        spin.set_margin_start(20)
        button.bind_property("selected", spin, "value",
                             GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL)
        box.append(spin)

        check = Gtk.CheckButton.new_with_label("Enable search")
        check.set_margin_start(20)
        button.bind_property("enable-search", check, "active",
                             GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL)
        box.append(check)

        # A dropdown with a separate list factory
        button = drop_down_new_from_strings(device_titles, device_icons, device_descriptions)
        box.append(button)

        hbox.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        hbox.append(box)

        label = Gtk.Label(label="Suggestions")
        label.add_css_class("title-4")
        box.append(label)

        # A basic suggestion entry
        entry = suggestion_entry_new()
        entry.set_property("placeholder-text", "Words with T or G…")
        strings = Gtk.StringList.new([
            "GNOME",
            "gnominious",
            "Gnomonic projection",
            "total",
            "totally",
            "toto",
            "tottery",
            "totterer",
            "Totten trust",
            "totipotent",
            "totipotency",
            "totemism",
            "totem pole",
            "Totara",
            "totalizer",
            "totalizator",
            "totalitarianism",
            "total parenteral nutrition",
            "total hysterectomy",
            "total eclipse",
            "Totipresence",
            "Totipalmi",
            "Tomboy",
            "zombie",
        ])
        entry.set_model(strings)

        box.append(entry)

        # A suggestion entry using a custom model, and no filtering
        entry = suggestion_entry_new()

        file = Gio.File.new_for_path(os.getcwd())
        dir = Gtk.DirectoryList.new("standard::display-name,standard::content-type,standard::icon,standard::size",
                                    file)
        entry.set_model(dir)

        expression = Gtk.ClosureExpression.new(GObject.TYPE_STRING, get_file_name, None)
        entry.set_expression(expression)

        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_item)
        factory.bind.connect(bind_item)

        entry.set_factory(factory)

        entry.set_use_filter(False)
        entry.set_show_arrow(True)

        box.append(entry)

        # A suggestion entry with match highlighting
        entry = suggestion_entry_new()
        entry.set_property("placeholder-text", "Destination")

        strings = Gtk.StringList.new([
            "app-mockups",
            "settings-mockups",
            "os-mockups",
            "software-mockups",
            "mocktails",
        ])
        entry.set_model(strings)

        box.append(entry)

        entry.set_match_func(match_func, None)

        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_highlight_item)
        factory.bind.connect(bind_highlight_item)
        entry.set_factory(factory)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
