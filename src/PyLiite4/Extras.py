"""A few application widgets and helpers built from GTK's public API.

If you're coming from Qt, the equivalents below should help you find your way.

- ``register_font()``: make a font from memory, a GResource or a file usable by the application, like
  ``QFontDatabase.addApplicationFont``.
- ``Tip`` and ``show_tip()``: a tooltip shown when the application decides, at a widget or a spot in it, like
  ``QToolTip.showText``.
- ``ShortcutRecorder``: a button that records the next key combination pressed, like ``QKeySequenceEdit``.
- ``RichView``: a text view that shows formatted text from an HTML subset, like ``QTextBrowser.setHtml``.
"""

from __future__ import annotations

import ctypes
import os
from typing import TYPE_CHECKING, Any

from PyLiite4 import Adw, Gdk, Gio, GLib, GObject, Graphene, Gtk, Pango
from PyLiite4 import _rich

if TYPE_CHECKING:
    from collections.abc import Callable

    from PyLiite4._runtime import BoundSignal

__all__ = ["RichView", "ShortcutRecorder", "Tip", "hide_tip", "register_font", "show_tip"]

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
_installed_css: list[tuple[Gdk.Display, str]] = []


def _install_css(display: Gdk.Display, css: str, priority: int) -> None:
    """Add ``css`` for ``display`` at ``priority``, once."""
    if (display, css) in _installed_css:
        return
    provider = Gtk.CssProvider()
    provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(display, provider, priority)
    _installed_css.append((display, css))


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
        height)`` or a point ``(x, y)``. Nothing happens if the widget isn't shown, as a tip there couldn't be seen;
        handlers that react to changes can call it without checking."""
        self.popdown()
        if not widget.get_mapped():
            return
        _install_css(widget.get_display(), _TIP_CSS, Gtk.STYLE_PROVIDER_PRIORITY_SETTINGS + 1)
        if self.get_parent() is not widget:
            self._leave_parent()
            self.set_parent(widget)
            # Unparent even hidden popovers before their parent goes away. Hiding isn't cleanup.
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

        # Defer cleanup: we're usually inside one of these controllers' handlers, still handling the event.
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
    time from the text's length, 0 to keep it up until the pointer leaves, a key is pressed or ``hide_tip()``. Nothing
    is shown if the widget isn't. Returns the ``Tip``. See ``Tip`` for how it behaves.
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


# Recording shortcuts

# Keys that only modify another, which a shortcut can't consist of.
_MODIFIER_KEYVALS = {Gdk.keyval_from_name(name) for name in (
    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Super_L", "Super_R",
    "Hyper_L", "Hyper_R", "ISO_Level3_Shift", "ISO_Level5_Shift", "Caps_Lock", "Num_Lock", "Mode_switch")}


# Keycaps for Adw.ShortcutLabel when libadwaita's style sheet isn't loaded, after GTK's own for its deprecated
# shortcut label, in the text colour so they suit any theme. Just above GTK's theme, as for tips.
_KEYCAP_CSS = """
shortcut-label > box { border-spacing: 6px; }
shortcut-label > box > label.keycap {
  min-width: 20px;
  min-height: 25px;
  padding: 0 6px 2px;
  border: 1px solid alpha(currentColor, 0.25);
  border-radius: 5px;
  background-color: alpha(currentColor, 0.05);
  box-shadow: inset 0 -2px alpha(currentColor, 0.12);
  font-size: smaller;
}
"""


def _all_true(_hint: Any, _accumulated: bool, handler_return: bool, *_data: Any) -> tuple[bool, bool]:
    # Go on while handlers accept; the first that rejects decides.
    return handler_return, handler_return


class ShortcutRecorder(Gtk.Button):
    """A button showing a shortcut, which records a new one when clicked: the equivalent of ``QKeySequenceEdit``.

    It works like the shortcut editor in GNOME Settings. Clicking it shows ``prompt``, and the next key combination
    pressed becomes ``accelerator``, in the form ``Gtk.accelerator_name()`` gives and
    ``Gtk.Application.set_accels_for_action()`` takes. Escape cancels, Backspace clears it to ``""``, and moving the
    focus away cancels. While it records, the window's own shortcuts and, where the desktop allows, the system's
    don't act on the keys.

    A printable key without a modifier, which would stop that character being typed, isn't accepted unless
    ``require-modifier`` is false. Handlers of ``validate(accelerator) -> bool`` can refuse others, a shortcut already
    in use say; the recorder then keeps recording. Follow ``notify::accelerator`` for changes and
    ``notify::recording`` for the start and end of recording.
    """

    __gtype_name__ = "PyLiite4ShortcutRecorder"
    __gsignals__ = {
        "validate": (GObject.SignalFlags.RUN_LAST, bool, (str,), _all_true),
    }
    if TYPE_CHECKING:
        validate: BoundSignal[Callable[[ShortcutRecorder, str], bool]]

    accelerator = GObject.Property(type=str, default="", nick="Accelerator",
                                   blurb="The shortcut, as Gtk.accelerator_name() writes it, or empty for none")
    prompt = GObject.Property(type=str, default="Press a shortcut…", nick="Prompt",
                              blurb="Shown while recording")
    placeholder = GObject.Property(type=str, default="Disabled", nick="Placeholder",
                                   blurb="Shown when there is no shortcut")
    require_modifier = GObject.Property(type=bool, default=True, nick="Require modifier",
                                        blurb="Whether a printable key needs a modifier")

    def __init__(self, **properties: Any) -> None:
        super().__init__(**properties)
        self.add_css_class("pyliite4-shortcut-recorder")
        # Before the keycaps are first styled: GTK doesn't restyle them for a style sheet added later.
        display = Gdk.Display.get_default()
        if display is not None and not Adw.is_initialized():
            _install_css(display, _KEYCAP_CSS, Gtk.STYLE_PROVIDER_PRIORITY_SETTINGS + 1)
        self._recording = False
        self._label = Adw.ShortcutLabel(halign=Gtk.Align.CENTER)
        self.bind_property("accelerator", self._label, "accelerator", GObject.BindingFlags.SYNC_CREATE)
        self.bind_property("placeholder", self._label, "disabled-text", GObject.BindingFlags.SYNC_CREATE)
        prompt = Gtk.Label()
        self.bind_property("prompt", prompt, "label", GObject.BindingFlags.SYNC_CREATE)
        self._stack = Gtk.Stack()
        self._stack.add_named(self._label, "shortcut")
        self._stack.add_named(prompt, "prompt")
        self.set_child(self._stack)
        self._keys = Gtk.EventControllerKey(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        self._keys.connect("key-pressed", self._key_pressed)
        self._focus = Gtk.EventControllerFocus()
        self._focus.connect("leave", lambda _controller: self.cancel())
        self.add_controller(self._focus)
        self._watching: Gtk.Widget | None = None
        self.connect("clicked", lambda _button: self.cancel() if self._recording else self.record())

    @GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READABLE, nick="Recording",
                      blurb="Whether the next key combination pressed is being recorded")
    def recording(self) -> bool:
        return self._recording

    def do_validate(self, accelerator: str) -> bool:
        return True

    def record(self) -> None:
        """Start recording, as a click does."""
        if self._recording or not self.get_mapped():
            return
        root = self.get_root()
        if not isinstance(root, Gtk.Widget):
            return
        self.grab_focus()
        # On the window, in the capture phase: ahead of its shortcuts, mnemonics and the focus widget's bindings.
        root.add_controller(self._keys)
        self._watching = root
        surface = root.get_native().get_surface() if root.get_native() is not None else None
        if isinstance(surface, Gdk.Toplevel):
            surface.inhibit_system_shortcuts(None)
        self._set_recording(True)
        self.announce(self.prompt, Gtk.AccessibleAnnouncementPriority.MEDIUM)

    def cancel(self) -> None:
        """Stop recording and keep the shortcut as it was."""
        if not self._recording:
            return
        if self._watching is not None:
            self._watching.remove_controller(self._keys)
            native = self._watching.get_native()
            surface = native.get_surface() if native is not None else None
            if isinstance(surface, Gdk.Toplevel):
                surface.restore_system_shortcuts()
            self._watching = None
        self._set_recording(False)

    def clear(self) -> None:
        """Remove the shortcut."""
        self.accelerator = ""

    def _set_recording(self, recording: bool) -> None:
        self._recording = recording
        self._stack.set_visible_child_name("prompt" if recording else "shortcut")
        self.notify("recording")

    def _key_pressed(self, _controller: Gtk.EventControllerKey, keyval: int, _keycode: int,
                     state: Gdk.ModifierType) -> bool:
        if keyval in _MODIFIER_KEYVALS:
            return True
        modifiers = Gdk.ModifierType(state & Gtk.accelerator_get_default_mod_mask())
        lower = Gdk.keyval_to_lower(keyval)
        # As GNOME Settings does: an upper-case key means Shift, written as Shift and the lower-case key.
        if lower != keyval:
            modifiers = Gdk.ModifierType(modifiers | Gdk.ModifierType.SHIFT_MASK)
        if lower == Gdk.keyval_from_name("ISO_Left_Tab"):
            lower = Gdk.keyval_from_name("Tab")
        if not modifiers and lower == Gdk.keyval_from_name("Escape"):
            self.cancel()
            return True
        if not modifiers and lower == Gdk.keyval_from_name("BackSpace"):
            self.cancel()
            self.clear()
            return True
        if self.require_modifier and not modifiers & ~Gdk.ModifierType.SHIFT_MASK and Gdk.keyval_to_unicode(lower):
            self.error_bell()
            return True
        if not Gtk.accelerator_valid(lower, modifiers):
            self.error_bell()
            return True
        accelerator = Gtk.accelerator_name(lower, modifiers)
        if not self.emit("validate", accelerator):
            return True
        self.cancel()
        self.accelerator = accelerator
        self.announce(Gtk.accelerator_get_label(lower, modifiers), Gtk.AccessibleAnnouncementPriority.MEDIUM)
        return True


# Formatted text

# The look of tables, in the text colour so it suits any theme, above GTK's theme as for tips.
_TABLE_CSS = """
.pyliite4-rich-table { border: 1px solid alpha(currentColor, 0.15); border-radius: 6px; }
.pyliite4-rich-table > label { padding: 4px 10px; border-bottom: 1px solid alpha(currentColor, 0.1); }
.pyliite4-rich-table > label.header { font-weight: bold; background-color: alpha(currentColor, 0.05); }
"""
_HEADING_SCALES = {1: 1.6, 2: 1.4, 3: 1.25, 4: 1.1, 5: 1.0, 6: 0.9}
_INDENT = 22
# The light and dark link colours of GTK's default theme, when libadwaita doesn't give an accent colour.
_LINKS = ("#1b6acb", "#78aeed")


def _rgba(colour: str | None) -> Gdk.RGBA | None:
    if not colour:
        return None
    rgba = Gdk.RGBA()
    return rgba if rgba.parse(colour) else None


def _with_alpha(rgba: Gdk.RGBA, alpha: float) -> Gdk.RGBA:
    copy = rgba.copy()
    copy.alpha = rgba.alpha * alpha
    return copy


def _pango_markup(runs: tuple[_rich.Run, ...]) -> str:
    """Runs as Pango markup, for a table cell's label."""
    parts = []
    for text, style in runs:
        attributes = []
        if style.bold:
            attributes.append('weight="bold"')
        if style.italic:
            attributes.append('style="italic"')
        if style.underline or style.link:
            attributes.append('underline="single"')
        if style.strike:
            attributes.append('strikethrough="true"')
        if style.code or style.family:
            attributes.append(f'font_family="{GLib.markup_escape_text(style.family or "monospace")}"')
        for name, colour in (("foreground", style.fg), ("background", style.bg)):
            if _rgba(colour) is not None:
                attributes.append(f'{name}="{GLib.markup_escape_text(_rgba(colour).to_string())}"')  # type: ignore[union-attr]
        piece = GLib.markup_escape_text(text)
        if attributes:
            piece = f"<span {' '.join(attributes)}>{piece}</span>"
        if style.link:
            piece = f'<a href="{GLib.markup_escape_text(style.link)}">{piece}</a>'
        parts.append(piece)
    return "".join(parts)


