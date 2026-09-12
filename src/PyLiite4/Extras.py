"""What Qt has and GTK lacks, built from GTK's public pieces and used the way GTK's own API is.

- ``register_font()``: make a font from memory, a GResource or a file usable by the application, like
  ``QFontDatabase.addApplicationFont``.
- ``Tip`` and ``show_tip()``: a tooltip shown when the application decides, at a widget or a spot in it, like
  ``QToolTip.showText``.
"""

from __future__ import annotations

import ctypes
import os
from typing import Any

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk, Pango

__all__ = ["Tip", "hide_tip", "register_font", "show_tip"]

# The fonts register_font() added, as paths fontconfig reads: their own, or /proc/self/fd/N for a memfd that stays
# open as long as the process runs.
_font_paths: list[str] = []
_font_families: dict[str, list[str]] = {}


def _font_families_in(path: str) -> list[str]:
    """The family names fontconfig gives the faces in the font file at ``path``, or [] if it isn't a font."""
    fontconfig = ctypes.CDLL("libfontconfig.so.1")
    fontconfig.FcFreeTypeQuery.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_void_p,
                                           ctypes.POINTER(ctypes.c_int)]
    fontconfig.FcFreeTypeQuery.restype = ctypes.c_void_p
    fontconfig.FcPatternGetString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int,
                                              ctypes.POINTER(ctypes.c_char_p)]
    fontconfig.FcPatternDestroy.argtypes = [ctypes.c_void_p]
    families: list[str] = []
    face, count = 0, ctypes.c_int(1)
    while face < max(count.value, 1):
        pattern = fontconfig.FcFreeTypeQuery(path.encode(), face, None, ctypes.byref(count))
        if not pattern:
            break
        index, name = 0, ctypes.c_char_p()
        # 0 is FcResultMatch.
        while fontconfig.FcPatternGetString(pattern, b"family", index, ctypes.byref(name)) == 0:
            family = (name.value or b"").decode()
            if family and family not in families:
                families.append(family)
            index += 1
        fontconfig.FcPatternDestroy(pattern)
        face += 1
    return families


def _reload_fonts() -> None:
    """Give the default font map every registered font, and make it forget what it found before.

    Pango keeps the fonts it chose for each description, so a family looked up before its font was added would stay
    on its fallback. Clearing the cache also replaces the font map's fontconfig configuration, which drops added
    fonts, so they are all added again afterwards. Pango then announces the change and GTK lays text out again.
    """
    from PyLiite4 import PangoCairo

    font_map = PangoCairo.FontMap.get_default()
    pangoft2 = ctypes.CDLL("libpangoft2-1.0.so.0")
    pangoft2.pango_fc_font_map_cache_clear.argtypes = [ctypes.c_void_p]
    # PangoFc isn't bound, and PyGObject's hash() of an object is its address.
    pangoft2.pango_fc_font_map_cache_clear(hash(font_map))
    for path in _font_paths:
        if not font_map.add_font_file(path):
            raise RuntimeError(f"Pango refused the font {path}")


def register_font(source: bytes | GLib.Bytes | Gio.File | str | os.PathLike[str]) -> list[str]:
    """Make a font usable by this application, and return the family names it adds.

    ``source`` is the font's data, a ``Gio.File`` (``Gio.File.new_for_uri("resource:///org/example/App/x.ttf")``
    for a font shipped in a GResource like the application's other files), or a path. Any format fontconfig
    reads works: TrueType, OpenType, collections, WOFF.

    Afterwards CSS ``font-family`` and ``Pango.FontDescription`` find the families, and text already laid out in them
    is laid out again. Nothing is installed: the font is this process's alone, and data stays in memory. Call it on
    the main thread; registering the same file twice returns the same families. Raises ``ValueError`` if
    ``source`` isn't a font, and ``FileNotFoundError`` for a path that doesn't exist.

    Other fonts added to the default font map directly, with ``add_font_file()``, are dropped by the first call.
    """
    data: bytes | None = None
    path: str | None = None
    if isinstance(source, (bytes, bytearray, memoryview)):
        data = bytes(source)
    elif isinstance(source, GLib.Bytes):
        data = bytes(source.get_data() or b"")
    elif isinstance(source, Gio.File):
        native = source.get_path()
        if native is not None:
            path = native
        else:
            data = bytes(source.load_bytes(None)[0].get_data() or b"")
    else:
        path = os.fspath(source)
    if path is not None:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        if path in _font_families:
            return list(_font_families[path])
    descriptor = None
    if data is not None:
        descriptor = os.memfd_create("pyliite4-font")
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view):]
        path = f"/proc/self/fd/{descriptor}"
    assert path is not None
    families = _font_families_in(path)
    if not families:
        if descriptor is not None:
            os.close(descriptor)
        raise ValueError(f"{'the data' if data is not None else path} isn't a font fontconfig can read")
    _font_paths.append(path)
    _font_families[path] = families
    _reload_fonts()
    return list(families)


