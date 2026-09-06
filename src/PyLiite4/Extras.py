"""What Qt has and GTK lacks, built from GTK's public pieces and used the way GTK's own API is.

- ``register_font()``: make a font from memory, a GResource or a file usable by the application, like
  ``QFontDatabase.addApplicationFont``.
"""

from __future__ import annotations

import ctypes
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyLiite4 import Gio, GLib

__all__ = ["register_font"]

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
    from PyLiite4 import Gio, GLib

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
