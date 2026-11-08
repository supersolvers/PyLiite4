"""Test GTK applications with pytest: an isolated session, fixtures, waiting, simulated input and failing on errors.

If you've used Qt's QTest or pytest-qt, this fills the same role. Enable the pytest plugin with::

    pytest --gtk

or ``gtk = true`` under ``[tool.pytest.ini_options]``. Until it is enabled the plugin does nothing, so installing
PyLiite4 doesn't change other projects' test runs. When enabled, before GTK initialises, it

- starts a private Xvfb display and D-Bus session, both stopped at the end of the test run. Windows stay off the
  desktop. The bus has no service directories, so requests from a test (including sandboxed WebKit helpers) can't
  auto-start desktop services such as portals;
- turns off portals and Wayland, records accessibility in-process (GTK's ``test`` backend, so
  ``Gtk.test_accessible_has_role()`` and its kin work), keeps settings in memory, and points the XDG config, data,
  state and runtime directories at a temporary directory, so tests don't read or write the user's own;
- fails each test that logs a GLib warning or critical, or whose callbacks raise a Python exception, as
  ``tests/run_demo.py`` does for the demos.

The helpers also work without the plugin, in any process where GTK has a display: ``wait_until``, ``wait_signal``,
``click``, ``type_text``, ``press_key``, ``find`` and ``collect_problems``.

Release long-lived objects in teardown, including windows kept in module globals. If they survive until Python
shuts down, the classes they depend on (a list model or a callback's object) may already be partly torn down.
GTK can abort at that point, so don't leave this cleanup to interpreter shutdown.

Input comes two ways:

- ``click``, ``activate``, ``type_text`` and ``press_key`` go through the signals, actions and shortcuts that real
  input ends up in. They are quick and need no display of a particular kind, but event controllers, gestures, focus
  handling and hit-testing aren't exercised.
- ``RealInput`` (``gtkbot.input``), the equivalent of ``QTest.mouseClick`` and ``QTest.keyClick``, sends real
  pointer and keyboard events through the X server's XTest extension, so they arrive as a user's would. GTK 4 has no
  API to inject events itself. It needs libXtst, and runs only on the plugin's private Xvfb unless
  ``PYLIITE4_TESTING_REAL_INPUT=1`` allows another display, since it moves that display's real pointer.
"""

from __future__ import annotations

import asyncio
import ctypes
import itertools
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import warnings
from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Any, TypeVar, overload

import pytest

if TYPE_CHECKING:
    from PyLiite4 import Gdk, GLib, GObject, Gtk
    from PyLiite4._runtime import BoundSignal

__all__ = [
    "GtkBot", "InteractionError", "LogRecord", "Problems", "RealInput", "SignalWaiter", "WaitTimeout", "activate",
    "click", "collect_problems", "expect_signal", "find", "find_all", "isolate_environment", "iterate", "press_key",
    "real_input", "show_window", "type_text", "wait", "wait_signal", "wait_until",
]

T = TypeVar("T")
W = TypeVar("W", bound="Gtk.Widget")

DEFAULT_TIMEOUT = 5.0


class WaitTimeout(TimeoutError):
    """A wait ran out of time before its condition held."""


class InteractionError(AssertionError):
    """Simulated input that a user couldn't perform, such as clicking an insensitive button."""


# Waiting


def _iteration(context: GLib.MainContext, may_block: bool) -> bool:
    """One main loop iteration, as GTK's own loop does it.

    PyGObject's ``MainContext.iteration`` pauses a running asyncio loop while Python code iterates; the introspected
    function underneath doesn't, so asyncio tasks go on during waits as they do under ``Gio.Application.run()``.
    """
    introspected = next((cls for cls in type(context).__mro__ if cls.__module__ == "gi.repository.GLib"
                         and "iteration" in vars(cls)), type(context))
    return bool(getattr(introspected, "iteration")(context, may_block))


def iterate() -> None:
    """Handle the events and callbacks that are ready now, without blocking.

    Bounded, since something can always be ready: asyncio's work, while its loop runs on GLib's (``gtk_asyncio``).
    """
    from PyLiite4 import GLib

    context = GLib.MainContext.default()
    deadline = time.monotonic() + 0.5
    for _ in range(10000):
        if not context.pending() or time.monotonic() > deadline:
            break
        _iteration(context, False)


def wait(seconds: float) -> None:
    """Run the main loop for ``seconds``, like ``qtbot.wait()``."""
    deadline = time.monotonic() + seconds
    wait_until(lambda: time.monotonic() >= deadline, timeout=seconds + 1)


def wait_until(condition: Callable[[], T], timeout: float = DEFAULT_TIMEOUT, *, message: str | None = None) -> T:
    """Run the GLib main loop until ``condition()`` returns a true value, and return that value.

    ``condition`` may also assert: an ``AssertionError`` means "not yet", and the last one is raised with the
    timeout, so its message explains the failure. Raises ``WaitTimeout`` after ``timeout`` seconds.
    """
    from PyLiite4 import GLib

    context = GLib.MainContext.default()
    deadline = time.monotonic() + timeout
    # Wake iteration() even without events, or a condition changed outside GTK might never get checked.
    tick = GLib.timeout_add(10, lambda: True)
    last_error: AssertionError | None = None
    try:
        while True:
            try:
                value = condition()
                if value:
                    return value
                last_error = None
            except AssertionError as error:
                last_error = error
            if time.monotonic() >= deadline:
                text = message or f"{getattr(condition, '__name__', 'condition')} didn't hold within {timeout} s"
                raise WaitTimeout(f"{text}: {last_error}" if last_error else text) from last_error
            _iteration(context, True)
    finally:
        GLib.Source.remove(tick)


class SignalWaiter:
    """Wait for one emission of a signal, connected before the code that emits it runs.

    Use it as a context manager, so that an emission during the ``with`` block counts::

        with expect_signal(button, "clicked") as waiter:
            click(button)
        assert waiter.args == ()

    ``args`` are the signal's arguments, without the emitting object. ``check``, if given, is called with them and
    an emission counts only if it returns true.
    """

    def __init__(self, target: GObject.Object | BoundSignal[Any], name: str | None = None,
                 timeout: float = DEFAULT_TIMEOUT, *, check: Callable[..., bool] | None = None) -> None:
        from PyLiite4._runtime import BoundSignal

        if isinstance(target, BoundSignal):
            if name is not None:
                raise TypeError("give either a bound signal or an object and a signal name")
            self.instance: GObject.Object = target.instance
            self.name = f"{target.name}::{target.detail}" if target.detail else target.name
        elif name is None:
            raise TypeError("a signal name is needed with an object")
        else:
            self.instance, self.name = target, name
        self.timeout = timeout
        self.check = check
        self.args: tuple[Any, ...] | None = None
        self._handler: int | None = None

    def _emitted(self, _instance: Any, *args: Any) -> None:
        if self.args is None and (self.check is None or self.check(*args)):
            self.args = args

    def connect(self) -> None:
        """Start listening. ``__enter__`` does this."""
        if self._handler is None:
            self._handler = self.instance.connect(self.name, self._emitted)

    def disconnect(self) -> None:
        """Stop listening. ``wait()`` and ``__exit__`` do this."""
        if self._handler is not None:
            self.instance.disconnect(self._handler)
            self._handler = None

    def wait(self) -> tuple[Any, ...]:
        """Run the main loop until the signal has been emitted, and return its arguments."""
        self.connect()
        try:
            wait_until(lambda: self.args is not None, self.timeout,
                       message=f"{self.name!r} of {self.instance!r} wasn't emitted within {self.timeout} s")
        finally:
            self.disconnect()
        assert self.args is not None
        return self.args

    def __enter__(self) -> SignalWaiter:
        self.connect()
        return self

    def __exit__(self, kind: type[BaseException] | None, value: BaseException | None,
                 trace: TracebackType | None) -> None:
        if kind is not None:
            self.disconnect()
            return
        self.wait()


def expect_signal(target: GObject.Object | BoundSignal[Any], name: str | None = None,
                  timeout: float = DEFAULT_TIMEOUT, *, check: Callable[..., bool] | None = None) -> SignalWaiter:
    """Return a context manager that waits, on exit, for the signal to be emitted. See ``SignalWaiter``.

    The signal is given as ``expect_signal(button, "clicked")`` or ``expect_signal(button.clicked)``.
    """
    return SignalWaiter(target, name, timeout, check=check)


