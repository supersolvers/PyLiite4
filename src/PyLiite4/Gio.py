"""Load the PyGObject namespace and attach signal helpers."""

from PyLiite4 import _runtime
from PyLiite4 import GLib, GObject  # noqa: F401

_runtime.bind(globals(), 'Gio', '2.0', (), {
    'ActionGroup': ('action_added', 'action_enabled_changed', 'action_removed', 'action_state_changed'),
    'AppLaunchContext': ('launch_failed',),
    'Application': ('activate', 'open'),
    'DBusAuthObserver': ('allow_mechanism', 'authorize_authenticated_peer'),
    'ListModel': ('items_changed',),
    'MenuModel': ('items_changed',),
    'MountOperation': ('reply',),
    'SimpleAction': ('activate', 'change_state'),
})
del _runtime, GLib, GObject
