"""Lists/Weather

This demo shows a few of the rarer features of GtkListView and
how they can be used to display weather information.

The hourly weather info uses a horizontal listview. This is easy
to achieve because GtkListView implements the GtkOrientable interface.
To make the items in the list stand out more, the listview uses
separators.

A GtkNoSelectionModel is used to make sure no item in the list can be
selected. All other interactions with the items is still possible.

The dataset used here has 70 000 items.
"""

from enum import IntEnum

from PyLiite4 import Gio, GLib, GObject, Gtk


class GtkWeatherType(IntEnum):
    CLEAR = 0
    FEW_CLOUDS = 1
    FOG = 2
    OVERCAST = 3
    SCATTERED_SHOWERS = 4
    SHOWERS = 5
    SNOW = 6
    STORM = 7


class GtkWeatherInfo(GObject.Object):
    __gtype_name__ = "GtkWeatherInfo"

    def __init__(self) -> None:
        super().__init__()
        self.timestamp = 0
        self.temperature = 0
        self.weather_type = GtkWeatherType.CLEAR


def gtk_weather_info_new(timestamp: GLib.DateTime, copy_from: GtkWeatherInfo | None) -> GtkWeatherInfo:
    result = GtkWeatherInfo()

    result.timestamp = timestamp.to_unix()
    if copy_from:
        result.temperature = copy_from.temperature
        result.weather_type = copy_from.weather_type

    return result


def parse_timestamp(string: str, _tz: GLib.TimeZone) -> GLib.DateTime:
    with_seconds = string + ":00"
    return GLib.DateTime.new_from_iso8601(with_seconds, _tz)


def parse_weather_type(clouds: str, precip: str, fallback: GtkWeatherType) -> GtkWeatherType:
    if "SN" in precip:
        return GtkWeatherType.SNOW

    if "TS" in precip:
        return GtkWeatherType.STORM

    if "DZ" in precip:
        return GtkWeatherType.SCATTERED_SHOWERS

    if "SH" in precip or "RA" in precip:
        return GtkWeatherType.SHOWERS

    if "FG" in precip:
        return GtkWeatherType.FOG

    if clouds == "M" or clouds == "":
        return fallback

    if "OVC" in clouds or "BKN" in clouds:
        return GtkWeatherType.OVERCAST

    if "BKN" in clouds or "SCT" in clouds:
        return GtkWeatherType.FEW_CLOUDS

    if "VV" in clouds:
        return GtkWeatherType.FOG

    return GtkWeatherType.CLEAR


def parse_temperature(s: str, fallback: float) -> float:
    # g_ascii_strtod() parses nothing from an empty string, and leaves nothing behind
    if s == "":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return fallback


def create_weather_model() -> Gio.ListModel:
    store = Gio.ListStore(item_type=GtkWeatherInfo)
    data = Gio.resources_lookup_data("/listview_weather/listview_weather.txt", Gio.ResourceLookupFlags.NONE)
    lines = data.get_data().decode().split("\n")

    utc = GLib.TimeZone.new_utc()
    timestamp = GLib.DateTime.new(utc, 2011, 1, 1, 0, 0, 0)
    info = gtk_weather_info_new(timestamp, None)
    items = [info]

    for line in lines:
        if not line:
            break

        fields = line.split(",")
        date = parse_timestamp(fields[0], utc)
        while date.difference(timestamp) > 30 * GLib.TIME_SPAN_MINUTE:
            timestamp = timestamp.add_hours(1)
            info = gtk_weather_info_new(timestamp, info)
            items.append(info)

        info.temperature = int(parse_temperature(fields[1], info.temperature))
        info.weather_type = parse_weather_type(fields[2], fields[3], info.weather_type)

    # C appends each item as it goes; adding them in one go is the same, and much faster from Python.
    store.splice(0, 0, items)

    return store


def setup_widget(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    list_item.set_child(box)

    child = Gtk.Label()
    child.set_width_chars(5)
    box.append(child)

    child = Gtk.Image()
    child.set_icon_size(Gtk.IconSize.LARGE)
    box.append(child)

    child = Gtk.Label()
    child.set_vexpand(True)
    child.set_valign(Gtk.Align.END)
    child.set_width_chars(4)
    box.append(child)


WEATHER_ICONS = {
    GtkWeatherType.CLEAR: "weather-clear-symbolic",
    GtkWeatherType.FEW_CLOUDS: "weather-few-clouds-symbolic",
    GtkWeatherType.FOG: "weather-fog-symbolic",
    GtkWeatherType.OVERCAST: "weather-overcast-symbolic",
    GtkWeatherType.SCATTERED_SHOWERS: "weather-showers-scattered-symbolic",
    GtkWeatherType.SHOWERS: "weather-showers-symbolic",
    GtkWeatherType.SNOW: "weather-snow-symbolic",
    GtkWeatherType.STORM: "weather-storm-symbolic",
}


def bind_widget(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    box = list_item.get_child()
    info = list_item.get_item()

    child = box.get_first_child()
    timestamp = GLib.DateTime.new_from_unix_utc(info.timestamp)
    s = timestamp.format("%R")
    child.set_text(s)

    child = child.get_next_sibling()
    icon_name = WEATHER_ICONS.get(info.weather_type)
    if icon_name:
        child.set_from_icon_name(icon_name)
    else:
        child.clear()

    child = child.get_next_sibling()
    s = f"{info.temperature}°"
    child.set_text(s)


window: Gtk.Window | None = None


def create_weather_view() -> Gtk.Widget:
    factory = Gtk.SignalListItemFactory()
    factory.setup.connect(setup_widget)
    factory.bind.connect(bind_widget)
    model = Gtk.NoSelection.new(create_weather_model())
    listview = Gtk.ListView.new(model, factory)
    listview.set_orientation(Gtk.Orientation.HORIZONTAL)
    listview.set_show_separators(True)

    return listview


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window
    if window is None:
        window = Gtk.Window()
        window.set_default_size(600, 400)
        window.set_title("Weather")
        window.set_display(do_widget.get_display())
        window.set_title("Weather")

        window.close_request.connect(close_request)

        sw = Gtk.ScrolledWindow()
        window.set_child(sw)
        listview = create_weather_view()
        sw.set_child(listview)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
