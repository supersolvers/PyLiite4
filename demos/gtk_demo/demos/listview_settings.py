"""Lists/Settings
#Keywords: GtkListItemFactory, GListModel

This demo shows a settings viewer for GSettings.

It demonstrates how to implement support for trees with GtkListView.
It also shows how to set up sorting and filtering for columns in a
GtkColumnView.

It also demonstrates different styles of list. The tree on the left
uses the ­.navigation-sidebar style class, the list on the right uses
the ­.data-table style class.
"""

from collections.abc import Callable
from typing import Any

from PyLiite4 import Gio, GLib, GObject, Gtk

from .settings_key import SettingsKey, settings_key_new


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


def item_value_changed(label: Gtk.EditableLabel, pspec: GObject.ParamSpec, cell: Gtk.ColumnViewCell) -> None:
    if label.get_editing():
        return

    text = label.get_text()

    self = cell.get_item()
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
    label.error_bell()

    value = self.get_property("value")
    label.set_text(value)


current_filter: Gtk.Filter | None = None


def transform_settings_to_keys(binding: GObject.Binding, treelistrow: Gtk.TreeListRow | None) -> Any:
    global current_filter
    data = binding.get_target()

    if treelistrow is None:
        return None
    settings = treelistrow.get_item()
    schema = settings.get_property("settings-schema")

    store = Gio.ListStore(item_type=SettingsKey)

    keys = schema.list_keys()

    for key in keys:
        almost_there = schema.get_key(key)
        finally_ = settings_key_new(settings, almost_there)
        store.append(finally_)

    sort_model = Gtk.SortListModel.new(store, data.get_sorter())

    filter = Gtk.StringFilter.new(Gtk.PropertyExpression.new(SettingsKey, None, "name"))
    current_filter = filter
    filter_model = Gtk.FilterListModel.new(sort_model, filter)

    return Gtk.NoSelection.new(filter_model)


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


def search_changed(entry: Gtk.SearchEntry, data: object = None) -> None:
    text = entry.get_text()

    if current_filter:
        current_filter.set_search(text)


def stop_search(entry: Gtk.SearchEntry, data: object = None) -> None:
    entry.set_text("")

    if current_filter:
        current_filter.set_search("")


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window
    if window is None:
        scope = BuilderCScope(search_enabled, search_changed, stop_search, item_value_changed)

        builder = Gtk.Builder()
        builder.set_scope(scope)

        builder.add_from_resource("/listview_settings/listview_settings.ui")

        window = builder.get_object("window")
        window.set_display(do_widget.get_display())

        window.close_request.connect(close_request)

        listview = builder.get_object("listview")
        columnview = builder.get_object("columnview")
        type_column = builder.get_object("type_column")
        default_column = builder.get_object("default_column")
        summary_column = builder.get_object("summary_column")
        description_column = builder.get_object("description_column")

        actions = Gio.SimpleActionGroup()

        action = Gio.PropertyAction.new("show-type", type_column, "visible")
        actions.add_action(action)

        action = Gio.PropertyAction.new("show-default", default_column, "visible")
        actions.add_action(action)

        action = Gio.PropertyAction.new("show-summary", summary_column, "visible")
        actions.add_action(action)

        action = Gio.PropertyAction.new("show-description", description_column, "visible")
        actions.add_action(action)

        columnview.insert_action_group("columnview", actions)

        model = create_settings_model(None, None)
        treemodel = Gtk.TreeListModel.new(model, False, True, create_settings_model)
        selection = Gtk.SingleSelection.new(treemodel)
        selection.bind_property("selected-item", columnview, "model", GObject.BindingFlags.SYNC_CREATE,
                                transform_settings_to_keys, None)
        listview.set_model(selection)

        name_column = builder.get_object("name_column")
        sorter = Gtk.StringSorter.new(Gtk.PropertyExpression.new(SettingsKey, None, "name"))
        name_column.set_sorter(sorter)

        sorter = Gtk.StringSorter.new(Gtk.PropertyExpression.new(SettingsKey, None, "type"))
        type_column.set_sorter(sorter)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