# Tips

# GTK's own tooltip look, from its default theme. GTK weighs selectors only within a style sheet, so this goes
# just above the priority GTK adds its own theme at, SETTINGS (libadwaita's is lower, at THEME), and below
# APPLICATION, so an application's style sheet can still restyle tips. GTK draws a popover's bubble from its arrow
# node's style, arrow shown or not, so that node gets the look too.
_TIP_CSS = """
popover.pyliite4-tip { box-shadow: none; }
popover.pyliite4-tip > arrow,
popover.pyliite4-tip > contents {
  background-color: rgba(0, 0, 0, 0.8);
  background-clip: padding-box;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: none;
  color: white;
}
popover.pyliite4-tip > contents {
  border-radius: 8px;
  padding: 6px 10px;
}
"""
_tip_css_displays: list[Gdk.Display] = []


class Tip(Gtk.Popover):
    """A tooltip the application shows when it decides, where it decides: the equivalent of ``QToolTip.showText``.

    GTK shows a widget's tooltip only while the pointer rests on it. A ``Tip`` is shown with ``popup_at()``, at a
    widget or a rectangle in it, and looks like GTK's tooltips. It takes no focus and grabs no input, so typing goes
    on in the focused widget. It hides after ``timeout`` milliseconds (-1 picks a time from the text's length, 0
    keeps it up), when the pointer moves off the widget, or on any key press or click in the window, as tooltips
    do.
    Its text is also announced, politely, to screen readers.

    Most code wants ``show_tip()``, which keeps one tip for the application as Qt does.
    """

    __gtype_name__ = "PyLiite4Tip"

    text = GObject.Property(type=str, default="", nick="Text", blurb="The tip's text")
    use_markup = GObject.Property(type=bool, default=False, nick="Use markup", blurb="Whether text is Pango markup")
    timeout = GObject.Property(type=int, default=-1, minimum=-1, nick="Timeout",
                               blurb="Milliseconds until the tip hides: -1 from the text's length, 0 never")

    def __init__(self, **properties: Any) -> None:
        super().__init__(autohide=False, has_arrow=False, can_focus=False, focusable=False,
                         accessible_role=Gtk.AccessibleRole.TOOLTIP, **properties)
        self.add_css_class("pyliite4-tip")
        label = Gtk.Label(wrap=True, max_width_chars=50, xalign=0, can_target=False)
        self.bind_property("text", label, "label", GObject.BindingFlags.SYNC_CREATE)
        self.bind_property("use-markup", label, "use-markup", GObject.BindingFlags.SYNC_CREATE)
        self.set_child(label)
        self._timer = 0
        self._watched: list[Gtk.EventController] = []
        self._parent_handler: tuple[Gtk.Widget, int] | None = None
        self.connect("closed", lambda _tip: self._stop_watching())

    def plain_text(self) -> str:
        """The text without markup, as it is announced."""
        if not self.use_markup:
            return str(self.text)
        try:
            return str(Pango.parse_markup(self.text, -1, "\0")[2])
        except GLib.Error:
            return str(self.text)

    def popup_at(self, widget: Gtk.Widget, rect: Gdk.Rectangle | tuple[int, int] | tuple[int, int, int, int] |
                 None = None) -> None:
        """Show the tip at ``widget``, or at ``rect`` in its coordinates: a ``Gdk.Rectangle``, ``(x, y, width,
        height)`` or a point ``(x, y)``. Raises ``ValueError`` if the widget isn't shown."""
        if not widget.get_mapped():
            raise ValueError(f"can't show a tip at {widget!r}: it isn't shown")
        self.popdown()
        display = widget.get_display()
        if display not in _tip_css_displays:
            provider = Gtk.CssProvider()
            provider.load_from_string(_TIP_CSS)
            Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_SETTINGS + 1)
            _tip_css_displays.append(display)
        if self.get_parent() is not widget:
            self._leave_parent()
            self.set_parent(widget)
            # A popover must leave its parent before the parent goes, shown or not.
            self._parent_handler = (widget, widget.connect("unrealize", lambda _widget: self._leave_parent()))
        if rect is not None and not isinstance(rect, Gdk.Rectangle):
            x, y, width, height = (*rect, 1, 1) if len(rect) == 2 else rect
            rect = Gdk.Rectangle()
            rect.x, rect.y, rect.width, rect.height = x, y, width, height
        self.set_pointing_to(rect)
        self.popup()
        self._watch(widget)
        timeout = self.timeout if self.timeout >= 0 else min(10000, 2000 + 50 * len(self.plain_text()))
        if timeout:
            self._timer = GLib.timeout_add(timeout, self._timed_out)
        widget.announce(self.plain_text(), Gtk.AccessibleAnnouncementPriority.MEDIUM)

    def _timed_out(self) -> bool:
        self._timer = 0
        self.popdown()
        return False

    def _watch(self, widget: Gtk.Widget) -> None:
        root = widget.get_root()
        if not isinstance(root, Gtk.Widget):
            return

        def moved(_controller: Gtk.EventControllerMotion, x: float, y: float) -> None:
            # Motion over the window rather than "leave" on the widget: a controller added while the pointer is
            # already over its widget never saw it enter, so it wouldn't report it leaving.
            under = root.pick(x, y, Gtk.PickFlags.DEFAULT)
            if under is None or not (under is widget or under.is_ancestor(widget)):
                self.popdown()

        motion = Gtk.EventControllerMotion(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        motion.connect("motion", moved)
        keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", lambda *_args: self.popdown() or False)
        clicks = Gtk.GestureClick(button=0, propagation_phase=Gtk.PropagationPhase.CAPTURE)
        clicks.connect("pressed", lambda *_args: self.popdown())
        self._watched = [motion, keys, clicks]
        for controller in self._watched:
            root.add_controller(controller)

    def _stop_watching(self) -> None:
        if self._timer:
            GLib.Source.remove(self._timer)
            self._timer = 0
        watched, self._watched = self._watched, []

        # Later: the tip usually hides from one of these controllers' own handlers, mid-event.
        def remove() -> bool:
            for controller in watched:
                owner = controller.get_widget()
                if owner is not None:
                    owner.remove_controller(controller)
            return False

        if watched:
            GLib.idle_add(remove)

    def _leave_parent(self) -> None:
        self.popdown()
        if self._parent_handler is not None:
            owner, handler = self._parent_handler
            owner.disconnect(handler)
            self._parent_handler = None
        if self.get_parent() is not None:
            self.unparent()


_shared_tip: Tip | None = None


def show_tip(widget: Gtk.Widget, text: str, rect: Gdk.Rectangle | tuple[int, int] | tuple[int, int, int, int] |
             None = None, *, use_markup: bool = False, timeout: int = -1) -> Tip:
    """Show ``text`` as a tooltip at ``widget``, or at ``rect`` in it, now: ``QToolTip.showText(pos, text, widget)``.

    The application has one such tip, as in Qt: showing another moves it. ``timeout`` is in milliseconds, -1 for a
    time from the text's length, 0 to keep it up until the pointer leaves, a key is pressed or ``hide_tip()``. Returns
    the ``Tip``. See ``Tip`` for how it behaves.
    """
    global _shared_tip
    if _shared_tip is None:
        _shared_tip = Tip()
    _shared_tip.popdown()
    _shared_tip.text, _shared_tip.use_markup, _shared_tip.timeout = text, use_markup, timeout
    _shared_tip.popup_at(widget, rect)
    return _shared_tip


def hide_tip() -> None:
    """Hide the tip ``show_tip()`` showed, if it is up."""
    if _shared_tip is not None:
        _shared_tip.popdown()
