"""The stubs are only useful if they describe what really exists at runtime."""

import ast
import importlib
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


@pytest.mark.parametrize("code", [
    "from PyLiite4 import GLib\nGLib.idle_add(GLib.PRIORITY_DEFAULT, print)\n",
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
