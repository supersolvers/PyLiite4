"""Signal objects, and the glue between generated modules and PyGObject.

Classes are PyGObject's own, extended in place rather than subclassed. Objects
that GTK creates itself, such as those from Gtk.Builder, therefore get the same
API, and existing PyGObject code keeps working.
"""

from __future__ import annotations

import asyncio
import inspect
import keyword
import weakref
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, Generic, TypeVar

import gi  # type: ignore

from gi.repository import GObject  # type: ignore

from PyLiite4 import _bundle, _fixes

F = TypeVar("F", bound=Callable[..., Any])
M = TypeVar("M", bound=Callable[..., Any])

_HANDLERS = "_pyliite4_handlers"


class BoundSignal(Generic[F]):
    """A signal of one object: ``button.clicked.connect(callback)``.

    As in GTK, callbacks receive the emitting object as their first argument.
    Use ``obj.notify["label"]`` to select a signal detail.

    As in PySide6, a bound method doesn't keep its object alive: the connection
    ends when the object goes away. Other callables are held strongly.
    """

    __slots__ = ("instance", "name", "detail")

    def __init__(self, instance: GObject.Object, name: str, detail: str | None = None) -> None:
        self.instance = instance
        self.name = name
        self.detail = detail

    @property
    def _full_name(self) -> str:
        return f"{self.name}::{self.detail}" if self.detail else self.name

    def __getitem__(self, detail: str) -> BoundSignal[F]:
        return BoundSignal(self.instance, self.name, detail)

    def __repr__(self) -> str:
        return f"<signal {self._full_name!r} of {self.instance!r}>"

    def connect(self, callback: F, *user_data: Any, after: bool = False) -> int:
        """Connect a callback and return its handler id."""
        connect = self.instance.connect_after if after else self.instance.connect
        if not inspect.ismethod(callback):
            handler = connect(self._full_name, callback, *user_data)
            self._records().append((self._full_name, lambda: callback, handler))
            return handler

        receiver = callback.__self__
        function = callback.__func__
        sender = GObject.Object.weak_ref(self.instance, lambda: None)
        handler_box: list[int] = []

        def receiver_gone(*_: Any) -> None:
            instance = sender()
            if instance is not None and handler_box:
                BoundSignal(instance, self.name, self.detail)._forget(handler_box[0])

        method: Callable[[], Any]
        if isinstance(receiver, GObject.Object):
            # PyGObject can replace a GObject's Python wrapper during its life,
            # so only a reference to the GObject itself tracks it reliably.
            receiver_ref = receiver.weak_ref(receiver_gone)

            def method() -> Any:
                target = receiver_ref()
                return None if target is None else function.__get__(target)
        else:
            method = weakref.WeakMethod(callback, receiver_gone)

        def relay(*args: Any) -> Any:
            target = method()
            return None if target is None else target(*args)

        handler = connect(self._full_name, relay, *user_data)
        handler_box.append(handler)
        self._records().append((self._full_name, method, handler))
        return handler

    def disconnect(self, target: F | int) -> None:
        """Disconnect by handler id, or every connection of a callback."""
        records = self._records()
        if isinstance(target, int):
            self._forget(target)
            return
        matching = [r for r in records if r[0] == self._full_name and r[1]() == target]
        if not matching:
            raise ValueError(f"{target!r} is not connected to {self._full_name!r}")
        for record in matching:
            self._forget(record[2])

    def emit(self, *args: Any) -> Any:
        return self.instance.emit(self._full_name, *args)

    @contextmanager
    def blocked(self, handler: int) -> Iterator[None]:
        """Temporarily stop one handler from running."""
        GObject.signal_handler_block(self.instance, handler)
        try:
            yield
        finally:
            GObject.signal_handler_unblock(self.instance, handler)

    def _forget(self, handler: int) -> None:
        GObject.signal_handler_disconnect(self.instance, handler)
        records = self._records()
        records[:] = [r for r in records if r[2] != handler]

    def _records(self) -> list[tuple[str, Any, int]]:
        try:
            return getattr(self.instance, _HANDLERS)
        except AttributeError:
            records: list[tuple[str, Any, int]] = []
            setattr(self.instance, _HANDLERS, records)
            return records


class SignalMethod(BoundSignal[F], Generic[F, M]):
    """A name that is both: ``widget.show()`` and ``widget.show.connect(...)``."""

    __slots__ = ("_method",)

    def __init__(self, instance: GObject.Object, name: str, method: Any) -> None:
        super().__init__(instance, name)
        self._method = method

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._method(*args, **kwargs)


