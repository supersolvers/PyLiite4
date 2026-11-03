"""The stubs are only useful if they describe what really exists at runtime."""

import ast
import importlib
import importlib.util
import inspect
import subprocess
import sys
from pathlib import Path

import pytest

from PyLiite4 import GObject

PACKAGE = Path(importlib.import_module("PyLiite4").__file__).parent
NAMESPACES = ["GLib", "GObject", "Gio", "GdkPixbuf", "Pango", "Graphene", "Gdk", "Gsk", "Gtk", "Adw"]


def stub_tree(namespace):
    return ast.parse((PACKAGE / f"{namespace}.pyi").read_text())


def public_names(tree):
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            yield node.name, node
        elif isinstance(node, ast.AnnAssign):
            yield node.target.id, node


@pytest.mark.parametrize("namespace", NAMESPACES)
def test_top_level_names_exist(namespace):
    module = importlib.import_module(f"PyLiite4.{namespace}")
    missing = [f"{namespace}.{name}" for name, _ in public_names(stub_tree(namespace))
               if not name.startswith("_") and not hasattr(module, name)]
    assert sorted(missing) == []


@pytest.mark.parametrize("namespace", NAMESPACES)
def test_module_names_resolve(namespace):
    module = importlib.import_module(f"PyLiite4.{namespace}")
    assert [n for n in module.__all__ if not hasattr(module, n)] == []


@pytest.mark.parametrize("namespace", NAMESPACES)
def test_class_members_exist(namespace):
    module = importlib.import_module(f"PyLiite4.{namespace}")
    missing = []
    for name, node in public_names(stub_tree(namespace)):
        if not isinstance(node, ast.ClassDef) or name.startswith("_"):
            continue
        cls = getattr(module, name, None)
        # GLib.Error is a Python exception whose fields exist only on instances.
        if cls is None or not isinstance(cls, type) or issubclass(cls, Exception):
            continue
        for member in node.body:
            if isinstance(member, ast.FunctionDef):
                member_name, is_property = member.name, any(
                    (isinstance(d, ast.Name) and d.id == "property")
                    or (isinstance(d, ast.Attribute) and d.attr == "setter") for d in member.decorator_list)
            elif isinstance(member, ast.AnnAssign):
                member_name, is_property = member.target.id, False
            else:
                continue
            if member_name.startswith("__") or member_name == "props" or hasattr(cls, member_name):
                continue
            # Attributes that a Python class, such as PyGObject's Gtk.TreeModelRow, sets in __init__.
            if (isinstance(member, ast.AnnAssign) and not issubclass(cls, GObject.GBoxed | GObject.Object)
                    and f"self.{member_name} =" in inspect.getsource(cls.__init__)):
                continue
            if member_name.startswith("do_") and member_name[3:] in vfunc_names(cls):
                continue
            if is_property and issubclass(cls, (GObject.Object, GObject.GInterface)):
                # Signals resolve on instances, so ask GObject about them.
                if member_name.replace("_", "-") in signal_names(cls) | property_names(cls):
                    continue
            missing.append(f"{name}.{member_name}")
    assert missing == []


def vfunc_names(cls):
    # Virtual methods can be overridden without being attributes of the class.
    info = getattr(cls, "__info__", None)
    return {v.get_name() for v in info.get_vfuncs()} if hasattr(info, "get_vfuncs") else set()


def property_names(cls):
    names = set()
    for base in cls.__mro__:
        info = base.__dict__.get("__info__")
        if hasattr(info, "get_properties"):
            names |= {spec.get_name() for spec in info.get_properties()}
    return names


def signal_names(cls):
    # GObject can't look up signals until a class is initialized, so use the typelib.
    names = set()
    for base in cls.__mro__:
        info = base.__dict__.get("__info__")
        if hasattr(info, "get_signals"):
            names |= {signal.get_name() for signal in info.get_signals()}
    return names


def mypy(tmp_path, code):
    path = tmp_path / "sample.py"
    path.write_text(code)
    env = {"PATH": "/usr/bin:/bin"}
    paths = [str(tmp_path)] + ([str(PACKAGE.parent)] if PACKAGE.parent.name != "site-packages" else [])
    env["MYPYPATH"] = ":".join(paths)
    return subprocess.run(
        [sys.executable, "-m", "mypy", "--no-error-summary", "--cache-dir",
         str(tmp_path / "cache"), str(path)],
        capture_output=True, text=True, env=env)


def test_stubs_type_check_cleanly(tmp_path):
    imports = ", ".join(NAMESPACES)
    result = mypy(tmp_path, f"from PyLiite4 import {imports}\n")
    assert result.returncode == 0, result.stdout[:3000]


