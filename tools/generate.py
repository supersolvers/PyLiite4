#!/usr/bin/env python3
"""Generate the PyLiite4 namespace modules and stubs from GObject Introspection data.

Usage: tools/generate.py [--gir-dir DIR ...] [--output DIR]

The checked-in modules come from this machine's GIR files where it has them, and the bundled stack's for the rest:

    tools/generate.py --gir-dir /usr/share/gir-1.0 --gir-dir ~/.cache/pyliite4-manylinux/opt/gtk/share/gir-1.0
"""

import argparse
import keyword
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
         "HarfBuzz": "HarfBuzz-0.0", "PangoCairo": "PangoCairo-1.0", "Rsvg": "Rsvg-2.0"}
DEPENDENCIES = {"GObject": ["GLib"], "Gio": ["GLib", "GObject"], "GdkPixbuf": ["GObject", "Gio"],
                "Pango": ["GObject", "Gio", "HarfBuzz"], "Graphene": ["GObject"],
                "Gdk": ["Gio", "GdkPixbuf", "Pango"], "Gsk": ["Gdk", "Graphene"],
                "Gtk": ["Gdk", "Gsk"], "Adw": ["Gtk"], "GtkSource": ["Gtk"], "Soup": ["Gio"], "Xdp": ["Gio"],
                "XdpGtk4": ["Xdp", "Gtk"], "Gst": ["GObject"], "GstBase": ["Gst"], "GstAudio": ["GstBase"],
                "GstVideo": ["GstBase"], "GstPbutils": ["GstAudio", "GstVideo"], "GstApp": ["GstBase"],
                "HarfBuzz": ["GObject"], "PangoCairo": ["Pango"], "Rsvg": ["GdkPixbuf", "Gio"]}

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

class GInterface: ...

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
class Template:
    def __init__(self, *, string: _Any = ..., filename: _str = ..., resource_path: _str = ...) -> None: ...
    def __call__(self, cls: _Any) -> _Any: ...
    @staticmethod
    def Child(name: _str = ..., internal: _bool = ...) -> _Any: ...
    @staticmethod
    def Callback(name: _str = ...) -> _Any: ...
    from_file: _Any
    from_resource: _Any
    from_string: _Any