def wait_signal(target: GObject.Object | BoundSignal[Any], name: str | None = None,
                timeout: float = DEFAULT_TIMEOUT, *, trigger: Callable[[], object] | None = None,
                check: Callable[..., bool] | None = None) -> tuple[Any, ...]:
    """Run the main loop until the signal is emitted, and return its arguments without the emitting object.

    ``trigger`` runs after connecting, for code that may emit the signal at once. ``check`` filters emissions by
    their arguments. Raises ``WaitTimeout`` after ``timeout`` seconds.
    """
    waiter = SignalWaiter(target, name, timeout, check=check)
    waiter.connect()
    try:
        if trigger is not None:
            trigger()
        return waiter.wait()
    finally:
        waiter.disconnect()


def show_window(window: Gtk.Window, timeout: float = DEFAULT_TIMEOUT) -> None:
    """Present ``window`` and wait until it is mapped and has drawn its first frame."""
    window.present()

    def mapped() -> bool:
        surface = window.get_surface()
        return window.get_mapped() and surface is not None and surface.get_mapped()

    wait_until(mapped, timeout, message=f"{window!r} wasn't mapped within {timeout} s")
    painted: list[bool] = []
    clock = window.get_frame_clock()
    if clock is None:
        return
    handler = clock.connect("after-paint", lambda _clock: painted.append(True))
    try:
        window.queue_draw()
        wait_until(lambda: painted, timeout, message=f"{window!r} wasn't drawn within {timeout} s")
    finally:
        clock.disconnect(handler)


# Simulated input


def _require_interactive(widget: Gtk.Widget, action: str) -> None:
    if not widget.is_visible():
        raise InteractionError(f"can't {action} {widget!r}: it or a parent is hidden")
    if not widget.is_sensitive():
        raise InteractionError(f"can't {action} {widget!r}: it or a parent is insensitive")


def activate(widget: Gtk.Widget) -> None:
    """Activate ``widget`` as Enter or Space would: its activate signal, or else its action.

    That is ``Gtk.Entry``'s Enter, toggling a ``Gtk.CheckButton`` or ``Gtk.Switch``, ``Gtk.ListBoxRow``'s
    ``row-activated``, opening a ``Gtk.MenuButton``. A realized ``Gtk.Button`` emits ``clicked`` 250 ms after
    activation, as in GTK; ``click()`` emits it at once.
    """
    from PyLiite4 import Gtk

    _require_interactive(widget, "activate")
    if Gtk.Widget.activate(widget):
        return
    if isinstance(widget, Gtk.Actionable):
        name = widget.get_action_name()
        if name and widget.activate_action(name, widget.get_action_target_value()):
            return
    raise InteractionError(f"{widget!r} has no activate signal or action")


def click(widget: Gtk.Widget) -> None:
    """Click ``widget``: emit ``clicked`` for a ``Gtk.Button``, which also runs its action, otherwise ``activate()``.

    Raises ``InteractionError`` if the widget is hidden or insensitive, as a user couldn't click it then. No
    pointer event is involved, so a ``Gtk.GestureClick`` of your own isn't triggered: emit its ``pressed`` and
    ``released`` signals instead.
    """
    from PyLiite4 import Gtk

    if isinstance(widget, Gtk.Button):
        _require_interactive(widget, "click")
        widget.emit("clicked")
    else:
        activate(widget)


def type_text(widget: Gtk.Editable | Gtk.TextView, text: str, *, replace: bool = False) -> None:
    """Type ``text`` into an editable or a text view at its cursor, one character at a time, as a user would.

    Each character is a separate insertion, so ``insert-text`` and ``changed`` handlers run once per character, and
    a selection is replaced. ``replace=True`` first deletes the whole content. For Enter, use ``activate()``.
    """
    from PyLiite4 import Gtk

    if isinstance(widget, Gtk.Widget):
        _require_interactive(widget, "type into")
    if isinstance(widget, Gtk.TextView):
        buffer = widget.get_buffer()
        editable = widget.get_editable()
        if not editable:
            raise InteractionError(f"can't type into {widget!r}: it isn't editable")
        if replace:
            buffer.select_range(buffer.get_start_iter(), buffer.get_end_iter())
        for character in text:
            buffer.delete_selection(True, editable)
            buffer.insert_interactive_at_cursor(character, -1, editable)
        if replace and not text:
            buffer.delete_selection(True, editable)
        return
    if not widget.get_editable():
        raise InteractionError(f"can't type into {widget!r}: it isn't editable")
    if replace:
        widget.select_region(0, -1)
        widget.delete_selection()
    # PyGObject's override takes (text, position), unlike the C signature that the stubs describe.
    insert: Callable[[str, int], int] = getattr(widget, "insert_text")
    for character in text:
        widget.delete_selection()
        widget.set_position(insert(character, widget.get_position()))


def _focus_target(widget: Gtk.Widget) -> Gtk.Widget:
    from PyLiite4 import Gtk

    if isinstance(widget, Gtk.Window):
        return widget.get_focus() or widget
    while isinstance(widget, Gtk.Editable):
        delegate = widget.get_delegate()
        if not isinstance(delegate, Gtk.Widget) or delegate is widget:
            break
        widget = delegate
    return widget


def _triggers_match(trigger: Gtk.ShortcutTrigger | None, wanted: Gtk.ShortcutTrigger) -> bool:
    from PyLiite4 import Gtk

    if isinstance(trigger, Gtk.AlternativeTrigger):
        return _triggers_match(trigger.get_first(), wanted) or _triggers_match(trigger.get_second(), wanted)
    return trigger is not None and trigger.equal(wanted)


def _shortcuts(controller: Gtk.ShortcutController) -> Iterator[Gtk.Shortcut]:
    from PyLiite4 import Gio, Gtk

    for index in range(controller.get_n_items()):
        item = controller.get_item(index)
        if isinstance(item, Gtk.Shortcut):
            yield item
        elif isinstance(item, Gio.ListModel):
            # A shortcut manager's models hold other controllers.
            for nested in range(item.get_n_items()):
                shortcut = item.get_item(nested)
                if isinstance(shortcut, Gtk.Shortcut):
                    yield shortcut


def _shortcut_controllers(widget: Gtk.Widget) -> list[Gtk.ShortcutController]:
    from PyLiite4 import Gtk

    controllers = widget.observe_controllers()
    found = []
    for index in range(controllers.get_n_items()):
        controller = controllers.get_item(index)
        if isinstance(controller, Gtk.ShortcutController):
            found.append(controller)
    return found


def press_key(widget: Gtk.Widget, accelerator: str) -> bool:
    """Press a key combination, such as ``"<Control>s"`` or ``"Escape"``, and return whether a shortcut took it.

    ``widget`` stands for the focus: a window means its focus widget. As GTK dispatches a key press, this runs the
    first matching shortcut of the capture-phase shortcut controllers from the window down to the widget, then of
    the others from the widget up, which include widget class bindings (``Gtk.Widget.add_shortcut``), application
    accelerators (``Gtk.Application.set_accels_for_action``) and ``Gtk.ShortcutController``\\ s, global ones too.

    It can't type text or reach ``Gtk.EventControllerKey`` handlers: GTK 4 can't synthesise key events. Use
    ``type_text()`` for text, ``activate()`` for Enter, and emit a key controller's ``key-pressed`` yourself.
    """
    from PyLiite4 import Gtk

    wanted = Gtk.ShortcutTrigger.parse_string(accelerator)
    if not isinstance(wanted, Gtk.KeyvalTrigger):
        raise ValueError(f"{accelerator!r} isn't a key combination like '<Control>s'")
    target = _focus_target(widget)
    _require_interactive(target, "press keys in")
    chain = [target]
    while (parent := chain[-1].get_parent()) is not None:
        chain.append(parent)
    capture = [(w, c) for w in reversed(chain) for c in _shortcut_controllers(w)
               if c.get_propagation_phase() == Gtk.PropagationPhase.CAPTURE]
    bubble = [(w, c) for w in chain for c in _shortcut_controllers(w)
              if c.get_propagation_phase() in (Gtk.PropagationPhase.BUBBLE, Gtk.PropagationPhase.TARGET)]
    for owner, controller in capture + bubble:
        if not owner.is_sensitive():
            continue
        for shortcut in _shortcuts(controller):
            action = shortcut.get_action()
            if action is not None and _triggers_match(shortcut.get_trigger(), wanted) and \
                    action.activate(Gtk.ShortcutActionFlags(0), owner, shortcut.get_arguments()):
                return True
    return False


# Real input, through XTest

