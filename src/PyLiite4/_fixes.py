"""Corrections to PyGObject and to GIR annotations, applied as each namespace is loaded.

Each fix replaces something that crashes, corrupts memory or can't be called from Python with a version that does
what the C API does.
"""

from __future__ import annotations

import math
from typing import Any

from gi.repository import GObject  # type: ignore


def apply(name: str, module: Any) -> None:
    fix = FIXES.get(name)
    if fix is not None and not getattr(module, "_pyliite4_fixed", False):
        fix(module)
        module._pyliite4_fixed = True


def fix_asyncio(loop: Any) -> None:
    """Let asyncio cancel a task that awaits one of Gio's async methods.

    asyncio's Task.cancel() calls cancel(msg) on what the task awaits, and PyGObject's awaitable, gi._gi.Async, takes
    no argument, so cancelling raises TypeError instead; and once Gio's operation is cancelled, the coroutine would get
    Gio's "cancelled" GLib.Error rather than CancelledError. GLib's loop makes its tasks as gi.events.GLibTask, on
    asyncio's C Task, which keeps cancelling's state out of reach; this gives the loop a task on asyncio's Python Task
    instead, which cancels such an awaitable the way it accepts and then raises CancelledError in the coroutine, as
    cancelling does.
    """
    import asyncio

    from gi import _gi  # type: ignore
    from gi.repository import GLib

    class GLibTask(asyncio.tasks._PyTask):  # type: ignore[name-defined, misc]
        """gi.events.GLibTask, cancellable while it awaits Gio."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._glib_idle_priority = GLib.PRIORITY_DEFAULT

        def set_priority(self, priority: int) -> None:
            """Set the GLib priority used to iterate the task's coroutine."""
            self._glib_idle_priority = priority

        def get_priority(self) -> int:
            """Get the GLib priority used to iterate the task's coroutine."""
            return int(self._glib_idle_priority)

        def cancel(self, msg: Any = None) -> bool:
            waiter = self._fut_waiter
            if not isinstance(waiter, _gi.Async):
                return bool(super().cancel(msg))
            # As asyncio's own cancel(), with the awaitable cancelled the way it accepts.
            self._log_traceback = False
            if self.done():
                return False
            # Python 3.11 and later count requests, for Task.cancelling().
            if hasattr(self, "_num_cancels_requested"):
                self._num_cancels_requested += 1
            waiter.cancel()
            self._must_cancel = True
            self._cancel_message = msg
            return True

    if not getattr(loop, "_pyliite4_tasks", False):
        loop.set_task_factory(lambda loop, coro, **kwargs: GLibTask(coro, loop=loop, **kwargs))
        loop._pyliite4_tasks = True


def _gio(Gio: Any) -> None:
    from gi.repository import GLib  # type: ignore

    # PyGObject copies `contents` into a temporary C array and frees it when the call returns, while the write is
    # still running, so the file receives freed memory. The GBytes variant keeps the data alive.
    def replace_contents_async(self: Any, contents: Any, *args: Any, **kwargs: Any) -> Any:
        data = contents if isinstance(contents, GLib.Bytes) else GLib.Bytes.new(bytes(contents))
        return self.replace_contents_bytes_async(data, *args, **kwargs)

    replace_contents_async.__doc__ = Gio.File.replace_contents_async.__doc__
    Gio.File.replace_contents_async = replace_contents_async


def _pango(Pango: Any) -> None:
    # C macros, which introspection doesn't see.
    for name, scale in (("XX_SMALL", 1 / 1.2 ** 3), ("X_SMALL", 1 / 1.2 ** 2), ("SMALL", 1 / 1.2), ("MEDIUM", 1.0),
                        ("LARGE", 1.2), ("X_LARGE", 1.2 ** 2), ("XX_LARGE", 1.2 ** 3)):
        setattr(Pango, f"SCALE_{name}", scale)

    # The introspected version corrupts the rectangles' memory; this is the C function's arithmetic.
    def extents_to_pixels(inclusive: Any = None, nearest: Any = None) -> None:
        """Convert rectangles in Pango units to pixels, in place: ``inclusive`` to the smallest pixel rectangle
        that contains it, ``nearest`` to the nearest one."""
        scale = Pango.SCALE

        def pixels(units: int) -> int:  # PANGO_PIXELS()
            return (int(units) + 512) >> 10

        if inclusive is not None:
            x, y = math.floor(inclusive.x / scale), math.floor(inclusive.y / scale)
            inclusive.width = math.ceil((inclusive.x + inclusive.width) / scale) - x
            inclusive.height = math.ceil((inclusive.y + inclusive.height) / scale) - y
            inclusive.x, inclusive.y = x, y
        if nearest is not None:
            x, y = pixels(nearest.x), pixels(nearest.y)
            nearest.width = pixels(nearest.x + nearest.width) - x
            nearest.height = pixels(nearest.y + nearest.height) - y
            nearest.x, nearest.y = x, y

    Pango.extents_to_pixels = extents_to_pixels


