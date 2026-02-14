"""Load the PyGObject namespace and attach signal helpers."""

from PyLiite4 import _runtime
from PyLiite4 import GLib, GObject, Gdk, GdkPixbuf, Gio, Graphene, Pango  # noqa: F401

_runtime.bind(globals(), 'Gsk', '4.0', (), {
})
del _runtime, GLib, GObject, Gdk, GdkPixbuf, Gio, Graphene, Pango
