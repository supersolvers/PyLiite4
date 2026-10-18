"""Workbench's demo library, ported to PyLiite4.

Workbench (https://github.com/workbenchdev/Workbench) is a GNOME app for trying out GTK; its demos are in the public
domain under CC0. Each one is a folder in ``library/``:

- ``main.ui``: the interface, converted from Workbench's Blueprint file to GtkBuilder XML. Its first top-level widget
  is the preview, shown in a window unless it's a window itself.
- ``main.py``: the code, run as a script after the interface is built. It reaches the interface through
  :data:`workbench`, as Workbench demos do.
- ``main.css`` (optional), loaded for the display while the demo runs.
- ``main.json``: Workbench's metadata, a category and description, plus ``"requires"``: namespaces the demo needs
  beyond GTK and libadwaita.
- ``icons/`` (optional): icons the demo uses by name.
"""

import importlib
import importlib.util
import json
import runpy
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from PyLiite4 import Adw, Gdk, Gio, GLib, Gtk

HERE = Path(__file__).parent
LIBRARY = HERE / "library"
CATEGORIES = {"user_interface": "User Interface", "controls": "Controls", "layout": "Layout",
              "feedback": "Feedback", "navigation": "Navigation", "platform": "Platform APIs",
              "network": "Network", "tools": "Tools"}
# Namespaces PyLiite4 doesn't provide; demos that need one are listed but can't run.
UNAVAILABLE = {"Gly"}
# Namespaces from the PyLiite4-Addons wheel, which demos can use when it's installed.
ADDONS = {"WebKit", "Shumate", "Spelling", "Manette", "Gom"}


@dataclass
class Demo:
    name: str
    category: str
    description: str
    requires: list[str] = field(default_factory=list)

    @property
    def folder(self) -> Path:
        return LIBRARY / self.name

    @property
    def missing(self) -> list[str]:
        return [namespace for namespace in self.requires if namespace in UNAVAILABLE
                or (namespace in ADDONS and importlib.util.find_spec(f"PyLiite4.{namespace}") is None)]


def demos() -> list[Demo]:
    found = []
    for metadata in sorted(LIBRARY.glob("*/main.json")):
        info = json.loads(metadata.read_text())
        found.append(Demo(metadata.parent.name, info.get("category", "tools"), info.get("description", ""),
                          info.get("requires", [])))
    return found


class Workbench:
    """What a running demo sees as ``workbench``: its builder, its window and a way to find its files."""

    def __init__(self) -> None:
        self.builder = Gtk.Builder()
        self.window: Gtk.Window | None = None
        self.folder = LIBRARY

    def resolve(self, path: str) -> str:
        """The URI of a file in the demo's folder."""
        return Gio.File.new_for_path(str(self.folder)).resolve_relative_path(path).get_uri()


workbench = Workbench()
_css: Gtk.CssProvider | None = None


def _preview_id(ui: Path) -> str:
    for element in ET.parse(ui).getroot():
        if element.tag == "object" and element.get("id"):
            return element.get("id")
    raise ValueError(f"{ui}: the first top-level object needs an id")


def _session_copy(demo: Demo) -> Path:
    """A fresh copy of the demo's folder to run from, as Workbench does, so demos that write files leave the
    repository alone."""
    folder = Path(GLib.get_user_cache_dir()) / "PyLiite4" / "workbench" / demo.name
    shutil.rmtree(folder, ignore_errors=True)
    shutil.copytree(demo.folder, folder, ignore=shutil.ignore_patterns("__pycache__"))
    return folder


def run(demo: Demo, application: Gtk.Application) -> Gtk.Window:
    """Build a demo's interface, run its code and show its window.

    Demos can register GObject types, which can't be registered twice, so run each one in a process of its own:
    ``python -m demos.workbench --run NAME`` does that.
    """
    global _css
    if demo.missing:
        raise RuntimeError(f"{demo.name} needs {', '.join(demo.missing)}, which isn't installed")
    # GtkBuilder only knows a library's widgets once its namespace is loaded.
    for namespace in demo.requires:
        module = importlib.import_module(f"PyLiite4.{namespace}")
        if namespace == "GtkSource":
            module.init()
    folder = _session_copy(demo)
    display = Gdk.Display.get_default()
    if _css is not None:
        Gtk.StyleContext.remove_provider_for_display(display, _css)
        _css = None
    if (folder / "main.css").exists():
        _css = Gtk.CssProvider()
        _css.load_from_path(str(folder / "main.css"))
        Gtk.StyleContext.add_provider_for_display(display, _css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    if (folder / "icons").is_dir():
        theme = Gtk.IconTheme.get_for_display(display)
        if str(folder / "icons") not in theme.get_search_path():
            theme.add_search_path(str(folder / "icons"))

    builder = Gtk.Builder()
    builder.add_from_file(str(folder / "main.ui"))
    preview = builder.get_object(_preview_id(folder / "main.ui"))
    if isinstance(preview, Gtk.Window):
        window = preview
        window.set_application(application)
    else:
        window = Adw.ApplicationWindow(application=application, title=demo.name, default_width=600,
                                       default_height=500, content=preview)
    workbench.builder, workbench.window, workbench.folder = builder, window, folder
    runpy.run_path(str(folder / "main.py"), run_name=f"workbench_{GLib.uuid_string_random()[:8]}")
    window.present()
    return window
