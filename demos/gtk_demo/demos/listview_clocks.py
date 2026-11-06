"""Lists/Clocks
#Keywords: GtkGridView, GtkListItemFactory, GListModel

This demo displays the time in different timezones.

The goal is to show how to set up expressions that track changes
in objects and make them update widgets. For that, we create a
clock object that updates its time every second and then use
various ways to display that time.

Typically, this will be done using GtkBuilder .ui files with the
help of the <binding> tag, but this demo shows the code that runs
behind that.
"""

from PyLiite4 import Gdk, Gio, GLib, GObject, Graphene, Gsk, Gtk

BLACK = Gdk.RGBA(red=0, green=0, blue=0, alpha=1)


def rounded_rect(x: float, y: float, width: float, height: float, radius: float) -> Gsk.RoundedRect:
    # Kept in a variable: a GskRoundedRect isn't boxed, so the one that init_from_rect() returns would point into
    # a temporary.
    outline = Gsk.RoundedRect()
    outline.init_from_rect(Graphene.Rect().init(x, y, width, height), radius)
    return outline


class GtkClock(GObject.Object, Gdk.Paintable):
    """This is our object. It's just a timezone"""

    __gtype_name__ = "GtkClock"

    def __init__(self, **properties: object) -> None:
        # None for the local timezone.
        self._timezone: GLib.TimeZone | None = None
        # The name of the location the clock shows the time for.
        self._location: str | None = None
        super().__init__(**properties)
        gtk_clock_start_ticking(self)

    def get_time(self) -> GLib.DateTime:
        """This function returns the current time in the clock's timezone."""
        if self._timezone:
            return GLib.DateTime.new_now(self._timezone)
        else:
            return GLib.DateTime.new_now_local()

    # The GdkPaintable interface, which gives a trivial way to display an analog clock. It also lets the listview
    # use the objects directly later, since they do something interesting.
    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        # save() and restore() undo the transforms the drawing starts out with.
        snapshot.save()

        # The (0, 0) point moves to the center of the area, so everything is drawn relative to it.
        snapshot.translate(Graphene.Point().init(width / 2, height / 2))

        # Scaled so that the clock can be drawn as if it were 100px in size, which keeps the math simple. min()
        # picks the smaller dimension for sizing, so the clock doesn't overdraw but keeps its aspect ratio.
        snapshot.scale(min(width, height) / 100.0, min(width, height) / 100.0)

        # The area is now a circle with diameter 100px (and radius 50px) that has its (0, 0) point at the center,
        # and a simple clock is drawn into it.
        time = self.get_time()

        # A border with a radius of half its size is a circle, drawn without requiring Cairo.
        outline = rounded_rect(-50, -50, 100, 100, 50)
        snapshot.append_border(outline, [4, 4, 4, 4], [BLACK, BLACK, BLACK, BLACK])

        # The hour hand, using transforms again: rather than computing where the angle points to, everything is
        # rotated and the hand is drawn as if it were :00. Hours past 12 need no special handling, since a full turn
        # of rotation changes nothing.
        snapshot.save()
        snapshot.rotate(30 * time.get_hour() + 0.5 * time.get_minute())
        outline = rounded_rect(-2, -23, 4, 25, 2)
        snapshot.push_rounded_clip(outline)
        snapshot.append_color(BLACK, outline.bounds)
        snapshot.pop()
        snapshot.restore()

        # The minute hand, drawn the same way but longer, so people can tell the hands apart.
        snapshot.save()
        snapshot.rotate(6 * time.get_minute())
        outline = rounded_rect(-2, -43, 4, 45, 2)
        snapshot.push_rounded_clip(outline)
        snapshot.append_color(BLACK, outline.bounds)
        snapshot.pop()
        snapshot.restore()

        # The second indicator
        snapshot.save()
        snapshot.rotate(6 * time.get_second())
        outline = rounded_rect(-2, -43, 4, 10, 2)
        snapshot.push_rounded_clip(outline)
        snapshot.append_color(BLACK, outline.bounds)
        snapshot.pop()
        snapshot.restore()

        # Restores the save() made before the initial transformations.
        snapshot.restore()

    # The clock's desired size is 100px, which suits an analog clock.
    def do_get_intrinsic_width(self) -> int:
        return 100

    def do_get_intrinsic_height(self) -> int:
        return 100

    @GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    def location(self) -> str | None:
        return self._location

    @location.setter
    def location(self, value: str | None) -> None:
        self._location = value

    @GObject.Property(type=GLib.DateTime, flags=GObject.ParamFlags.READABLE)
    def time(self) -> GLib.DateTime:
        return self.get_time()

    @GObject.Property(type=GLib.TimeZone, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    def timezone(self) -> GLib.TimeZone | None:
        return self._timezone

    @timezone.setter
    def timezone(self, value: GLib.TimeZone | None) -> None:
        self._timezone = value


# All the ticking clocks.
# C's list doesn't keep the clocks alive, and a clock leaves it when it is finalized. PyGObject can't hold a
# GObject weakly (a weak reference to a Python wrapper dies with the wrapper, even while the GObject lives on), so
# the list holds them, and the clocks stop ticking when their window closes, which is when C finalizes them.
ticking_clocks: list[GtkClock] = []

# The ID of the timeout source that updates all the ticking clocks.
ticking_clock_id = 0


def gtk_clock_tick() -> bool:
    """Every second, this function is called to tell everybody that
    the clocks are ticking.
    """
    for clock in ticking_clocks:
        # The time property now has a different value.
        clock.notify("time")

        # The hands of the clock are drawn differently too.
        clock.invalidate_contents()

    return GLib.SOURCE_CONTINUE


def gtk_clock_stop_ticking(self: GtkClock) -> None:
    global ticking_clock_id

    ticking_clocks.remove(self)

    # The tick updates stop once no clock is left.
    if not ticking_clocks and ticking_clock_id != 0:
        GLib.source_remove(ticking_clock_id)
        ticking_clock_id = 0


def gtk_clock_start_ticking(self: GtkClock) -> None:
    global ticking_clock_id

    # The first clock to tick starts the tick updates.
    if ticking_clock_id == 0:
        ticking_clock_id = GLib.timeout_add_seconds(1, gtk_clock_tick)

    ticking_clocks.insert(0, self)


def gtk_clock_new(location: str, _tz: GLib.TimeZone | None) -> GtkClock:
    return GtkClock(location=location, timezone=_tz)


def create_clocks_model() -> Gio.ListModel:
    result = Gio.ListStore(item_type=GtkClock)

    result.append(gtk_clock_new("local", None))
    result.append(gtk_clock_new("UTC", GLib.TimeZone.new_utc()))
    # Timezones with GTK hackers in them.
    result.append(gtk_clock_new("San Francisco", GLib.TimeZone.new_identifier("America/Los_Angeles")))
    result.append(gtk_clock_new("Xalapa", GLib.TimeZone.new_identifier("America/Mexico_City")))
    result.append(gtk_clock_new("Boston", GLib.TimeZone.new_identifier("America/New_York")))
    result.append(gtk_clock_new("London", GLib.TimeZone.new_identifier("Europe/London")))
    result.append(gtk_clock_new("Berlin", GLib.TimeZone.new_identifier("Europe/Berlin")))
    result.append(gtk_clock_new("Moscow", GLib.TimeZone.new_identifier("Europe/Moscow")))
    result.append(gtk_clock_new("New Delhi", GLib.TimeZone.new_identifier("Asia/Kolkata")))
    result.append(gtk_clock_new("Shanghai", GLib.TimeZone.new_identifier("Asia/Shanghai")))

    return result


def convert_time_to_string(image: GObject.Object, time: GLib.DateTime) -> str:
    return time.format("%x\n%X")


def setup_listitem_cb(factory: Gtk.ListItemFactory, list_item: Gtk.ListItem) -> None:
    """And this function is the crux for this whole demo.
    It shows how to use expressions to set up bindings.
    """
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    list_item.set_child(box)

    # An expression that gets the clock from the listitem, in two steps:
    # 1. An expression that gets the list item.
    # 2. That expression's "item" property, which is the clock.
    expression = Gtk.ConstantExpression.new_for_value(GObject.Value(Gtk.ListItem, list_item))
    clock_expression = Gtk.PropertyExpression.new(Gtk.ListItem, expression, "item")

    # The clock's location goes in a label, from the clock's "location" property.
    expression = Gtk.PropertyExpression.new(GtkClock, clock_expression, "location")
    location_label = Gtk.Label()
    expression.bind(location_label, "label", location_label)
    box.append(location_label)

    # The item itself is bound to a GtkPicture, with the clock expression as it is.
    expression = clock_expression
    picture = Gtk.Picture()
    expression.bind(picture, "paintable", picture)
    box.append(picture)
    picture.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[location_label]])

    # Everything comes together in a label that displays the time as text. The GDateTime of the time property
    # is transformed into a string, which the label can display.
    expression = Gtk.PropertyExpression.new(GtkClock, clock_expression, "time")
    expression = Gtk.ClosureExpression.new(GObject.TYPE_STRING, convert_time_to_string, [expression])
    time_label = Gtk.Label()
    expression.bind(time_label, "label", time_label)
    box.append(time_label)


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    # C finalizes the clocks with the window, which stops them ticking.
    for clock in win.get_child().get_child().get_model().get_model():
        gtk_clock_stop_ticking(clock)
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_title("Clocks")
        window.set_default_size(600, 400)
        window.set_display(do_widget.get_display())
        window.close_request.connect(close_request)

        # List widgets always go into a scrolled window.
        sw = Gtk.ScrolledWindow()
        window.set_child(sw)

        # The setup handler binds the listitems with expressions, so the factory needs only the setup signal: the
        # bindings take care of the bind step.
        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(setup_listitem_cb)

        model = Gtk.NoSelection.new(create_clocks_model())
        gridview = Gtk.GridView.new(model, factory)
        gridview.update_property([Gtk.AccessibleProperty.LABEL], ["Clocks"])
        gridview.set_hscroll_policy(Gtk.ScrollablePolicy.NATURAL)
        gridview.set_vscroll_policy(Gtk.ScrollablePolicy.NATURAL)

        sw.set_child(gridview)

    if not window.get_visible():
        window.set_visible(True)
    else:
        close_request(window)

    return window
