"""PyLiite4's corrections to PyGObject and to GTK's annotations (src/PyLiite4/_fixes.py), and to font handling."""

import subprocess
import sys
import textwrap

import pytest

from PyLiite4 import Gdk, Gio, GLib, GObject, Graphene, Gsk, Gtk, Pango


def spin(condition, seconds=5):
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + seconds * 1_000_000
    while not condition() and GLib.get_monotonic_time() < deadline:
        context.iteration(False)
    return condition()


def test_replace_contents_async_writes_the_data(tmp_path):
    target = tmp_path / "out.txt"
    file = Gio.File.new_for_path(str(target))
    done = []
    file.replace_contents_async(b"new contents" * 1000, None, False, Gio.FileCreateFlags.NONE, None,
                                lambda f, result: done.append(f.replace_contents_finish(result)))
    assert spin(lambda: done)
    assert target.read_bytes() == b"new contents" * 1000


def test_rounded_rect_init_returns_the_rectangle():
    rect = Gsk.RoundedRect().init_from_rect(Graphene.Rect().init(1, 2, 30, 40), 5)
    assert (rect.bounds.origin.x, rect.bounds.size.width, rect.bounds.size.height) == (1, 30, 40)
    assert rect.corner[0].width == 5


def test_extents_to_pixels():
    inclusive = Pango.Rectangle()
    inclusive.x, inclusive.y, inclusive.width, inclusive.height = 1500, -100, 2048, 1024
    nearest = Pango.Rectangle()
    nearest.x, nearest.y, nearest.width, nearest.height = 1500, -100, 2048, 1024
    Pango.extents_to_pixels(inclusive, nearest)
    assert (inclusive.x, inclusive.y, inclusive.width, inclusive.height) == (1, -1, 3, 2)
    assert (nearest.x, nearest.y, nearest.width, nearest.height) == (1, 0, 2, 1)
    assert Pango.SCALE_X_LARGE == pytest.approx(1.44)


def test_custom_layout_keeps_its_callbacks():
    assert Gtk.init_check()
    calls = []
    layout = Gtk.CustomLayout.new(None, lambda widget, orientation, for_size: (10, 20, -1, -1),
                                  lambda widget, width, height, baseline: calls.append((width, height)))
    box = Gtk.Box(layout_manager=layout)
    import gc
    gc.collect()
    assert box.measure(Gtk.Orientation.HORIZONTAL, -1)[:2] == (10, 20)
    box.allocate(50, 60, -1, None)
    assert calls == [(50, 60)]


def test_expression_evaluate_returns_the_value():
    label = Gtk.Label(label="hello")
    expression = Gtk.PropertyExpression.new(Gtk.Label, None, "label")
    assert expression.evaluate(label) == "hello"
    value = GObject.Value()
    assert expression.evaluate(label, value) and value.get_value() == "hello"


def test_image_set_from_gicon_accepts_none():
    image = Gtk.Image()
    image.set_from_gicon(Gio.ThemedIcon.new("document-open"))
    image.set_from_gicon(None)
    assert image.get_storage_type() == Gtk.ImageType.EMPTY


BUILDER_UI = """
<interface>
  <object class="GtkStringList" id="model"/>
  <object class="GtkButton" id="plain"><signal name="clicked" handler="plain"/></object>
  <object class="GtkButton" id="with_object"><signal name="clicked" handler="with_object" object="model"
      swapped="no"/></object>
  <object class="GtkButton" id="swapped"><signal name="clicked" handler="swapped" object="model"/></object>
</interface>
"""


def test_builder_signals_match_gtk():
    calls = {}
    builder = Gtk.Builder({"plain": lambda *args: calls.setdefault("plain", args),
                           "with_object": lambda *args: calls.setdefault("with_object", args),
                           "swapped": lambda *args: calls.setdefault("swapped", args)})
    builder.add_from_string(BUILDER_UI)
    model = builder.get_object("model")
    for name in ("plain", "with_object", "swapped"):
        builder.get_object(name).emit("clicked")
    # As GTK's C scope connects them: the object last, or first when swapped. The empty model must still arrive.
    assert calls["plain"] == (builder.get_object("plain"),)
    assert calls["with_object"] == (builder.get_object("with_object"), model)
    assert calls["swapped"] == (model, builder.get_object("swapped"))


@Gtk.Template(string="""
<interface>
  <template class="FixesSwappedTemplate" parent="GtkBox">
    <child>
      <object class="GtkButton" id="button">
        <signal name="clicked" handler="on_clicked" object="FixesSwappedTemplate" swapped="yes"/>
      </object>
    </child>
  </template>
</interface>
""")
class SwappedTemplate(Gtk.Box):
    __gtype_name__ = "FixesSwappedTemplate"
    button = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.received = None

    @Gtk.Template.Callback()
    def on_clicked(self, *args):
        self.received = args


def test_template_accepts_swapped_handlers():
    widget = SwappedTemplate()
    widget.button.emit("clicked")
    # Swapped: the object first, then the emitter.
    assert widget.received == (widget, widget.button)


def test_path_points():
    path = Gsk.Path.parse("M 0 0 L 100 0 L 100 100")
    ok, start = path.get_start_point()
    assert ok and start.get_position(path).x == 0
    ok, point = Gsk.PathMeasure.new(path).get_point(150)
    position = point.get_position(path)
    assert ok and (position.x, position.y) == (100, 50)
    ok, closest, distance = path.get_closest_point(Graphene.Point().init(50, 10), 100)
    assert ok and closest.get_position(path).x == 50 and distance == pytest.approx(10)
    assert path.get_closest_point(Graphene.Point().init(500, 500), 1) == (False, None, 0.0)
    builder = Gsk.PathBuilder.new()
    builder.add_segment(path, start, point)
    assert builder.to_path().to_string() == "M 0 0 L 100 0 L 100 50"


def test_generic_families_resolve_to_their_kind():
    assert Gtk.init_check()
    context = Gtk.Label().get_pango_context()
    # Pango lists the generic "Monospace" among the families, so look for a real one.
    families = context.get_font_map().list_families()
    if not any(family.is_monospace() and family.get_name().lower() != "monospace" for family in families):
        pytest.skip("no monospace font installed")
    font = context.get_font_map().load_font(context, Pango.FontDescription.from_string("Monospace 12"))
    assert font.get_face().get_family().is_monospace(), font.describe().to_string()


def test_variable_font_instances_render():
    # Old FreeType corrupted memory reading some variable fonts' metrics variations, so render in a child process.
    script = textwrap.dedent("""
        from PyLiite4 import Gtk, Pango
        Gtk.init()
        context = Gtk.Label().get_pango_context()
        families = [f for f in context.get_font_map().list_families() if f.is_variable()]
        for family in families[:5]:
            label = Gtk.Label(label="Variable fonts")
            label.set_attributes(Pango.AttrList.from_string(f'0 -1 font-desc "{family.get_name()} 14 @wght=300"'))
            label.measure(Gtk.Orientation.HORIZONTAL, -1)
        print(len(families))
    """)
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-2000:]
    if result.stdout.strip() == "0":
        pytest.skip("no variable fonts installed")
