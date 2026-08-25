import importlib.util

import pytest

from PyLiite4 import Gio, Gtk
from PyLiite4.tools import resources, ui

OBJECTS = """<?xml version="1.0"?>
<interface>
  <object class="GtkBox" id="main-box">
    <child>
      <object class="GtkButton" id="title">
        <property name="label">Hi</property>
        <signal name="clicked" handler="on_title_clicked"/>
      </object>
    </child>
    <child><object class="GtkLabel"/></child>
  </object>
</interface>
"""

TEMPLATE = """<?xml version="1.0"?>
<interface>
  <template class="PyLiite4TestPanel" parent="GtkBox">
    <child>
      <object class="GtkButton" id="save-button">
        <property name="label">Save</property>
        <signal name="clicked" handler="on_save_clicked"/>
      </object>
    </child>
    <child><object class="GtkLabel" id="status"/></child>
  </template>
</interface>
"""


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compile_file(tmp_path, name, text):
    source, target = tmp_path / name, tmp_path / f"{name.split('.')[0]}_ui.py"
    source.write_text(text)
    assert ui.main([str(source), "-o", str(target)]) == 0
    return load(target), target.read_text()


def test_ui_objects(tmp_path):
    module, code = compile_file(tmp_path, "main.ui", OBJECTS)
    clicks = []
    objects = module.MainObjects({"on_title_clicked": lambda button: clicks.append(button)})
    assert isinstance(objects.main_box, Gtk.Box)
    assert objects.title.get_label() == "Hi"
    objects.title.clicked.emit()
    assert clicks == [objects.title]
    assert "self.title = cast(Gtk.Button," in code


def test_ui_template(tmp_path):
    module, code = compile_file(tmp_path, "panel.ui", TEMPLATE)
    assert "save_button: Gtk.Button" in code and "status: Gtk.Label" in code

    @module.template
    class Panel(module.PyLiite4TestPanelChildren, Gtk.Box):
        __gtype_name__ = "PyLiite4TestPanel"

        def on_save_clicked(self, button: Gtk.Button) -> None:
            self.status.set_label(f"saved by {button.get_label()}")

    panel = Panel()
    panel.save_button.clicked.emit()
    assert panel.status.get_label() == "saved by Save"


def test_ui_template_checks_the_class(tmp_path):
    # Each class registers its GType name, so each case needs a template of its own.
    def compiled(name):
        return compile_file(tmp_path, f"{name}.ui", TEMPLATE.replace("PyLiite4TestPanel", name))[0]

    unnamed, wrong_parent, no_handler = compiled("PyLiite4A"), compiled("PyLiite4B"), compiled("PyLiite4C")

    with pytest.raises(TypeError, match="__gtype_name__"):
        @unnamed.template
        class Unnamed(Gtk.Box):
            def on_save_clicked(self, button): ...

    with pytest.raises(TypeError, match="subclass of Box"):
        @wrong_parent.template
        class WrongParent(Gtk.Grid):
            __gtype_name__ = "PyLiite4B"

            def on_save_clicked(self, button): ...

    with pytest.raises(TypeError, match="on_save_clicked"):
        @no_handler.template
        class NoHandler(Gtk.Box):
            __gtype_name__ = "PyLiite4C"


def test_ui_rejects_bad_files(tmp_path):
    source = tmp_path / "t.ui"
    for text in ["<interface>", "<other/>", "<interface><template class='X'/></interface>",
                 "<interface><template class='X' parent='GtkBox'/><template class='Y' parent='GtkBox'/></interface>"]:
        source.write_text(text)
        assert ui.main([str(source)]) == 1


def test_resources(tmp_path):
    (tmp_path / "hello.txt").write_text("hello from a resource")
    source, target = tmp_path / "app.gresource.xml", tmp_path / "app_resources.py"
    source.write_text('<gresources><gresource prefix="/test/pyliite4"><file>hello.txt</file></gresource></gresources>')
    assert resources.main([str(source), "-o", str(target)]) == 0
    load(target)
    data = Gio.resources_lookup_data("/test/pyliite4/hello.txt", Gio.ResourceLookupFlags.NONE)
    assert data.get_data() == b"hello from a resource"


def test_resources_reports_failure(tmp_path):
    source = tmp_path / "bad.gresource.xml"
    source.write_text('<gresources><gresource prefix="/x"><file>missing</file></gresource></gresources>')
    assert resources.main([str(source), "-o", str(tmp_path / "o.py")]) != 0


RESOURCE_TEMPLATE = """<?xml version="1.0"?>
<interface>
  <template class="PyLiite4TestCounter" parent="GtkBox">
    <child>
      <object class="GtkLabel" id="count">
        <binding name="label">
          <closure type="gchararray" function="describe">
            <lookup name="value">adjustment</lookup>
          </closure>
        </binding>
      </object>
    </child>
  </template>
  <object class="GtkAdjustment" id="adjustment">
    <property name="upper">10</property>
  </object>
</interface>
"""


def test_ui_template_from_resource_with_outside_objects_and_closures(tmp_path):
    (tmp_path / "counter.ui").write_text(RESOURCE_TEMPLATE)
    (tmp_path / "counter.gresource.xml").write_text(
        '<gresources><gresource prefix="/test/pyliite4"><file>counter.ui</file></gresource></gresources>')
    assert resources.main([str(tmp_path / "counter.gresource.xml"), "-o", str(tmp_path / "counter_res.py")]) == 0
    load(tmp_path / "counter_res.py")
    target = tmp_path / "counter_ui.py"
    assert ui.main([str(tmp_path / "counter.ui"), "-o", str(target), "--resource", "/test/pyliite4/counter.ui"]) == 0
    code = target.read_text()
    assert "_UI =" not in code and "resource_path=RESOURCE" in code
    assert "adjustment: Gtk.Adjustment" in code and "'describe'" in code
    module = load(target)

    @module.template
    class Counter(module.PyLiite4TestCounterChildren, Gtk.Box):
        __gtype_name__ = "PyLiite4TestCounter"

        # As in C, an expression closure gets the object it's evaluated for (here the template) first.
        def describe(self, _this: Gtk.Box, value: float) -> str:
            return f"{value:.0f} of 10"

    counter = Counter()
    counter.adjustment.set_value(3)
    assert counter.count.get_label() == "3 of 10"