# Set by the plugin to the Xvfb display it started, the one display RealInput may drive without being allowed to.
_PRIVATE_DISPLAY = "PYLIITE4_TESTING_DISPLAY"
# Omit service directories so this bus can't auto-start desktop services. A portal launched by a test could
# otherwise outlive the bus under the user's service manager.
_BUS_CONFIG = """<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <keep_umask/>
  <listen>unix:tmpdir=/tmp</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""

# The modifier keys a modifier mask is pressed with, as X keysyms.
_MODIFIER_KEYS = (("SHIFT_MASK", 0xFFE1), ("CONTROL_MASK", 0xFFE3), ("ALT_MASK", 0xFFE9), ("SUPER_MASK", 0xFFEB),
                  ("HYPER_MASK", 0xFFED), ("META_MASK", 0xFFE7))
# Characters that type_text() can't send as themselves.
_KEY_NAMES = {"\n": "Return", "\r": "Return", "\t": "Tab", "\b": "BackSpace", "\x1b": "Escape"}


class _XLib:
    """libX11 and libXtst through ctypes, on a connection of their own to the display GDK uses."""

    def __init__(self, display_name: str) -> None:
        from ctypes import POINTER, c_char_p, c_int, c_ubyte, c_uint, c_ulong, c_void_p

        try:
            # The same libX11 GDK loaded, since a loaded soname is reused; libXtst is the system's.
            self.x11 = ctypes.CDLL("libX11.so.6")
            self.xtst = ctypes.CDLL("libXtst.so.6")
        except OSError as error:
            raise InteractionError(f"real input needs libXtst ({error}); install libxtst6 or libXtst") from error
        x11, xtst = self.x11, self.xtst
        x11.XOpenDisplay.argtypes, x11.XOpenDisplay.restype = [c_char_p], c_void_p
        x11.XCloseDisplay.argtypes = [c_void_p]
        x11.XDefaultRootWindow.argtypes, x11.XDefaultRootWindow.restype = [c_void_p], c_ulong
        x11.XTranslateCoordinates.argtypes = [c_void_p, c_ulong, c_ulong, c_int, c_int, POINTER(c_int), POINTER(c_int),
                                              POINTER(c_ulong)]
        x11.XSync.argtypes = [c_void_p, c_int]
        x11.XSetInputFocus.argtypes = [c_void_p, c_ulong, c_int, c_ulong]
        x11.XDisplayKeycodes.argtypes = [c_void_p, POINTER(c_int), POINTER(c_int)]
        x11.XGetKeyboardMapping.argtypes = [c_void_p, c_ubyte, c_int, POINTER(c_int)]
        x11.XGetKeyboardMapping.restype = POINTER(c_ulong)
        x11.XChangeKeyboardMapping.argtypes = [c_void_p, c_int, c_int, POINTER(c_ulong), c_int]
        x11.XFree.argtypes = [c_void_p]
        xtst.XTestQueryExtension.argtypes = [c_void_p, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int)]
        xtst.XTestFakeMotionEvent.argtypes = [c_void_p, c_int, c_int, c_int, c_ulong]
        xtst.XTestFakeButtonEvent.argtypes = [c_void_p, c_uint, c_int, c_ulong]
        xtst.XTestFakeKeyEvent.argtypes = [c_void_p, c_uint, c_int, c_ulong]
        self.display = x11.XOpenDisplay(display_name.encode())
        if not self.display:
            raise InteractionError(f"couldn't open display {display_name!r} for real input")
        numbers = [c_int() for _ in range(4)]
        if not xtst.XTestQueryExtension(self.display, *[ctypes.byref(number) for number in numbers]):
            raise InteractionError(f"display {display_name!r} has no XTest extension")
        self.root = x11.XDefaultRootWindow(self.display)
        self._load_keymap()

    def _load_keymap(self) -> None:
        from ctypes import c_int

        low, high, per_code = c_int(), c_int(), c_int()
        self.x11.XDisplayKeycodes(self.display, ctypes.byref(low), ctypes.byref(high))
        self.low, count = low.value, high.value - low.value + 1
        table = self.x11.XGetKeyboardMapping(self.display, low.value, count, ctypes.byref(per_code))
        self.per_code = per_code.value
        self.keymap = [[table[code * self.per_code + column] for column in range(self.per_code)]
                       for code in range(count)]
        self.x11.XFree(table)

    def keycode(self, keysym: int) -> tuple[int, bool]:
        """The keycode that types ``keysym``, and whether Shift is needed, remapping a free keycode if none does."""
        for column in (0, 1):
            for index, symbols in enumerate(self.keymap):
                if column < len(symbols) and symbols[column] == keysym:
                    return self.low + index, column == 1
        free = next((index for index, symbols in enumerate(self.keymap) if not any(symbols)), None)
        if free is None:
            raise InteractionError(f"no free keycode to type keysym {keysym:#x} with")
        # Both levels, as xdotool does, so the character comes out whatever the Shift state.
        pair = (ctypes.c_ulong * 2)(keysym, keysym)
        self.x11.XChangeKeyboardMapping(self.display, self.low + free, 2, pair, 1)
        self.sync()
        self._load_keymap()
        return self.low + free, False

    def sync(self) -> None:
        self.x11.XSync(self.display, 0)

    def close(self) -> None:
        self.x11.XCloseDisplay(self.display)


def _xid(surface: Gdk.Surface) -> int:
    """The X window of an X11 surface."""
    import gi  # type: ignore

    gi.require_version("GdkX11", "4.0")
    from gi.repository import GdkX11  # type: ignore

    # Deprecated with the rest of GdkX11, but still the only way to the X window.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return int(GdkX11.X11Surface.get_xid(surface))


@dataclass(frozen=True)
class _Received:
    """What RealInput needs of an event GTK received, kept after the event itself is gone."""

    kind: str
    position: tuple[float, float] | None
    button: int
    keycode: int

    @classmethod
    def of(cls, event: Gdk.Event) -> _Received:
        from PyLiite4 import Gdk

        found, x, y = event.get_position()
        return cls(event.get_event_type().value_name.removeprefix("GDK_"), (x, y) if found else None,
                   event.get_button() if isinstance(event, Gdk.ButtonEvent) else 0,
                   event.get_keycode() if isinstance(event, Gdk.KeyEvent) else 0)


class RealInput:
    """Real pointer and keyboard input, the equivalent of ``QTest``'s mouse and key functions.

    Each call sends X events through XTest and handles them until GTK has received them, so when it returns they have
    gone through the widgets' event controllers, gestures, focus handling and key bindings, as a user's input would.
    What those handlers start later, such as a popover opening, needs ``wait_until()``.

    Positions are in the widget's own coordinates, its centre by default. ``modifiers`` are written like an
    accelerator, ``"<Control><Shift>"``. Buttons are numbered as in GDK: 1 is primary, 2 middle, 3 secondary.

    Raises ``InteractionError`` when a user couldn't do it: the widget is hidden, insensitive, or under another
    widget at that point; and when GTK doesn't receive the input.
    """

    def __init__(self) -> None:
        from PyLiite4 import Gdk

        display = Gdk.Display.get_default()
        if display is None or type(display).__name__ != "X11Display":
            raise InteractionError("real input needs GTK on X11 (GDK_BACKEND=x11), which the plugin's Xvfb provides")
        name = display.get_name()
        if name != os.environ.get(_PRIVATE_DISPLAY) and os.environ.get("PYLIITE4_TESTING_REAL_INPUT") != "1":
            raise InteractionError(f"refusing real input on display {name}, which isn't the plugin's private Xvfb: "
                                   "it would move that display's own pointer. Set PYLIITE4_TESTING_REAL_INPUT=1 to "
                                   "allow it")
        self._display = display
        self._x = _XLib(name)
        self._buttons: set[int] = set()

    # Where things are

    def _locate(self, widget: Gtk.Widget, at: tuple[float, float] | None,
                action: str) -> tuple[int, int, float, float]:
        """The root window position of ``at`` in ``widget``, and the position in its surface, checked to be where the
        widget gets the pointer."""
        from PyLiite4 import Graphene, Gtk

        _require_interactive(widget, action)
        native = widget.get_native()
        surface = native.get_surface() if native is not None else None
        if native is None or surface is None or not widget.get_mapped():
            raise InteractionError(f"can't {action} {widget!r}: it isn't shown in a window")
        if widget.get_width() <= 0 or widget.get_height() <= 0:
            raise InteractionError(f"can't {action} {widget!r}: it has no size yet; wait_until() it is laid out")
        x, y = at if at is not None else (widget.get_width() / 2, widget.get_height() / 2)
        point = Graphene.Point()
        point.x, point.y = x, y
        assert isinstance(native, Gtk.Widget)
        found, inside = widget.compute_point(native, point)
        if not found:
            raise InteractionError(f"can't {action} {widget!r}: no position in its window")
        picked = native.pick(inside.x, inside.y, Gtk.PickFlags.DEFAULT)
        if picked is None or not (picked is widget or picked.is_ancestor(widget)):
            raise InteractionError(f"can't {action} {widget!r} at {x:g}, {y:g}: "
                                   f"{_describe(picked) if picked else 'nothing'} is there")
        offset_x, offset_y = native.get_surface_transform()
        surface_x, surface_y = inside.x + offset_x, inside.y + offset_y
        scale = surface.get_scale()
        root_x, root_y, child = ctypes.c_int(), ctypes.c_int(), ctypes.c_ulong()
        self._x.x11.XTranslateCoordinates(self._x.display, _xid(surface), self._x.root,
                                          round(surface_x * scale), round(surface_y * scale),
                                          ctypes.byref(root_x), ctypes.byref(root_y), ctypes.byref(child))
        return root_x.value, root_y.value, surface_x, surface_y

    def _focus(self, widget: Gtk.Widget) -> None:
        """Give ``widget``'s window the keyboard, and ``widget`` the focus unless it is the window."""
        from PyLiite4 import Gtk

        root = widget.get_root()
        if not isinstance(root, Gtk.Window) or not root.get_mapped():
            raise InteractionError(f"can't type into {widget!r}: it isn't shown in a window")
        if not root.is_active():
            surface = root.get_surface()
            assert surface is not None
            # 1 is RevertToPointerRoot; with no window manager, nothing else gives a window the keyboard.
            self._x.x11.XSetInputFocus(self._x.display, _xid(surface), 1, 0)
            self._deliver(root, [], lambda: None)
            wait_until(root.is_active, message=f"{root!r} didn't get the keyboard focus")
        if widget is not root:
            focus = root.get_focus()
            if focus is None or not (focus is widget or focus.is_ancestor(widget)):
                if not widget.grab_focus():
                    raise InteractionError(f"can't type into {widget!r}: it can't take the focus")
                iterate()

    # Getting input to GTK

    def _frame(self, native: Gtk.Widget) -> None:
        """Run a frame of ``native``'s surface, which is when GDK delivers the pointer motion it holds back."""
        from PyLiite4 import Gdk

        clock = native.get_frame_clock()
        if clock is None:
            return
        painted: list[bool] = []
        handler = clock.connect("after-paint", lambda _clock: painted.append(True))
        try:
            clock.request_phase(Gdk.FrameClockPhase(Gdk.FrameClockPhase.FLUSH_EVENTS
                                                    | Gdk.FrameClockPhase.AFTER_PAINT))
            try:
                wait_until(lambda: painted, timeout=1)
            except WaitTimeout:
                pass
        finally:
            clock.disconnect(handler)

    def _deliver(self, widget: Gtk.Widget, expected: list[Callable[[_Received], bool]],
                 send: Callable[[], None]) -> None:
        """Send events with ``send()``, then handle what arrives until ``widget``'s window has received events that
        meet each of ``expected``, in order.

        The X server makes XTest's events on its own time, so a round trip doesn't mean they have reached GDK; and
        GDK delivers motion at the next frame. What arrives is watched rather than assumed.
        """
        from PyLiite4 import Gtk

        native = widget if isinstance(widget, Gtk.Native) else widget.get_native()
        assert isinstance(native, Gtk.Widget)
        seen: list[_Received] = []

        def received(controller: Gtk.EventControllerLegacy, _event: object) -> bool:
            # PyGObject passes the signal's event as None; the controller still has it, for now only.
            event = controller.get_current_event()
            if event is not None:
                seen.append(_Received.of(event))
            return False

        watcher = Gtk.EventControllerLegacy(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        watcher.connect("event", received)
        native.add_controller(watcher)
        try:
            send()
            self._x.sync()
            deadline = time.monotonic() + 5
            while True:
                # A round trip on GDK's own connection: what the server sent before it is queued after it.
                self._display.sync()
                iterate()
                remaining = list(expected)
                for event in seen:
                    if remaining and remaining[0](event):
                        remaining.pop(0)
                if not remaining:
                    break
                if time.monotonic() > deadline:
                    raise InteractionError(f"GTK didn't receive the input sent to {widget!r}")
                self._frame(native)
            self._frame(native)
            iterate()
        finally:
            native.remove_controller(watcher)

    @staticmethod
    def _pointer_at(x: float, y: float) -> Callable[[_Received], bool]:
        return lambda event: event.kind in ("MOTION_NOTIFY", "ENTER_NOTIFY") and event.position is not None \
            and abs(event.position[0] - x) < 1.5 and abs(event.position[1] - y) < 1.5

    @staticmethod
    def _button(press: bool, button: int) -> Callable[[_Received], bool]:
        kind = "BUTTON_PRESS" if press else "BUTTON_RELEASE"
        return lambda event: event.kind == kind and event.button == button

    @staticmethod
    def _key(press: bool, keycode: int) -> Callable[[_Received], bool]:
        kind = "KEY_PRESS" if press else "KEY_RELEASE"
        return lambda event: event.kind == kind and event.keycode == keycode

    @staticmethod
    def _scrolled(event: _Received) -> bool:
        return event.kind == "SCROLL"

    def _modifiers(self, modifiers: str) -> list[int]:
        from PyLiite4 import Gdk, Gtk

        if not modifiers:
            return []
        ok, _keyval, mask = Gtk.accelerator_parse(modifiers + "a")
        if not ok:
            raise ValueError(f"{modifiers!r} isn't a modifier list like '<Control><Shift>'")
        return [keysym for name, keysym in _MODIFIER_KEYS if mask & getattr(Gdk.ModifierType, name)]

    def _keys(self, keysyms: list[int], press: bool) -> None:
        for keysym in keysyms if press else reversed(keysyms):
            self._x.xtst.XTestFakeKeyEvent(self._x.display, self._x.keycode(keysym)[0], press, 0)

    def _buttons_with(self, keys: list[int], events: list[tuple[int, bool]]) -> Callable[[], None]:
        def send() -> None:
            self._keys(keys, True)
            for button, press in events:
                self._x.xtst.XTestFakeButtonEvent(self._x.display, button, press, 0)
            self._keys(keys, False)
        return send

    # The pointer

    def move(self, widget: Gtk.Widget, at: tuple[float, float] | None = None) -> None:
        """Move the pointer over ``widget``."""
        x, y, surface_x, surface_y = self._locate(widget, at, "move to")
        self._deliver(widget, [self._pointer_at(surface_x, surface_y)],
                      lambda: self._x.xtst.XTestFakeMotionEvent(self._x.display, -1, x, y, 0))

    def press(self, widget: Gtk.Widget, button: int = 1, at: tuple[float, float] | None = None,
              modifiers: str = "") -> None:
        """Move to ``widget`` and press ``button``, leaving it down until ``release()``."""
        keys = self._modifiers(modifiers)
        self.move(widget, at)
        self._deliver(widget, [self._button(True, button)], self._buttons_with(keys, [(button, True)]))
        self._buttons.add(button)

    def release(self, widget: Gtk.Widget | None = None, button: int = 1, at: tuple[float, float] | None = None,
                modifiers: str = "") -> None:
        """Release ``button``, after moving to ``widget`` if one is given."""
        keys = self._modifiers(modifiers)
        if widget is not None:
            self.move(widget, at)
        send = self._buttons_with(keys, [(button, False)])
        if widget is not None:
            self._deliver(widget, [self._button(False, button)], send)
        else:
            send()
            self._x.sync()
            self._display.sync()
            iterate()
        self._buttons.discard(button)

    def click(self, widget: Gtk.Widget, button: int = 1, at: tuple[float, float] | None = None,
              modifiers: str = "") -> None:
        """Press and release ``button`` over ``widget``, like ``QTest.mouseClick``."""
        keys = self._modifiers(modifiers)
        self.move(widget, at)
        self._deliver(widget, [self._button(True, button), self._button(False, button)],
                      self._buttons_with(keys, [(button, True), (button, False)]))

    def double_click(self, widget: Gtk.Widget, button: int = 1, at: tuple[float, float] | None = None,
                     modifiers: str = "") -> None:
        """Click twice in quick succession, like ``QTest.mouseDClick``."""
        keys = self._modifiers(modifiers)
        self.move(widget, at)
        self._deliver(widget, [self._button(True, button), self._button(False, button)] * 2,
                      self._buttons_with(keys, [(button, True), (button, False)] * 2))

    def drag(self, source: Gtk.Widget, target: Gtk.Widget | None = None, *, start: tuple[float, float] | None = None,
             end: tuple[float, float] | None = None, button: int = 1, steps: int = 10) -> None:
        """Press over ``source``, move in ``steps`` to ``end`` in ``target`` (``source`` itself by default), release.

        The steps cross GTK's drag threshold the way a hand does, so drag gestures and drag-and-drop both start.
        """
        target = target or source
        x0, y0, _, _ = self._locate(source, start, "drag from")
        x1, y1, _, _ = self._locate(target, end, "drag to")
        self.move(source, start)
        self._deliver(source, [self._button(True, button)], self._buttons_with([], [(button, True)]))
        for step in range(1, steps + 1):
            x, y = round(x0 + (x1 - x0) * step / steps), round(y0 + (y1 - y0) * step / steps)

            def send(x: int = x, y: int = y) -> None:
                self._x.xtst.XTestFakeMotionEvent(self._x.display, -1, x, y, 0)
            # Not required to arrive at the window: once drag-and-drop starts, the drag's own surface gets them.
            self._deliver(source, [], send)
            wait(0.01)
        self._deliver(source, [], self._buttons_with([], [(button, False)]))

    def scroll(self, widget: Gtk.Widget, dy: int = 1, dx: int = 0, at: tuple[float, float] | None = None) -> None:
        """Turn the wheel over ``widget``: positive ``dy`` scrolls down, positive ``dx`` right, one notch each."""
        self.move(widget, at)
        events = []
        for amount, back, forward in ((dy, 4, 5), (dx, 6, 7)):
            wheel = forward if amount > 0 else back
            events += [(wheel, True), (wheel, False)] * abs(amount)
        self._deliver(widget, [self._scrolled] if events else [], self._buttons_with([], events))

    # The keyboard

    def _parse(self, accelerator: str) -> tuple[list[int], int]:
        from PyLiite4 import Gtk

        ok, keyval, _mask = Gtk.accelerator_parse(accelerator)
        if not ok or not keyval:
            raise ValueError(f"{accelerator!r} isn't a key combination like '<Control>s' or 'Escape'")
        return self._modifiers(accelerator[:accelerator.rfind(">") + 1]), keyval

    def key(self, widget: Gtk.Widget, accelerator: str) -> None:
        """Press and release a key combination, ``"<Control>s"`` or ``"Escape"``, in ``widget``, like
        ``QTest.keyClick``. A window stands for its focus widget."""
        self.key_down(widget, accelerator)
        self.key_up(widget, accelerator)

    def key_down(self, widget: Gtk.Widget, accelerator: str) -> None:
        """Press a key combination and leave it down until ``key_up()``."""
        keys, keyval = self._parse(accelerator)
        self._focus(widget)
        code, shifted = self._x.keycode(keyval)
        # A remapped keycode must reach GDK's keymap before the key does.
        self._deliver(widget, [], lambda: None)
        held = keys + ([0xFFE1] if shifted and 0xFFE1 not in keys else [])

        def send() -> None:
            self._keys(held, True)
            self._x.xtst.XTestFakeKeyEvent(self._x.display, code, True, 0)
        self._deliver(widget, [self._key(True, code)], send)

    def key_up(self, widget: Gtk.Widget, accelerator: str) -> None:
        """Release a key combination pressed with ``key_down()``."""
        keys, keyval = self._parse(accelerator)
        code, shifted = self._x.keycode(keyval)
        held = keys + ([0xFFE1] if shifted and 0xFFE1 not in keys else [])

        def send() -> None:
            self._x.xtst.XTestFakeKeyEvent(self._x.display, code, False, 0)
            self._keys(held, False)
        self._deliver(widget, [self._key(False, code)], send)

    def type(self, widget: Gtk.Widget, text: str) -> None:
        """Type ``text`` into ``widget`` key by key, like ``QTest.keyClicks``. Newlines press Return and tabs Tab."""
        from PyLiite4 import Gdk

        self._focus(widget)
        for character in text:
            name = _KEY_NAMES.get(character)
            keyval = Gdk.keyval_from_name(name) if name else Gdk.unicode_to_keyval(ord(character))
            code, shifted = self._x.keycode(keyval)
            # The keymap may have changed for this character: let GDK see it before the key does.
            self._deliver(widget, [], lambda: None)

            def send(code: int = code, shifted: bool = shifted) -> None:
                if shifted:
                    self._keys([0xFFE1], True)
                self._x.xtst.XTestFakeKeyEvent(self._x.display, code, True, 0)
                self._x.xtst.XTestFakeKeyEvent(self._x.display, code, False, 0)
                if shifted:
                    self._keys([0xFFE1], False)
            self._deliver(widget, [self._key(True, code), self._key(False, code)], send)

    def release_all(self) -> None:
        """Release any button still pressed, so the next test starts clean."""
        for button in sorted(self._buttons):
            self._x.xtst.XTestFakeButtonEvent(self._x.display, button, False, 0)
        self._buttons.clear()
        self._x.sync()
        self._display.sync()
        iterate()


_real_input: RealInput | None = None


def real_input() -> RealInput:
    """The process's ``RealInput``, connected on first use."""
    global _real_input
    if _real_input is None:
        _real_input = RealInput()
    return _real_input


# Finding widgets


def _children(widget: Gtk.Widget) -> Iterator[Gtk.Widget]:
    child = widget.get_first_child()
    while child is not None:
        yield child
        child = child.get_next_sibling()


def _walk(widget: Gtk.Widget) -> Iterator[Gtk.Widget]:
    yield widget
    for child in _children(widget):
        yield from _walk(child)


def _labels(widget: Gtk.Widget) -> list[str]:
    from PyLiite4 import Gtk

    if isinstance(widget, Gtk.Label):
        return [widget.get_text(), widget.get_label()]
    if widget.find_property("label") is None:
        return []
    label = widget.get_property("label")
    if not isinstance(label, str):
        return []
    if widget.find_property("use-underline") is not None and widget.get_property("use-underline"):
        return [re.sub(r"_(.)", r"\1", label), label]
    return [label]


def _matches(text: str | None, wanted: str | re.Pattern[str]) -> bool:
    if text is None:
        return False
    return bool(wanted.search(text)) if isinstance(wanted, re.Pattern) else text == wanted


def _describe(widget: Gtk.Widget) -> str:
    details = [f"name={widget.get_name()!r}"]
    if labels := _labels(widget):
        details.append(f"label={labels[0]!r}")
    from PyLiite4 import Gtk

    if isinstance(widget, Gtk.Buildable) and (buildable_id := widget.get_buildable_id()):
        details.append(f"id={buildable_id!r}")
    return f"{type(widget).__name__}({', '.join(details)})"


@overload
def find_all(root: Gtk.Widget, cls: None = None, *, name: str | re.Pattern[str] | None = None,
             label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
             predicate: Callable[[Gtk.Widget], bool] | None = None) -> list[Gtk.Widget]: ...
@overload
def find_all(root: Gtk.Widget, cls: type[W], *, name: str | re.Pattern[str] | None = None,
             label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
             predicate: Callable[[W], bool] | None = None) -> list[W]: ...
def find_all(root: Gtk.Widget, cls: type[Any] | None = None, *, name: str | re.Pattern[str] | None = None,
             label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
             predicate: Callable[[Any], bool] | None = None) -> list[Any]:
    """Return the widgets in ``root``'s tree, ``root`` included and in tree order, that meet every criterion.

    ``cls`` is a widget class. ``name`` is the widget name (``Gtk.Widget.get_name()``, which is the type's name if
    none was set). ``label`` is a ``Gtk.Label``'s text, or the ``label`` property of a widget that has one, with or
    without its mnemonic underscore. ``buildable_id`` is the id in the ``Gtk.Builder`` file the widget came from.
    ``name`` and ``label`` may be compiled regular expressions, which are searched for. The tree includes each
    widget's internal children, such as a button's label, and popovers.
    """
    from PyLiite4 import Gtk

    found = []
    for widget in _walk(root):
        if cls is not None and not isinstance(widget, cls):
            continue
        if name is not None and not _matches(widget.get_name(), name):
            continue
        if label is not None and not any(_matches(text, label) for text in _labels(widget)):
            continue
        if buildable_id is not None and not (isinstance(widget, Gtk.Buildable)
                                             and widget.get_buildable_id() == buildable_id):
            continue
        if predicate is not None and not predicate(widget):
            continue
        found.append(widget)
    return found


@overload
def find(root: Gtk.Widget, cls: None = None, *, name: str | re.Pattern[str] | None = None,
         label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
         predicate: Callable[[Gtk.Widget], bool] | None = None) -> Gtk.Widget: ...
@overload
def find(root: Gtk.Widget, cls: type[W], *, name: str | re.Pattern[str] | None = None,
         label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
         predicate: Callable[[W], bool] | None = None) -> W: ...
def find(root: Gtk.Widget, cls: type[Any] | None = None, *, name: str | re.Pattern[str] | None = None,
         label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
         predicate: Callable[[Any], bool] | None = None) -> Any:
    """Return the one widget that ``find_all()`` finds. Raises ``LookupError`` if there are none or several."""
    found = find_all(root, cls, name=name, label=label, buildable_id=buildable_id, predicate=predicate)
    if len(found) == 1:
        return found[0]
    criteria = ", ".join(f"{key}={value!r}" for key, value in
                         (("cls", cls and cls.__name__), ("name", name), ("label", label),
                          ("buildable_id", buildable_id), ("predicate", predicate)) if value is not None)
    if found:
        listed = "\n  ".join(_describe(widget) for widget in found[:20])
        raise LookupError(f"{len(found)} widgets match {criteria} under {root!r}; use find_all():\n  {listed}")
    candidates = [widget for widget in _walk(root) if cls is None or isinstance(widget, cls)]
    listed = "\n  ".join(_describe(widget) for widget in candidates[:20])
    more = f"\n  and {len(candidates) - 20} more" if len(candidates) > 20 else ""
    raise LookupError(f"no widget matches {criteria} under {root!r}"
                      + (f"; these have the type:\n  {listed}{more}" if listed else ""))


# GLib log messages and Python exceptions


@dataclass
class LogRecord:
    """A message logged through GLib."""

    domain: str | None
    level: GLib.LogLevelFlags
    message: str

    @property
    def level_name(self) -> str:
        from PyLiite4 import GLib

        for flag, name in ((GLib.LogLevelFlags.LEVEL_ERROR, "ERROR"), (GLib.LogLevelFlags.LEVEL_CRITICAL, "CRITICAL"),
                           (GLib.LogLevelFlags.LEVEL_WARNING, "WARNING"), (GLib.LogLevelFlags.LEVEL_MESSAGE, "MESSAGE"),
                           (GLib.LogLevelFlags.LEVEL_INFO, "INFO"), (GLib.LogLevelFlags.LEVEL_DEBUG, "DEBUG")):
            if self.level & flag:
                return name
        return str(int(self.level))

    def __str__(self) -> str:
        return f"{self.domain or '(no domain)'}-{self.level_name}: {self.message}"


# GLib's levels, most severe first, and the names that select a threshold.
_LEVELS = {"error": 1 << 2, "critical": 1 << 3, "warning": 1 << 4, "message": 1 << 5}


@dataclass
class Problems:
    """GLib messages and callback exceptions collected while it is active. See ``collect_problems()``.

    ``records`` holds every message at ``message`` level or above; those at ``fail_level`` or above, unless they
    match one of ``ignore``, are failures. ``exceptions`` holds exceptions that callbacks raised and PyGObject
    could only print. Remove expected entries from either list, or call ``take()``, before ``check()`` runs.
    """

    fail_level: str = "warning"
    ignore: list[re.Pattern[str]] = field(default_factory=list)
    records: list[LogRecord] = field(default_factory=list)
    exceptions: list[BaseException] = field(default_factory=list)
    _previous_hook: Callable[[type[BaseException], BaseException, TracebackType | None], Any] | None = \
        field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.fail_level not in (*_LEVELS, "none"):
            raise ValueError(f"fail_level must be one of {', '.join(_LEVELS)} or none, not {self.fail_level!r}")

    def take(self, pattern: str | re.Pattern[str]) -> list[LogRecord]:
        """Remove and return the records whose message contains a match for ``pattern``."""
        expression = re.compile(pattern) if isinstance(pattern, str) else pattern
        taken = [record for record in self.records if expression.search(str(record))]
        self.records[:] = [record for record in self.records if record not in taken]
        return taken

    def clear(self) -> None:
        """Forget everything collected so far."""
        self.records.clear()
        self.exceptions.clear()

    def failures(self) -> list[str]:
        """Describe each record and exception that fails a test."""
        # This level and the more severe ones, which have lower bits.
        levels = 0 if self.fail_level == "none" else (_LEVELS[self.fail_level] << 1) - _LEVELS["error"]
        failing = [str(record) for record in self.records if int(record.level) & levels
                   and not any(pattern.search(str(record)) for pattern in self.ignore)]
        failing += ["".join(traceback.format_exception(type(error), error, error.__traceback__)).rstrip()
                    for error in self.exceptions]
        return failing

    def check(self) -> None:
        """Raise ``AssertionError`` describing the failures, if there are any, and forget everything collected."""
        failures = self.failures()
        self.clear()
        if failures:
            raise AssertionError("\n".join(["GTK reported problems:", *failures]))

    def _record_exception(self, kind: type[BaseException], value: BaseException,
                          trace: TracebackType | None) -> None:
        if value.__traceback__ is None:
            value = value.with_traceback(trace)
        self.exceptions.append(value)

    def __enter__(self) -> Problems:
        _install_log_handlers()
        _collectors.append(self)
        self._previous_hook = sys.excepthook
        sys.excepthook = self._record_exception
        return self

    def __exit__(self, kind: type[BaseException] | None, value: BaseException | None,
                 trace: TracebackType | None) -> None:
        if self._previous_hook is not None:
            sys.excepthook = self._previous_hook
        _collectors.remove(self)


def collect_problems(fail_level: str = "warning", ignore: list[str] | None = None) -> Problems:
    """Return a context manager that collects GLib messages and callback exceptions; see ``Problems``.

    ``fail_level`` is ``error``, ``critical``, ``warning``, ``message`` or ``none``. Call ``check()`` at the end::

        with collect_problems() as problems:
            run_the_code()
        problems.check()

    GLib allows one log writer per process, so an application that calls ``GLib.log_set_writer_func()`` itself
    can't be tested with this; its messages aren't collected, and GLib aborts if that call comes second.
    """
    return Problems(fail_level, [re.compile(pattern) for pattern in ignore or []])


_collectors: list[Problems] = []
_log_handlers_installed = False
# The levels worth keeping: message and more severe.
_KEPT_LEVELS = 0b111100


def _collect(domain: str | None, level: int, message: str) -> None:
    if level & _KEPT_LEVELS:
        from PyLiite4 import GLib

        for collector in _collectors:
            collector.records.append(LogRecord(domain, GLib.LogLevelFlags(level & _KEPT_LEVELS), message))


def _install_log_handlers() -> None:
    """Route GLib's messages through ``_collect``. GLib allows this once per process, so it stays installed."""
    global _log_handlers_installed
    if _log_handlers_installed:
        return
    _log_handlers_installed = True
    from PyLiite4 import GLib

    def writer(level: GLib.LogLevelFlags, fields: list[GLib.LogField], *_rest: Any) -> GLib.LogWriterOutput:
        values: dict[str, str] = {}
        for log_field in fields:
            if log_field.key in ("GLIB_DOMAIN", "MESSAGE") and isinstance(log_field.value, int) and log_field.value:
                raw = ctypes.string_at(log_field.value, log_field.length if log_field.length >= 0 else -1)
                values[log_field.key] = raw.decode(errors="replace")
        _collect(values.get("GLIB_DOMAIN"), int(level), values.get("MESSAGE", ""))
        return GLib.log_writer_default(level, fields)

    # The stubs describe the C function, which takes the callback's user data and destroy notify too.
    set_writer: Callable[..., None] = getattr(GLib, "log_set_writer_func")
    set_writer(writer, None)

    # PyGObject turns these domains' messages into Python warnings with a handler of its own, which bypasses the
    # writer. This one does the same after collecting them.
    def handler(domain: str | None, level: GLib.LogLevelFlags, message: str | None, *_rest: Any) -> None:
        _collect(domain, int(level), message or "")
        warnings.warn(message or "", Warning, stacklevel=2)

    levels = GLib.LogLevelFlags(GLib.LogLevelFlags.LEVEL_MASK | GLib.LogLevelFlags.FLAG_FATAL
                                | GLib.LogLevelFlags.FLAG_RECURSION)
    for domain in ("GLib", "GLib-GObject", "GThread"):
        GLib.log_set_handler(domain, levels, handler)


# The isolated environment


class _Isolation:
    """The display, bus and directories of one test run, and the environment as it was before."""

    def __init__(self) -> None:
        self.saved: dict[str, str | None] = {}
        self.processes: list[subprocess.Popen[bytes]] = []
        self.directory: str | None = None
        self.writer: int | None = None

    def set(self, name: str, value: str | None) -> None:
        if name not in self.saved:
            self.saved[name] = os.environ.get(name)
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value

    def start(self, command: list[str], what: str) -> str:
        """Start a daemon that prints its address on a file descriptor named by ``{fd}``, and return the address."""
        reader, writer = os.pipe()
        try:
            process = subprocess.Popen([part.replace("{fd}", str(writer)) for part in command], pass_fds=(writer,),
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, start_new_session=True)
        except OSError as error:
            os.close(reader)
            os.close(writer)
            raise pytest.UsageError(f"couldn't start {what}: {error}") from error
        os.close(writer)
        self.processes.append(process)
        output = b""
        deadline = time.monotonic() + 10
        with os.fdopen(reader, "rb", buffering=0) as stream:
            while b"\n" not in output and time.monotonic() < deadline:
                ready, _, _ = select.select([stream], [], [], max(0.0, deadline - time.monotonic()))
                if not ready:
                    break
                chunk = stream.read(4096)
                if not chunk:
                    break
                output += chunk
        if b"\n" not in output:
            raise pytest.UsageError(f"{what} didn't start (exit status {process.poll()})")
        return output.decode().strip()

    def watch(self) -> None:
        """Start a watcher that ends the daemons and removes the directory once this process has exited.

        GTK keeps its display open until the process ends, and losing it earlier makes GDK exit mid-teardown, so
        ``stop()`` can't end the display while GTK is initialised. The watcher holds the read end of a pipe whose
        write end only this process has: when that closes, at exit however it comes, the watcher cleans up.
        """
        reader, self.writer = os.pipe()
        try:
            subprocess.Popen([sys.executable, "-I", "-c", _WATCHER, str(reader), self.directory or "",
                              *[str(process.pid) for process in self.processes]],
                             pass_fds=(reader,), stdin=subprocess.DEVNULL, start_new_session=True)
        finally:
            os.close(reader)

    def stop(self) -> None:
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.saved.clear()
        if _gtk_initialized():
            return
        for process in reversed(self.processes):
            # Each daemon leads a process group of its own, with the services the bus started.
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
            except ProcessLookupError:
                pass
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        self.processes.clear()
        if self.directory is not None:
            shutil.rmtree(self.directory, ignore_errors=True)
            self.directory = None
        if self.writer is not None:
            os.close(self.writer)
            self.writer = None


# Run by _Isolation.watch() as python -I -c: waits for the pipe to close, then ends the process groups named and
# removes the directory.
_WATCHER = """
import os, shutil, signal, sys, time
reader, directory, groups = int(sys.argv[1]), sys.argv[2], [int(group) for group in sys.argv[3:]]
while os.read(reader, 1):
    pass
for number, sent in enumerate((signal.SIGTERM, signal.SIGKILL)):
    for group in groups:
        try:
            os.killpg(group, sent)
        except ProcessLookupError:
            pass
    if number == 0:
        time.sleep(0.5)
if directory:
    shutil.rmtree(directory, ignore_errors=True)
"""


def _gtk_initialized() -> bool:
    gtk = sys.modules.get("gi.repository.Gtk")
    return gtk is not None and bool(gtk.is_initialized())


def isolate_environment(display: str = "xvfb") -> Callable[[], None]:
    """Prepare this process for GTK tests, before GTK initialises, and return a function that undoes it.

    ``display`` is ``xvfb``, to start a private Xvfb, or ``inherit``, to use ``$DISPLAY`` as it is, for running
    under ``xvfb-run`` or watching the tests on a desktop. Either way the process gets a private D-Bus session
    with service activation disabled, ``GDK_BACKEND=x11`` without ``WAYLAND_DISPLAY``, no portals (``GDK_DEBUG=no-portals``, ``ADW_DISABLE_PORTAL``),
    accessibility recorded in-process (``GTK_A11Y=test``), in-memory settings (``GSETTINGS_BACKEND=memory``), and temporary XDG
    config, data, state and runtime directories. With ``display="inherit"`` and ``GDK_BACKEND=wayland`` set, the
    Wayland display and runtime directory are kept, for a headless compositor.

    Raises ``pytest.UsageError`` if GTK is already initialised, if Xvfb or dbus-daemon is missing, or if there's no
    display to inherit.
    """
    if display not in ("xvfb", "inherit"):
        raise pytest.UsageError(f"gtk_display must be xvfb or inherit, not {display!r}")
    if _gtk_initialized():
        raise pytest.UsageError("GTK was initialised before PyLiite4.testing could isolate it: load the plugin with "
                                "-p PyLiite4.testing or its entry point rather than from a conftest.py that imports "
                                "Gtk first")
    wayland = display == "inherit" and os.environ.get("GDK_BACKEND") == "wayland"
    if display == "inherit" and not wayland and not os.environ.get("DISPLAY"):
        raise pytest.UsageError("gtk_display = inherit, but there's no $DISPLAY: run pytest under xvfb-run -a, or "
                                "let the plugin start Xvfb")
    for program in ["dbus-daemon", *(["Xvfb"] if display == "xvfb" else [])]:
        if shutil.which(program) is None:
            raise pytest.UsageError(f"PyLiite4.testing needs {program}, which isn't installed")

    isolation = _Isolation()
    try:
        isolation.directory = tempfile.mkdtemp(prefix="pyliite4-testing-")
        for name in ("config", "data", "state", *([] if wayland else ["runtime"])):
            os.mkdir(os.path.join(isolation.directory, name), 0o700)
            isolation.set(f"XDG_{name.upper()}_{'DIR' if name == 'runtime' else 'HOME'}",
                          os.path.join(isolation.directory, name))
        debug = [flag for flag in os.environ.get("GDK_DEBUG", "").split(",") if flag]
        isolation.set("GDK_DEBUG", ",".join(debug if "no-portals" in debug else [*debug, "no-portals"]))
        isolation.set("ADW_DISABLE_PORTAL", "1")
        # GTK's in-process backend: no accessibility bus, but roles and states are recorded for tests to check.
        isolation.set("GTK_A11Y", "test")
        isolation.set("GSETTINGS_BACKEND", "memory")
        isolation.set("NO_AT_BRIDGE", "1")
        if not wayland:
            # GDK prefers Wayland, and finds wayland-0 by itself, so name the backend too.
            isolation.set("WAYLAND_DISPLAY", None)
            isolation.set("GDK_BACKEND", "x11")
        if display == "xvfb":
            number = isolation.start(["Xvfb", "-displayfd", "{fd}", "-nolisten", "tcp", "-noreset",
                                      "-screen", "0", "1280x1024x24"], "Xvfb")
            isolation.set("DISPLAY", f":{number}")
            isolation.set("XAUTHORITY", None)
            isolation.set(_PRIVATE_DISPLAY, f":{number}")
        bus_config = os.path.join(isolation.directory, "session-bus.conf")
        with open(bus_config, "w") as file:
            file.write(_BUS_CONFIG)
        isolation.set("DBUS_SESSION_BUS_ADDRESS", isolation.start(
            ["dbus-daemon", f"--config-file={bus_config}", "--nofork", "--print-address={fd}"], "dbus-daemon"))
        isolation.watch()
    except BaseException:
        isolation.stop()
        raise
    return isolation.stop


# The pytest plugin


_ENABLED = pytest.StashKey[bool]()
_UNDO = pytest.StashKey[Callable[[], None]]()
_PROBLEMS = pytest.StashKey[Problems]()


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("gtk", "GTK testing (PyLiite4.testing)")
    group.addoption("--gtk", action="store_true", default=None,
                    help="isolate GTK, provide the GTK fixtures and fail tests on GLib warnings")
    group.addoption("--gtk-display", choices=("xvfb", "inherit"), default=None,
                    help="start a private Xvfb (the default), or use $DISPLAY as it is")
    parser.addini("gtk", "enable PyLiite4.testing, as --gtk does", type="bool", default=False)
    parser.addini("gtk_display", "xvfb or inherit, as --gtk-display", default="xvfb")
    parser.addini("gtk_log_level", "fail tests on GLib messages at this level or above: error, critical, warning, "
                  "message or none", default="warning")
    parser.addini("gtk_log_ignore", "regular expressions for GLib messages that don't fail tests", type="linelist",
                  default=[])


def _option(config: pytest.Config, name: str) -> Any:
    # Before pytest_configure the command line is parsed only into known_args_namespace.
    value = getattr(config.known_args_namespace, name, None)
    return value if value is not None else config.getoption(name, default=None)


def _setup(config: pytest.Config) -> None:
    if _ENABLED in config.stash:
        return
    option = _option(config, "gtk")
    config.stash[_ENABLED] = enabled = bool(option if option is not None else config.getini("gtk"))
    if enabled:
        config.stash[_UNDO] = isolate_environment(_option(config, "gtk_display") or config.getini("gtk_display"))


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config: pytest.Config, parser: pytest.Parser, args: list[str]) -> None:
    # Before conftest.py files load, which may import Gtk. Only plugins loaded with -p or an entry point see this.
    _setup(early_config)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "gtk_log_ignore(*patterns): GLib messages matching any of these regular "
                            "expressions don't fail the test")
    _setup(config)


