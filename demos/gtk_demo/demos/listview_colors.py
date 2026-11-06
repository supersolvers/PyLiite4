"""Lists/Colors
#Keywords: GtkSortListModel, GtkMultiSelection

This demo displays a grid of colors.

It is using a GtkGridView, and shows how to display
and sort the data in various ways. The controls for
this are implemented using GtkDropDown.

The dataset used here has up to 16 777 216 items.

Note that this demo also functions as a performance
test for some of the list model machinery, and the
biggest sizes here can lock up the application for
extended times when used with sorting.
"""

import locale

from PyLiite4 import Gdk, Gio, GLib, GObject, Graphene, Gtk, Pango


class GtkColor(GObject.Object, Gdk.Paintable):
    """This is our object. It's just a color"""

    __gtype_name__ = "GtkColor"

    def __init__(self, **properties: object) -> None:
        self._name: str | None = None
        self._color = Gdk.RGBA()
        self.h = 0
        self.s = 0
        self.v = 0
        super().__init__(**properties)

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        snapshot.append_color(self._color, Graphene.Rect().init(0, 0, width, height))

    def do_get_intrinsic_width(self) -> int:
        return 32

    def do_get_intrinsic_height(self) -> int:
        return 32

    @GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    def name(self) -> str | None:
        return self._name

    @name.setter
    def name(self, value: str | None) -> None:
        self._name = value

    @GObject.Property(type=Gdk.RGBA, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    def color(self) -> Gdk.RGBA:
        return self._color

    @color.setter
    def color(self, value: Gdk.RGBA) -> None:
        self._color = value.copy()
        h, s, v = rgb_to_hsv(self._color)
        self.h = round(360 * h)
        self.s = round(100 * s)
        self.v = round(100 * v)

    @GObject.Property(type=float, minimum=0, maximum=1, default=0, flags=GObject.ParamFlags.READABLE)
    def red(self) -> float:
        return self._color.red

    @GObject.Property(type=float, minimum=0, maximum=1, default=0, flags=GObject.ParamFlags.READABLE)
    def green(self) -> float:
        return self._color.green

    @GObject.Property(type=float, minimum=0, maximum=1, default=0, flags=GObject.ParamFlags.READABLE)
    def blue(self) -> float:
        return self._color.blue

    @GObject.Property(type=int, minimum=0, maximum=360, default=0, flags=GObject.ParamFlags.READABLE)
    def hue(self) -> int:
        return self.h

    @GObject.Property(type=int, minimum=0, maximum=100, default=0, flags=GObject.ParamFlags.READABLE)
    def saturation(self) -> int:
        return self.s

    @GObject.Property(type=int, minimum=0, maximum=100, default=0, flags=GObject.ParamFlags.READABLE)
    def value(self) -> int:
        return self.v


def rgb_to_hsv(rgba: Gdk.RGBA) -> tuple[float, float, float]:
    red = rgba.red
    green = rgba.green
    blue = rgba.blue

    h = 0.0

    if red > green:
        if red > blue:
            max = red
        else:
            max = blue

        if green < blue:
            min = green
        else:
            min = blue
    else:
        if green > blue:
            max = green
        else:
            max = blue

        if red < blue:
            min = red
        else:
            min = blue

    v = max

    if max != 0.0:
        s = (max - min) / max
    else:
        s = 0.0

    if s == 0.0:
        h = 0.0
    else:
        delta = max - min

        if red == max:
            h = (green - blue) / delta
        elif green == max:
            h = 2 + (blue - red) / delta
        elif blue == max:
            h = 4 + (red - green) / delta

        h /= 6.0

        if h < 0.0:
            h += 1.0
        elif h > 1.0:
            h -= 1.0

    return h, s, v


def gtk_color_new(name: str, r: float, g: float, b: float) -> GtkColor:
    color = Gdk.RGBA(red=r, green=g, blue=b, alpha=1.0)

    return GtkColor(name=name, color=color)


N_COLORS = 256 * 256 * 256

MAP = [
    0xFF0000, 0x00FF00, 0x0000FF,
    0x7F0000, 0x007F00, 0x00007F,
    0x3F0000, 0x003F00, 0x00003F,
    0x1F0000, 0x001F00, 0x00001F,
    0x0F0000, 0x000F00, 0x00000F,
    0x070000, 0x000700, 0x000007,
    0x030000, 0x000300, 0x000003,
    0x010000, 0x000100, 0x000001,
]


def position_to_color(position: int) -> int:
    result = 0

    for i in range(len(MAP)):
        if position & (1 << i):
            result ^= MAP[i]

    return result


class GtkColorList(GObject.Object, Gio.ListModel):
    __gtype_name__ = "GtkColorList"

    def __init__(self, **properties: object) -> None:
        # C allocates all N_COLORS slots; a dict holds only the colors made so far.
        self.colors: dict[int, GtkColor] = {}
        self._size = 0  # How many colors are allowed.
        self.limit = 0

        data = Gio.resources_lookup_data("/listview_colors/color.names.txt", Gio.ResourceLookupFlags.NONE)
        lines = data.get_data().decode().split("\n")

        for line in lines:
            if line[:1] == "#" or line == "":
                continue

            fields = line.split(" ")
            name = fields[1]
            red = int(fields[3])
            green = int(fields[4])
            blue = int(fields[5])

            pos = ((red & 0xFF) << 16) | ((green & 0xFF) << 8) | blue
            if pos not in self.colors:
                self.colors[pos] = gtk_color_new(name, red / 255., green / 255., blue / 255.)

        super().__init__(**properties)

    def do_get_item_type(self) -> GObject.GType:
        return GtkColor.__gtype__

    def do_get_n_items(self) -> int:
        return self._size

    def do_get_item(self, position: int) -> GtkColor | None:
        if position >= self._size:
            return None

        position = position_to_color(position)

        if position not in self.colors:
            red = (position >> 16) & 0xFF
            green = (position >> 8) & 0xFF
            blue = position & 0xFF

            self.colors[position] = gtk_color_new("", red / 255., green / 255., blue / 255.)

        return self.colors[position]

    def set_size(self, size: int) -> None:
        old_size = self._size

        self._size = size
        if self._size > old_size:
            self.items_changed(old_size, 0, self._size - old_size)
        elif old_size > self._size:
            self.items_changed(self._size, old_size - self._size, 0)

        self.notify("size")

    @GObject.Property(type=GObject.TYPE_UINT, minimum=0, maximum=N_COLORS, default=0)
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        self.set_size(value)


def gtk_color_list_new(size: int) -> Gio.ListModel:
    return GtkColorList(size=size)


def get_rgb_markup(this: object, color: GtkColor | None) -> str | None:
    if not color:
        return None

    return "<b>R:</b> %d <b>G:</b> %d <b>B:</b> %d" % (int(color._color.red * 255),
                                                      int(color._color.green * 255),
                                                      int(color._color.blue * 255))


def get_hsv_markup(this: object, color: GtkColor | None) -> str | None:
    if not color:
        return None

    return f"<b>H:</b> {color.h} <b>S:</b> {color.s} <b>V:</b> {color.v}"


def item_expression(list_item: Gtk.ListItem) -> Gtk.Expression:
    expression = Gtk.ConstantExpression.new_for_value(GObject.Value(Gtk.ListItem, list_item))
    return Gtk.PropertyExpression.new(Gtk.ListItem, expression, "item")


def setup_simple_listitem_cb(factory: Gtk.ListItemFactory, list_item: Gtk.ListItem) -> None:
    color_expression = item_expression(list_item)

    picture = Gtk.Picture()
    picture.set_size_request(32, 32)
    color_expression.bind(picture, "paintable", None)

    list_item.set_child(picture)


def setup_listitem_cb(factory: Gtk.ListItemFactory, list_item: Gtk.ListItem) -> None:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    list_item.set_child(box)

    color_expression = item_expression(list_item)

    expression = Gtk.PropertyExpression.new(GtkColor, color_expression, "name")
    name_label = Gtk.Label()
    expression.bind(name_label, "label", None)
    box.append(name_label)

    expression = color_expression
    picture = Gtk.Picture()
    expression.bind(picture, "paintable", None)
    box.append(picture)

    params = [color_expression]
    expression = Gtk.ClosureExpression.new(GObject.TYPE_STRING, get_rgb_markup, params)

    rgb_label = Gtk.Label()
    rgb_label.set_use_markup(True)
    expression.bind(rgb_label, "label", None)
    box.append(rgb_label)

    params = [color_expression]
    expression = Gtk.ClosureExpression.new(GObject.TYPE_STRING, get_hsv_markup, params)

    hsv_label = Gtk.Label()
    hsv_label.set_use_markup(True)
    expression.bind(hsv_label, "label", None)
    box.append(hsv_label)


def setup_selection_listitem_cb(factory: Gtk.ListItemFactory, list_item: Gtk.ListItem) -> None:
    color_expression = item_expression(list_item)

    picture = Gtk.Picture()
    picture.set_size_request(8, 8)
    color_expression.bind(picture, "paintable", None)

    list_item.set_child(picture)




def set_title(item: GObject.Object, title: str) -> None:
    item.demo_title = title


def get_title(item: GObject.Object) -> str | None:
    return getattr(item, "demo_title", None)


def create_color_grid() -> Gtk.GridView:
    gridview = Gtk.GridView.new(None, None)
    gridview.set_hscroll_policy(Gtk.ScrollablePolicy.NATURAL)
    gridview.set_vscroll_policy(Gtk.ScrollablePolicy.NATURAL)

    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_simple_listitem_cb)
    gridview.set_factory(factory)

    gridview.set_max_columns(24)
    gridview.set_enable_rubberband(True)

    return gridview