class _SignalMethodDescriptor:
    def __init__(self, name: str, function: Any) -> None:
        self.name = name
        self.function = function
        self.__doc__ = getattr(function, "__doc__", None)

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        if instance is None:
            return self.function
        return SignalMethod(instance, self.name, self.function.__get__(instance, owner))


class Signal(GObject.Signal):
    """Declare a signal on a GObject subclass: ``changed = Signal(str)``."""

    def __new__(cls, *types: Any, name: str = "", **kwargs: Any) -> Signal:
        return str.__new__(cls, name)

    def __init__(self, *types: Any, name: str = "", arg_types: Any = None, **kwargs: Any) -> None:
        super().__init__(name=name, arg_types=tuple(types) or arg_types or (), **kwargs)

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        if instance is None:
            return self
        return BoundSignal(instance, self.name)


Property = GObject.Property


_property_tables: dict[type, dict[str, Any]] = {}


def _properties(cls: type) -> dict[str, Any]:
    table = _property_tables.get(cls)
    if table is None:
        table = {spec.name.replace("-", "_"): spec for spec in GObject.list_properties(cls)}
        _property_tables[cls] = table
    return table


def _object_getattr(self: GObject.Object, name: str) -> Any:
    # Only reached when normal lookup fails, so methods and Python attributes win.
    if not name.startswith("_"):
        if GObject.signal_lookup(name.replace("_", "-"), type(self).__gtype__):
            return BoundSignal(self, name.replace("_", "-"))
        spec = _properties(type(self)).get(name)
        if spec is not None:
            if not spec.flags & GObject.ParamFlags.READABLE:
                raise AttributeError(f"property {name!r} of {type(self).__name__!r} is write-only")
            return self.get_property(spec.name)
    raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")


# PyGObject's own version keeps the wrapper alive as long as the GObject once it has attributes.
_gobject_setattr = GObject.Object.__setattr__


def _object_setattr(self: GObject.Object, name: str, value: Any) -> None:
    if not name.startswith("_") and not hasattr(type(self), name) and name not in self.__dict__:
        spec = _properties(type(self)).get(name)
        if spec is not None:
            if not spec.flags & GObject.ParamFlags.WRITABLE or spec.flags & GObject.ParamFlags.CONSTRUCT_ONLY:
                raise AttributeError(f"property {name!r} of {type(self).__name__!r} can't be set")
            self.set_property(spec.name, value)
            return
    _gobject_setattr(self, name, value)


GObject.Object.__getattr__ = _object_getattr
GObject.Object.__setattr__ = _object_setattr


def _class_attribute(cls: type, name: str) -> Any:
    for base in cls.__mro__:
        if name in base.__dict__:
            value = base.__dict__[name]
            return value.function if isinstance(value, _SignalMethodDescriptor) else value
    return None


def bind(namespace: dict[str, Any], gi_name: str, version: str, names: tuple[str, ...],
         signal_methods: dict[str, tuple[str, ...]]) -> None:
    """Make a generated module a view of a PyGObject namespace."""
    gi.require_version(gi_name, version)
    module = getattr(__import__("gi.repository", fromlist=[gi_name]), gi_name)
    # Libraries set their translation directory when they load.
    _bundle.bind_translations()
    _fixes.apply(gi_name, module)

    for class_name, attributes in signal_methods.items():
        cls = getattr(module, class_name, None)
        for attribute in attributes:
            function = _class_attribute(cls, attribute) if cls else None
            if callable(function):
                setattr(cls, attribute, _SignalMethodDescriptor(attribute.replace("_", "-"), function))

    def __getattr__(name: str) -> Any:
        try:
            return getattr(module, name)
        except NotImplementedError as error:
            # PyGObject raises this for callback types, which exist only as annotations.
            raise AttributeError(str(error)) from None

    def __dir__() -> list[str]:
        return sorted(set(names) | set(namespace))

    namespace.update(__getattr__=__getattr__, __dir__=__dir__, __all__=list(names))


def use_asyncio() -> asyncio.AbstractEventLoop:
    """Run asyncio on GLib's main loop, and return that loop.

    Call this on the main thread before ``Gio.Application.run()``. While the
    application runs, coroutines run too: start them with
    ``app.create_asyncio_task()``, and await Gio's async methods by leaving out
    the callback.
    """
    from gi.events import GLibEventLoopPolicy  # type: ignore

    loop: asyncio.AbstractEventLoop = GLibEventLoopPolicy().get_event_loop()
    return loop


def escape(name: str) -> str:
    """Spell a GIR name the way PyGObject exposes it."""
    return f"{name}_" if keyword.iskeyword(name) else name
