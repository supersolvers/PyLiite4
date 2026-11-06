"""Tree View/Tree Store

The GtkTreeStore is used to store data in tree form, to be
used later on by a GtkTreeView to display it. This demo builds
a simple GtkTreeStore and displays it. If you're new to the
GtkTreeView widgets and associates, look into the GtkListStore
example first.
"""

from dataclasses import dataclass, field

from PyLiite4 import GObject, Gtk

window: Gtk.Window | None = None


@dataclass
class TreeItem:
    label: str
    alex: bool = False
    havoc: bool = False
    tim: bool = False
    owen: bool = False
    dave: bool = False
    world_holiday: bool = False  # Shared by the European hackers.
    children: list["TreeItem"] = field(default_factory=list)


# Columns
(
    HOLIDAY_NAME_COLUMN,
    ALEX_COLUMN,
    HAVOC_COLUMN,
    TIM_COLUMN,
    OWEN_COLUMN,
    DAVE_COLUMN,

    VISIBLE_COLUMN,
    WORLD_COLUMN,
    NUM_COLUMNS,
) = range(9)

# Tree data
january = [
    TreeItem("New Years Day", True, True, True, True, False, True),
    TreeItem("Presidential Inauguration", False, True, False, True, False, False),
    TreeItem("Martin Luther King Jr. day", False, True, False, True, False, False),
]

february = [
    TreeItem("Presidents' Day", False, True, False, True, False, False),
    TreeItem("Groundhog Day", False, False, False, False, False, False),
    TreeItem("Valentine's Day", False, False, False, False, True, True),
]

march = [
    TreeItem("National Tree Planting Day", False, False, False, False, False, False),
    TreeItem("St Patrick's Day", False, False, False, False, False, True),
]

april = [
    TreeItem("April Fools' Day", False, False, False, False, False, True),
    TreeItem("Army Day", False, False, False, False, False, False),
    TreeItem("Earth Day", False, False, False, False, False, True),
    TreeItem("Administrative Professionals' Day", False, False, False, False, False, False),
]

may = [
    TreeItem("Nurses' Day", False, False, False, False, False, False),
    TreeItem("National Day of Prayer", False, False, False, False, False, False),
    TreeItem("Mothers' Day", False, False, False, False, False, True),
    TreeItem("Armed Forces Day", False, False, False, False, False, False),
    TreeItem("Memorial Day", True, True, True, True, False, True),
]

june = [
    TreeItem("June Fathers' Day", False, False, False, False, False, True),
    TreeItem("Juneteenth (Liberation Day)", False, False, False, False, False, False),
    TreeItem("Flag Day", False, True, False, True, False, False),
]

july = [
    TreeItem("Parents' Day", False, False, False, False, False, True),
    TreeItem("Independence Day", False, True, False, True, False, False),
]

august = [
    TreeItem("Air Force Day", False, False, False, False, False, False),
    TreeItem("Coast Guard Day", False, False, False, False, False, False),
    TreeItem("Friendship Day", False, False, False, False, False, False),
]

september = [
    TreeItem("Grandparents' Day", False, False, False, False, False, True),
    TreeItem("Citizenship Day or Constitution Day", False, False, False, False, False, False),
    TreeItem("Labor Day", True, True, True, True, False, True),
]

october = [
    TreeItem("National Children's Day", False, False, False, False, False, False),
    TreeItem("Bosses' Day", False, False, False, False, False, False),
    TreeItem("Sweetest Day", False, False, False, False, False, False),
    TreeItem("Mother-in-Law's Day", False, False, False, False, False, False),
    TreeItem("Navy Day", False, False, False, False, False, False),
    TreeItem("Columbus Day", False, True, False, True, False, False),
    TreeItem("Halloween", False, False, False, False, False, True),
]

november = [
    TreeItem("Marine Corps Day", False, False, False, False, False, False),
    TreeItem("Veterans' Day", True, True, True, True, False, True),
    TreeItem("Thanksgiving", False, True, False, True, False, False),
]

december = [
    TreeItem("Pearl Harbor Remembrance Day", False, False, False, False, False, False),
    TreeItem("Christmas", True, True, True, True, False, True),
    TreeItem("Kwanzaa", False, False, False, False, False, False),
]


