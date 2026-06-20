"""GStreamer, GtkSourceView, libsoup and libportal, which bundled wheels carry next to GTK.

A source checkout uses whichever of them the system has, so each test skips when its library is missing.
"""

import importlib
import importlib.util
from pathlib import Path

import pytest


def namespace(name):
    try:
        return importlib.import_module(f"PyLiite4.{name}")
    except (ImportError, ValueError) as error:
        if bundled():
            raise
        pytest.skip(f"{name} is not installed: {error}")


def bundled():
    return (Path(importlib.import_module("PyLiite4").__file__).parent / "_bundled").is_dir()


def test_gstreamer_has_its_python_overrides():
    Gst = namespace("Gst")
    if not bundled() and importlib.util.find_spec("gi.overrides.Gst") is None:
        pytest.skip("the system has GStreamer without gst-python")
    Gst.init(None)
    # Gst.Fraction comes from gst-python's overrides, not from the typelib.
    assert str(Gst.Fraction(30, 1)) == "30/1"
    caps = Gst.Caps.from_string("video/x-raw,framerate=25/1")
    assert caps.get_structure(0).get_fraction("framerate")[1:] == (25, 1)
    assert Gst.ElementFactory.make("playbin") is not None


def test_gstreamer_video_types_load():
    GstVideo = namespace("GstVideo")
    namespace("Gst").init(None)
    info = GstVideo.VideoInfo.new()
    assert info.set_format(GstVideo.VideoFormat.RGBA, 4, 2)
    assert info.size == 4 * 2 * 4


def test_source_view_knows_languages_and_schemes():
    GtkSource = namespace("GtkSource")
    GtkSource.init()
    language = GtkSource.LanguageManager.get_default().get_language("python3")
    assert language is not None
    assert "Adwaita" in GtkSource.StyleSchemeManager.get_default().get_scheme_ids()
    buffer = GtkSource.Buffer(language=language)
    buffer.set_text("def f():\n    return 1\n")
    assert buffer.get_language().get_id() == "python3"


def test_soup_serves_and_fetches_over_loopback():
    Soup = namespace("Soup")
    from PyLiite4 import GLib

    server = Soup.Server()
    server.add_handler("/", lambda _server, message, _path, _query: (
        message.set_status(200, None),
        message.set_response("text/plain", Soup.MemoryUse.COPY, b"hello")))
    server.listen_local(0, Soup.ServerListenOptions.IPV4_ONLY)
    port = server.get_uris()[0].get_port()
    session = Soup.Session()
    message = Soup.Message.new("GET", f"http://127.0.0.1:{port}/")
    result = {}
    session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, None,
                                lambda s, task: result.update(data=s.send_and_read_finish(task)))
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + 5_000_000
    while "data" not in result and GLib.get_monotonic_time() < deadline:
        context.iteration(True)
    assert message.get_status() == 200 and result["data"].get_data() == b"hello"


def test_tls_backend_is_available():
    namespace("Soup")
    from PyLiite4 import Gio

    assert Gio.TlsBackend.get_default().supports_tls()


def test_portal_bindings_load():
    Xdp = namespace("Xdp")
    XdpGtk4 = namespace("XdpGtk4")
    assert Xdp.ScreenshotFlags.INTERACTIVE and callable(XdpGtk4.parent_new_gtk)
