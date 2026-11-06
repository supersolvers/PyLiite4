#!/usr/bin/env python3
"""Generate the PyLiite4 namespace modules and stubs from GObject Introspection data.

Usage: tools/generate.py [--gir-dir DIR ...] [--output DIR]

The checked-in modules come from this machine's GIR files where it has them, and the bundled stack's for the rest:

    tools/generate.py --gir-dir /usr/share/gir-1.0 --gir-dir ~/.cache/pyliite4-manylinux/opt/gtk/share/gir-1.0
"""

import argparse
import ast
import html
import keyword
import re
import textwrap
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# C helpers that PyGObject doesn't expose, and types replaced by the extras below.
SKIPPED = {"GLib.MainContextPusher", "GLib.MutexLocker", "GLib.RWLockReaderLocker", "GLib.RWLockWriterLocker",
           "GLib.RecMutexLocker", "GLib.RefString", "GLib.Error", "GObject.GType", "GObject.Property",
           "GObject.Signal"}
NAMESPACES = ["GLib", "GObject", "Gio", "GdkPixbuf", "HarfBuzz", "Pango", "PangoCairo", "Graphene", "Gdk", "Gsk", "Gtk",
              "Adw", "Rsvg", "GtkSource",
              "Soup", "Xdp", "XdpGtk4", "Gst", "GstBase", "GstAudio", "GstVideo", "GstPbutils", "GstApp"]
FILES = {"GLib": "GLib-2.0", "GObject": "GObject-2.0", "Gio": "Gio-2.0", "GdkPixbuf": "GdkPixbuf-2.0",
         "Pango": "Pango-1.0", "Graphene": "Graphene-1.0", "Gdk": "Gdk-4.0", "Gsk": "Gsk-4.0",
         "Gtk": "Gtk-4.0", "Adw": "Adw-1", "GtkSource": "GtkSource-5", "Soup": "Soup-3.0", "Xdp": "Xdp-1.0",
         "XdpGtk4": "XdpGtk4-1.0", "Gst": "Gst-1.0", "GstBase": "GstBase-1.0", "GstAudio": "GstAudio-1.0",
         "GstVideo": "GstVideo-1.0", "GstPbutils": "GstPbutils-1.0", "GstApp": "GstApp-1.0",
         "HarfBuzz": "HarfBuzz-0.0", "PangoCairo": "PangoCairo-1.0", "Rsvg": "Rsvg-2.0",
         "JavaScriptCore": "JavaScriptCore-6.0", "WebKit": "WebKit-6.0", "Shumate": "Shumate-1.0",
         "Spelling": "Spelling-1", "Vte": "Vte-3.91", "Gom": "Gom-1.0", "Manette": "Manette-0.2",
         "Poppler": "Poppler-0.18"}
# In the PyLiite4-Addons wheel (tools/build_addons_wheel.py), after the namespaces above that they use.
ADDON_NAMESPACES = ["JavaScriptCore", "WebKit", "Shumate", "Spelling", "Vte", "Gom", "Manette"]
# In the PyLiite4-Poppler wheel, which is GPL.
POPPLER_NAMESPACES = ["Poppler"]
DEPENDENCIES = {"GObject": ["GLib"], "Gio": ["GLib", "GObject"], "GdkPixbuf": ["GObject", "Gio"],
                "Pango": ["GObject", "Gio", "HarfBuzz"], "Graphene": ["GObject"],
                "Gdk": ["Gio", "GdkPixbuf", "Pango"], "Gsk": ["Gdk", "Graphene"],
                "Gtk": ["Gdk", "Gsk"], "Adw": ["Gtk"], "GtkSource": ["Gtk"], "Soup": ["Gio"], "Xdp": ["Gio"],
                "XdpGtk4": ["Xdp", "Gtk"], "Gst": ["GObject"], "GstBase": ["Gst"], "GstAudio": ["GstBase"],
                "GstVideo": ["GstBase"], "GstPbutils": ["GstAudio", "GstVideo"], "GstApp": ["GstBase"],
                "HarfBuzz": ["GObject"], "PangoCairo": ["Pango"], "Rsvg": ["GdkPixbuf", "Gio"],
                "JavaScriptCore": ["GObject"], "WebKit": ["Gtk", "Soup", "JavaScriptCore"], "Shumate": ["Gtk"],
                "Spelling": ["GtkSource"], "Vte": ["Gtk"], "Gom": ["Gio"], "Manette": ["Gio"],
                "Poppler": ["Gio"]}

CORE = "http://www.gtk.org/introspection/core/1.0"
C = "http://www.gtk.org/introspection/c/1.0"
GLIB = "http://www.gtk.org/introspection/glib/1.0"

SCALARS = {
    "none": "None", "utf8": "_str", "filename": "_str", "gboolean": "_bool", "gchar": "_int", "guchar": "_int",
    "gint": "_int", "guint": "_int", "gint8": "_int", "guint8": "_int", "gint16": "_int", "guint16": "_int",
    "gint32": "_int", "guint32": "_int", "gint64": "_int", "guint64": "_int", "glong": "_int", "gulong": "_int",
    "gshort": "_int", "gushort": "_int", "gsize": "_int", "gssize": "_int", "goffset": "_int", "gintptr": "_int",
    "guintptr": "_int", "gunichar": "_str", "gfloat": "_float", "gdouble": "_float", "long double": "_float",
    "gpointer": "_Any", "gconstpointer": "_Any", "va_list": "_Any", "GType": "GObject.GType",
}

