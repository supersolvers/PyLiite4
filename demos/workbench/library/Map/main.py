import math

from PyLiite4 import Gtk, Shumate

from demos.workbench import workbench

map_widget: Shumate.SimpleMap = workbench.builder.get_object("map_widget")
registry = Shumate.MapSourceRegistry.new_with_defaults()

# Use OpenStreetMap as the source
map_source = registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK)
viewport = map_widget.get_viewport()

map_widget.set_map_source(map_source)
map_widget.get_map().center_on(0, 0)

# Reference map source used by MarkerLayer
viewport.set_reference_map_source(map_source)
viewport.set_zoom_level(5)

marker_layer = Shumate.MarkerLayer(
    viewport=viewport,
    selection_mode=Gtk.SelectionMode.SINGLE,
)

marker: Shumate.Marker = workbench.builder.get_object("marker")
marker.set_location(0, 0)
marker_layer.add_marker(marker)
map_widget.get_map().add_layer(marker_layer)

gesture = Gtk.GestureClick()
map_widget.add_controller(gesture)

button_marker: Gtk.ToggleButton = workbench.builder.get_object("button_marker")


def on_gesture_pressed(_self: Gtk.GestureClick, _n_press: int, x: float, y: float) -> None:
    if button_marker.get_active():
        location = viewport.widget_coords_to_location(map_widget, x, y)
        marker.set_location(location[0], location[1])
        print(f"Marker placed at {location[0]}, {location[1]}")


gesture.pressed.connect(on_gesture_pressed)


entry_latitude: Gtk.Entry = workbench.builder.get_object("entry_latitude")
entry_longitude: Gtk.Entry = workbench.builder.get_object("entry_longitude")
button_go: Gtk.Button = workbench.builder.get_object("button_go")


def go_to_location() -> None:
    latitude = float(entry_latitude.get_text() or 0)
    longitude = float(entry_longitude.get_text() or 0)
    if math.isnan(latitude) or math.isnan(longitude):
        print("Please enter valid coordinates")
        return

    if latitude > Shumate.MAX_LATITUDE or latitude < Shumate.MIN_LATITUDE:
        print(
            f"Latitudes must be between {Shumate.MIN_LATITUDE} and {Shumate.MAX_LATITUDE}",
        )
        return

    if longitude > Shumate.MAX_LONGITUDE or longitude < Shumate.MIN_LONGITUDE:
        print(
            f"Longitudes must be between {Shumate.MIN_LONGITUDE} and {Shumate.MAX_LONGITUDE}",
        )
        return

    viewport.set_zoom_level(5)
    map_widget.get_map().go_to(latitude, longitude)


button_go.clicked.connect(lambda _: go_to_location())

entry_latitude.activate.connect(lambda _: go_to_location())

entry_longitude.activate.connect(lambda _: go_to_location())
