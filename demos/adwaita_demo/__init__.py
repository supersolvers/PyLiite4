"""A Python port of Adwaita Demo, the tour of libadwaita's widgets that ships with libadwaita.

The layout follows libadwaita's ``demo/`` folder: one module per C file, named after it with ``-`` replaced by ``_``,
next to its ``.ui`` template and the typed module ``pyliite4-ui`` generated from it (``*_ui.py``). Page folders with a
``-`` in their name are renamed the same way, so that Python can import them.

:func:`register_resources` compiles libadwaita's own ``adwaita-demo.gresources.xml`` into a GResource, so the demo
finds its icons, style sheet, shortcuts dialog and metadata by the same resource paths as in C.
"""

import hashlib
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from PyLiite4 import Adw, Gdk, Gio, GLib, Gtk

HERE = Path(__file__).parent
RESOURCE_BASE_PATH = "/org/gnome/Adwaita1/Demo"
METAINFO = "data/org.gnome.Adwaita1.Demo.metainfo.xml"

_registered: Gio.Resource | None = None


def _metainfo() -> bytes:
    """The metainfo file, as meson's configure_file() makes it from the .in.in template (minus translations)."""
    template = (HERE / f"{METAINFO}.in.in").read_text()
    version = f"{Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}"
    return template.replace("@BUILD_VERSION@", version).replace("@BUILD_DATE@", "unknown").encode()


def register_resources() -> None:
    """Compile and register the demo's GResource, once per process."""
    global _registered
    if _registered is not None:
        return
    tree = ET.parse(HERE / "adwaita-demo.gresources.xml")
    for resource in tree.getroot():
        for entry in resource:
            name = entry.text or ""
            # Python can't import folders with a "-", so the pages live in pages/bottom_sheets/ and so on.
            if name.startswith("pages/"):
                folder, _, file = name.removeprefix("pages/").partition("/")
                entry.text = f"pages/{folder.replace('-', '_')}/{file}"
                entry.set("alias", name)
    xml = ET.tostring(tree.getroot())
    metainfo = _metainfo()
    inputs = hashlib.sha256(xml + metainfo)
    for entry in tree.getroot().iter("file"):
        if entry.text != METAINFO:
            inputs.update((HERE / (entry.text or "")).read_bytes())
    cache = Path(GLib.get_user_cache_dir()) / "PyLiite4" / "adwaita-demo"
    target = cache / f"demo-{inputs.hexdigest()[:16]}.gresource"
    if not target.exists():
        compiler = shutil.which("glib-compile-resources")
        if compiler is None:
            raise RuntimeError("glib-compile-resources was not found")
        generated = cache / target.stem
        (generated / METAINFO).parent.mkdir(parents=True, exist_ok=True)
        (generated / METAINFO).write_bytes(metainfo)
        listing = cache / f"{target.stem}.gresource.xml"
        listing.write_bytes(xml)
        subprocess.run([compiler, f"--target={target}.tmp", f"--sourcedir={HERE}", f"--sourcedir={generated}",
                        str(listing)], check=True)
        Path(f"{target}.tmp").replace(target)
        listing.unlink()
        shutil.rmtree(generated)
    _registered = Gio.Resource.load(str(target))
    Gio.resources_register(_registered)


def _setup_plain_application(app: Gtk.Application) -> None:
    """Do for a plain Gtk.Application what Adw.Application does at startup for the demo's resource base path.

    Adw.Application loads ``style.css``, adds ``icons/`` to the icon theme and turns ``shortcuts-dialog.ui`` into the
    ``app.shortcuts`` action. tests/run_demo.py opens the demo in a Gtk.Application, so do the same by hand.
    """
    Adw.init()
    display = Gdk.Display.get_default()
    provider = Gtk.CssProvider()
    provider.load_from_resource(f"{RESOURCE_BASE_PATH}/style.css")
    Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    Gtk.IconTheme.get_for_display(display).add_resource_path(f"{RESOURCE_BASE_PATH}/icons")

    def show_shortcuts(_action: Gio.SimpleAction, _parameter: GLib.Variant | None) -> None:
        builder = Gtk.Builder.new_from_resource(f"{RESOURCE_BASE_PATH}/shortcuts-dialog.ui")
        dialog: Adw.ShortcutsDialog = builder.get_object("shortcuts_dialog")
        dialog.present(app.get_active_window())

    action = Gio.SimpleAction(name="shortcuts")
    action.activate.connect(show_shortcuts)
    app.add_action(action)
    app.set_accels_for_action("app.shortcuts", ["<Control>question"])


def open_window(app: Gtk.Application) -> Gtk.Window:
    """Register the resources, then build and present the demo's main window for ``app``."""
    register_resources()
    from . import adwaita_demo

    if not isinstance(app, Adw.Application):
        _setup_plain_application(app)
    if app.lookup_action("about") is None:
        adwaita_demo.add_actions(app)
    return adwaita_demo.show_window(app)


def _sidebar(window: Gtk.Window) -> Adw.Sidebar:
    from .adw_demo_window import AdwDemoWindow

    assert isinstance(window, AdwDemoWindow)
    return window.sidebar


def page_names(window: Gtk.Window) -> list[str]:
    """The title of every page in the window's sidebar."""
    items = _sidebar(window).get_items()
    return [items.get_item(index).get_title() for index in range(items.get_n_items())]


def show_page(window: Gtk.Window, name: str) -> None:
    """Show the page titled ``name``, as clicking its sidebar row does."""
    sidebar = _sidebar(window)
    index = page_names(window).index(name)
    sidebar.set_selected(index)
    sidebar.activated.emit(index)