def add_colors(widget: Gtk.Widget, clock: Gdk.FrameClock, colors: GtkColorList) -> bool:
    limit = colors.limit
    colors.set_size(min(limit, colors._size + max(1, limit // 4096)))

    if colors._size >= limit:
        return GLib.SOURCE_REMOVE
    else:
        return GLib.SOURCE_CONTINUE


def refill(button: Gtk.Button, colors: GtkColorList) -> None:
    colors.set_size(0)
    button.add_tick_callback(add_colors, colors)


def format_number(n: int) -> str:
    """printf's %'u: grouped in thousands as the locale does it"""
    return locale.format_string("%u", n, grouping=True)


def limit_changed_cb(dropdown: Gtk.DropDown, pspec: GObject.ParamSpec, colors: GtkColorList) -> None:
    old_limit = colors.limit
    new_limit = 1 << (3 * (dropdown.get_selected() + 1))

    colors.limit = new_limit

    if old_limit == colors._size:
        colors.set_size(new_limit)


def limit_changed_cb2(dropdown: Gtk.DropDown, pspec: GObject.ParamSpec, label: Gtk.Label) -> None:
    limit = 1 << (3 * (dropdown.get_selected() + 1))

    string = format_number(limit)
    length = len(string)

    label.set_width_chars(length + 2)  # Room for " /" as well.


def items_changed_cb(model: Gio.ListModel, position: int, removed: int, added: int, label: Gtk.Label) -> None:
    n = model.get_n_items()

    label.set_label(f"{format_number(n)} /")


def setup_number_item(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
    label = Gtk.Label(label="")
    label.set_xalign(1)

    attrs = Pango.AttrList()
    attrs.insert(Pango.attr_font_features_new("tnum"))
    label.set_attributes(attrs)

    item.set_child(label)


def bind_number_item(factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
    label = item.get_child()

    limit = 1 << (3 * (item.get_position() + 1))
    label.set_label(format_number(limit))


def update_selection_count(model: Gio.ListModel, position: int, removed: int, added: int,
                           label: Gtk.Label) -> None:
    label.set_label(f"{model.get_n_items()}")


def update_selection_average(model: Gio.ListModel, position: int, removed: int, added: int,
                             picture: Gtk.Picture) -> None:
    n = model.get_n_items()
    red = green = blue = 0.0

    for i in range(n):
        color = model.get_item(i)

        red += color._color.red
        green += color._color.green
        blue += color._color.blue

    if n == 0:
        # C divides by zero here and gets a NaN color, which draws nothing.
        picture.set_paintable(None)
        return

    color = gtk_color_new("", red / n, green / n, blue / n)
    picture.set_paintable(color)


def update_progress_cb(model: Gtk.SortListModel, pspec: GObject.ParamSpec, progress: Gtk.ProgressBar) -> None:
    total = model.get_n_items()
    total = max(total, 1)  # Avoids a division by 0 below.
    pending = model.get_pending()

    progress.set_visible(pending != 0)
    progress.set_fraction((total - pending) / total)


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        provider = Gtk.CssProvider()
        provider.load_from_resource("/listview_colors/listview_colors.css")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)

        sort_model = Gtk.SortListModel.new(gtk_color_list_new(0), None)
        sort_model.set_incremental(True)
        selection = Gtk.MultiSelection.new(sort_model)

        window = Gtk.Window()
        window.set_title("Colors")
        header = Gtk.HeaderBar()
        window.set_titlebar(header)

        window.set_default_size(600, 400)
        window.set_display(do_widget.get_display())
        window.close_request.connect(close_request)

        overlay = Gtk.Overlay()
        window.set_child(overlay)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        overlay.set_child(box)

        progress = Gtk.ProgressBar()
        progress.set_hexpand(True)
        progress.set_valign(Gtk.Align.START)
        sort_model.notify["pending"].connect(update_progress_cb, progress)
        overlay.add_overlay(progress)

        selection_info_revealer = Gtk.Revealer()
        box.append(selection_info_revealer)

        grid = Gtk.Grid()
        selection_info_revealer.set_child(grid)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)

        label = Gtk.Label(label="Selection")
        label.set_hexpand(True)
        label.add_css_class("title-3")
        grid.attach(label, 0, 0, 5, 1)

        grid.attach(Gtk.Label(label="Size:"), 0, 2, 1, 1)

        selection_size_label = Gtk.Label(label="0")
        grid.attach(selection_size_label, 1, 2, 1, 1)

        grid.attach(Gtk.Label(label="Average:"), 2, 2, 1, 1)

        selection_average_picture = Gtk.Picture()
        selection_average_picture.set_size_request(32, 32)
        grid.attach(selection_average_picture, 3, 2, 1, 1)

        label = Gtk.Label(label="")
        label.set_hexpand(True)
        grid.attach(label, 4, 2, 1, 1)

        sw = Gtk.ScrolledWindow()
        sw.set_hexpand(True)

        grid.attach(sw, 0, 1, 5, 1)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_selection_listitem_cb)
        selection_view = Gtk.GridView.new(None, factory)
        selection_view.add_css_class("compact")
        selection_view.set_max_columns(200)
        sw.set_child(selection_view)

        sw = Gtk.ScrolledWindow()
        box.append(sw)

        gridview = create_color_grid()
        gridview.set_model(selection)
        sw.set_child(gridview)
        sw.set_hexpand(True)
        sw.set_vexpand(True)

        selection_filter = Gtk.SelectionFilterModel.new(selection)
        selection_filter.items_changed.connect(update_selection_count, selection_size_label)
        selection_filter.items_changed.connect(update_selection_average, selection_average_picture)

        no_selection = Gtk.NoSelection.new(selection_filter)
        selection_view.set_model(no_selection)

        selection_info_toggle = Gtk.ToggleButton()
        selection_info_toggle.set_icon_name("emblem-important-symbolic")
        selection_info_toggle.set_tooltip_text("Show selection info")
        header.pack_start(selection_info_toggle)

        selection_info_toggle.bind_property("active", selection_info_revealer, "reveal-child",
                                            GObject.BindingFlags.DEFAULT)

        button = Gtk.Button.new_with_mnemonic("_Refill")
        button.clicked.connect(refill, sort_model.get_model())

        header.pack_start(button)

        label = Gtk.Label(label="0 /")
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_font_features_new("tnum"))
        label.set_attributes(attrs)
        string = format_number(4096)
        label.set_width_chars(len(string) + 2)
        label.set_xalign(1)

        selection.items_changed.connect(items_changed_cb, label)
        header.pack_start(label)

        dropdown = Gtk.DropDown.new_from_strings(["8", "64", "512", "4096", "32768", "262144", "2097152",
                                                  "16777216"])
        dropdown.notify["selected"].connect(limit_changed_cb, sort_model.get_model())
        dropdown.notify["selected"].connect(limit_changed_cb2, label)
        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_number_item)
        factory.bind.connect(bind_number_item)
        dropdown.set_factory(factory)
        dropdown.set_selected(3)  # 4096
        header.pack_start(dropdown)

        sorters = Gio.ListStore(item_type=Gtk.Sorter)

        # An empty multisorter doesn't do any sorting and the sortmodel is
        # smart enough to know that.
        sorter = Gtk.MultiSorter.new()
        set_title(sorter, "Unsorted")
        sorters.append(sorter)

        sorter = Gtk.StringSorter.new(Gtk.PropertyExpression.new(GtkColor, None, "name"))
        set_title(sorter, "Name")
        sorters.append(sorter)

        multi_sorter = Gtk.MultiSorter.new()

        sorter = Gtk.NumericSorter.new(Gtk.PropertyExpression.new(GtkColor, None, "red"))
        sorter.set_sort_order(Gtk.SortType.DESCENDING)
        set_title(sorter, "Red")
        sorters.append(sorter)
        multi_sorter.append(sorter)

        sorter = Gtk.NumericSorter.new(Gtk.PropertyExpression.new(GtkColor, None, "green"))
        sorter.set_sort_order(Gtk.SortType.DESCENDING)
        set_title(sorter, "Green")
        sorters.append(sorter)
        multi_sorter.append(sorter)

        sorter = Gtk.NumericSorter.new(Gtk.PropertyExpression.new(GtkColor, None, "blue"))
        sorter.set_sort_order(Gtk.SortType.DESCENDING)
        set_title(sorter, "Blue")
        sorters.append(sorter)
        multi_sorter.append(sorter)

        set_title(multi_sorter, "RGB")
        sorters.append(multi_sorter)

        multi_sorter = Gtk.MultiSorter.new()

        sorter = Gtk.NumericSorter.new(Gtk.PropertyExpression.new(GtkColor, None, "hue"))
        sorter.set_sort_order(Gtk.SortType.DESCENDING)
        set_title(sorter, "Hue")
        sorters.append(sorter)
        multi_sorter.append(sorter)

        sorter = Gtk.NumericSorter.new(Gtk.PropertyExpression.new(GtkColor, None, "saturation"))
        sorter.set_sort_order(Gtk.SortType.DESCENDING)
        set_title(sorter, "Saturation")
        sorters.append(sorter)
        multi_sorter.append(sorter)

        sorter = Gtk.NumericSorter.new(Gtk.PropertyExpression.new(GtkColor, None, "value"))
        sorter.set_sort_order(Gtk.SortType.DESCENDING)
        set_title(sorter, "Value")
        sorters.append(sorter)
        multi_sorter.append(sorter)

        set_title(multi_sorter, "HSV")
        sorters.append(multi_sorter)

        expression = Gtk.ClosureExpression.new(GObject.TYPE_STRING, get_title, None)

        dropdown = Gtk.DropDown.new(sorters, expression)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.append(Gtk.Label(label="Sort by:"))
        box.append(dropdown)
        header.pack_end(box)

        dropdown.bind_property("selected-item", sort_model, "sorter", GObject.BindingFlags.SYNC_CREATE)

        factories = Gio.ListStore(item_type=Gtk.ListItemFactory)

        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_simple_listitem_cb)
        set_title(factory, "Colors")
        factories.append(factory)

        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_listitem_cb)
        set_title(factory, "Everything")
        factories.append(factory)

        expression = Gtk.ClosureExpression.new(GObject.TYPE_STRING, get_title, None)
        dropdown = Gtk.DropDown.new(factories, expression)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.append(Gtk.Label(label="Show:"))
        box.append(dropdown)
        header.pack_end(box)

        dropdown.bind_property("selected-item", gridview, "factory", GObject.BindingFlags.SYNC_CREATE)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