def _gsk(Gsk: Any) -> None:
    # GskRoundedRect isn't boxed, so the struct the init methods return is a copy whose memory is freed at once.
    # In C they return the rectangle they were called on, so return that.
    def returning_self(method: Any) -> Any:
        def init(self: Any, *args: Any) -> Any:
            method(self, *args)
            return self

        init.__name__, init.__doc__ = method.__name__, method.__doc__
        return init

    for name in ("init", "init_copy", "init_from_rect"):
        setattr(Gsk.RoundedRect, name, returning_self(getattr(Gsk.RoundedRect, name)))
    _fix_path_points(Gsk)


def _fix_path_points(Gsk: Any) -> None:
    """Make the functions that produce a GskPathPoint callable.

    They fill a caller-allocated GskPathPoint, which PyGObject can't allocate ("Could not caller allocate
    argument"). Call them through ctypes into a buffer of our own, then hand the point to Python through a GValue,
    which copies it into a proper Gsk.PathPoint. PyGObject's hash() of a boxed value is its C address.
    """
    import ctypes

    gtk = ctypes.CDLL("libgtk-4.so.1")
    gobject = ctypes.CDLL("libgobject-2.0.so.0")
    gobject.g_value_set_boxed.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    pointer, c_float, c_int = ctypes.c_void_p, ctypes.c_float, ctypes.c_int
    signatures = {
        "gsk_path_get_start_point": [pointer, pointer],
        "gsk_path_get_end_point": [pointer, pointer],
        "gsk_path_get_closest_point": [pointer, pointer, c_float, pointer, ctypes.POINTER(c_float)],
        "gsk_path_measure_get_point": [pointer, c_float, pointer],
    }
    for name, argtypes in signatures.items():
        getattr(gtk, name).argtypes = argtypes
        getattr(gtk, name).restype = c_int

    def to_python(address: int) -> Any:
        value = GObject.Value()
        value.init(Gsk.PathPoint.__gtype__)
        gobject.g_value_set_boxed(hash(value), address)
        return value.get_value()

    def point_buffer() -> tuple[Any, int]:
        # GskPathPoint is 64 bytes, aligned like a graphene_vec4_t.
        buffer = ctypes.create_string_buffer(64 + 16)
        return buffer, (ctypes.addressof(buffer) + 15) & ~15

    def call(function: Any, *args: Any) -> tuple[bool, Any]:
        _buffer, address = point_buffer()
        return (True, to_python(address)) if function(*args, address) else (False, None)

    def get_start_point(self: Any) -> tuple[bool, Any]:
        """Return (True, the point at the start of the path), or (False, None) if the path is empty."""
        return call(gtk.gsk_path_get_start_point, hash(self))

    def get_end_point(self: Any) -> tuple[bool, Any]:
        """Return (True, the point at the end of the path), or (False, None) if the path is empty."""
        return call(gtk.gsk_path_get_end_point, hash(self))

    def get_closest_point(self: Any, point: Any, threshold: float) -> tuple[bool, Any, float]:
        """Return (True, the point on the path closest to ``point``, its distance), or (False, None, 0.0) if no
        point is within ``threshold``."""
        distance = c_float()
        _buffer, address = point_buffer()
        if not gtk.gsk_path_get_closest_point(hash(self), hash(point), threshold, address, ctypes.byref(distance)):
            return False, None, 0.0
        return True, to_python(address), distance.value

    def get_point(self: Any, distance: float) -> tuple[bool, Any]:
        """Return (True, the point ``distance`` along the path), or (False, None) if the path is empty."""
        return call(gtk.gsk_path_measure_get_point, hash(self), distance)

    Gsk.Path.get_start_point = get_start_point
    Gsk.Path.get_end_point = get_end_point
    Gsk.Path.get_closest_point = get_closest_point
    Gsk.PathMeasure.get_point = get_point


