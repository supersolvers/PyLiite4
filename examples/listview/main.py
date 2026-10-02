"""A sortable, filterable table: a Gio.ListStore of Python objects shown in a Gtk.ColumnView.

The data is a Gio.ListStore of City, a GObject.Object with properties. The view is built from list models, each
wrapping the one before:

    Gio.ListStore -> Gtk.FilterListModel -> Gtk.SortListModel -> Gtk.SingleSelection -> Gtk.ColumnView

Each column has a factory, which makes a label for each visible cell and fills it in, and a sorter; clicking a column
header sorts by it. The search entry filters by name with a Gtk.StringFilter, the switch with a Gtk.CustomFilter.

Run it from the repository root:

    python examples/listview/main.py
"""

import sys
from collections.abc import Callable

from PyLiite4 import Adw, GObject, Gio, Gtk

LARGE = 5_000_000


class City(GObject.Object):
    __gtype_name__ = "ExampleCity"

    # Properties, rather than plain attributes, so that expressions such as the sorters' can read them.
    name = GObject.Property(type=str, default="")
    country = GObject.Property(type=str, default="")
    population = GObject.Property(type=int, default=0)

    def __init__(self, name: str, country: str, population: int) -> None:
        super().__init__(name=name, country=country, population=population)


# Populations of the cities proper, rounded.
CITIES = [
    ("Tokyo", "Japan", 14_000_000), ("Istanbul", "Türkiye", 15_600_000), ("Bangkok", "Thailand", 5_500_000),
    ("Tehran", "Iran", 9_000_000), ("Lagos", "Nigeria", 15_000_000), ("Berlin", "Germany", 3_800_000),
    ("Madrid", "Spain", 3_400_000), ("Nairobi", "Kenya", 4_400_000), ("Lima", "Peru", 10_000_000),
    ("Montreal", "Canada", 1_800_000), ("Ankara", "Türkiye", 5_800_000), ("Helsinki", "Finland", 680_000),
    ("Wellington", "New Zealand", 215_000), ("Milan", "Italy", 1_400_000), ("Santiago", "Chile", 6_300_000),
]


def text_column(title: str, text: Callable[[City], str], sorter: Gtk.Sorter, numeric: bool = False
                ) -> Gtk.ColumnViewColumn:
    """A column of labels. The factory makes one per visible row and refills it as rows scroll by."""
    factory = Gtk.SignalListItemFactory()

    def setup(factory: Gtk.SignalListItemFactory, cell: GObject.Object) -> None:
        assert isinstance(cell, Gtk.ColumnViewCell)
        cell.set_child(Gtk.Label(xalign=1 if numeric else 0, css_classes=["numeric"] if numeric else []))

    def bind(factory: Gtk.SignalListItemFactory, cell: GObject.Object) -> None:
        assert isinstance(cell, Gtk.ColumnViewCell)
        label, city = cell.get_child(), cell.get_item()
        assert isinstance(label, Gtk.Label) and isinstance(city, City)
        label.set_label(text(city))

    factory.setup.connect(setup)
    factory.bind.connect(bind)
    return Gtk.ColumnViewColumn(title=title, factory=factory, sorter=sorter, expand=not numeric)


def build_window(app: Adw.Application) -> Adw.ApplicationWindow:
    store: Gio.ListStore[City] = Gio.ListStore(item_type=City)
    for name, country, population in CITIES:
        store.append(City(name, country, population))

    def has(property_name: str) -> Gtk.Expression:
        return Gtk.PropertyExpression.new(City, None, property_name)

    name_filter = Gtk.StringFilter(expression=has("name"), ignore_case=True,
                                   match_mode=Gtk.StringFilterMatchMode.SUBSTRING)
    switch = Gtk.Switch(valign=Gtk.Align.CENTER)

    def large_enough(item: City) -> bool:
        return not switch.get_active() or bool(item.population >= LARGE)

    size_filter = Gtk.CustomFilter.new(large_enough)
    filters = Gtk.EveryFilter()
    filters.append(name_filter)
    filters.append(size_filter)
    filtered = Gtk.FilterListModel(model=store, filter=filters)

    view = Gtk.ColumnView(show_column_separators=True, css_classes=["data-table"])
    view.append_column(text_column("City", lambda city: str(city.name), Gtk.StringSorter(expression=has("name"))))
    view.append_column(text_column("Country", lambda city: str(city.country),
                                   Gtk.StringSorter(expression=has("country"))))
    view.append_column(text_column("Population", lambda city: f"{city.population:,}",
                                   Gtk.NumericSorter(expression=has("population")), numeric=True))
    # The view's sorter follows the column headers the user clicks.
    sorted_model = Gtk.SortListModel(model=filtered)
    sorted_model.set_sorter(view.get_sorter())
    view.set_model(Gtk.SingleSelection(model=sorted_model))

    search = Gtk.SearchEntry(placeholder_text="Search cities", hexpand=True)
    search.search_changed.connect(lambda entry: name_filter.set_search(entry.get_text()))
    switch.notify["active"].connect(lambda *_: size_filter.changed(
        Gtk.FilterChange.MORE_STRICT if switch.get_active() else Gtk.FilterChange.LESS_STRICT))
    count = Gtk.Label(xalign=0, css_classes=["dim-label"])

    def update_count(*_: object) -> None:
        count.set_label(f"{filtered.get_n_items()} of {len(store)} cities")

    filtered.items_changed.connect(update_count)
    update_count()

    controls = Gtk.Box(spacing=12, margin_start=12, margin_end=12, margin_top=6, margin_bottom=6)
    controls.append(search)
    controls.append(Gtk.Label(label=f"Over {LARGE:,} only"))
    controls.append(switch)
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    content.append(controls)
    content.append(Gtk.ScrolledWindow(child=view, vexpand=True))
    footer = Gtk.Box(margin_start=12, margin_top=6, margin_bottom=6)
    footer.append(count)
    content.append(footer)

    toolbar = Adw.ToolbarView(content=content)
    toolbar.add_top_bar(Adw.HeaderBar())
    return Adw.ApplicationWindow(application=app, title="Cities", default_width=520, default_height=480,
                                 content=toolbar)


def on_activate(app: Gio.Application) -> None:
    assert isinstance(app, Adw.Application)
    build_window(app).present()


if __name__ == "__main__":
    application = Adw.Application(application_id="org.example.PyLiite4ListView")
    application.activate.connect(on_activate)
    sys.exit(application.run(sys.argv))