def test_type_checker_accepts_correct_code(tmp_path):
    result = mypy(tmp_path, """
from PyLiite4.Gtk import Box, Button, Orientation
def on_click(button: Button) -> None:
    text: str | None = button.get_label()
button = Button(label="x", margin_top=3)
button.clicked.connect(on_click)
button.show()
button.show.connect(lambda widget: None)
box = Box(orientation=Orientation.VERTICAL)
box.append(button)
n: int = box.get_spacing()
button.label = "y"
m: int = box.spacing
""")
    assert result.returncode == 0, result.stdout


def test_type_checker_accepts_gtk_patterns(tmp_path):
    result = mypy(tmp_path, """
import asyncio
from PyLiite4 import GLib, GObject, Gio, Graphene, Gtk, cairo, use_asyncio

class Fruit(GObject.Object):
    name = GObject.Property(type=str, default="")

store: Gio.ListStore[Fruit] = Gio.ListStore(item_type=Fruit)
store.append(Fruit())
first: Fruit = store[0]
names = [fruit.name for fruit in store]
model = Gio.ListStore.new(Fruit)
GLib.idle_add(lambda: GLib.SOURCE_REMOVE)
GLib.idle_add(print, "done", priority=GLib.PRIORITY_DEFAULT_IDLE)
GLib.timeout_add(100, lambda text: False, "x")
loop: asyncio.AbstractEventLoop = use_asyncio()

async def load(file: Gio.File) -> bytes:
    ok, data, etag = await file.load_contents_async(None)
    info: Gio.FileInfo = await file.query_info_async("standard::*", Gio.FileQueryInfoFlags.NONE, 0)
    return data

def loaded(file: Gio.File, result: Gio.AsyncResult) -> None: ...
Gio.File.new_for_path("/").load_contents_async(None, loaded)

class Canvas(Gtk.Widget):
    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        cr: cairo.Context[cairo.Surface] = snapshot.append_cairo(Graphene.Rect().init(0, 0, 10, 10))
        cr.paint()

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        return 10, 10, -1, -1

builder = Gtk.Builder({"on_clicked": print})
builder.add_from_string("<interface/>")
variant = GLib.Variant("as", ["a"])
items: list[str] = variant.unpack()
""")
    assert result.returncode == 0, result.stdout


def test_type_checker_accepts_pygobject_overrides(tmp_path):
    result = mypy(tmp_path, """
from PyLiite4 import Gdk, GLib, Gtk, Pango

provider = Gtk.CssProvider()
provider.load_from_data("label { color: red; }")
buffer = Gtk.TextBuffer()
buffer.set_text("hi")
buffer.insert(buffer.get_end_iter(), "!")
tag: Gtk.TextTag = buffer.create_tag("bold", weight=Pango.Weight.BOLD)
buffer.insert_with_tags(buffer.get_start_iter(), "x", tag)
bounds = buffer.get_selection_bounds()
if bounds:
    start, end = bounds
    text: str = buffer.get_text(start, end, False)
entry = Gtk.Entry()
position: int = entry.insert_text("x", 0)
box = Gtk.Box()
children: list[Gtk.Widget] = list(box)
point = box.translate_coordinates(box, 1.0, 2.0)
if point is not None:
    x, y = point
color = Gdk.RGBA(red=1.0, alpha=0.5)
loop = GLib.MainLoop(None)
more: bool = GLib.MainContext.default().iteration()
font = Pango.FontDescription("Sans 12")
# A callback's user data before other arguments is an argument of its own.
found: bool = buffer.get_start_iter().forward_find_char(lambda char, data: char == "!", None, None)
# GObject.Value converts to and from plain values.
box.update_property([Gtk.AccessibleProperty.LABEL], ["Box"])
same: str = Gtk.ConstantExpression.new_for_value("x").get_value()
""")
    assert result.returncode == 0, result.stdout


TREE_MODEL_CODE = """
from PyLiite4 import Gtk

store = Gtk.ListStore(str, int)
first = store.append(["a", 1])
store.insert(0, ["b", 2])
store.set(first, 0, "c", 1, 3)
store.set(first, [0, 1], ["d", 4])
store.set(first, {0: "e"})
name, count = store[first]
values: list[object] = store[0][:]
store[0] = ["f", 5]
following: Gtk.TreeIter | None = store.iter_next(store.get_iter(0))
got: tuple[object, ...] = store.get(first, 0, 1)
rows = [(row[0], row.path.get_indices()) for row in store]
del store[0]
tree = Gtk.TreeStore(str)
tree.append(tree.append(None, ["root"]), ["child"])
path = Gtk.TreePath((0, 1))
indices = [len(path), *path, Gtk.TreePath(3) < path]
"""


def test_type_checker_accepts_tree_models(tmp_path):
    """PyGObject's Gtk.ListStore, TreeStore and TreeModel overrides, which most code using GTK 3's tree views relies on."""
    result = mypy(tmp_path, TREE_MODEL_CODE)
    assert result.returncode == 0, result.stdout


