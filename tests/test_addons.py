"""PyLiite4-Addons: WebKitGTK, libshumate, libspelling, VTE, Gom and libmanette, from the add-ons wheel.

They need the add-ons wheel installed next to a bundled PyLiite4 wheel, so every test skips without it.
"""

import importlib
from pathlib import Path

import pytest

import PyLiite4
from PyLiite4 import GLib, GObject, Gtk
from PyLiite4.testing import wait_until

ADDONS = Path(PyLiite4.__file__).parent / "_addons"
NAMESPACES = ["JavaScriptCore", "WebKit", "Shumate", "Spelling", "Vte", "Gom", "Manette"]

pytestmark = pytest.mark.skipif(not ADDONS.is_dir(), reason="PyLiite4-Addons is not installed")


def loaded(library):
    return {line.split()[-1] for line in Path("/proc/self/maps").read_text().splitlines() if library in line}


def test_namespaces_load_their_libraries_from_the_addons():
    from PyLiite4 import Gom, Manette, Shumate, Spelling, Vte, WebKit  # noqa: F401
    for name in NAMESPACES:
        importlib.import_module(f"PyLiite4.{name}")
    # Creating an object of each makes GObject Introspection load its library.
    WebKit.Settings()
    Vte.Terminal()
    Shumate.Coordinate()
    Spelling.Checker()
    Gom.Adapter()
    Manette.Monitor()
    for library in ("libwebkitgtk-6.0.so.4", "libjavascriptcoregtk-6.0.so.1", "libvte-2.91-gtk4.so.0",
                    "libshumate-1.0.so.1", "libspelling-1.so.2", "libgom-1.0.so.0", "libmanette-0.2.so.0"):
        paths = loaded(library)
        assert paths and all(path.startswith(str(ADDONS)) for path in paths), (library, paths)
    # Their dependencies that the main wheel has come from it, not from a second copy.
    assert all("_bundled" in path for path in loaded("libgtk-4.so.1"))


def test_webkit_renders_a_page_and_runs_javascript():
    from PyLiite4 import WebKit
    view = WebKit.WebView()
    window = Gtk.Window(child=view, default_width=400, default_height=300)
    window.present()
    events = []
    view.load_changed.connect(lambda view, event: events.append(event))
    view.load_html("<title>PyLiite4</title><p id=greeting>Hello from WebKit</p>", None)
    # The page loads in WebKit's own processes, which the wheel bundles.
    wait_until(lambda: WebKit.LoadEvent.FINISHED in events, timeout=60)
    # The title can arrive just after the load finishes.
    wait_until(lambda: view.get_title() == "PyLiite4", timeout=10)
    results = []
    view.evaluate_javascript("document.getElementById('greeting').textContent", -1, None, None, None,
                             lambda view, result: results.append(view.evaluate_javascript_finish(result)))
    value = wait_until(lambda: results, timeout=30)[0]
    assert value.to_string() == "Hello from WebKit"
    window.destroy()


def test_vte_runs_a_command_in_a_terminal():
    from PyLiite4 import Vte
    terminal = Vte.Terminal()
    window = Gtk.Window(child=terminal)
    window.present()
    exited = []
    terminal.child_exited.connect(lambda terminal, status: exited.append(status))
    terminal.spawn_async(Vte.PtyFlags.DEFAULT, None, ["/bin/sh", "-c", "echo PyLiite4-$((6 * 7))"], None,
                         GLib.SpawnFlags.DEFAULT, None, None, -1, None, lambda terminal, pid, error: None)
    assert wait_until(lambda: exited, timeout=30) == [0]
    wait_until(lambda: "PyLiite4-42" in (terminal.get_text_format(Vte.Format.TEXT) or ""), timeout=10)
    window.destroy()


def test_spelling_uses_the_system_dictionaries():
    from PyLiite4 import Spelling
    provider = Spelling.Provider.get_default()
    languages = [provider.list_languages()[i].get_code() for i in range(len(provider.list_languages()))]
    if "en_US" not in languages:
        pytest.skip(f"no en_US Hunspell dictionary on this system: {languages}")
    checker = Spelling.Checker(provider=provider, language="en_US")
    assert checker.check_word("hello", -1)
    assert not checker.check_word("helo", -1)
    assert "hello" in checker.list_corrections("helo")


def test_shumate_shows_a_map():
    from PyLiite4 import Shumate
    registry = Shumate.MapSourceRegistry.new_with_defaults()
    source = registry.get_by_id(Shumate.MAP_SOURCE_OSM_MAPNIK)
    assert source is not None
    simple = Shumate.SimpleMap(map_source=source)
    simple.get_map().center_on(48.8566, 2.3522)
    window = Gtk.Window(child=simple, default_width=300, default_height=200)
    window.present()
    wait_until(lambda: simple.get_mapped())
    assert simple.get_viewport().get_latitude() == pytest.approx(48.8566)
    window.destroy()


def test_gom_stores_and_finds_objects(tmp_path):
    from PyLiite4 import Gom

    class Note(Gom.Resource):
        __gtype_name__ = "PyLiite4TestNote"
        id = GObject.Property(type=int)
        text = GObject.Property(type=str)

    Note.set_table("notes")
    Note.set_primary_key("id")
    adapter = Gom.Adapter()
    assert adapter.open_sync(str(tmp_path / "notes.db"))
    repository = Gom.Repository(adapter=adapter)
    assert repository.automatic_migrate_sync(1, [Note.__gtype__])
    assert Note(repository=repository, text="hello").save_sync()
    found = repository.find_sync(Note.__gtype__, None)
    found.fetch_sync(0, found.get_count())
    # len() and indexing come from Gom's own PyGObject overrides, which the add-ons wheel carries.
    assert len(found) == 1 and found[0].text == "hello"
    adapter.close_sync()


def test_manette_lists_game_controllers():
    from PyLiite4 import Manette
    monitor = Manette.Monitor()
    devices, iterator = [], monitor.iterate()
    while (found := iterator.next())[0]:
        devices.append(found[1])
    # A test machine usually has none, so this checks that the monitor works at all.
    assert all(isinstance(device, Manette.Device) for device in devices)