"""


def tag(element):
    return element.tag.rsplit("}", 1)[-1]


def core(element, name):
    return element.findall(f"{{{CORE}}}{name}")


def escape(name):
    name = name.replace("-", "_")
    # PyGObject still treats "print" as a keyword, from Python 2.
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
    def __init__(self, gir_dirs):
        self.roots = {}
        self.versions = {}
        for namespace in NAMESPACES:
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
        return self.reference(name, namespace)

    def parameters(self, element, namespace):
        """Split a callable into visible (in, out) parameters, as PyGObject presents them."""
        container = element.find(f"{{{CORE}}}parameters")
        if container is None:
            return [], [], False
        params = core(container, "parameter")
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
        inputs, outputs, varargs = self.parameters(element, namespace)
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
                lines += [f"    {line}" for line in overloads or [self.signature(method, namespace, "self")]]
        for child in core(element, "constructor") + core(element, "function"):
            name = escape(child.get("shadows") or child.get("name"))
            if callable_usable(child) and name not in seen:
                seen.add(name)
                decorator, first = ("classmethod", "cls") if tag(child) == "constructor" else ("staticmethod", None)
                overloads = self.async_lines(child, namespace, siblings, first, decorator)
                lines += [f"    {line}" for line in overloads or [f"@{decorator}", self.signature(child, namespace, first)]]
        for vfunc in core(element, "virtual-method"):
            name = f"do_{escape(vfunc.get('name'))}"
            if callable_usable(vfunc) and name not in seen:
                seen.add(name)
                lines.append(f"    {self.signature(vfunc, namespace, 'self', prefix='do_')}")
        return lines

    def property_type(self, prop, namespace):
        annotation = self.py_type(prop, namespace)
        return f"{annotation} | None" if nullable(prop) and annotation not in ("_Any", "None") else annotation

    def class_stub(self, info, namespace):
        short = info.name
        bases = []
        if info.kind == "interface":
            bases.append("GObject.GInterface" if namespace != "GObject" else "GInterface")
        elif info.parent:
            target, name = info.parent.split(".", 1)
            bases.append(name if target == namespace else info.parent)
        if info.parent:
            inherited = {c.qualified for c in self.ancestors(self.classes[info.parent])} if info.parent in self.classes else set()
        else:
            inherited = set()
        for interface in info.interfaces:
            if interface in inherited or interface not in self.classes:
                continue
            target, name = interface.split(".", 1)
            bases.append(name if target == namespace else interface)
        bases = [b.removeprefix(f"{namespace}.") for b in BASES.get(info.qualified, bases)]
        props_base = ""
        if info.parent:
            target, name = info.parent.split(".", 1)
            props_base = f"(_{name}Props)" if target == namespace else f"({info.parent.split('.')[0]}._{name}Props)"
        lines = [f"class _{short}Props{props_base}:"]
        own_props = {}
        for current in [info] + [self.classes[i] for i in info.interfaces if i in self.classes]:
            for prop in current.properties:
                own_props.setdefault(prop.get("name").replace("-", "_"), self.property_type(prop, current.namespace)
                                     if current.namespace == namespace else "_Any")
        lines += [f"    {escape(k)}: {v}" for k, v in own_props.items()] or ["    ..."]
        lines.append("")

        lines.append(f"class {short}({', '.join(bases)}):" if bases else f"class {short}:")
        if info.qualified == "GObject.Object":
            lines.append(OBJECT_EXTRAS.rstrip("\n"))
        lines.append(f"    props: _{short}Props  # type: ignore[assignment]")

        seen = {"props"}
        if info.qualified == "GObject.Object":
            seen |= {"get_property", "set_property", "freeze_notify", "thaw_notify", "connect", "emit", "disconnect"}
        if info.kind == "class" and "def __init__" not in CLASS_EXTRAS.get(info.qualified, ""):
            constructor = self.constructor_properties(info, namespace)
            if constructor:
                seen.add("__init__")
                lines.append(f"    def __init__(self, *, {', '.join(constructor)}, **properties: _Any) -> None: ...")
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
            lines.append(f"    def {attribute}(self) -> _BoundSignal[{kind}]: ...")
        for name in sorted(clashes):
            attribute = escape(name)
            if name not in info.signals and name not in info.methods:
                continue
            seen.add(attribute)
            owner = signal_owners[name]
            kind = self.signal_type(owner.signals[name], short, owner.namespace) if owner.namespace == namespace else "_Callable[..., _Any]"
            method = method_owners[name]
            method_kind = self.bound_method_type(method.methods[name], namespace) if method.namespace == namespace else "_Callable[..., _Any]"
            lines.append("    @property")
            lines.append(f"    def {attribute}(self) -> _SignalMethod[{kind}, {method_kind}]: ...")
        lines += self.callable_lines(info.element, namespace, seen, info.qualified)
        lines += self.class_struct_lines(info, namespace, seen)
        lines += self.attribute_properties(info, own_props, seen)
        return lines

    def class_struct_lines(self, info, namespace, seen):
        """Methods of the class struct, such as GtkWidgetClass's, which PyGObject puts on the class."""
        struct = info.element.get(f"{{{GLIB}}}type-struct")
        record = next((e for e in self.roots[namespace] if tag(e) == "record" and e.get("name") == struct), None)
        lines = []
        for method in core(record, "method") if record is not None else []:
            name = escape(method.get("name"))
            if callable_usable(method) and name not in seen:
                seen.add(name)
                lines += ["    @classmethod", f"    {self.signature(method, namespace, 'cls')}"]
        return lines

    def attribute_properties(self, info, types, seen):
        """Typed ``obj.label`` attributes. A method or signal of the same name takes priority."""
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
                    lines += ["    @property", f"    def {name}(self) -> {annotation}: ..."]
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
               '"""Generated by tools/generate.py. Do not edit."""', "",
               "import builtins as _builtins",
               "from builtins import bool as _bool, bytes as _bytes, dict as _dict, float as _float, int as _int",
               "from builtins import int as _builtin_int, list as _list, str as _str, str as _builtin_str",
               "from builtins import tuple as _tuple",
               "import asyncio as _asyncio",
               "from collections.abc import Awaitable as _Awaitable, Callable as _Callable",
               "from collections.abc import Coroutine as _Coroutine, Iterator as _Iterator",
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
                    out += self.async_lines(element, namespace, siblings, None, None) or [self.signature(element, namespace)]
            elif kind == "constant":
                out.append(f"{escape(name)}: {self.py_type(element, namespace)}")
            else:
                continue
            names.add(name)
            out.append("")
        text = "\n".join(out) + "\n"
        return text.replace("GObject.", "") if namespace == "GObject" else text

    def record_stub(self, element, namespace):
        lines = [f"class {element.get('name')}:"]
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
        seen = set()
        for member in core(element, "member"):
            # Members such as IOCondition.IN and Category.3D keep their spelling.
            name = member.get("name").replace("-", "_").upper()
            if name.isidentifier() and not keyword.iskeyword(name) and name not in seen:
                seen.add(name)
                lines.append(f"    {name}: {element.get('name')}")
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
        order = NAMESPACES[:NAMESPACES.index(namespace)]
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
    args = parser.parse_args()
    generator = Generator(args.gir_dir or [Path("/usr/share/gir-1.0")])
    for namespace in NAMESPACES:
        (args.output / f"{namespace}.py").write_text(generator.module(namespace))
        (args.output / f"{namespace}.pyi").write_text(generator.stub(namespace))
        print(f"{namespace} {generator.versions[namespace]}: "
              f"{sum(1 for c in generator.classes.values() if c.namespace == namespace)} classes/interfaces")


if __name__ == "__main__":
    main()