def pytest_unconfigure(config: pytest.Config) -> None:
    undo = config.stash.get(_UNDO, None)
    if undo is not None:
        del config.stash[_UNDO]
        undo()


def _problems(item: pytest.Item) -> Problems:
    problems = item.stash.get(_PROBLEMS, None)
    if problems is None:
        ignore = list(item.config.getini("gtk_log_ignore"))
        for marker in item.iter_markers("gtk_log_ignore"):
            ignore += marker.args
        problems = collect_problems(item.config.getini("gtk_log_level"), ignore)
        item.stash[_PROBLEMS] = problems
    return problems


def _watch(item: pytest.Item, when: str) -> Generator[None, object, object]:
    if not item.config.stash.get(_ENABLED, False):
        return (yield)
    problems = _problems(item)
    with problems:
        try:
            result = yield
        except BaseException:
            if failures := problems.failures():
                item.add_report_section(when, "gtk", "\n".join(failures))
            problems.clear()
            raise
    try:
        problems.check()
    except AssertionError as error:
        pytest.fail(str(error), pytrace=False)
    return result


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item: pytest.Item) -> Generator[None, object, object]:
    return (yield from _watch(item, "setup"))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, object, object]:
    return (yield from _watch(item, "call"))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> Generator[None, object, object]:
    return (yield from _watch(item, "teardown"))