def _gtk(Gtk: Any) -> None:
    _fix_builder_scope(Gtk)

    # The callbacks are annotated scope="call", so PyGObject frees them as soon as new() returns, and the first
    # layout crashes. A layout manager subclass calls them for as long as it lives.
    class CustomLayout(Gtk.LayoutManager):
        __gtype_name__ = "PyLiite4CustomLayout"

        def __init__(self, request_mode: Any, measure: Any, allocate: Any) -> None:
            super().__init__()
            self._request_mode, self._measure, self._allocate = request_mode, measure, allocate

        def do_get_request_mode(self, widget: Any) -> Any:
            return self._request_mode(widget) if self._request_mode else Gtk.SizeRequestMode.CONSTANT_SIZE

        def do_measure(self, widget: Any, orientation: Any, for_size: int) -> Any:
            return self._measure(widget, orientation, for_size)

        def do_allocate(self, widget: Any, width: int, height: int, baseline: int) -> None:
            self._allocate(widget, width, height, baseline)

    Gtk.CustomLayout.new = staticmethod(lambda request_mode, measure, allocate:
                                        CustomLayout(request_mode, measure, allocate))

    # The value is an out argument that must be initialised, which PyGObject can't do; return it instead.
    evaluate = Gtk.Expression.evaluate

    def expression_evaluate(self: Any, this: Any = None, value: Any = None) -> Any:
        """Evaluate the expression for ``this`` and return the result, or None if it can't be evaluated. Passing
        a ``GObject.Value`` fills it and returns whether that worked, as in C."""
        if value is not None:
            return evaluate(self, this, value)
        result = GObject.Value()
        return result.get_value() if evaluate(self, this, result) else None

    Gtk.Expression.evaluate = expression_evaluate

    # NULL clears these in C, but their arguments aren't annotated as nullable.
    set_from_gicon = Gtk.Image.set_from_gicon
    Gtk.Image.set_from_gicon = lambda self, icon: self.clear() if icon is None else set_from_gicon(self, icon)

    # GTK's test accessibility backend (GTK_A11Y=test) has no announce function, which announce() calls anyway, so
    # it crashes. Under that backend, keep the announcements instead, for tests to read (PyLiite4.testing does).
    announce = Gtk.Accessible.announce

    def accessible_announce(self: Any, message: str, priority: Any) -> None:
        context = self.get_at_context()
        if context is not None and type(context).__name__ == "GtkTestATContext":
            announcements.append((message, priority))
            return
        announce(self, message, priority)

    Gtk.Accessible.announce = accessible_announce


# Announcements made under GTK's test accessibility backend, as (message, priority), oldest first.
announcements: list[tuple[str, Any]] = []


def _fix_builder_scope(Gtk: Any) -> None:
    """Connect signals from .ui files the way GTK's own C scope does.

    PyGObject's scope refuses swapped handlers, drops a connect object that is falsy (an empty list model), and
    passes the object where the emitter belongs. In GTK, a handler with ``object=`` gets the object as its last
    argument, or, when swapped (the default whenever ``object=`` is given), as its first argument with the emitter
    last.
    """
    from gi import _gtktemplate  # type: ignore
    from gi.overrides import Gtk as GtkOverrides  # type: ignore

    def create_closure(self: Any, builder: Any, func_name: str, flags: Any, obj: Any) -> Any:
        if not self._scope_object:
            current_object = builder.get_current_object()
            if func_name not in current_object.__gtktemplate_methods__:
                return None
            current_object.__gtktemplate_handlers__.add(func_name)
            handler_name = current_object.__gtktemplate_methods__[func_name]
        else:
            current_object = self._scope_object
            handler_name = func_name
        handler, bound = _gtktemplate._extract_handler_and_args(current_object, handler_name)
        swapped = bool(flags & Gtk.BuilderClosureFlags.SWAPPED)

        def closure(*args: Any) -> Any:
            if swapped:
                return handler(*bound, obj, *args[1:], args[0])
            if obj is not None:
                return handler(*bound, *args, obj)
            return handler(*bound, *args)

        closure.__gtk_template__ = True  # type: ignore[attr-defined]
        return closure

    if getattr(_gtktemplate.define_builder_scope, "_pyliite4", False):
        return
    # PyGObject binds virtual methods when a class is registered, so the fix needs a subclass of its own. Templates
    # ask define_builder_scope() for a scope class each time; one class serves them all.
    class BuilderScope(GtkOverrides.Builder.BuilderScope):
        __gtype_name__ = "PyLiite4BuilderScope"
        do_create_closure = create_closure

    def define_builder_scope() -> Any:
        return BuilderScope

    define_builder_scope._pyliite4 = True  # type: ignore[attr-defined]
    _gtktemplate.define_builder_scope = define_builder_scope
    GtkOverrides.Builder.BuilderScope = BuilderScope


FIXES = {"Gio": _gio, "Pango": _pango, "Gsk": _gsk, "Gtk": _gtk}