GOBJECT_EXTRAS = """\
class GType:
    name: _str
    pytype: _Any
    def __init__(self, type_: _Any) -> None: ...

class GEnum(_builtin_int):
    value_name: _str
    value_nick: _str

class GFlags(_builtin_int):
    first_value_name: _str
    first_value_nick: _str

class GInterface:
    # Untyped, so that a class can implement interfaces in Python. Their properties are typed as attributes.
    props: _Any

class Property:
    def __init__(self, getter: _Any = ..., setter: _Any = ..., type: _Any = ..., default: _Any = ...,
                 nick: _str = ..., blurb: _str = ..., flags: _Any = ..., minimum: _Any = ...,
                 maximum: _Any = ...) -> None: ...
    def __get__(self, instance: _Any, owner: _Any = ...) -> _Any: ...
    def __set__(self, instance: _Any, value: _Any) -> None: ...
    def __call__(self, function: _Any) -> Property: ...
    def getter(self, function: _Any) -> Property: ...
    def setter(self, function: _Any) -> Property: ...

class Signal(_builtin_str):
    def __init__(self, name: _str = ..., func: _Any = ..., flags: _Any = ..., return_type: _Any = ...,
                 arg_types: _Any = ..., doc: _str = ..., accumulator: _Any = ..., accu_data: _Any = ...) -> None: ...
    def __get__(self, instance: _Any, owner: _Any = ...) -> _Any: ...

TYPE_NONE: GType
TYPE_INTERFACE: GType
TYPE_CHAR: GType
TYPE_UCHAR: GType
TYPE_BOOLEAN: GType
TYPE_INT: GType
TYPE_UINT: GType
TYPE_LONG: GType
TYPE_ULONG: GType
TYPE_INT64: GType
TYPE_UINT64: GType
TYPE_ENUM: GType
TYPE_FLAGS: GType
TYPE_FLOAT: GType
TYPE_DOUBLE: GType
TYPE_STRING: GType
TYPE_POINTER: GType
TYPE_BOXED: GType
TYPE_PARAM: GType
TYPE_OBJECT: GType
TYPE_PYOBJECT: GType
TYPE_GTYPE: GType
TYPE_STRV: GType
TYPE_VARIANT: GType
"""
OBJECT_EXTRAS = """\
    def __init__(self, **properties: _Any) -> None: ...
    def connect(self, detailed_signal: _str, handler: _Callable[..., _Any], *args: _Any) -> _int: ...
    def connect_after(self, detailed_signal: _str, handler: _Callable[..., _Any], *args: _Any) -> _int: ...
    def emit(self, detailed_signal: _str, *args: _Any) -> _Any: ...
    def disconnect(self, handler_id: _int) -> None: ...
    def handler_block(self, handler_id: _int) -> _Any: ...
    def handler_unblock(self, handler_id: _int) -> None: ...
    def get_property(self, property_name: _str) -> _Any: ...
    def set_property(self, property_name: _str, value: _Any) -> None: ...
    def freeze_notify(self) -> _Any: ...
    def thaw_notify(self) -> None: ...
    __gtype__: GType
"""
GLIB_EXTRAS = """\
class Error(_builtins.Exception):
    message: _str
    code: _int
    domain: _str
    def __init__(self, message: _str = ..., domain: _str = ..., code: _int = ...) -> None: ...
    def matches(self, domain: _Any, code: _int) -> _bool: ...
    def copy(self) -> Error: ...
    @staticmethod
    def new_literal(domain: _Any, message: _str, code: _int) -> Error: ...
"""
# PyGObject replaces these functions with Python versions whose signatures differ from the C ones.
OVERRIDDEN = {"GLib.idle_add", "GLib.timeout_add", "GLib.timeout_add_seconds", "GLib.markup_escape_text"}
GLIB_FUNCTION_EXTRAS = """\
glib_version: _tuple[_int, _int, _int]
def markup_escape_text(text: _str, length: _int = ...) -> _str: ...
def idle_add(function: _Callable[..., _bool | None], *user_data: _Any, priority: _int = ...) -> _int: ...
def timeout_add(interval: _int, function: _Callable[..., _bool | None], *user_data: _Any,
                priority: _int = ...) -> _int: ...
def timeout_add_seconds(interval: _int, function: _Callable[..., _bool | None], *user_data: _Any,
                        priority: _int = ...) -> _int: ...
"""
# Members that PyGObject's overrides add to classes, keyed by class.
CLASS_EXTRAS = {
    # PyLiite4's corrections in _fixes.py.
    "Gtk.Expression": """\
    def evaluate(self, this_: GObject.Object | None = ..., value: GObject.Value | None = ...) -> _Any: ...
""",
    "Gtk.Image": """\
    def set_from_gicon(self, icon: Gio.Icon | None) -> None: ...
""",
    "GLib.Variant": """\
    def __init__(self, format_string: _str, value: _Any) -> None: ...
    def unpack(self) -> _Any: ...
    def keys(self) -> _list[_Any]: ...
    def __len__(self) -> _int: ...
    def __getitem__(self, key: _Any) -> _Any: ...
""",
    "Gio.ListModel": """\
    def __len__(self) -> _int: ...
    @_overload
    def __getitem__(self, key: _int) -> _ItemT: ...
    @_overload
    def __getitem__(self, key: _builtins.slice) -> _list[_ItemT]: ...
    def __iter__(self) -> _Iterator[_ItemT]: ...
    def __contains__(self, item: _Any) -> _bool: ...
""",
    "Gio.ListStore": """\
    def append(self, item: _ItemT) -> None: ...
    def insert(self, position: _int, item: _ItemT) -> None: ...
    def insert_sorted(self, item: _ItemT, compare_func: _Callable[..., _int], *user_data: _Any) -> _int: ...
    def sort(self, compare_func: _Callable[..., _int], *user_data: _Any) -> None: ...
    def splice(self, position: _int, n_removals: _int, additions: _list[_ItemT]) -> None: ...
    def find(self, item: _ItemT) -> _tuple[_bool, _int]: ...
    def find_with_equal_func(self, item: _ItemT, equal_func: _Callable[..., _bool],
                             *user_data: _Any) -> _tuple[_bool, _int]: ...
    @_overload
    def __setitem__(self, key: _int, value: _ItemT) -> None: ...
    @_overload
    def __setitem__(self, key: _builtins.slice, value: _list[_ItemT]) -> None: ...
    def __delitem__(self, key: _int | _builtins.slice) -> None: ...
""",
    "Gio.Settings": """\
    def __getitem__(self, key: _str) -> _Any: ...
    def __setitem__(self, key: _str, value: _Any) -> None: ...
    def __contains__(self, key: _str) -> _bool: ...
    def __iter__(self) -> _Iterator[_str]: ...
    def __len__(self) -> _int: ...
    def keys(self) -> _list[_str]: ...
""",
    "Gio.Application": """\
    def create_asyncio_task(self, coro: _Coroutine[_Any, _Any, _T]) -> _asyncio.Task[_T]: ...
""",
    "Gtk.Builder": """\
    def __init__(self, scope_object_or_map: _Any = ..., **properties: _Any) -> None: ...
    def add_from_string(self, buffer: _str) -> _bool: ...
    def add_objects_from_string(self, buffer: _str, object_ids: _list[_str]) -> _bool: ...
""",
    "Gio.FileEnumerator": """\
    def __iter__(self) -> _Iterator[FileInfo]: ...
    def __next__(self) -> FileInfo: ...
""",
    # PyGObject's overrides (gi/overrides), for what GObject Introspection doesn't describe.
    "Gtk.Widget": """\
    def __iter__(self) -> _Iterator[Widget]: ...
    def __contains__(self, child: Widget) -> _bool: ...
""",
    "Gtk.TextBuffer": """\
    def create_tag(self, tag_name: _str | None = ..., **properties: _Any) -> TextTag: ...
    def insert_with_tags(self, iter: TextIter, text: _str, *tags: TextTag) -> None: ...
    def insert_with_tags_by_name(self, iter: TextIter, text: _str, *tags: _str) -> None: ...
""",
    "Gtk.TreeModel": """\
    def __len__(self) -> _int: ...
    def __bool__(self) -> _bool: ...
    def __getitem__(self, key: TreeIter | TreePath | _int | _str | _tuple[_int, ...]) -> TreeModelRow: ...
    def __setitem__(self, key: TreeIter | TreePath | _int | _str | _tuple[_int, ...], value: _Sequence[_Any]) -> None: ...
    def __delitem__(self, key: TreeIter | TreePath | _int | _str | _tuple[_int, ...]) -> None: ...
    def __iter__(self) -> TreeModelRowIter: ...
    def set_row(self, treeiter: TreeIter, row: _Sequence[_Any]) -> None: ...
    def get(self, treeiter: TreeIter, *columns: _int) -> _tuple[_Any, ...]: ...
""",
    "Gtk.ListStore": """\
    def __init__(self, *column_types: _GTypeLike) -> None: ...
    @_overload
    def set(self, treeiter: TreeIter, columns: _Sequence[_int], values: _Sequence[_Any], /) -> None: ...
    @_overload
    def set(self, treeiter: TreeIter, values: _dict[_int, _Any], /) -> None: ...
    @_overload
    def set(self, treeiter: TreeIter, /, *columns_and_values: _Any) -> None: ...
""",
    "Gtk.TreeStore": """\
    def __init__(self, *column_types: _GTypeLike) -> None: ...
    @_overload
    def set(self, treeiter: TreeIter, columns: _Sequence[_int], values: _Sequence[_Any], /) -> None: ...
    @_overload
    def set(self, treeiter: TreeIter, values: _dict[_int, _Any], /) -> None: ...
    @_overload
    def set(self, treeiter: TreeIter, /, *columns_and_values: _Any) -> None: ...
""",
    "Gtk.TreePath": """\
    def __init__(self, path: _int | _str | _Sequence[_int] = ...) -> None: ...
    def __iter__(self) -> _Iterator[_int]: ...
    def __len__(self) -> _int: ...
    def __getitem__(self, index: _int) -> _int: ...
    def __lt__(self, other: TreePath) -> _bool: ...
    def __le__(self, other: TreePath) -> _bool: ...
    def __gt__(self, other: TreePath) -> _bool: ...
    def __ge__(self, other: TreePath) -> _bool: ...
""",
    "Gdk.RGBA": """\
    def __init__(self, red: _float = ..., green: _float = ..., blue: _float = ..., alpha: _float = ...) -> None: ...
""",
    "GLib.MainLoop": """\
    def __init__(self, context: MainContext | None = ...) -> None: ...
""",
    "Pango.FontDescription": """\
    def __init__(self, string: _str | None = ...) -> None: ...
""",
    "Pango.Layout": """\
    def __init__(self, context: Context) -> None: ...
""",
}
# PyGObject's overrides that change what a method takes or returns, by the method's Python name.
OVERRIDE_SIGNATURES = {
    "Gtk.Editable.insert_text": "def insert_text(self, text: _str, position: _int) -> _int: ...",
    "Gtk.TextBuffer.set_text": "def set_text(self, text: _str, length: _int = ...) -> None: ...",
    "Gtk.TextBuffer.insert": "def insert(self, iter: TextIter, text: _str, length: _int = ...) -> None: ...",
    "Gtk.TextBuffer.insert_at_cursor": "def insert_at_cursor(self, text: _str, length: _int = ...) -> None: ...",
    "Gtk.TextBuffer.create_mark": "def create_mark(self, mark_name: _str | None, where: TextIter, "
                                  "left_gravity: _bool = ...) -> TextMark: ...",
    "Gtk.CssProvider.load_from_data": "def load_from_data(self, text: _str | _bytes, length: _int = ...) -> None: ...",
    # It raises ValueError for a path that isn't in the model.
    "Gtk.TreeModel.get_iter": "def get_iter(self, path: TreePath | _str | _int | _tuple[_int, ...]) -> TreeIter: ...",
    "Pango.Layout.set_text": "def set_text(self, text: _str, length: _int = ...) -> None: ...",
    "Pango.Layout.set_markup": "def set_markup(self, text: _str, length: _int = ...) -> None: ...",
    "GLib.MainContext.iteration": "def iteration(self, may_block: _bool = ...) -> _bool: ...",
    # Rows go in as sequences of plain values, one per column.
    "Gtk.TreeModel.iter_next": "def iter_next(self, aiter: TreeIter) -> TreeIter | None: ...",
    "Gtk.TreeModel.iter_previous": "def iter_previous(self, aiter: TreeIter) -> TreeIter | None: ...",
    "Gtk.ListStore.append": "def append(self, row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.ListStore.prepend": "def prepend(self, row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.ListStore.insert": "def insert(self, position: _int, row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.ListStore.insert_before": "def insert_before(self, sibling: TreeIter | None, row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.ListStore.insert_after": "def insert_after(self, sibling: TreeIter | None, row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.TreeStore.append": "def append(self, parent: TreeIter | None, row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.TreeStore.prepend": "def prepend(self, parent: TreeIter | None, row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.TreeStore.insert": "def insert(self, parent: TreeIter | None, position: _int, row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.TreeStore.insert_before": "def insert_before(self, parent: TreeIter | None, sibling: TreeIter | None, "
                                   "row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
    "Gtk.TreeStore.insert_after": "def insert_after(self, parent: TreeIter | None, sibling: TreeIter | None, "
                                  "row: _Sequence[_Any] | None = ...) -> TreeIter: ...",
}
# Methods PyGObject wraps in strip_boolean_result: they return their out values without the C function's success
# flag, and on failure this value instead, or raise ValueError where it is empty.
STRIPPED_BOOLEAN = {
    "Gtk.Widget.translate_coordinates": "None",
    "Gtk.Editable.get_selection_bounds": "_tuple[()]",
    "Gtk.TextBuffer.get_selection_bounds": "_tuple[()]",
    "Gtk.TextIter.forward_search": "None",
    "Gtk.TextIter.backward_search": "None",
    "Gtk.IMContext.get_surrounding": "None",
    "Gtk.RecentInfo.get_application_info": "None",
    "Gtk.ComboBox.get_active_iter": "None",
    "Gtk.IconView.get_item_at_pos": "None",
    "Gtk.IconView.get_visible_range": "None",
    "Gtk.IconView.get_dest_item_at_pos": "None",
    "Gtk.TreeModel.get_iter_first": "None",
    "Gtk.TreeModel.iter_children": "None",
    "Gtk.TreeModel.iter_nth_child": "None",
    "Gtk.TreeModel.iter_parent": "None",
    "Gtk.TreeModel.get_iter_from_string": "",
    "Gtk.TreeSortable.get_sort_column_id": "_tuple[None, None]",
    "Gtk.TreeView.get_path_at_pos": "None",
    "Gtk.TreeView.get_visible_range": "None",
    "Gtk.TreeView.get_dest_row_at_pos": "None",
    "Gtk.TreeViewColumn.cell_get_position": "None",
}
# Generic list models: Gio.ListStore[Item] holds Items.
BASES = {"Gio.ListModel": ["GObject.GInterface", "_Generic[_ItemT]"], "Gio.ListStore": ["GObject.Object", "ListModel[_ItemT]"]}
NAMESPACE_EXTRAS = {
    "Gio": '_ItemT = _TypeVar("_ItemT", bound=GObject.Object)\n_T = _TypeVar("_T")\n',
    # C macros, which PyLiite4 adds (see _fixes.py).
    "Pango": "".join(f"SCALE_{name}: _float\n" for name in
                     ("XX_SMALL", "X_SMALL", "SMALL", "MEDIUM", "LARGE", "X_LARGE", "XX_LARGE")),
}
# pycairo's classes, which GTK's drawing functions take and return.
CAIRO = {"Context", "Surface", "FontOptions", "Region", "Matrix", "Pattern", "ScaledFont", "FontFace", "RectangleInt"}
GTK_EXTRAS = """\
class TreeModelRow:
    model: TreeModel
    iter: TreeIter
    def __init__(self, model: TreeModel, iter_or_path: TreeIter | TreePath) -> None: ...
    @_builtins.property
    def path(self) -> TreePath: ...
    @_builtins.property
    def next(self) -> TreeModelRow | None: ...
    @_builtins.property
    def previous(self) -> TreeModelRow | None: ...
    @_builtins.property
    def parent(self) -> TreeModelRow | None: ...
    def get_next(self) -> TreeModelRow | None: ...
    def get_previous(self) -> TreeModelRow | None: ...
    def get_parent(self) -> TreeModelRow | None: ...
    @_overload
    def __getitem__(self, key: _int) -> _Any: ...
    @_overload
    def __getitem__(self, key: _builtins.slice) -> _list[_Any]: ...
    def __setitem__(self, key: _int | _builtins.slice, value: _Any) -> None: ...
    # Through __getitem__, a column at a time.
    def __iter__(self) -> _Iterator[_Any]: ...
    def iterchildren(self) -> TreeModelRowIter: ...
class TreeModelRowIter:
    def __init__(self, model: TreeModel, aiter: TreeIter | None) -> None: ...
    def __next__(self) -> TreeModelRow: ...
    def __iter__(self) -> TreeModelRowIter: ...
_WidgetT = _TypeVar("_WidgetT", bound=_builtins.type[Widget])
class Template:
    def __init__(self, *, string: _Any = ..., filename: _str = ..., resource_path: _str = ...) -> None: ...
    def __call__(self, cls: _WidgetT) -> _WidgetT: ...
    @staticmethod
    def Child(name: _str = ..., internal: _bool = ...) -> _Any: ...
    @staticmethod
    def Callback(name: _str = ...) -> _Any: ...
    from_file: _Any
    from_resource: _Any
    from_string: _Any
"""
# The libraries, for the module docstrings.
DESCRIPTIONS = {
    "GLib": "GLib, the low-level core library: main loops, data structures and utilities",
    "GObject": "GObject, the type system and object model the other libraries build on",
    "Gio": "Gio, for files, applications, settings, D-Bus and asynchronous I/O",
    "GdkPixbuf": "GdkPixbuf, for loading and scaling images",
    "HarfBuzz": "HarfBuzz, the text shaping engine",
    "Pango": "Pango, for laying out and rendering text",
    "PangoCairo": "PangoCairo, for rendering Pango text with cairo",
    "Graphene": "Graphene, for vectors, matrices, points and rectangles",
    "Gdk": "GDK, GTK's layer over the windowing system: displays, surfaces, events, textures and clipboards",
    "Gsk": "GSK, GTK's scene graph and renderers",
    "Gtk": "GTK, the widget toolkit",
    "Adw": "libadwaita, GNOME's widgets and styles on top of GTK",
    "Rsvg": "librsvg, for rendering SVG images",
    "GtkSource": "GtkSourceView, a text editing widget with syntax highlighting",
    "Soup": "libsoup, an HTTP client and server library",
    "Xdp": "libportal, for using XDG desktop portals",
    "XdpGtk4": "libportal's GTK 4 helpers",
    "Gst": "GStreamer, the multimedia framework",
    "GstBase": "GStreamer's base classes for elements",
    "GstAudio": "GStreamer's audio library",
    "GstVideo": "GStreamer's video library",
    "GstPbutils": "GStreamer's playback and discovery utilities",
    "GstApp": "GStreamer's appsrc and appsink elements",
    "JavaScriptCore": "JavaScriptCore, WebKit's JavaScript engine, from PyLiite4-Addons",
    "WebKit": "WebKitGTK, a web content engine, from PyLiite4-Addons",
    "Shumate": "libshumate, a map widget, from PyLiite4-Addons",
    "Spelling": "libspelling, spell checking for GtkSourceView, from PyLiite4-Addons",
    "Vte": "VTE, a terminal emulator widget, from PyLiite4-Addons",
    "Gom": "Gom, an object mapper for SQLite, from PyLiite4-Addons",
    "Manette": "libmanette, for game controllers, from PyLiite4-Addons",
    "Poppler": "Poppler, for reading and drawing PDF documents, from PyLiite4-Poppler, which is GPL",
}
# Starts each line of a docstring, so that the GObject stub's renaming leaves doc text alone.
DOC = "\0"
LINK = re.compile(r"\[(\w+)@([\w.:-]+)(?:#[\w-]+)?\]")
# Notes about freeing memory, which PyGObject does for you.
FREE_SENTENCE = re.compile(r"(?:Free\b|Free-function:|Unref\b|Do not (?:modify or )?free\b|Use \S+ to free\b"
                           r"|(?:The|This|Caller|You)\b[^.]*\b(?:free|freed|unref|unreffed)\b (?:it )?(?:with|using)\b)")
