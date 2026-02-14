"""Load the PyGObject namespace and attach signal helpers."""

from PyLiite4 import _runtime
from PyLiite4 import GLib, GObject, Gdk, GdkPixbuf, Gio, Graphene, Gsk, Gtk, Pango  # noqa: F401

_runtime.bind(globals(), 'Adw', '1', (), {
    'ActionRow': ('activate',),
    'MessageDialog': ('response',),
    'SplitButton': ('activate',),
    'TabButton': ('activate',),
    'TabView': ('close_page',),
})
del _runtime, GLib, GObject, Gdk, GdkPixbuf, Gio, Graphene, Gsk, Gtk, Pango
