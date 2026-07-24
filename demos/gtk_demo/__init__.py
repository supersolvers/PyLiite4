"""A Python port of GTK Demo, the collection of examples that ships with GTK.

Each demo is a module in ``demos/`` named after GTK's C file, with a ``do(parent)`` function like the C ``do_*()``
ones. Its docstring is the C file's header comment: a title, which a "/" places under a parent row, then an optional
``#Keywords:`` line and a description. Modules without ``do`` are helpers that demos share.

``data/`` holds GTK's own data files and ``demo.gresource.xml``. :func:`register_resources` compiles them into a
GResource with the Python sources in place of the C ones, so demos load their data by the same resource paths as in C.
"""

import ast
import hashlib
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

from PyLiite4 import Gio, GLib, Gtk

HERE = Path(__file__).parent
DATA = HERE / "data"
DEMOS = HERE / "demos"


@dataclass
class Demo:
    name: str
    title: str
    description: str
    keywords: list[str] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return f"{self.name}.py"

    def run(self, parent: Gtk.Widget) -> Gtk.Widget | None:
        return import_module(f"{__name__}.demos.{self.name}").do(parent)


def _keywords(title: str, description: str) -> list[str]:
    # As GTK's geninclude.py does: the title's words and the GTK type names in the description.
    words = re.findall(r"[\w-]+", title.replace("/", " "))
    words += [word.rstrip(".,;:") for word in description.split()
              if re.match(r"(Gtk|Gdk|Pango|G[A-Z])\w", word) and word != "GTK"]
    return [word.lower() for word in words]


def all_demos() -> list[Demo]:
    """Every demo, sorted by title, read from the modules without importing them."""
    found = []
    for path in sorted(DEMOS.glob("*.py")):
        tree = ast.parse(path.read_text(), str(path))
        if not any(isinstance(node, ast.FunctionDef) and node.name == "do" for node in tree.body):
            continue
        docstring = ast.get_docstring(tree) or path.stem
        title, _, rest = docstring.partition("\n")
        keywords = []
        lines = []
        for line in rest.strip("\n").splitlines():
            if line.startswith("#Keywords:"):
                keywords = [word.strip().lower() for word in line.removeprefix("#Keywords:").split(",")]
            else:
                lines.append(line)
        description = "\n".join(lines).strip()
        found.append(Demo(path.stem, title.strip(), description, keywords + _keywords(title, description)))
    return sorted(found, key=lambda demo: demo.title.lower())


def _python_source(c_name: str) -> Path | None:
    path = DEMOS / f"{Path(c_name).stem.replace('-', '_')}.py"
    return path if path.exists() else None


_registered: Gio.Resource | None = None


def register_resources() -> None:
    """Compile and register the demos' GResource, once per process."""
    global _registered
    if _registered is not None:
        return
    tree = ET.parse(DATA / "demo.gresource.xml")
    for resource in tree.getroot():
        for entry in list(resource):
            name = entry.text or ""
            if not name.endswith((".c", ".h")):
                continue
            source = _python_source(name)
            # A C header has no Python counterpart: its .c file's module covers both.
            if source is None or name.endswith(".h"):
                resource.remove(entry)
            else:
                entry.set("alias", source.name)
                entry.text = f"../{DEMOS.name}/{source.name}"
    xml = ET.tostring(tree.getroot())
    inputs = hashlib.sha256(xml)
    for path in sorted(DEMOS.glob("*.py")):
        inputs.update(path.read_bytes())
    cache = Path(GLib.get_user_cache_dir()) / "PyLiite4" / "gtk-demo"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"demo-{inputs.hexdigest()[:16]}.gresource"
    if not target.exists():
        compiler = shutil.which("glib-compile-resources")
        if compiler is None:
            raise RuntimeError("glib-compile-resources was not found")
        # Other processes may be compiling the same resource, so work under names of this process's own.
        listing = cache / f"{target.stem}.{os.getpid()}.gresource.xml"
        temporary = cache / f"{target.name}.{os.getpid()}.tmp"
        listing.write_bytes(xml)
        try:
            subprocess.run([compiler, f"--target={temporary}", f"--sourcedir={DATA}", str(listing)], check=True)
            temporary.replace(target)
        finally:
            listing.unlink(missing_ok=True)
            temporary.unlink(missing_ok=True)
    _registered = Gio.Resource.load(str(target))
    Gio.resources_register(_registered)