def test_tree_model_code_runs():
    """What the stubs say about the tree models is what PyGObject does."""
    namespace: dict[str, object] = {}
    exec(TREE_MODEL_CODE, namespace)
    assert namespace["rows"] == [("f", [0]), ("e", [1])]
    assert namespace["indices"] == [2, 0, 1, False]


def test_user_data_before_other_arguments_is_passed():
    """What the stubs say about forward_find_char's user data is what PyGObject does."""
    from PyLiite4 import Gtk
    buffer = Gtk.TextBuffer(text="ab!c")
    start = buffer.get_start_iter()
    assert start.forward_find_char(lambda char, data: char == data, "!", None)
    assert start.get_offset() == 2


def test_type_checker_accepts_classes_with_several_bases(tmp_path):
    """Bases that define a name differently, such as Gtk.Widget's and Gtk.Native's realize, or interfaces implemented
    in Python, don't make a subclass with another base an error."""
    result = mypy(tmp_path, """
from PyLiite4 import Adw, GObject, Gio, Gtk

class Mixin: ...
class Window(Gtk.Window, Mixin): ...
class AppWindow(Adw.ApplicationWindow, Mixin): ...
class Row(Adw.EntryRow, Mixin): ...
class Model(GObject.Object, Gio.ListModel[GObject.Object]): ...
class Shape(Gtk.Widget, Gtk.Orientable): ...
class Group(GObject.Object, Gio.ActionGroup): ...
orientation: Gtk.Orientation = Shape().orientation
Window().realize()
""")
    assert result.returncode == 0, result.stdout


def generator_module():
    path = Path(__file__).parents[1] / "tools" / "generate.py"
    if not path.exists():
        pytest.skip("needs a source checkout, with tools/generate.py")
    spec = importlib.util.spec_from_file_location("generate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_overrides_the_stubs_describe_still_exist():
    """PyGObject still overrides what the generator's tables say it does."""
    generate = generator_module()
    for path in [*generate.STRIPPED_BOOLEAN, *generate.OVERRIDE_SIGNATURES]:
        namespace, owner, name = path.split(".")
        method = getattr(getattr(importlib.import_module(f"PyLiite4.{namespace}"), owner), name)
        assert Path(method.__code__.co_filename).parent.name == "overrides", path
        assert method.__qualname__.startswith("strip_boolean_result") == (path in generate.STRIPPED_BOOLEAN), path


@pytest.mark.parametrize("code", [
    "from PyLiite4 import GLib\nGLib.idle_add(GLib.PRIORITY_DEFAULT, print)\n",
    "from PyLiite4 import Gtk\nok, x, y = Gtk.Box().translate_coordinates(Gtk.Box(), 1.0, 2.0)\n",
    "from PyLiite4 import Gio, GObject, Gtk\nstore: Gio.ListStore[Gtk.Label] = Gio.ListStore()\nstore.append(Gtk.Button())\n",
    "from PyLiite4 import Gio\nasync def f(file: Gio.File) -> None:\n    data: str = (await file.load_contents_async(None))[1]\n",
])
def test_type_checker_rejects_wrong_gtk_patterns(tmp_path, code):
    result = mypy(tmp_path, code)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "sample.py" in result.stdout


def test_generated_ui_modules_type_check(tmp_path):
    from PyLiite4.tools import ui
    template = ('<interface><template class="Panel" parent="AdwBin"><child>'
                '<object class="GtkButton" id="save-button"><signal name="clicked" handler="on_save"/></object>'
                '</child></template></interface>')
    (tmp_path / "panel_ui.py").write_text(ui.compile_ui(template, "panel.ui"))
    (tmp_path / "main_ui.py").write_text(ui.compile_ui('<interface><object class="GtkLabel" id="a"/></interface>',
                                                       "main.ui"))
    result = mypy(tmp_path, """
from PyLiite4 import Adw, Gtk
from panel_ui import PanelChildren, template
from main_ui import MainObjects

@template
class Panel(PanelChildren, Adw.Bin):
    __gtype_name__ = "Panel"

    def on_save(self, button: Gtk.Button) -> None:
        self.save_button.set_label("Saved")

text: str = MainObjects().a.get_label()
""")
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("code", [
    "from PyLiite4.Gtk import Button\nButton().set_label(3)\n",
    "from PyLiite4.Gtk import Box\nBox().append('x')\n",
    "from PyLiite4.Gtk import Button\nButton().no_such_method()\n",
    "from PyLiite4.Gtk import Button\ndef f(x: int) -> None: ...\nButton().clicked.connect(f)\n",
])
def test_type_checker_rejects_wrong_code(tmp_path, code):
    result = mypy(tmp_path, code)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "sample.py" in result.stdout