# Fixtures


@pytest.fixture(scope="session")
def _gtk_session(pytestconfig: pytest.Config) -> None:
    if not pytestconfig.stash.get(_ENABLED, False):
        pytest.fail("the GTK fixtures need PyLiite4.testing enabled: pass --gtk, or set gtk = true in the pytest "
                    "configuration", pytrace=False)
    from PyLiite4 import Gdk, Gtk

    if not Gtk.init_check() or Gdk.Display.get_default() is None:
        pytest.fail(f"GTK couldn't open a display (DISPLAY={os.environ.get('DISPLAY')!r})", pytrace=False)


@pytest.fixture
def gtk_log(request: pytest.FixtureRequest, _gtk_session: None) -> Problems:
    """The GLib messages and callback exceptions of the running test, which fail it unless removed.

    ``gtk_log.take("pattern")`` removes and returns the expected messages; ``gtk_log.exceptions.clear()`` accepts
    the exceptions.
    """
    return _problems(request.node)


@pytest.fixture
def gtk_asyncio(_gtk_session: None) -> Iterator[asyncio.AbstractEventLoop]:
    """GLib's asyncio loop, marked running for the test as ``Gio.Application.run()`` marks it.

    Coroutines and tasks, the application's ``create_asyncio_task()`` ones among them, then make progress while the
    helpers wait, and Gio's async methods can be awaited. ``gtk_app`` uses it, as an application's run does.
    """
    from PyLiite4 import use_asyncio

    loop: Any = use_asyncio()
    with loop.running(lambda: None):
        yield loop


