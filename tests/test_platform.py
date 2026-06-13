"""Features that depend on data files and plugins, which a bundle can easily lose."""

import ctypes
import struct
import wave
import zlib
from pathlib import Path

import pytest

from PyLiite4 import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk



def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


PNG = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
       + png_chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff")) + png_chunk(b"IEND", b""))
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>'


@pytest.fixture(autouse=True)
def gtk():
    assert Gtk.init_check(), "no display: run the tests under xvfb-run"


def test_icon_from_adwaita_theme_is_found():
    theme = Gtk.IconTheme()
    theme.set_theme_name("Adwaita")
    # Not one of the icons GTK carries in its own resources.
    assert theme.has_icon("folder-symbolic") or theme.has_icon("folder")
    paintable = theme.lookup_icon("media-playback-start-symbolic", None, 16, 1, Gtk.TextDirection.NONE, 0)
    assert paintable.get_file().query_exists(None)


def test_texture_loads_png():
    texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(PNG))
    assert texture.get_width() == 1


def test_pixbuf_loader_handles_svg():
    formats = {f.get_name() for f in GdkPixbuf.Pixbuf.get_formats()}
    assert "svg" in formats
    loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
    loader.write(SVG)
    loader.close()
    assert loader.get_pixbuf().get_width() == 4


def test_gtk_settings_schema_available():
    assert Gio.SettingsSchemaSource.get_default().lookup("org.gtk.gtk4.Settings.FileChooser", True)


def test_adwaita_widgets():
    Adw.init()
    row = Adw.ActionRow(title="Title", subtitle="Subtitle")
    assert row.get_title() == "Title"
    calls = []
    row.activated.connect(lambda _: calls.append(1))
    row.activated.emit()
    assert calls == [1]


def test_cairo_drawing():
    area = Gtk.DrawingArea()
    area.set_draw_func(lambda *_: None)
    import cairo
    assert cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1).get_width() == 1


def wait(condition, seconds=10):
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + seconds * 1_000_000
    while not condition() and GLib.get_monotonic_time() < deadline:
        context.iteration(False)
    return condition()


def test_media_file_prepares_audio(tmp_path):
    path = tmp_path / "tone.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\x00\x01" * 8000)
    media = Gtk.MediaFile.new_for_filename(str(path))
    assert wait(lambda: media.is_prepared() or media.get_error()), "media never prepared"
    assert media.get_error() is None
    assert media.has_audio()
    assert media.get_duration() > 0


def test_input_method_module_is_loaded():
    Gtk.Entry()
    bundle = Path(Gtk.__file__).parent / "_bundled"
    if bundle.is_dir():
        with open("/proc/self/maps") as maps:
            loaded = {line.split()[-1] for line in maps if "libim-" in line}
        assert loaded and all(path.startswith(str(bundle)) for path in loaded)


def test_bundle_carries_its_notices():
    bundle = Path(Gtk.__file__).parent / "_bundled"
    if bundle.is_dir():
        notices = (bundle / "licenses" / "NOTICES.txt").read_text()
        assert "\ngtk 4." in notices and "\nPyGObject " in notices
        # libjbig is GPL-only, and must not reach an LGPL application through libtiff.
        assert not list((bundle / "lib").glob("libjbig*"))


def test_fonts_are_found():
    assert Gtk.Label().get_pango_context().list_families()


def test_translations_bind_to_bundle():
    bundle = Path(Gtk.__file__).parent / "_bundled" / "share" / "locale"
    if bundle.is_dir():
        libc = ctypes.CDLL(None)
        libc.bindtextdomain.restype = ctypes.c_char_p
        libc.bindtextdomain.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        assert libc.bindtextdomain(b"gtk40", None).decode() == str(bundle)
