"""PyLiite4 next to code that uses PyGObject directly, such as matplotlib's GTK 4 backend, and next to numpy.

A bundled wheel puts its own PyGObject first on sys.path, so ``import gi`` anywhere in the process gets the same
PyGObject and GTK as PyLiite4. matplotlib and numpy are optional: their tests skip when they aren't installed.
"""

from pathlib import Path

import pytest

import PyLiite4
from PyLiite4 import Gdk, GLib, Gtk, cairo
from PyLiite4.testing import wait_until

BUNDLE = Path(PyLiite4.__file__).parent / "_bundled"


def render(widget):
    """The pixels of a shown widget's window, as R, G, B, A bytes, and the row stride."""
    paintable = Gtk.WidgetPaintable.new(widget.get_root())
    wait_until(lambda: paintable.get_intrinsic_width() > 0)

    def snapshot():
        snap = Gtk.Snapshot()
        paintable.snapshot(snap, paintable.get_intrinsic_width(), paintable.get_intrinsic_height())
        return snap.to_node()

    node = wait_until(snapshot)
    texture = widget.get_native().get_renderer().render_texture(node, None)
    downloader = Gdk.TextureDownloader.new(texture)
    downloader.set_format(Gdk.MemoryFormat.R8G8B8A8)
    data, stride = downloader.download_bytes()
    return data.get_data(), stride, texture.get_width(), texture.get_height()


def test_plain_gi_gets_the_same_pygobject_and_classes():
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk as PlainGtk
    assert PlainGtk.Button is Gtk.Button
    assert PlainGtk.get_major_version() == Gtk.get_major_version()
    if BUNDLE.is_dir():
        assert gi.__file__.startswith(str(BUNDLE))
    # An object made one way is usable the other way.
    button = PlainGtk.Button(label="plain")
    box = Gtk.Box()
    box.append(button)
    assert box.get_first_child() is button


def test_matplotlib_draws_in_a_gtk4_window():
    pytest.importorskip("matplotlib")
    import matplotlib
    matplotlib.use("GTK4Agg")
    from matplotlib.backends.backend_gtk4agg import FigureCanvasGTK4Agg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(2, 2), dpi=50, facecolor=(1.0, 0.0, 0.0))
    figure.add_subplot().plot([0, 1, 2], [2, 0, 1])
    canvas = FigureCanvasGTK4Agg(figure)
    # matplotlib's canvas is a widget of the same GTK.
    assert isinstance(canvas, Gtk.Widget)
    window = Gtk.Window(child=canvas, default_width=100, default_height=100)
    window.present()
    wait_until(canvas.get_mapped)
    data, stride, width, height = render(canvas)
    red = sum(1 for y in range(height) for x in range(width)
              if data[y * stride + x * 4] > 200 and data[y * stride + x * 4 + 1] < 60)
    # The red figure background, around the white axes.
    assert red > width * height // 10
    window.destroy()


def test_numpy_arrays_become_textures_and_back():
    numpy = pytest.importorskip("numpy")
    pixels = numpy.zeros((3, 4, 4), dtype=numpy.uint8)
    pixels[..., 0] = numpy.arange(4) * 60
    pixels[..., 3] = 255
    texture = Gdk.MemoryTexture.new(4, 3, Gdk.MemoryFormat.R8G8B8A8, GLib.Bytes.new(pixels.tobytes()), 16)
    downloader = Gdk.TextureDownloader.new(texture)
    downloader.set_format(Gdk.MemoryFormat.R8G8B8A8)
    data, stride = downloader.download_bytes()
    back = numpy.frombuffer(data.get_data(), dtype=numpy.uint8).reshape(3, stride // 4, 4)[:, :4]
    assert (back == pixels).all()


def test_cairo_draws_into_a_numpy_array():
    numpy = pytest.importorskip("numpy")
    pixels = numpy.zeros((10, 10, 4), dtype=numpy.uint8)
    surface = cairo.ImageSurface.create_for_data(memoryview(pixels), cairo.FORMAT_ARGB32, 10, 10, 40)
    context = cairo.Context(surface)
    context.set_source_rgb(0.0, 0.0, 1.0)
    context.paint()
    surface.flush()
    # ARGB32 is stored as B, G, R, A on little-endian machines.
    assert (pixels[..., 0] == 255).all() and (pixels[..., 2] == 0).all()
