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
