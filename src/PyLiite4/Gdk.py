"""Load the PyGObject namespace and attach signal helpers."""

from PyLiite4 import _runtime
from PyLiite4 import GLib, GObject, GdkPixbuf, Gio, Pango  # noqa: F401

_runtime.bind(globals(), 'Gdk', '4.0', (), {
    'ContentProvider': ('content_changed',),
    'Paintable': ('invalidate_contents', 'invalidate_size'),
})
del _runtime, GLib, GObject, GdkPixbuf, Gio, Pango
