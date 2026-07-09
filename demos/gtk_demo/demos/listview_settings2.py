"""Lists/Alternative Settings
#Keywords: GtkListHeaderFactory, GtkSectionModel

This demo shows an alternative settings viewer for GSettings.

It demonstrates how to implement support for sections with GtkListView.

It also shows how to quickly flatten a large tree of items into a list
that can be filtered to find the items one is looking for.
"""

from collections.abc import Callable
from typing import Any

from PyLiite4 import Gio, GLib, GObject, Gtk

from .settings_key import SettingsKey, settings_key_get_search_string, settings_key_new


class BuilderCScope(GObject.Object, Gtk.BuilderScope):
    """What GtkBuilderCScope does for C callbacks: a signal's object, or else the builder's current object,
    is passed after the signal's arguments, or in place of the emitter when the signal is swapped.

    PyGObject's own scope always puts the object in place of the emitter, and fails on swapped signals."""

    def __init__(self, *callbacks: Callable[..., Any]) -> None:
        super().__init__()
        self.callbacks = {callback.__name__: callback for callback in callbacks}

    def do_create_closure(self, builder: Gtk.Builder, function_name: str, flags: Gtk.BuilderClosureFlags,
                          object: GObject.Object | None) -> Callable[..., Any]:
        callback = self.callbacks[function_name]
        if object is None:
            object = builder.get_current_object()
        if object is None:
            return callback
        if flags & Gtk.BuilderClosureFlags.SWAPPED:
            return lambda instance, *args: callback(object, *args, instance)
        return lambda *args: callback(*args, object)


def item_value_changed(entry: Gtk.Entry, pspec: GObject.ParamSpec, item: Gtk.ListItem) -> None:
    text = entry.get_text()

    self = item.get_item()
    key = self.get_key()

    type = key.get_value_type()
    name = key.get_name()

    try:
        variant = GLib.Variant.parse(type, text, None, None)
    except GLib.Error as error:
        GLib.log_default_handler(None, GLib.LogLevelFlags.LEVEL_WARNING, error.message)
    else:
        if key.range_check(variant):
            self.get_settings().set_value(name, variant)
            return

        GLib.log_default_handler(None, GLib.LogLevelFlags.LEVEL_WARNING, f"Not a valid value for {name}")

    # revert
    entry.error_bell()

    value = self.get_property("value")
    entry.set_text(value)


def map_settings_to_keys(item: Gio.Settings, unused: object = None) -> Gio.ListModel:
    settings = item

    schema = settings.get_property("settings-schema")

    store = Gio.ListStore(item_type=SettingsKey)

    keys = schema.list_keys()

    for key in keys:
        almost_there = schema.get_key(key)
        finally_ = settings_key_new(settings, almost_there)
        store.append(finally_)

    return store


def create_settings_model(item: Gio.Settings | None, unused: object = None) -> Gio.ListModel | None:
    settings = item

    if settings is None:
        schemas, _ = Gio.SettingsSchemaSource.get_default().list_schemas(True)
    else:
        schemas = settings.list_children()

    if not schemas:
        return None

    schemas = sorted(schemas)

    result = Gio.ListStore(item_type=Gio.Settings)
    for schema in schemas:
        if settings is None:
            child = Gio.Settings.new(schema)
        else:
            child = settings.get_child(schema)

        result.append(child)

    return result


def search_enabled(entry: Gtk.SearchEntry, *_args: object) -> None:
    entry.set_text("")


def stop_search(entry: Gtk.SearchEntry, data: object = None) -> None:
    entry.set_text("")


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window
    if window is None:
        scope = BuilderCScope(search_enabled, stop_search, settings_key_get_search_string, item_value_changed)

        builder = Gtk.Builder()
        builder.set_scope(scope)

        builder.add_from_resource("/listview_settings2/listview_settings2.ui")

        window = builder.get_object("window")
        window.set_display(do_widget.get_display())

        window.close_request.connect(close_request)

        listview = builder.get_object("listview")
        filter = builder.get_object("filter")

        model = create_settings_model(None, None)
        treemodel = Gtk.TreeListModel.new(model, True, True, create_settings_model)
        model = Gtk.MapListModel.new(treemodel, map_settings_to_keys)
        model = Gtk.FlattenListModel.new(model)
        model = Gtk.FilterListModel.new(model, filter)
        selection = Gtk.NoSelection.new(model)

        listview.set_model(selection)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