@pytest.fixture
def gtk_app_class() -> type[Gtk.Application]:
    """The class ``gtk_app`` instantiates. Override this fixture to return ``Adw.Application`` or your own."""
    from PyLiite4 import Gtk

    return Gtk.Application


_application_ids = itertools.count(1)


@pytest.fixture
def gtk_app(gtk_app_class: type[Gtk.Application], gtk_asyncio: asyncio.AbstractEventLoop) -> Iterator[Gtk.Application]:
    """A registered application, not running: the test drives the main loop through the helpers. Its asyncio tasks
    run, as under ``run()``; see ``gtk_asyncio``.

    Each test gets its own, with a unique application id, since an id can't be registered twice in one process.
    ``gtk_app.activate()`` runs your ``activate`` handler. Its windows are destroyed afterwards.
    """
    from PyLiite4 import Gio

    app = gtk_app_class(application_id=f"org.pyliite4.testing.App{os.getpid()}x{next(_application_ids)}",
                        flags=Gio.ApplicationFlags.NON_UNIQUE)
    app.register(None)
    yield app
    for window in app.get_windows():
        window.destroy()
    iterate()


class GtkBot:
    """The helpers, plus clean-up: windows shown through it, or opened during the test, are destroyed after it.

    Returned by the ``gtkbot`` fixture. ``input`` is the ``RealInput`` for real pointer and keyboard events, and
    ``announcements`` what the test announced to screen readers.
    """

    def __init__(self) -> None:
        from PyLiite4 import Gtk, _fixes

        _fixes.announcements.clear()
        self._existing = {id(window) for window in Gtk.Window.list_toplevels()}
        self._windows: list[Gtk.Window] = []
        self._input: RealInput | None = None

    @property
    def input(self) -> RealInput:
        """Real pointer and keyboard input; see ``RealInput``."""
        if self._input is None:
            self._input = real_input()
        return self._input

    @property
    def announcements(self) -> list[str]:
        """The messages announced to screen readers during the test (``Gtk.Accessible.announce``), oldest first."""
        from PyLiite4 import _fixes

        return [message for message, _priority in _fixes.announcements]

    def add(self, window: Gtk.Window) -> None:
        """Destroy ``window`` after the test."""
        self._windows.append(window)

    def show(self, widget: Gtk.Widget, timeout: float = DEFAULT_TIMEOUT) -> Gtk.Window:
        """Show ``widget`` with ``show_window()``, in a window of its own unless it is one, and return the window,
        which is destroyed after the test."""
        from PyLiite4 import Gtk

        window = widget if isinstance(widget, Gtk.Window) else Gtk.Window(child=widget)
        self.add(window)
        show_window(window, timeout)
        return window

    def close(self) -> None:
        """Release held buttons, destroy the test's windows and handle what that set off."""
        from PyLiite4 import Gtk

        if self._input is not None:
            self._input.release_all()
        windows = self._windows + [window for window in Gtk.Window.list_toplevels()
                                   if isinstance(window, Gtk.Window) and id(window) not in self._existing
                                   and window not in self._windows]
        for window in windows:
            window.destroy()
        self._windows.clear()
        iterate()

    iterate = staticmethod(iterate)
    wait = staticmethod(wait)
    wait_until = staticmethod(wait_until)
    wait_signal = staticmethod(wait_signal)
    expect_signal = staticmethod(expect_signal)
    click = staticmethod(click)
    activate = staticmethod(activate)
    type_text = staticmethod(type_text)
    press_key = staticmethod(press_key)
    if TYPE_CHECKING:
        # Typed through the functions, whose overloads staticmethod() would hide.
        @overload
        @staticmethod
        def find(root: Gtk.Widget, cls: None = None, *, name: str | re.Pattern[str] | None = None,
                 label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
                 predicate: Callable[[Gtk.Widget], bool] | None = None) -> Gtk.Widget: ...
        @overload
        @staticmethod
        def find(root: Gtk.Widget, cls: type[W], *, name: str | re.Pattern[str] | None = None,
                 label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
                 predicate: Callable[[W], bool] | None = None) -> W: ...
        @staticmethod
        def find(root: Gtk.Widget, cls: type[Any] | None = None, **criteria: Any) -> Any: ...
        @overload
        @staticmethod
        def find_all(root: Gtk.Widget, cls: None = None, *, name: str | re.Pattern[str] | None = None,
                     label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
                     predicate: Callable[[Gtk.Widget], bool] | None = None) -> list[Gtk.Widget]: ...
        @overload
        @staticmethod
        def find_all(root: Gtk.Widget, cls: type[W], *, name: str | re.Pattern[str] | None = None,
                     label: str | re.Pattern[str] | None = None, buildable_id: str | None = None,
                     predicate: Callable[[W], bool] | None = None) -> list[W]: ...
        @staticmethod
        def find_all(root: Gtk.Widget, cls: type[Any] | None = None, **criteria: Any) -> list[Any]: ...
    else:
        find = staticmethod(find)
        find_all = staticmethod(find_all)


@pytest.fixture
def gtkbot(_gtk_session: None) -> Iterator[GtkBot]:
    """A ``GtkBot``, like pytest-qt's ``qtbot``."""
    bot = GtkBot()
    yield bot
    bot.close()
