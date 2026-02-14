"""Load the PyGObject namespace and attach signal helpers."""

from PyLiite4 import _runtime

_runtime.bind(globals(), 'GLib', '2.0', (), {
})
del _runtime
