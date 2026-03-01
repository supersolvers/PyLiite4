"""Run the example for real: open a window, click through GTK, render to PNG."""

import importlib.util
import os
import shutil
from pathlib import Path

from PyLiite4 import GLib, Gtk


def spin(condition, seconds=5):
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + seconds * 1_000_000
    while not condition() and GLib.get_monotonic_time() < deadline:
        context.iteration(False)
    return condition()


def find(widget, kind):
    if isinstance(widget, kind):
        return widget
    child = widget.get_first_child()
    while child:
        found = find(child, kind)
        if found:
            return found
        child = child.get_next_sibling()
    return None


def test_example_application_renders(tmp_path):
    spec = importlib.util.spec_from_file_location("hello", Path(__file__).parent.parent / "examples" / "hello.py")
    example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    assert Gtk.init_check(), "no display: run the tests under xvfb-run"
    application = Gtk.Application(application_id="org.example.PyLiite4Test")
    result = {}

    def activated(app):
        try:
            example.on_activate(app)
            window = app.get_windows()[0]
            assert spin(window.get_mapped)
            content = window.get_child()
            button, label = find(content, Gtk.Button), find(content, Gtk.Label)
            assert label.get_text() == "Not clicked yet"
            button.activate()
            assert spin(lambda: label.get_text() == "Clicked 1 times")
            paintable = Gtk.WidgetPaintable.new(window)
            assert spin(lambda: paintable.get_intrinsic_width() > 0)
            node = {}

            def render_node():
                snapshot = Gtk.Snapshot()
                paintable.snapshot(snapshot, paintable.get_intrinsic_width(), paintable.get_intrinsic_height())
                node["root"] = snapshot.to_node()
                return node["root"] is not None

            assert spin(render_node)
            texture = window.get_native().get_renderer().render_texture(node["root"], None)
            path = tmp_path / "hello.png"
            texture.save_to_png(str(path))
            result.update(path=path, size=(texture.get_width(), texture.get_height()))
        except BaseException as error:
            # An exception can't cross the main loop, and would leave it running forever.
            result["error"] = error
        finally:
            app.quit()

    application.activate.connect(activated)
    application.run([])
    if "error" in result:
        raise result["error"]
    assert result["path"].stat().st_size > 500
    assert min(result["size"]) > 20
    if target := os.environ.get("PYLIITE4_KEEP_RENDER"):
        shutil.copy(result["path"], target)
