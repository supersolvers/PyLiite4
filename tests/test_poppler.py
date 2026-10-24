"""PyLiite4-Poppler: Poppler, from the GPL wheel of that name.

It needs that wheel installed next to a bundled PyLiite4 wheel, so every test skips without it.
"""

from pathlib import Path

import pytest

import PyLiite4
from PyLiite4 import GLib, cairo

POPPLER = Path(PyLiite4.__file__).parent / "_poppler"

pytestmark = pytest.mark.skipif(not POPPLER.is_dir(), reason="PyLiite4-Poppler is not installed")


def pdf(tmp_path):
    """A two-page PDF, made with Cairo: a red square on the first page, and a line of text on each."""
    path = tmp_path / "test.pdf"
    surface = cairo.PDFSurface(str(path), 200, 100)
    context = cairo.Context(surface)
    for page in (1, 2):
        if page == 1:
            context.set_source_rgb(1.0, 0.0, 0.0)
            context.rectangle(0, 0, 100, 100)
            context.fill()
        context.set_source_rgb(0.0, 0.0, 0.0)
        context.select_font_face("Sans")
        context.set_font_size(12)
        context.move_to(110, 50)
        context.show_text(f"Page {page}")
        context.show_page()
    surface.finish()
    return path


def test_poppler_loads_from_its_wheel():
    from PyLiite4 import Poppler
    Poppler.get_version()
    maps = Path("/proc/self/maps").read_text().splitlines()
    paths = {line.split()[-1] for line in maps if "libpoppler" in line}
    assert paths and all(path.startswith(str(POPPLER)) for path in paths), paths
    # Cairo and GLib come from the main wheel, not from a second copy.
    assert all("_bundled" in line.split()[-1] for line in maps if "libcairo.so" in line)


def test_poppler_reads_and_draws_a_pdf(tmp_path):
    from PyLiite4 import Poppler
    document = Poppler.Document.new_from_bytes(GLib.Bytes.new(pdf(tmp_path).read_bytes()), None)
    assert document.get_n_pages() == 2
    page = document.get_page(0)
    assert page.get_size() == (200.0, 100.0)
    assert "Page 1" in page.get_text()
    assert "Page 2" in document.get_page(1).get_text()

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 100)
    context = cairo.Context(surface)
    page.render(context)
    surface.flush()
    data = surface.get_data()
    # ARGB32 is stored as B, G, R, A on little-endian machines. The square is red, and render() leaves the rest of
    # the page, which has no background, transparent.
    assert tuple(data[(50 * 200 + 50) * 4:(50 * 200 + 50) * 4 + 4]) == (0, 0, 255, 255)
    assert data[(10 * 200 + 190) * 4 + 3] == 0


def test_poppler_opens_a_file_through_gio(tmp_path):
    from PyLiite4 import Gio, Poppler
    document = Poppler.Document.new_from_gfile(Gio.File.new_for_path(str(pdf(tmp_path))), None, None)
    assert document.get_n_pages() == 2