toplevel = [
    TreeItem("January", children=january),
    TreeItem("February", children=february),
    TreeItem("March", children=march),
    TreeItem("April", children=april),
    TreeItem("May", children=may),
    TreeItem("June", children=june),
    TreeItem("July", children=july),
    TreeItem("August", children=august),
    TreeItem("September", children=september),
    TreeItem("October", children=october),
    TreeItem("November", children=november),
    TreeItem("December", children=december),
]


def create_model() -> Gtk.TreeModel:
    model = Gtk.TreeStore.new([GObject.TYPE_STRING,
                               GObject.TYPE_BOOLEAN,
                               GObject.TYPE_BOOLEAN,
                               GObject.TYPE_BOOLEAN,
                               GObject.TYPE_BOOLEAN,
                               GObject.TYPE_BOOLEAN,
                               GObject.TYPE_BOOLEAN,
                               GObject.TYPE_BOOLEAN])

    # A row for each month, with its holidays as children.
    for month in toplevel:
        iter = model.append(None)
        model.set(iter, {
            HOLIDAY_NAME_COLUMN: month.label,
            ALEX_COLUMN: False,
            HAVOC_COLUMN: False,
            TIM_COLUMN: False,
            OWEN_COLUMN: False,
            DAVE_COLUMN: False,
            VISIBLE_COLUMN: False,
            WORLD_COLUMN: False,
        })

        for holiday in month.children:
            child_iter = model.append(iter)
            model.set(child_iter, {
                HOLIDAY_NAME_COLUMN: holiday.label,
                ALEX_COLUMN: holiday.alex,
                HAVOC_COLUMN: holiday.havoc,
                TIM_COLUMN: holiday.tim,
                OWEN_COLUMN: holiday.owen,
                DAVE_COLUMN: holiday.dave,
                VISIBLE_COLUMN: True,
                WORLD_COLUMN: holiday.world_holiday,
            })

    return model


def item_toggled(cell: Gtk.CellRendererToggle, path_str: str, model: Gtk.TreeStore, column: int) -> None:
    path = Gtk.TreePath.new_from_string(path_str)

    iter = model.get_iter(path)
    toggle_item = model.get_value(iter, column)

    toggle_item = not toggle_item

    model.set_value(iter, column, toggle_item)


def add_toggle_column(treeview: Gtk.TreeView, model: Gtk.TreeModel, title: str, column_id: int,
                      activatable: bool) -> None:
    renderer = Gtk.CellRendererToggle()
    renderer.set_property("xalign", 0.0)

    # C keeps the column in the renderer's object data.
    renderer.toggled.connect(item_toggled, model, column_id)

    attributes = {"active": column_id, "visible": VISIBLE_COLUMN}
    if activatable:
        attributes["activatable"] = WORLD_COLUMN
    treeview.insert_column_with_attributes(-1, title, renderer, **attributes)
    # PyGObject's insert_column_with_attributes() returns None rather than the number of columns.
    col_offset = treeview.get_n_columns()

    column = treeview.get_column(col_offset - 1)
    column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
    column.set_clickable(True)


def add_columns(treeview: Gtk.TreeView) -> None:
    model = treeview.get_model()

    # The holiday names
    renderer = Gtk.CellRendererText()
    renderer.set_property("xalign", 0.0)

    treeview.insert_column_with_attributes(-1, "Holiday", renderer, text=HOLIDAY_NAME_COLUMN)
    col_offset = treeview.get_n_columns()
    column = treeview.get_column(col_offset - 1)
    column.set_clickable(True)

    add_toggle_column(treeview, model, "Alex", ALEX_COLUMN, True)

    add_toggle_column(treeview, model, "Havoc", HAVOC_COLUMN, False)

    add_toggle_column(treeview, model, "Tim", TIM_COLUMN, True)

    add_toggle_column(treeview, model, "Owen", OWEN_COLUMN, False)

    add_toggle_column(treeview, model, "Dave", DAVE_COLUMN, False)


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Tree Store")
        window.destroy.connect(destroyed)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        window.set_child(vbox)

        vbox.append(Gtk.Label(label="Jonathan's Holiday Card Planning Sheet"))

        sw = Gtk.ScrolledWindow()
        sw.set_has_frame(True)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vbox.append(sw)

        model = create_model()

        treeview = Gtk.TreeView.new_with_model(model)
        treeview.set_vexpand(True)
        treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

        add_columns(treeview)

        sw.set_child(treeview)

        # All rows expand once the tree view has been realized.
        treeview.realize.connect(Gtk.TreeView.expand_all)
        window.set_default_size(650, 400)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
