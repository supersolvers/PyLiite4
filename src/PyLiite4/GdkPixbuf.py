"""Load the PyGObject namespace and attach signal helpers."""

from PyLiite4 import _runtime
from PyLiite4 import GLib, GObject, Gio  # noqa: F401

_runtime.bind(globals(), 'GdkPixbuf', '2.0', (), {
})
del _runtime, GLib, GObject, Gio