FREE_CLAUSE = re.compile(r",?\s+(?:(?:which |that )?(?:should|must) be\s+)?(?:freed|unreffed|unref'd)\s+(?:with|using)\s+"
                         r"(?:\[[^\]]*\]|\S+\(\)|`[^`]*`|\S+)(?:\s+when (?:no longer needed|done))?")


def tag(element):
    return element.tag.rsplit("}", 1)[-1]


def core(element, name):
    return element.findall(f"{{{CORE}}}{name}")


def escape(name):
    name = name.replace("-", "_")
    # PyGObject still treats "print" as a Python 2 keyword. That one has a long memory.
    if keyword.iskeyword(name) or name == "print":
        return f"{name}_"
    return f"_{name}" if name[:1].isdigit() else name


def settable(annotation):
    """The type a property accepts: PyGObject takes a Python class for a GType."""
    return "_GTypeLike" if annotation == "GObject.GType" else annotation


def nullable(element):
    return element.get("nullable") == "1" or element.get("allow-none") == "1"


def callable_usable(element):
    return element.get("introspectable", "1") != "0" and not element.get("moved-to") and not element.get("shadowed-by")


def docstring(text, indent):
    """The lines of a docstring, each marked with DOC, or none if there's no text."""
    if not text:
        return []
    text = text.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    text = text[:-1] + '\\"' if text.endswith('"') else text
    lines = [line.rstrip() for line in text.split("\n")]
    if len(lines) == 1:
        return [f'{DOC}{indent}"""{text}"""']
    return [f'{DOC}{indent}"""{lines[0]}', *[f"{DOC}{indent}{line}" if line else DOC for line in lines[1:]],
            f'{DOC}{indent}"""']