class _TableBox(Gtk.Widget):
    """Holds a table's grid at a fixed width, and asks for the height the grid needs at it.

    GtkTextView measures an embedded widget as if its width didn't depend on its height, which wrapping cells do; a
    constant size keeps that from going wrong, and the width is set from the view's in RichView.do_size_allocate.
    """

    __gtype_name__ = "PyLiite4RichTable"

    def __init__(self, grid: Gtk.Grid) -> None:
        super().__init__()
        self.grid = grid
        self.width = 0
        grid.set_parent(self)

    def natural_width(self) -> int:
        return int(self.grid.measure(Gtk.Orientation.HORIZONTAL, -1)[1])

    def do_get_request_mode(self) -> Gtk.SizeRequestMode:
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        width = self.width or self.natural_width()
        if orientation == Gtk.Orientation.HORIZONTAL:
            return width, width, -1, -1
        minimum, natural, _, _ = self.grid.measure(Gtk.Orientation.VERTICAL, width)
        return minimum, natural, -1, -1

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        self.grid.allocate(width, height, baseline, None)

    def do_dispose(self) -> None:
        if self.grid.get_parent() is self:
            self.grid.unparent()
        Gtk.Widget.do_dispose(self)


class _Rendered:
    """A block as it is in the buffer: where it starts, and the table widget it embeds, if any."""

    def __init__(self, block: _rich.Block, mark: Gtk.TextMark) -> None:
        self.block = block
        self.mark = mark
        self.anchor: Gtk.TextChildAnchor | None = None
        self.table: _TableBox | None = None


