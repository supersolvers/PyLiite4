"""PyLiite4.Extras.register_font, in the isolated session of PyLiite4.testing, with fonts built by tiny_font."""

from pathlib import Path

from test_testing import run_pytest

TESTS = Path(__file__).resolve().parent

FONTS = f"""
    import shutil
    import subprocess
    import sys

    import pytest

    sys.path.insert(0, {str(TESTS)!r})

    from PyLiite4 import Gdk, Gio, GLib, Gtk, Pango, PangoCairo
    from PyLiite4.Extras import register_font
    from tiny_font import tiny_font

    CSS = Gtk.CssProvider()
    CSS.load_from_string(".one {{ font-family: 'Tiny One'; }} .two {{ font-family: 'Tiny Two'; }} "
                         ".three {{ font-family: 'Tiny Three'; }} .four {{ font-family: 'Tiny Four'; }}")
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), CSS, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


    def used(label):
        \"\"\"The family Pango laid ``label``'s text out in.\"\"\"
        return label.get_layout().get_line_readonly(0).runs[0].item.analysis.font.describe().get_family()


    def label(gtkbot, css_class):
        widget = Gtk.Label(label="AAA", css_classes=[css_class])
        gtkbot.show(widget)
        return widget


    def loads(family):
        context = PangoCairo.FontMap.get_default().create_context()
        return context.load_font(Pango.FontDescription.from_string(f"{{family}} 12")).describe().get_family()


    def test_from_memory(gtkbot):
        assert register_font(tiny_font("Tiny One")) == ["Tiny One"]
        assert used(label(gtkbot, "one")) == "Tiny One"
        assert loads("Tiny One") == "Tiny One"


    def test_after_the_family_was_looked_up(gtkbot):
        # Pango has already chosen a fallback for the family, and text is laid out in it.
        early = label(gtkbot, "two")
        assert used(early) != "Tiny Two"
        assert register_font(GLib.Bytes.new(tiny_font("Tiny Two"))) == ["Tiny Two"]
        gtkbot.wait_until(lambda: used(early) == "Tiny Two")
        assert used(label(gtkbot, "two")) == "Tiny Two"
        # The font registered before is still there.
        assert used(label(gtkbot, "one")) == "Tiny One"


    def test_from_a_file_and_a_resource(gtkbot, tmp_path):
        path = tmp_path / "three.ttf"
        path.write_bytes(tiny_font("Tiny Three"))
        assert register_font(path) == ["Tiny Three"]
        assert register_font(str(path)) == ["Tiny Three"]
        assert used(label(gtkbot, "three")) == "Tiny Three"
        if shutil.which("glib-compile-resources") is None:
            pytest.skip("needs glib-compile-resources")
        (tmp_path / "four.ttf").write_bytes(tiny_font("Tiny Four"))
        (tmp_path / "fonts.gresource.xml").write_text(
            '<gresources><gresource prefix="/org/example/Fonts"><file>four.ttf</file></gresource></gresources>')
        subprocess.run(["glib-compile-resources", "--sourcedir", str(tmp_path), "--target",
                        str(tmp_path / "fonts.gresource"), str(tmp_path / "fonts.gresource.xml")], check=True)
        Gio.resources_register(Gio.Resource.load(str(tmp_path / "fonts.gresource")))
        assert register_font(Gio.File.new_for_uri("resource:///org/example/Fonts/four.ttf")) == ["Tiny Four"]
        assert used(label(gtkbot, "four")) == "Tiny Four"
        assert [loads(f"Tiny {{name}}") for name in ("One", "Two", "Three", "Four")] == \\
            ["Tiny One", "Tiny Two", "Tiny Three", "Tiny Four"]


    def test_not_a_font(tmp_path):
        with pytest.raises(ValueError, match="isn't a font"):
            register_font(b"not a font at all")
        (tmp_path / "text.ttf").write_text("hello")
        with pytest.raises(ValueError, match="text.ttf isn't a font"):
            register_font(tmp_path / "text.ttf")
        with pytest.raises(FileNotFoundError):
            register_font(tmp_path / "missing.ttf")
"""


def test_register_font(tmp_path):
    result = run_pytest(tmp_path, {"test_inner_fonts.py": FONTS}, "--gtk")
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr[-2000:]
    assert "4 passed" in result.stdout, result.stdout[-3000:]
