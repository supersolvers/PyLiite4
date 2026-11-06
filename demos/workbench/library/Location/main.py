import sys

from PyLiite4 import Adw, Gio, GLib, GObject, Gtk, Xdp, XdpGtk4

from demos.workbench import workbench

portal = Xdp.Portal()
parent = XdpGtk4.parent_new_gtk(workbench.window)

revealer: Gtk.Revealer = workbench.builder.get_object("revealer")
start: Gtk.Button = workbench.builder.get_object("start")
close: Gtk.Button = workbench.builder.get_object("close")
distance_threshold: Adw.SpinRow = workbench.builder.get_object("distance_threshold")
time_threshold: Adw.SpinRow = workbench.builder.get_object("time_threshold")
accuracy_button: Adw.ComboRow = workbench.builder.get_object("accuracy_button")

latitude_label: Gtk.Label = workbench.builder.get_object("latitude")
longitude_label: Gtk.Label = workbench.builder.get_object("longitude")
accuracy_label: Gtk.Label = workbench.builder.get_object("accuracy")
altitude_label: Gtk.Label = workbench.builder.get_object("altitude")
speed_label: Gtk.Label = workbench.builder.get_object("speed")
heading_label: Gtk.Label = workbench.builder.get_object("heading")
description_label: Gtk.Label = workbench.builder.get_object("description")
timestamp_label: Gtk.Label = workbench.builder.get_object("timestamp")

location_accuracy = Xdp.LocationAccuracy.EXACT
distance_threshold_value = distance_threshold.get_value()
time_threshold_value = time_threshold.get_value()


def on_location_monitor_started(portal: Xdp.Portal, result: Gio.AsyncResult) -> None:
    try:
        success = portal.location_monitor_start_finish(result)
    except GLib.Error as error:
        print(error.message, file=sys.stderr)
        success = False
    if success:
        print("Location access granted")
        revealer.set_reveal_child(True)
    else:
        print("Error retrieving location")


def start_session() -> None:
    start.set_sensitive(False)
    close.set_sensitive(True)
    portal.location_monitor_start(
        parent,
        distance_threshold_value,
        time_threshold_value,
        location_accuracy,
        Xdp.LocationMonitorFlags.NONE,
        None,
        on_location_monitor_started,
    )


def on_time_threshold_changed(_row: Adw.SpinRow, _value: GObject.ParamSpec) -> None:
    global time_threshold_value
    portal.location_monitor_stop()
    revealer.set_reveal_child(False)
    time_threshold_value = time_threshold.get_value()
    print("Time threshold changed")
    start_session()


def on_distance_threshold_changed(_row: Adw.SpinRow, _value: GObject.ParamSpec) -> None:
    global distance_threshold_value
    portal.location_monitor_stop()
    revealer.set_reveal_child(False)
    distance_threshold_value = distance_threshold.get_value()
    print("Distance threshold changed")
    start_session()


def on_selected_item_changed(_row: Adw.ComboRow, _item: GObject.ParamSpec) -> None:
    global location_accuracy
    print("Accuracy changed")
    portal.location_monitor_stop()
    revealer.set_reveal_child(False)
    accuracy_flag = accuracy_button.get_selected_item().get_string()
    location_accuracy = getattr(Xdp.LocationAccuracy, accuracy_flag.upper())
    start_session()


def on_location_updated(
    _self: Xdp.Portal,
    latitude: float,
    longitude: float,
    altitude: float,
    accuracy: float,
    speed: float,
    heading: float,
    description: str,
    timestamp_s: int,
    _timestamp_ms: int,
) -> None:
    latitude_label.set_label(str(latitude))
    longitude_label.set_label(str(longitude))
    accuracy_label.set_label(str(accuracy))
    altitude_label.set_label(str(altitude))
    speed_label.set_label(str(speed))
    heading_label.set_label(str(heading))
    description_label.set_label(description)

    # The UNIX timestamp, as a local date and time
    timestamp = GLib.DateTime.new_from_unix_local(timestamp_s)
    formatted_timestamp = timestamp.format("%c")
    timestamp_label.set_label(formatted_timestamp)


def on_close(_button: Gtk.Button) -> None:
    start.set_sensitive(True)
    close.set_sensitive(False)
    portal.location_monitor_stop()
    revealer.set_reveal_child(False)
    print("Session closed")


time_threshold.notify["value"].connect(on_time_threshold_changed)

distance_threshold.notify["value"].connect(on_distance_threshold_changed)

accuracy_button.notify["selected-item"].connect(on_selected_item_changed)

portal.location_updated.connect(on_location_updated)

start.clicked.connect(lambda _: start_session())

close.clicked.connect(on_close)