class RichView(Gtk.TextView):
    """A read-only text view that shows formatted text, the equivalent of ``QTextBrowser`` with ``setHtml``.

    ``set_markup()`` takes the HTML subset ``PyLiite4._rich`` describes, Qt's rich text roughly, with Pango markup's
    tags and span attributes too: paragraphs, headings, lists, quotes, preformatted blocks, rules, tables, links, and
    bold, italic, underlined, struck, monospace and coloured text. Unknown tags show their text; ``script`` and the
    like are dropped. A link is a link only when its scheme is in ``link-schemes``.

    Links emit ``activate-link(uri)`` when clicked, which opens them with ``Gtk.UriLauncher`` unless a handler
    returns true, as ``Gtk.Label``'s does, and ``hover-link(uri)`` when the pointer moves onto one or off (``None``).
    Calling ``set_markup()`` again re-renders only from the first block that changed, so text streamed in a little
    at a time keeps its selection. Copying gives the text with tables as tab-separated lines.

    Colours follow the theme: links take libadwaita's accent colour, and code, quotes and rules the text colour.
    ``get_tag()`` gives the named tags (``link``, ``code``, ``pre``, ``quote``, ``h1``-``h6``) for adjusting. For a
    height cap, put the view in a ``Gtk.ScrolledWindow`` with ``propagate-natural-height`` and ``max-content-height``.
    """

    __gtype_name__ = "PyLiite4RichView"
    __gsignals__ = {
        "activate-link": (GObject.SignalFlags.RUN_LAST, bool, (str,), GObject.signal_accumulator_true_handled),
        "hover-link": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }
    if TYPE_CHECKING:
        activate_link: BoundSignal[Callable[[RichView, str], bool]]
        hover_link: BoundSignal[Callable[[RichView, str | None], None]]

    link_schemes = GObject.Property(type=GObject.TYPE_STRV, nick="Link schemes",
                                    blurb="The URI schemes links may have; others are shown as text")

    def __init__(self, **properties: Any) -> None:
        super().__init__(**properties)
        # Set here rather than passed up: when GtkBuilder creates the view, __init__ gets no properties to pass.
        for name, value in (("editable", False), ("cursor_visible", False), ("wrap_mode", Gtk.WrapMode.WORD_CHAR)):
            if name not in properties and name.replace("_", "-") not in properties:
                self.set_property(name, value)
        if not self.link_schemes:
            self.link_schemes = ["http", "https", "mailto"]
        self.add_css_class("pyliite4-rich-view")
        display = Gdk.Display.get_default()
        if display is not None:
            _install_css(display, _TABLE_CSS, Gtk.STYLE_PROVIDER_PRIORITY_SETTINGS + 1)
        self._markup = ""
        self._rendered: list[_Rendered] = []
        self._style_tags: dict[_rich.Style, Gtk.TextTag] = {}
        self._block_tags: dict[tuple[object, ...], Gtk.TextTag] = {}
        self._links: dict[str, str] = {}
        self._hovered: str | None = None
        self._colours: dict[str, Gdk.RGBA] = {}
        self._named: dict[str, Gtk.TextTag] = {}
        self._pressed: tuple[float, float] | None = None
        self._make_named_tags()

        click = Gtk.GestureClick(button=Gdk.BUTTON_PRIMARY, propagation_phase=Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", lambda _gesture, _n, x, y: setattr(self, "_pressed", (x, y)))
        click.connect("released", self._released)
        self.add_controller(click)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", lambda _controller, x, y: self._hover(self._link_at(x, y)))
        # Coming in from outside, the first position comes with enter, not motion.
        motion.connect("enter", lambda _controller, x, y: self._hover(self._link_at(x, y)))
        motion.connect("leave", lambda _controller: self._hover(None))
        self.add_controller(motion)
        self.connect("map", lambda _view: self._restyle())
        for name in ("left-margin", "right-margin"):
            self.connect(f"notify::{name}", lambda *_args: self._rerender())
        settings = Gtk.Settings.get_default()
        if settings is not None:
            for name in ("gtk-theme-name", "gtk-application-prefer-dark-theme"):
                settings.connect(f"notify::{name}", lambda *_args: self._restyle())
        manager = Adw.StyleManager.get_default()
        for name in ("dark", "accent-color", "high-contrast"):
            manager.connect(f"notify::{name}", lambda *_args: self._restyle())

    # The markup

    @GObject.Property(type=str, default="", nick="Markup", blurb="The text shown, in RichView's HTML subset")
    def markup(self) -> str:
        return self._markup

    @markup.setter  # type: ignore[no-redef]
    def markup(self, markup: str) -> None:
        self.set_markup(markup)

    def set_markup(self, markup: str) -> None:
        """Show ``markup``, re-rendering only from the first block that differs from what is shown."""
        blocks = _rich.parse(markup or "", tuple(self.link_schemes or ()))
        first = 0
        while first < len(blocks) and first < len(self._rendered) and blocks[first] == self._rendered[first].block:
            first += 1
        buffer = self.get_buffer()
        if first < len(self._rendered):
            start = buffer.get_iter_at_mark(self._rendered[first].mark)
            buffer.delete(start, buffer.get_end_iter())
            for rendered in self._rendered[first:]:
                buffer.delete_mark(rendered.mark)
            del self._rendered[first:]
        for block in blocks[first:]:
            self._insert(block)
        if markup != self._markup:
            self._markup = markup
            self.notify("markup")

    def _rerender(self) -> None:
        markup, self._markup = self._markup, ""
        buffer = self.get_buffer()
        buffer.delete(buffer.get_start_iter(), buffer.get_end_iter())
        for rendered in self._rendered:
            buffer.delete_mark(rendered.mark)
        self._rendered = []
        self.set_markup(markup)

    def get_tag(self, name: str) -> Gtk.TextTag | None:
        """The named tag ``link``, ``code``, ``pre``, ``quote`` or ``h1``-``h6``, whose properties all text of that
        kind takes unless its own style sets them."""
        return self._named.get(name)

    def plain_text(self, start: Gtk.TextIter | None = None, end: Gtk.TextIter | None = None) -> str:
        """The text between ``start`` and ``end``, all of it by default, as copying gives it."""
        buffer = self.get_buffer()
        start = start or buffer.get_start_iter()
        end = end or buffer.get_end_iter()
        text = buffer.get_slice(start, end, True)
        tables = iter(self._table_texts(start, end))
        return "".join(next(tables, "") if character == "\ufffc" else character
                       for character in text).replace(_rich.LINE_BREAK, "\n")

    def _table_texts(self, start: Gtk.TextIter, end: Gtk.TextIter) -> list[str]:
        texts = []
        buffer = self.get_buffer()
        for rendered in self._rendered:
            if rendered.anchor is None or rendered.anchor.get_deleted():
                continue
            where = buffer.get_iter_at_child_anchor(rendered.anchor)
            if start.compare(where) <= 0 < end.compare(where):
                texts.append("\n".join("\t".join(_rich.plain(cell.runs).replace("\n", " ") for cell in row)
                                       for row in rendered.block.rows))
        return texts

    # Rendering

    def _make_named_tags(self) -> None:
        table = self.get_buffer().get_tag_table()
        for name in ("link", "code", "pre", "quote", "rule", *(f"h{level}" for level in range(1, 7))):
            tag = Gtk.TextTag(name=f"pyliite4-{name}")
            table.add(tag)
            self._named[name] = tag
        for level, scale in _HEADING_SCALES.items():
            self._named[f"h{level}"].props.scale = scale
            self._named[f"h{level}"].props.weight = Pango.Weight.BOLD
        self._named["code"].props.family = "monospace"
        self._named["pre"].props.family = "monospace"
        self._named["link"].props.underline = Pango.Underline.SINGLE
        # The rule's text is there to be copied; the line is drawn in its place.
        self._named["rule"].props.foreground_rgba = Gdk.RGBA()
        for tag in self._named.values():
            tag.set_priority(0)

    def _restyle(self) -> None:
        text = self.get_color()
        dark = Adw.StyleManager.get_default().get_dark()
        if Adw.is_initialized():
            link = Adw.AccentColor.to_standalone_rgba(Adw.StyleManager.get_default().get_accent_color(), dark)
        else:
            link = _rgba(_LINKS[1 if text.red + text.green + text.blue > 1.5 else 0]) or text
        self._colours = {"text": text, "link": link, "shade": _with_alpha(text, 0.07),
                         "dim": _with_alpha(text, 0.7), "line": _with_alpha(text, 0.25)}
        self._named["link"].props.foreground_rgba = link
        self._named["code"].props.background_rgba = self._colours["shade"]
        self._named["pre"].props.paragraph_background_rgba = self._colours["shade"]
        self._named["quote"].props.foreground_rgba = self._colours["dim"]
        self.queue_draw()

    def _style_tag(self, style: _rich.Style) -> Gtk.TextTag:
        tag = self._style_tags.get(style)
        if tag is not None:
            return tag
        properties: dict[str, Any] = {}
        if style.bold:
            properties["weight"] = Pango.Weight.BOLD
        if style.italic:
            properties["style"] = Pango.Style.ITALIC
        if style.underline:
            properties["underline"] = Pango.Underline.SINGLE
        if style.strike:
            properties["strikethrough"] = True
        if style.family:
            properties["family"] = style.family
        if style.size_px:
            properties["size_points"] = style.size_px * 0.75
        if style.scale:
            properties["scale"] = style.scale
        if style.rise:
            properties["rise"] = style.rise * 4 * Pango.SCALE
        if (fg := _rgba(style.fg)) is not None:
            properties["foreground_rgba"] = fg
        if (bg := _rgba(style.bg)) is not None:
            properties["background_rgba"] = bg
        tag = Gtk.TextTag(**properties)
        self.get_buffer().get_tag_table().add(tag)
        self._style_tags[style] = tag
        return tag

    def _link_tag(self, uri: str) -> Gtk.TextTag:
        name = f"pyliite4-link:{uri}"
        table = self.get_buffer().get_tag_table()
        tag = table.lookup(name)
        if tag is None:
            tag = Gtk.TextTag(name=name)
            table.add(tag)
            self._links[name] = uri
        return tag

    def _block_tag(self, block: _rich.Block) -> Gtk.TextTag:
        margins = (self.get_left_margin(), self.get_right_margin())
        key = (block.kind, block.depth, block.quote, block.indent, block.style.bg, margins)
        tag = self._block_tags.get(key)
        if tag is not None:
            return tag
        # A tag's margin replaces the view's, so it includes it.
        left = margins[0] + block.indent + _INDENT * block.quote
        properties: dict[str, Any] = {"pixels_below_lines": 3 if block.kind == "item" else 8}
        if block.kind == "item":
            left += _INDENT * block.depth
            properties["indent"] = -_INDENT + 4
        if block.kind == "heading":
            properties["pixels_above_lines"] = 6
        if block.kind == "pre":
            left += 10
            properties["right_margin"] = margins[1] + 10
        if left:
            properties["left_margin"] = left
        if (bg := _rgba(block.style.bg)) is not None:
            properties["paragraph_background_rgba"] = bg
        tag = Gtk.TextTag(**properties)
        self.get_buffer().get_tag_table().add(tag)
        tag.set_priority(0)
        self._block_tags[key] = tag
        return tag

    def _insert(self, block: _rich.Block) -> None:
        buffer = self.get_buffer()
        end = buffer.get_end_iter()
        # Before the separating newline, with left gravity, so text inserted after doesn't move it.
        mark = buffer.create_mark(None, end, True)
        rendered = _Rendered(block, mark)
        self._rendered.append(rendered)
        if len(self._rendered) > 1:
            buffer.insert(end, "\n", -1)
        start_offset = buffer.get_end_iter().get_offset()
        kind_tags = [self._block_tag(block)]
        if block.quote:
            kind_tags.append(self._named["quote"])
        if block.kind == "heading":
            kind_tags.append(self._named[f"h{block.level}"])
        if block.kind == "pre":
            kind_tags.append(self._named["pre"])
        if block.kind == "item":
            self._append(f"{block.marker} ", kind_tags)
        if block.kind == "rule":
            self._append("———", [self._named["rule"], *kind_tags])
        elif block.kind == "table":
            anchor = buffer.create_child_anchor(buffer.get_end_iter())
            rendered.anchor = anchor
            rendered.table = _TableBox(self._table(block))
            self.add_child_at_anchor(rendered.table, anchor)
            self._fit_table(rendered, self.get_width())
        else:
            for text, style in block.runs:
                tags = [self._style_tag(style)]
                if style.code:
                    tags.append(self._named["code"])
                if style.link:
                    tags += [self._named["link"], self._link_tag(style.link)]
                self._append(text, [*tags, *kind_tags])
        start = buffer.get_iter_at_offset(start_offset)
        for tag in kind_tags:
            buffer.apply_tag(tag, start, buffer.get_end_iter())

    def _append(self, text: str, tags: list[Gtk.TextTag]) -> None:
        buffer = self.get_buffer()
        offset = buffer.get_end_iter().get_offset()
        buffer.insert(buffer.get_end_iter(), text, -1)
        start = buffer.get_iter_at_offset(offset)
        for tag in tags:
            buffer.apply_tag(tag, start, buffer.get_end_iter())

    def _table(self, block: _rich.Block) -> Gtk.Grid:
        # Filling its box, which sets the width; aligned, GTK would measure it for the height it is given.
        grid = Gtk.Grid()
        grid.add_css_class("pyliite4-rich-table")
        for row, cells in enumerate(block.rows):
            for column, cell in enumerate(cells):
                label = Gtk.Label(use_markup=True, selectable=True, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR,
                                  xalign=0, yalign=0, max_width_chars=60, hexpand=True)
                label.set_markup(_pango_markup(cell.runs))
                if cell.header:
                    label.add_css_class("header")
                if (bg := _rgba(cell.style.bg)) is not None:
                    label.set_markup(f'<span background="{bg.to_string()}">{label.get_label()}</span>')
                label.connect("activate-link", lambda _label, uri: bool(self.emit("activate-link", uri)))
                grid.attach(label, column, row, 1, 1)
        return grid

    def _fit_table(self, rendered: _Rendered, width: int) -> bool:
        """Give a table its natural width, capped at the view's; the cells wrap to fit. Returns whether the width
        changed."""
        table = rendered.table
        if table is None or not width:
            return False
        left = self.get_left_margin() + _INDENT * rendered.block.quote
        wanted = max(40, min(table.natural_width(), width - left - self.get_right_margin() - 4))
        if table.width == wanted:
            return False
        table.width = wanted
        table.queue_resize()
        return True

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        minimum, natural, minimum_baseline, natural_baseline = Gtk.TextView.do_measure(self, orientation, for_size)
        if orientation == Gtk.Orientation.HORIZONTAL:
            # GtkTextView counts an embedded widget's width in its own minimum; tables refit to any width, and
            # wrapped text needs little, so the view can always shrink.
            minimum = min(minimum, self.get_left_margin() + self.get_right_margin() + 48)
            # A horizontal measurement has no baseline.
            return minimum, natural, -1, -1
        return minimum, natural, minimum_baseline, natural_baseline

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        Gtk.TextView.do_size_allocate(self, width, height, baseline)
        changed = [rendered for rendered in self._rendered if self._fit_table(rendered, width)]
        if changed:
            GLib.idle_add(self._remeasure, changed)

    def _remeasure(self, changed: list[_Rendered]) -> bool:
        # GtkTextView measures an embedded widget when it lays out its line, and not when the widget asks to be
        # resized; touching the line with a tag lays it out again.
        buffer = self.get_buffer()
        touch = buffer.get_tag_table().lookup("pyliite4-relayout")
        if touch is None:
            touch = Gtk.TextTag(name="pyliite4-relayout")
            buffer.get_tag_table().add(touch)
        for rendered in changed:
            if rendered.anchor is None or rendered.anchor.get_deleted():
                continue
            start = buffer.get_iter_at_child_anchor(rendered.anchor)
            end = start.copy()
            end.forward_char()
            buffer.apply_tag(touch, start, end)
            buffer.remove_tag(touch, start, end)
        return False

    def do_snapshot_layer(self, layer: Gtk.TextViewLayer, snapshot: Gtk.Snapshot) -> None:
        if layer != Gtk.TextViewLayer.BELOW_TEXT or not self._colours:
            return
        buffer = self.get_buffer()
        visible = self.get_visible_rect()
        for index, rendered in enumerate(self._rendered):
            block = rendered.block
            if block.kind != "rule" and not block.quote:
                continue
            start = buffer.get_iter_at_mark(rendered.mark)
            if index:
                start.forward_char()
            end = buffer.get_iter_at_mark(self._rendered[index + 1].mark) if index + 1 < len(self._rendered) \
                else buffer.get_end_iter()
            top, _ = self.get_line_yrange(start)
            last_top, last_height = self.get_line_yrange(end)
            bottom = last_top + last_height
            if bottom < visible.y or top > visible.y + visible.height:
                continue
            left = self.get_left_margin() + block.indent + _INDENT * max(0, block.quote - 1)
            if block.kind == "rule":
                middle = top + (bottom - top) // 2
                snapshot.append_color(self._colours["line"], Graphene.Rect().init(
                    left + _INDENT * (block.quote > 0), middle, max(0, visible.width - left - _INDENT * (block.quote > 0)
                                                                    - self.get_right_margin()), 1))
            for level in range(block.quote):
                snapshot.append_color(self._colours["line"], Graphene.Rect().init(
                    self.get_left_margin() + _INDENT * level + 4, top, 3, max(0, bottom - top - 8)))

    def do_copy_clipboard(self) -> None:
        buffer = self.get_buffer()
        start, end = buffer.get_iter_at_mark(buffer.get_insert()), buffer.get_iter_at_mark(buffer.get_selection_bound())
        if start.equal(end):
            return
        if start.compare(end) > 0:
            start, end = end, start
        value = GObject.Value()
        value.init(GObject.TYPE_STRING)
        value.set_string(self.plain_text(start, end))
        self.get_clipboard().set(value)

    # Links

    def _link_at(self, x: float, y: float) -> str | None:
        buffer_x, buffer_y = self.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))
        found, where = self.get_iter_at_location(buffer_x, buffer_y)
        if not found:
            return None
        for tag in where.get_tags():
            name = tag.props.name
            if name and name in self._links:
                return self._links[name]
        return None

    def _hover(self, uri: str | None) -> None:
        if uri == self._hovered:
            return
        self._hovered = uri
        self.set_cursor_from_name("pointer" if uri else None)
        self.emit("hover-link", uri)

    def _released(self, _gesture: Gtk.GestureClick, _n: int, x: float, y: float) -> None:
        pressed, self._pressed = self._pressed, None
        if pressed is None or abs(pressed[0] - x) > 4 or abs(pressed[1] - y) > 4:
            return
        if self.get_buffer().get_has_selection():
            return
        uri = self._link_at(x, y)
        if uri:
            self.emit("activate-link", uri)

    def do_activate_link(self, uri: str) -> bool:
        root = self.get_root()
        Gtk.UriLauncher(uri=uri).launch(root if isinstance(root, Gtk.Window) else None, None, None)
        return True
