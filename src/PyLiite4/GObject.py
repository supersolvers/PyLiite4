"""Load the PyGObject namespace and attach signal helpers."""

from PyLiite4 import _runtime
from PyLiite4 import GLib  # noqa: F401

_runtime.bind(globals(), 'GObject', '2.0', (), {
    'Object': ('notify',),
})
del _runtime, GLib