def with_doc(lines, text, indent="    "):
    """Give the first one-line ``def ...: ...`` in lines, of one or more overloads, a docstring."""
    if not text:
        return lines
    result = []
    for line in lines:
        if line.lstrip().startswith("def ") and line.endswith(": ...") and text:
            result += [line[:-len(" ...")], *docstring(text, line[:len(line) - len(line.lstrip())] + indent)]
            text = None
        else:
            result.append(line)
    return result


def override_type(signature):
    """The bound method type of a stub ``def``, such as _Callable[[_str, _int], _int]."""
    function = ast.parse(signature).body[0]
    arguments = function.args
    returned = ast.unparse(function.returns)
    if arguments.defaults or arguments.vararg or arguments.kwarg or arguments.kwonlyargs:
        return f"_Callable[..., {returned}]"
    return f"_Callable[[{', '.join(ast.unparse(a.annotation) for a in arguments.args[1:])}], {returned}]"


def find_gir(gir_dirs, name):
    # Debian keeps architecture-specific files such as GLib's in a multiarch directory.
    multiarch = list(Path("/usr/lib").glob("*/gir-1.0"))
    directories = [d for gir_dir in gir_dirs for d in [gir_dir, *(multiarch if gir_dir == Path("/usr/share/gir-1.0")
                                                                 else [])]]
    for directory in directories:
        if (directory / f"{name}.gir").exists():
            return directory / f"{name}.gir"
    raise FileNotFoundError(f"{name}.gir")


@dataclass
class ClassInfo:
    namespace: str
    name: str
    kind: str
    element: ET.Element
    parent: str | None = None
    interfaces: list = field(default_factory=list)
    signals: dict = field(default_factory=dict)
    methods: dict = field(default_factory=dict)
    properties: list = field(default_factory=list)
    prerequisites: list = field(default_factory=list)

    @property
    def qualified(self):
        return f"{self.namespace}.{self.name}"


class Generator:
    def __init__(self, gir_dirs, extra=()):
        self.namespaces = NAMESPACES + list(extra)
        self.roots = {}
        self.versions = {}
        for namespace in self.namespaces:
            root = ET.parse(find_gir(gir_dirs, FILES[namespace])).getroot()
            ns = root.find(f"{{{CORE}}}namespace")
            self.roots[namespace] = ns
            self.versions[namespace] = ns.get("version")
        self.known = {}
        self.classes = {}
        for namespace, ns in self.roots.items():
            for element in ns:
                name = element.get("name")
                if name and tag(element) in ("class", "interface", "record", "union", "enumeration",
                                             "bitfield", "callback", "alias") and (
                        tag(element) == "class" or element.get("introspectable", "1") != "0"):
                    self.known[f"{namespace}.{name}"] = element
                if tag(element) in ("class", "interface"):
                    self.classes[f"{namespace}.{name}"] = self.read_class(namespace, element)
        self.index_c_names()
        self.members, self.empty_classes = {}, {}

    def qualify(self, name, namespace):
        return name if "." in name else f"{namespace}.{name}"

    def read_class(self, namespace, element):
        info = ClassInfo(namespace, element.get("name"), tag(element), element)
        if element.get("parent"):
            info.parent = self.qualify(element.get("parent"), namespace)
        info.interfaces = [self.qualify(i.get("name"), namespace) for i in core(element, "implements")]
        info.prerequisites = [self.qualify(i.get("name"), namespace) for i in core(element, "prerequisite")]
        for signal in element.findall(f"{{{GLIB}}}signal"):
            if signal.get("introspectable", "1") != "0":
                info.signals[signal.get("name").replace("-", "_")] = signal
        for method in core(element, "method"):
            if callable_usable(method):
                info.methods[escape(method.get("shadows") or method.get("name"))] = method
        info.properties = [p for p in core(element, "property") if p.get("introspectable", "1") != "0"]
        return info

    def ancestors(self, info):
        """The class itself, its parents, and every interface they implement."""
        seen = {}
        stack = [info]
        while stack:
            current = stack.pop(0)
            if current.qualified in seen:
                continue
            seen[current.qualified] = current
            for name in [current.parent, *current.interfaces, *current.prerequisites]:
                if name and name in self.classes:
                    stack.append(self.classes[name])
        return list(seen.values())

    def signal_methods(self, namespace):
        """Names that are both a signal and a method on a class in this namespace."""
        result = {}
        for info in self.classes.values():
            if info.namespace != namespace:
                continue
            family = self.ancestors(info)
            signals = {name for c in family for name in c.signals}
            methods = {name for c in family for name in c.methods}
            own = (set(info.signals) | set(info.methods)) & signals & methods
            if own:
                result[info.name] = tuple(sorted(own))
        return dict(sorted(result.items()))

    def signal_clashes(self, info):
        family = self.ancestors(info)
        return {name for c in family for name in c.signals} & {name for c in family for name in c.methods}

    # Types --------------------------------------------------------------------------------------

    def reference(self, name, namespace):
        if name in SCALARS:
            return SCALARS[name]
        qualified = self.qualify(name, namespace)
        if qualified in ("GLib.List", "GLib.SList", "GLib.PtrArray", "GLib.Array"):
            return "_list[_Any]"
        if qualified.startswith("cairo.") and qualified[6:] in CAIRO:
            return f"_cairo.{qualified[6:]}"
        if qualified not in self.known or (qualified in SKIPPED and qualified != "GLib.Error"):
            return "_Any"
        target, short = qualified.split(".", 1)
        return short if target == namespace else qualified

    def py_type(self, element, namespace):
        """Return the annotation for a <type> or <array> child of element."""
        array = element.find(f"{{{CORE}}}array")
        if array is not None:
            inner = array.find(f"{{{CORE}}}type")
            if inner is not None and inner.get("name") in ("guint8", "gchar") and array.get("name") is None:
                if inner.get("name") == "guint8":
                    return "_bytes"
            if array.get("name") == "GLib.ByteArray":
                return "_bytes"
            return f"_list[{self.py_type(array, namespace)}]"
        type_ = element.find(f"{{{CORE}}}type")
        if type_ is None:
            return "_Any"
        name = type_.get("name", "none")
        children = core(type_, "type")
        if name in ("GLib.List", "GLib.SList", "List", "SList", "GLib.PtrArray", "PtrArray") and children:
            return f"_list[{self.py_type(type_, namespace)}]"
        if name in ("GLib.HashTable", "HashTable"):
            if len(children) == 2:
                key = self.reference(children[0].get("name", "gpointer"), namespace)
                value = self.reference(children[1].get("name", "gpointer"), namespace)
                return f"_dict[{key}, {value}]"
            return "_dict[_Any, _Any]"
        if name == "GObject.Callback" or (name == "Callback" and namespace == "GObject"):
            return "_Callable[..., _Any]"
        # PyGObject converts a GValue to and from a plain Python value, whichever way it goes.
        if name == "GObject.Value" or (name == "Value" and namespace == "GObject"):
            return "_Any"
        return self.reference(name, namespace)

    def hidden_parameters(self, element):
        """A callable's parameters, and the indexes of those PyGObject fills in itself."""
        container = element.find(f"{{{CORE}}}parameters")
        params = core(container, "parameter") if container is not None else []
        hidden = set()
        for param in params:
            for attribute in ("closure", "destroy"):
                if param.get(attribute) is not None:
                    hidden.add(int(param.get(attribute)))
            array = param.find(f"{{{CORE}}}array")
            if array is not None and array.get("length") is not None:
                hidden.add(int(array.get("length")))
        result = element.find(f"{{{CORE}}}return-value")
        if result is not None:
            array = result.find(f"{{{CORE}}}array")
            if array is not None and array.get("length") is not None:
                hidden.add(int(array.get("length")))
        # PyGObject takes a callback's user data as an argument of its own. Last, it's optional and left out; before
        # other arguments, as in Vte.Terminal.spawn_async, it still takes its place among them.
        for param in params:
            data = param.get("closure")
            data_type = params[int(data)].find(f"{{{CORE}}}type") if data is not None else None
            if data_type is not None and data_type.get("name") != "GLib.DestroyNotify":
                later = [i for i in range(int(data) + 1, len(params))
                         if i not in hidden and params[i].get("direction", "in") in ("in", "inout")]
                if later:
                    hidden.discard(int(data))
        return params, hidden

    def parameters(self, element, namespace):
        """Split a callable into visible (in, out) parameters, as PyGObject presents them."""
        if element.find(f"{{{CORE}}}parameters") is None:
            return [], [], False
        params, hidden = self.hidden_parameters(element)
        inputs, outputs, varargs = [], [], False
        for index, param in enumerate(params):
            if index in hidden:
                continue
            if param.find(f"{{{CORE}}}varargs") is not None:
                varargs = True
                continue
            annotation = self.py_type(param, namespace)
            direction = param.get("direction", "in")
            if direction in ("in", "inout"):
                # PyGObject accepts a Python class wherever GTK wants a GType.
                if annotation == "GObject.GType":
                    annotation = "_GTypeLike"
                name = escape(param.get("name"))
                if name == "self":
                    name = "self_"
                inputs.append((name, annotation, nullable(param)))
            if direction in ("out", "inout"):
                # For an out argument, allow-none and optional mean the caller may skip it, not that it's None.
                maybe_none = param.get("nullable") == "1" and annotation != "_Any"
                outputs.append(f"{annotation} | None" if maybe_none else annotation)
        return inputs, outputs, varargs

    def signature(self, element, namespace, first=None, name_override=None, prefix="", keep=None, required=False,
                  returns=None):
        """A stub ``def``: of only the first ``keep`` parameters, or with every parameter ``required``."""
        path = self.paths.get(element)
        if path in OVERRIDE_SIGNATURES and not prefix and keep is None and name_override is None:
            return OVERRIDE_SIGNATURES[path]
        inputs, outputs, varargs = self.parameters(element, namespace)
        if path in STRIPPED_BOOLEAN and returns is None:
            returns = outputs[0] if len(outputs) == 1 else f"_tuple[{', '.join(outputs)}]"
            returns += f" | {STRIPPED_BOOLEAN[path]}" if STRIPPED_BOOLEAN[path] else ""
        if keep is not None:
            inputs, varargs = inputs[:keep], False
        parts = [first] if first else []
        names = [n for n, _, _ in inputs]
        required_until = max((i for i, (_, _, opt) in enumerate(inputs) if not opt), default=-1)
        for index, (name, annotation, optional) in enumerate(inputs):
            if names.index(name) != index:
                name = f"{name}_{index}"
            text = f"{name}: {annotation}"
            if optional and annotation != "_Any" and annotation != "None":
                text += " | None"
            if index > required_until and not required:
                text += " = ..."
            parts.append(text)
        if varargs:
            parts.append("*args: _Any")
        result = element.find(f"{{{CORE}}}return-value")
        returned = self.py_type(result, namespace) if result is not None else "None"
        if result is not None and nullable(result) and returned not in ("_Any", "None"):
            returned += " | None"
        values = ([] if returned == "None" else [returned]) + outputs
        if not values:
            annotation = "None"
        elif len(values) == 1:
            annotation = values[0]
        else:
            annotation = f"_tuple[{', '.join(values)}]"
        name = name_override or escape(element.get("shadows") or element.get("name"))
        return f"def {prefix}{name}({', '.join(parts)}) -> {returns or annotation}: ..."

    def return_annotation(self, element, namespace):
        return self.signature(element, namespace, name_override="f").split(") -> ", 1)[1][:-len(": ...")]

    def async_lines(self, element, namespace, siblings, first, decorator):
        """Overloads for an async function: without a callback, PyGObject returns an awaitable of the result."""
        finish = siblings.get(element.get(f"{{{GLIB}}}finish-func") or "")
        if finish is None or not callable_usable(finish):
            return None
        inputs, _, varargs = self.parameters(element, namespace)
        callbacks = [i for i, p in enumerate(core(element.find(f"{{{CORE}}}parameters"), "parameter"))
                     if p.get("scope") == "async"]
        names = [n for n, _, _ in inputs]
        if varargs or len(callbacks) != 1 or not names or names[-1] != "callback":
            return None
        awaited = f"_Awaitable[{self.return_annotation(finish, namespace)}]"
        prefix = [f"@{decorator}"] if decorator else []
        return ["@_overload", *prefix, self.signature(element, namespace, first, keep=len(names) - 1, returns=awaited),
                "@_overload", *prefix, self.signature(element, namespace, first, required=True)]

    def signal_type(self, signal, owner, namespace):
        inputs, _, _ = self.parameters(signal, namespace)
        types = [owner]
        for _, annotation, optional in inputs:
            types.append(f"{annotation} | None" if optional and annotation not in ("_Any", "None") else annotation)
        result = signal.find(f"{{{CORE}}}return-value")
        returned = self.py_type(result, namespace) if result is not None else "None"
        return f"_Callable[[{', '.join(types)}], {returned}]"

    # Documentation ------------------------------------------------------------------------------

    def index_c_names(self):
        """Map C names such as gtk_widget_show and GtkWidget to the Python names PyGObject exposes, and each callable
        element to its Python name."""
        self.c_names, self.c_callables, self.paths = {}, set(), {}

        def add(c_name, python, is_callable=False):
            if c_name and c_name not in self.c_names:
                self.c_names[c_name] = python
                if is_callable:
                    self.c_callables.add(c_name)

        for namespace, ns in self.roots.items():
            for element in ns:
                if not element.get("name"):
                    continue
                kind, python = tag(element), f"{namespace}.{escape(element.get('shadows') or element.get('name'))}"
                owner = element.get(f"{{{GLIB}}}is-gtype-struct-for")
                if owner:
                    # PyGObject puts the class struct's methods, such as GtkWidgetClass's, on the class.
                    python = f"{namespace}.{owner}"
                elif kind in ("function", "constant"):
                    add(element.get(f"{{{C}}}identifier") or element.get(f"{{{C}}}type"), python, kind == "function")
                    self.paths[element] = python
                else:
                    add(element.get(f"{{{C}}}type") or element.get(f"{{{GLIB}}}type-name"), python)
                for child in element:
                    if tag(child) in ("method", "constructor", "function"):
                        self.paths[child] = f"{python}.{escape(child.get('shadows') or child.get('name'))}"
                        add(child.get(f"{{{C}}}identifier"), self.paths[child], True)
                    elif tag(child) == "member":
                        add(child.get(f"{{{C}}}identifier"), f"{python}.{child.get('name').replace('-', '_').upper()}")

    def link_text(self, kind, target, link):
        """The Python spelling of a gi-docgen link such as [method@Gtk.Widget.show]."""
        if kind == "id":
            python = self.c_names.get(target, target)
            return link(kind, python, python + ("()" if target in self.c_callables else ""))
        if kind == "property" and ":" in target:
            owner, name = target.split(":", 1)
            return link(kind, f"{owner}.props.{name.replace('-', '_')}", f"{owner}.props.{name.replace('-', '_')}")
        if kind == "signal" and "::" in target:
            owner, name = target.split("::", 1)
            return link(kind, f"{owner}.{escape(name.replace('-', '_'))}", f"{owner}.{escape(name.replace('-', '_'))}")
        owner, _, name = target.rpartition(".")
        if kind in ("method", "ctor", "func", "class_method", "vfunc") and owner:
            name = f"do_{escape(name)}" if kind == "vfunc" else escape(name)
            return link(kind, f"{owner}.{name}", f"{owner}.{name}()")
        if kind in ("enum", "flags", "error") and tag(self.known.get(owner, ET.Element("x"))) in (
                "enumeration", "bitfield"):
            return link(kind, owner, f"{owner}.{name.replace('-', '_').upper()}")
        return link(kind, target, target)

    def convert(self, text, instance=None, link=None):
        """gi-docgen's Markdown, with Python names: [class@Gtk.Button] becomes Gtk.Button and %TRUE True."""
        link = link or (lambda kind, target, text: text)
        result = []
        for index, part in enumerate(re.split(r"(```.*?```|\|\[.*?\]\|)", text, flags=re.S)):
            if index % 2 == 0:
                result.append(self.prose(part, instance, link))
            elif part.startswith("|["):
                # gtk-doc's |[<!-- language="C" --> ... ]| code blocks.
                language = re.match(r'\|\[\s*<!--\s*language="(\w+)"\s*-->', part)
                body = part[language.end() if language else 2:-2].strip("\n")
                result.append(f"```{language.group(1).lower() if language else ''}\n{body}\n```")
            else:
                result.append(part)
        return re.sub(r"\n{3,}", "\n\n", "".join(result)).strip()

    def prose(self, text, instance, link):
        """Convert text outside code blocks."""
        # Notes about freeing results, which PyGObject does for you.
        # Sentences alternate with the spaces between them. A dropped sentence takes the space before it with it,
        # unless that is a paragraph break.
        sentences = re.split(r"((?<=\.)[ \t]+|(?<=\.)\n(?!\n)|\n\n+)", FREE_CLAUSE.sub("", text))
        kept, pending = [], ""
        for index in range(0, len(sentences), 2):
            space = pending or (sentences[index - 1] if index else "")
            pending = space if FREE_SENTENCE.match(sentences[index]) and "\n\n" in space else ""
            if not FREE_SENTENCE.match(sentences[index]):
                kept += [space, sentences[index]]
        text = "".join(kept)
        text = re.sub(r"<picture\b.*?</picture>|<img [^>]*>|!\[[^\]]*\]\([^)]*\)|</?kbd>", "", text, flags=re.S)
        parts = re.split(r"(`[^`\n]*`)", text)
        for index, part in enumerate(parts):
            if index % 2:
                # Inline code that is just a C name, such as `GtkButton` or `gtk_widget_show()`.
                name = re.fullmatch(r"`(\w+)(\(\))?`", part)
                if name and name.group(1) in ("TRUE", "FALSE", "NULL"):
                    parts[index] = f"`{name.group(1).title() if name.group(1) != 'NULL' else 'None'}`"
                elif name and name.group(1) in self.c_names:
                    python = self.c_names[name.group(1)]
                    parts[index] = f"`{link('id', python, python + (name.group(2) or ''))}`"
                continue
            part = LINK.sub(lambda m: self.link_text(m.group(1), m.group(2), link), part)
            part = re.sub(r"(?<![\w#&])#([A-Z]\w*)(::?[\w-]+)?", lambda m: self.hash_name(m, link), part)
            part = re.sub(r"(?<![\w%])%([A-Z][A-Z0-9_]*)\b(-terminated)?", lambda m: self.percent_name(m, link), part)
            part = re.sub(r"\b([a-z]\w*_\w+)\s?\(\)", lambda m: link("id", self.c_names[m.group(1)],
                          self.c_names[m.group(1)] + "()") if m.group(1) in self.c_names else m.group(0), part)
            part = re.sub(r"(?<![\w@./])@(\w+)", lambda m: "self" if m.group(1) == instance else m.group(1), part)
            parts[index] = html.unescape(part)
        return "".join(parts)

    def hash_name(self, match, link):
        """gtk-doc's #GtkWidget, #GtkWidget:visible and #GtkWidget::destroy."""
        name, member = match.group(1), match.group(2)
        if name not in self.c_names:
            return match.group(0)
        python = self.c_names[name]
        if not member:
            return link("id", python, python)
        if member.startswith("::"):
            signal = f"{python}.{escape(member[2:].replace('-', '_'))}"
            return link("signal", signal, signal)
        return link("property", f"{python}.props.{member[1:].replace('-', '_')}",
                    f"{python}.props.{member[1:].replace('-', '_')}")

    def percent_name(self, match, link):
        name, terminated = match.group(1), match.group(2)
        if terminated:
            return match.group(0)[1:]
        if name in ("TRUE", "FALSE", "NULL"):
            return name.title() if name != "NULL" else "None"
        return link("id", self.c_names[name], self.c_names[name]) if name in self.c_names else name

    def doc(self, element, instance=None, link=None):
        """The converted <doc> of element, and a note if it is deprecated."""
        doc = element.find(f"{{{CORE}}}doc")
        parts = [self.convert(doc.text, instance, link)] if doc is not None and doc.text else []
        if element.get("deprecated") == "1":
            note = element.find(f"{{{CORE}}}doc-deprecated")
            note = self.convert(note.text, instance, link) if note is not None and note.text else ""
            since = f" since {element.get('deprecated-version')}" if element.get("deprecated-version") else ""
            parts.append(f"Deprecated{since}" + (f": {note}" if note else "."))
        return "\n\n".join(p for p in parts if p)

    def callable_doc(self, element, link=None):
        """A callable's doc, with Google-style Args and Returns sections for its visible parameters."""
        container = element.find(f"{{{CORE}}}parameters")
        this = container.find(f"{{{CORE}}}instance-parameter") if container is not None else None
        instance = this.get("name") if this is not None else None
        params, hidden = self.hidden_parameters(element)
        args, returns = [], []
        result = element.find(f"{{{CORE}}}return-value")
        # A success flag PyGObject strips isn't returned.
        if result is not None and self.paths.get(element) not in STRIPPED_BOOLEAN and self.doc(result, instance, link):
            returns.append(("", self.doc(result, instance, link)))
        for index, param in enumerate(params):
            text = self.doc(param, instance, link)
            if index in hidden or param.find(f"{{{CORE}}}varargs") is not None or not text:
                continue
            name = escape(param.get("name"))
            if param.get("direction", "in") in ("in", "inout"):
                args.append(("self_" if name == "self" else name, text))
            if param.get("direction", "in") in ("out", "inout"):
                returns.append((name, text))
        sections = [self.doc(element, instance, link)]
        for title, items in (("Args", args), ("Returns", returns if len(returns) > 1 else
                                                [("", returns[0][1])] if returns else [])):
            if items:
                lines = [f"{title}:"]
                for name, text in items:
                    first, _, rest = text.partition("\n")
                    rest = "\n".join(f"        {line}" if line else "" for line in textwrap.dedent(rest).split("\n"))
                    lines.append(f"    {name + ': ' if name else ''}{first}" + (f"\n{rest}" if rest else ""))
                sections.append("\n".join(lines))
        return "\n\n".join(s for s in sections if s)

    # Stubs --------------------------------------------------------------------------------------

    def callable_lines(self, element, namespace, seen, qualified=None):
        lines = [line for line in CLASS_EXTRAS.get(qualified, "").splitlines()]
        seen |= {line.split("def ", 1)[1].split("(", 1)[0] for line in lines if "def " in line}
        siblings = {e.get("name"): e for e in core(element, "method") + core(element, "function")}
        for method in core(element, "method"):
            name = escape(method.get("shadows") or method.get("name"))
            if callable_usable(method) and name not in seen:
                seen.add(name)
                overloads = self.async_lines(method, namespace, siblings, "self", None)
                lines += with_doc([f"    {line}" for line in overloads or [self.signature(method, namespace, "self")]],
                                  self.callable_doc(method))
        for child in core(element, "constructor") + core(element, "function"):
            name = escape(child.get("shadows") or child.get("name"))
            if callable_usable(child) and name not in seen:
                seen.add(name)
                decorator, first = ("classmethod", "cls") if tag(child) == "constructor" else ("staticmethod", None)
                overloads = self.async_lines(child, namespace, siblings, first, decorator)
                lines += with_doc([f"    {line}" for line in overloads or [f"@{decorator}", self.signature(child, namespace, first)]],
                                  self.callable_doc(child))
        for vfunc in core(element, "virtual-method"):
            name = f"do_{escape(vfunc.get('name'))}"
            if callable_usable(vfunc) and name not in seen:
                seen.add(name)
                text = self.callable_doc(vfunc)
                invoker = siblings.get(vfunc.get("invoker") or "")
                if invoker is not None and text == self.callable_doc(invoker):
                    text = f"The virtual method behind {escape(invoker.get('name'))}(), for subclasses to override."
                lines += with_doc([f"    {self.signature(vfunc, namespace, 'self', prefix='do_')}"], text)
        return lines

    def property_type(self, prop, namespace):
        annotation = self.py_type(prop, namespace)
        return f"{annotation} | None" if nullable(prop) and annotation not in ("_Any", "None") else annotation

    def stub_bases(self, info):
        """The qualified names of a class's bases in its stub: its parent and the interfaces it adds."""
        if info.kind == "interface":
            return ["GObject.GInterface"]
        bases = [info.parent] if info.parent else []
        inherited = {c.qualified for c in self.ancestors(self.classes[info.parent])} if info.parent in self.classes else set()
        return bases + [i for i in info.interfaces if i not in inherited and i in self.classes]

    def stub_mro(self, qualified):
        """The qualified names of the classes in a stub class's MRO, which Python works out from empty classes."""
        def empty(name):
            if name not in self.empty_classes:
                bases = self.stub_bases(self.classes[name]) if name in self.classes else []
                self.empty_classes[name] = type(name, tuple(empty(b) for b in bases) or (object,), {})
            return self.empty_classes[name]
        return [c.__name__ for c in empty(qualified).__mro__[:-1]]

    def member_names(self, info):
        """The public names a class's stub defines, apart from props."""
        if info.qualified not in self.members:
            lines = self.class_stub(info, info.namespace)
            start = next(i for i, line in enumerate(lines) if line.startswith(f"class {info.name}"))
            self.members[info.qualified] = {m.group(1) for line in lines[start:]
                                            if (m := re.match(r"    (?:def )?([a-zA-Z]\w*)\s*[:(=]", line))} - {"props"}
        return self.members[info.qualified]

    def aliases(self, info, namespace, seen):
        """Lines that settle a name two unrelated bases define differently, as Python does: the first in the MRO
        wins. Otherwise type checkers reject a subclass with another base, such as a mixin."""
        mro = [self.classes[name] for name in self.stub_mro(info.qualified)[1:] if name in self.classes]
        lines, found = [], set(seen)
        for index, first in enumerate(mro):
            for name in sorted(self.member_names(first) - found):
                found.add(name)
                if any(name in self.member_names(later) and later.qualified not in self.stub_mro(first.qualified)
                       for later in mro[index + 1:]):
                    owner = first.qualified.removeprefix(f"{namespace}.")
                    lines.append(f"    {name} = {owner}.{name}  # type: ignore[assignment]")
                    seen.add(name)
        return lines

    def class_stub(self, info, namespace):
        short = info.name
        bases = [b.removeprefix(f"{namespace}.") for b in BASES.get(info.qualified, self.stub_bases(info))]
        props_base = ""
        if info.parent:
            target, name = info.parent.split(".", 1)
            props_base = f"(_{name}Props)" if target == namespace else f"({info.parent.split('.')[0]}._{name}Props)"
        own_props = {}
        for current in [info] + [self.classes[i] for i in info.interfaces if i in self.classes]:
            for prop in current.properties:
                own_props.setdefault(prop.get("name").replace("-", "_"), self.property_type(prop, current.namespace)
                                     if current.namespace == namespace else "_Any")
        lines = [f"class {short}({', '.join(bases)}):" if bases else f"class {short}:"]
        lines += docstring(self.doc(info.element), "    ")
        if info.qualified == "GObject.Object":
            lines.append(OBJECT_EXTRAS.rstrip("\n"))
        if info.kind != "interface":
            lines.append(f"    props: _{short}Props  # type: ignore[assignment]")

        seen = {"props"}
        if info.qualified == "GObject.Object":
            seen |= {"get_property", "set_property", "freeze_notify", "thaw_notify", "connect", "emit", "disconnect"}
        if info.kind == "class" and "def __init__" not in CLASS_EXTRAS.get(info.qualified, ""):
            constructor = self.constructor_properties(info, namespace)
            if constructor:
                seen.add("__init__")
                # Gst.Device has a property called properties.
                rest = "other_properties" if any(p.startswith("properties:") for p in constructor) else "properties"
                lines.append(f"    def __init__(self, *, {', '.join(constructor)}, **{rest}: _Any) -> None: ...")
        clashes = self.signal_clashes(info)
        signal_owners = {name: c for c in reversed(self.ancestors(info)) for name in c.signals}
        method_owners = {name: c for c in reversed(self.ancestors(info)) for name in c.methods}
        for name, signal in info.signals.items():
            attribute = escape(name)
            seen.add(attribute)
            if name in clashes:
                continue
            kind = self.signal_type(signal, short, namespace)
            lines.append(f"    @property")
            lines += with_doc([f"    def {attribute}(self) -> _BoundSignal[{kind}]: ..."], self.doc(signal))
        for name in sorted(clashes):
            attribute = escape(name)
            if name not in info.signals and name not in info.methods:
                continue
            seen.add(attribute)
            owner = signal_owners[name]
            kind = self.signal_type(owner.signals[name], short, owner.namespace) if owner.namespace == namespace else "_Callable[..., _Any]"
            method = method_owners[name]
            method_kind = self.bound_method_type(method.methods[name], namespace) if method.namespace == namespace else "_Callable[..., _Any]"
            if self.paths.get(method.methods[name]) in OVERRIDE_SIGNATURES:
                method_kind = override_type(OVERRIDE_SIGNATURES[self.paths[method.methods[name]]])
            lines.append("    @property")
            text = self.callable_doc(info.methods[name]) if name in info.methods else self.doc(info.signals[name])
            lines += with_doc([f"    def {attribute}(self) -> _SignalMethod[{kind}, {method_kind}]: ..."], text)
        lines += self.callable_lines(info.element, namespace, seen, info.qualified)
        lines += self.class_struct_lines(info, namespace, seen)
        # A property's doc goes on its attribute, or failing that on its entry in props.
        docs = {prop.get("name").replace("-", "_"): self.doc(prop) for prop in info.properties}
        lines += self.attribute_properties(info, own_props, seen, docs)
        if info.kind == "class":
            lines += self.aliases(info, namespace, seen)
        props = [f"class _{short}Props{props_base}:"]
        for name, annotation in own_props.items():
            props += [f"    {escape(name)}: {annotation}", *docstring(docs.get(name), "    ")]
        return props + (["    ..."] if not own_props else []) + [""] + lines

    def class_struct_lines(self, info, namespace, seen):
        """Methods of the class struct, such as GtkWidgetClass's, which PyGObject puts on the class."""
        struct = info.element.get(f"{{{GLIB}}}type-struct")
        record = next((e for e in self.roots[namespace] if tag(e) == "record" and e.get("name") == struct), None)
        lines = []
        for method in core(record, "method") if record is not None else []:
            name = escape(method.get("name"))
            if callable_usable(method) and name not in seen:
                seen.add(name)
                lines += with_doc(["    @classmethod", f"    {self.signature(method, namespace, 'cls')}"],
                                  self.callable_doc(method))
        return lines

    def attribute_properties(self, info, types, seen, docs):
        """Typed ``obj.label`` attributes, taking their docs from docs. A method or signal of the same name takes
        priority."""
        family = self.ancestors(info)
        taken = {name for c in family for name in (*c.methods, *c.signals)}
        taken |= {escape(e.get("name")) for c in family for e in core(c.element, "function") + core(c.element, "constructor")}
        lines = []
        for current in [info] + [self.classes[i] for i in info.interfaces if i in self.classes]:
            for prop in current.properties:
                name = prop.get("name").replace("-", "_")
                if name in seen or name in taken or keyword.iskeyword(name):
                    continue
                seen.add(name)
                annotation = types[name]
                if prop.get("readable", "1") != "0":
                    text = docs.pop(name, "") if current is info else ""
                    lines += ["    @property", *with_doc([f"    def {name}(self) -> {annotation}: ..."], text)]
                    if prop.get("writable") == "1" and prop.get("construct-only") != "1":
                        lines += [f"    @{name}.setter", f"    def {name}(self, value: {settable(annotation)}) -> None: ..."]
        return lines

    def bound_method_type(self, method, namespace):
        inputs, outputs, varargs = self.parameters(method, namespace)
        if varargs or any(optional for _, _, optional in inputs):
            return "_Callable[..., _Any]"
        result = method.find(f"{{{CORE}}}return-value")
        returned = self.py_type(result, namespace) if result is not None else "None"
        values = ([] if returned == "None" else [returned]) + outputs
        annotation = "None" if not values else values[0] if len(values) == 1 else f"_tuple[{', '.join(values)}]"
        return f"_Callable[[{', '.join(a for _, a, _ in inputs)}], {annotation}]"

    def constructor_properties(self, info, namespace):
        properties = {}
        for current in self.ancestors(info):
            for prop in current.properties:
                if prop.get("writable") != "1" and prop.get("construct-only") != "1":
                    continue
                name = escape(prop.get("name"))
                annotation = self.property_type(prop, current.namespace)
                if current.namespace != namespace:
                    annotation = "_Any"
                properties.setdefault(name, f"{name}: {settable(annotation)} = ...")
        return list(properties.values())

    def stub(self, namespace):
        ns = self.roots[namespace]
        imports = sorted(d for d in self.dependency_closure(namespace) if d != namespace)
        if namespace != "GObject":
            imports = sorted(set(imports) | {"GObject"})
        # GTK's class hierarchy breaks substitutability, so these two can't be avoided.
        out = ['# mypy: disable-error-code="override,misc"',
               *docstring(f"{DESCRIPTIONS[namespace]}, version {self.versions[namespace]}.\n\n"
                          "Generated by tools/generate.py from GObject Introspection data. Do not edit.", ""), "",
               "import builtins as _builtins",
               "from builtins import bool as _bool, bytes as _bytes, dict as _dict, float as _float, int as _int",
               "from builtins import int as _builtin_int, list as _list, str as _str, str as _builtin_str",
               "from builtins import tuple as _tuple",
               "import asyncio as _asyncio",
               "from collections.abc import Awaitable as _Awaitable, Callable as _Callable",
               "from collections.abc import Coroutine as _Coroutine, Iterator as _Iterator, Sequence as _Sequence",
               "from typing import Any as _Any, Generic as _Generic, TypeVar as _TypeVar, overload as _overload", "",
               "from PyLiite4 import cairo as _cairo", "",
               "from PyLiite4._runtime import BoundSignal as _BoundSignal, SignalMethod as _SignalMethod"]
        out += [f"from PyLiite4 import {name}" for name in imports]
        out += ["", "_GTypeLike = GObject.GType | _builtins.type", NAMESPACE_EXTRAS.get(namespace, "")]
        if namespace == "GObject":
            out.append(GOBJECT_EXTRAS)
        if namespace == "GLib":
            out.append(GLIB_EXTRAS)
            out.append(GLIB_FUNCTION_EXTRAS)
        if namespace == "Gtk":
            out.append(GTK_EXTRAS)
        names = set()
        for element in ns:
            kind = tag(element)
            name = element.get("name")
            if not name or element.get("introspectable", "1") == "0" and kind not in ("class",):
                continue
            if f"{namespace}.{name}" in SKIPPED or f"{namespace}.{element.get('shadows') or name}" in OVERRIDDEN:
                continue
            if kind in ("class", "interface"):
                out += self.class_stub(self.classes[f"{namespace}.{name}"], namespace)
            elif kind in ("record", "union"):
                out += self.record_stub(element, namespace)
            elif kind in ("enumeration", "bitfield"):
                out += self.enum_stub(element, namespace)
            elif kind == "callback":
                inputs, _, _ = self.parameters(element, namespace)
                result = element.find(f"{{{CORE}}}return-value")
                returned = self.py_type(result, namespace) if result is not None else "None"
                out.append(f"{name} = _Callable[..., {returned}]")
            elif kind == "alias":
                out.append(f"{name} = {self.py_type(element, namespace)}")
            elif kind == "function":
                if callable_usable(element):
                    siblings = {e.get("name"): e for e in ns if tag(e) == "function"}
                    out += with_doc(self.async_lines(element, namespace, siblings, None, None)
                                    or [self.signature(element, namespace)], self.callable_doc(element))
            elif kind == "constant":
                out.append(f"{escape(name)}: {self.py_type(element, namespace)}")
            else:
                continue
            if kind in ("callback", "alias", "constant"):
                out += docstring(self.doc(element), "")
            names.add(name)
            out.append("")
        lines = "\n".join(out).split("\n")
        if namespace == "GObject":
            lines = [line if line.startswith(DOC) else line.replace("GObject.", "") for line in lines]
        return "\n".join(line.removeprefix(DOC) for line in lines) + "\n"

    def record_stub(self, element, namespace):
        lines = [f"class {element.get('name')}:", *docstring(self.doc(element), "    ")]
        seen = set()
        body = self.callable_lines(element, namespace, seen, f"{namespace}.{element.get('name')}")
        for item in core(element, "field"):
            name = escape(item.get("name"))
            if item.get("private") != "1" and name not in seen and item.find(f"{{{CORE}}}callback") is None:
                seen.add(name)
                body.insert(0, f"    {name}: {self.py_type(item, namespace)}")
        return lines + (body or ["    ..."])

    def enum_stub(self, element, namespace):
        base = "GFlags" if tag(element) == "bitfield" else "GEnum"
        base = base if namespace == "GObject" else f"GObject.{base}"
        lines = [f"class {element.get('name')}({base}):"]
        lines += docstring(self.doc(element), "    ")
        seen = set()
        for member in core(element, "member"):
            # Members such as IOCondition.IN and Category.3D keep their spelling.
            name = member.get("name").replace("-", "_").upper()
            if name.isidentifier() and not keyword.iskeyword(name) and name not in seen:
                seen.add(name)
                lines.append(f"    {name}: {element.get('name')}")
                lines += docstring(self.doc(member), "    ")
        return lines + self.callable_lines(element, namespace, seen) if seen else lines + ["    ..."]

    def dependency_closure(self, namespace):
        result = set()
        stack = list(DEPENDENCIES.get(namespace, []))
        while stack:
            current = stack.pop()
            if current not in result:
                result.add(current)
                stack += DEPENDENCIES.get(current, [])
        return result | self.referenced_namespaces(namespace)

    def referenced_namespaces(self, namespace):
        order = self.namespaces[:self.namespaces.index(namespace)]
        return {n for n in order if n in self.dependency_closure_base(namespace)}

    def dependency_closure_base(self, namespace):
        result, stack = set(), list(DEPENDENCIES.get(namespace, []))
        while stack:
            current = stack.pop()
            if current not in result:
                result.add(current)
                stack += DEPENDENCIES.get(current, [])
        return result

    # Modules ------------------------------------------------------------------------------------

    def module(self, namespace):
        ns = self.roots[namespace]
        names = sorted({escape(e.get("shadows") or e.get("name")) for e in ns
                        if e.get("name") and tag(e) in ("class", "interface", "record", "union", "enumeration",
                                                        "bitfield", "function", "constant")
                        and e.get("introspectable", "1") != "0" and not e.get("shadowed-by") and f"{namespace}.{e.get('name')}" not in SKIPPED})
        deps = sorted(self.dependency_closure_base(namespace))
        lines = ['"""Generated by tools/generate.py. Do not edit."""', "", "from PyLiite4 import _runtime"]
        if deps:
            lines.append(f"from PyLiite4 import {', '.join(deps)}  # noqa: F401")
        lines += ["", f"_runtime.bind(globals(), {namespace!r}, {self.versions[namespace]!r}, ("]
        lines += [f"    {name!r}," for name in names]
        lines += ["), {"]
        lines += [f"    {k!r}: {v!r}," for k, v in self.signal_methods(namespace).items()]
        lines += ["})", f"del _runtime" + (f", {', '.join(deps)}" if deps else ""), ""]
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gir-dir", type=Path, action="append",
                        help="where to find GIR files; repeat to search several, in order (default: /usr/share/gir-1.0)")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent.parent / "src" / "PyLiite4")
    wheel = parser.add_mutually_exclusive_group()
    wheel.add_argument("--addons", action="store_true",
                       help="write the PyLiite4-Addons namespaces, such as WebKit, instead of PyLiite4's")
    wheel.add_argument("--poppler", action="store_true", help="write the PyLiite4-Poppler namespace")
    args = parser.parse_args()
    extra = ADDON_NAMESPACES if args.addons else POPPLER_NAMESPACES if args.poppler else []
    generator = Generator(args.gir_dir or [Path("/usr/share/gir-1.0")], extra)
    for namespace in extra or NAMESPACES:
        (args.output / f"{namespace}.py").write_text(generator.module(namespace))
        (args.output / f"{namespace}.pyi").write_text(generator.stub(namespace))
        print(f"{namespace} {generator.versions[namespace]}: "
              f"{sum(1 for c in generator.classes.values() if c.namespace == namespace)} classes/interfaces")


if __name__ == "__main__":
    main()
