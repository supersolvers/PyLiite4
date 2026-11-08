"""PyLiite4-Addons: WebKitGTK, libshumate, libspelling, VTE, Gom, libmanette and glycin, from the add-ons wheel.

They need the add-ons wheel installed next to a bundled PyLiite4 wheel, so every test skips without it.
"""

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import PyLiite4
from PyLiite4 import GLib, GObject, Gtk
from PyLiite4.testing import wait_until

ADDONS = Path(PyLiite4.__file__).parent / "_addons"
NAMESPACES = ["JavaScriptCore", "WebKit", "Shumate", "Spelling", "Vte", "Gom", "Manette", "Gly", "GlyGtk4"]

pytestmark = pytest.mark.skipif(not ADDONS.is_dir(), reason="PyLiite4-Addons is not installed")


def bubblewrap_works():
    bwrap = shutil.which("bwrap")
    return bool(bwrap) and subprocess.run([bwrap, "--ro-bind", "/", "/", "--unshare-all", "true"],
                                          capture_output=True).returncode == 0


# WebKit and glycin run their helper processes in bubblewrap sandboxes, as upstream does.
needs_bubblewrap = pytest.mark.skipif(not bubblewrap_works(), reason="bubblewrap isn't installed or can't run here")


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


@needs_bubblewrap
def test_webkit_runs_pages_in_its_sandbox():
    from PyLiite4 import WebKit
    if os.environ.get("WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS", "0") != "0":
        pytest.skip("WebKit's sandbox is turned off in this environment")
    view = WebKit.WebView()
    window = Gtk.Window(child=view)
    window.present()
    events = []
    view.load_changed.connect(lambda view, event: events.append(event))
    view.load_html("<p>Sandboxed</p>", None)
    wait_until(lambda: WebKit.LoadEvent.FINISHED in events, timeout=60)

    def ancestors(pid):
        names = []
        while pid > 1 and pid != os.getpid():
            stat = Path(f"/proc/{pid}/stat").read_text()
            names.append(stat[stat.index("(") + 1:stat.rindex(")")])
            pid = int(stat[stat.rindex(")") + 2:].split()[1])
        return names, pid == os.getpid()

    web_processes = []
    for entry in Path("/proc").iterdir():
        try:
            if entry.name.isdigit() and (entry / "comm").read_text().startswith("WebKitWebProces"):
                names, ours = ancestors(int(entry.name))
                if ours:
                    web_processes.append(names)
        except (FileNotFoundError, ProcessLookupError):
            continue
    # The page's process runs under bwrap, which a patch lets WebKit find on PATH.
    assert web_processes and all("bwrap" in names for names in web_processes), web_processes
    window.destroy()


def test_webkit_explains_a_sandbox_that_cant_start(tmp_path):
    # A bwrap that can't create namespaces, as inside another sandbox. WebKit itself would end the program.
    (tmp_path / "bwrap").write_text("#!/bin/sh\necho 'bwrap: No permissions to create a new namespace' >&2\nexit 1\n")
    (tmp_path / "bwrap").chmod(0o755)
    environment = {key: value for key, value in os.environ.items() if key != "WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS"}
    environment["PATH"] = f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}"
    script = "from PyLiite4 import WebKit"
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=environment)
    assert result.returncode != 0 and "ImportError" in result.stderr, result.stderr
    assert "No permissions to create a new namespace" in result.stderr
    assert "WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1" in result.stderr
    # The opt-out, for an application that shows only its own content.
    environment["WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS"] = "1"
    assert subprocess.run([sys.executable, "-c", script], env=environment).returncode == 0


# 16x16 images in #3070c0, which the wheel's libheif decodes but can't encode.
AVIF = ("AAAAHGZ0eXBhdmlmAAAAAG1pZjFhdmlmbWlhZgAAANZtZXRhAAAAAAAAACFoZGxyAAAAAAAAAABwaWN0AAAAAAAAAAAAAAAAAAAAAA5w"
        "aXRtAAAAAAABAAAAImlsb2MAAAAAREAAAQABAAAAAAD6AAEAAAAAAAAAIAAAACNpaW5mAAAAAAABAAAAFWluZmUCAAAAAAEAAGF2MDEA"
        "AAAAVmlwcnAAAAA4aXBjbwAAAAxhdjFDgQAMAAAAABRpc3BlAAAAAAAAABAAAAAQAAAAEHBpeGkAAAAAAwgICAAAABZpcG1hAAAAAAAA"
        "AAEAAQOBAgMAAAAobWRhdBIACgkYDP/YICGg0IAyERZABhhhhAAAeJ2iz/wMe7Di")
HEIF = ("AAAAHGZ0eXBoZWljAAAAAG1pZjFoZWljbWlhZgAAAWhtZXRhAAAAAAAAACFoZGxyAAAAAAAAAABwaWN0AAAAAAAAAAAAAAAAAAAAAA5w"
        "aXRtAAAAAAABAAAAImlsb2MAAAAAREAAAQABAAAAAAGMAAEAAAAAAAAANAAAACNpaW5mAAAAAAABAAAAFWluZmUCAAAAAAEAAGh2YzEA"
        "AAAA6GlwcnAAAADJaXBjbwAAAHVodmNDAQNwAAAAAAAAAAAAHvAA/P34+AAADwNgAAEAGEABDAH//wNwAAADAJAAAAMAAAMAHroCQGEA"
        "AQApQgEBA3AAAAMAkAAAAwAAAwAeoCCBBZbqrprm4CGgwIAAAAyAAAADAIRiAAEABkQBwXPBiQAAABRpc3BlAAAAAAAAAEAAAABAAAAA"
        "KGNsYXAAAAAQAAAAAQAAABAAAAAB////0AAAAAL////QAAAAAgAAABBwaXhpAAAAAAMICAgAAAAXaXBtYQAAAAAAAAABAAEEgQIEgwAA"
        "ADxtZGF0AAAAMCgBrwnIWZjQOSNXf/+85Tkfj/X/90cbVn8Tr+jsZTrKQ59EsZPOO74MgIeDuF7LcA==")
GLY_SCRIPT = """
import base64, sys
from pathlib import Path
from PyLiite4 import Gio, GLib, Gly, GlyGtk4

folder = Path(sys.argv[1])
pixels = GLib.Bytes.new(bytes([0x30, 0x70, 0xc0]) * 16 * 16)
for mime_type, name in [("image/png", "png"), ("image/jpeg", "jpg"), ("image/webp", "webp"), ("image/jxl", "jxl")]:
    # Encoding runs in the sandbox too.
    try:
        creator = Gly.Creator.new(mime_type)
        creator.add_frame(16, 16, Gly.MemoryFormat.R8G8B8, pixels)
        (folder / f"square.{name}").write_bytes(creator.create().get_data().get_data())
    except GLib.Error as error:
        print(f".{name}", "error", error.message)
(folder / "square.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">'
                                   '<rect width="16" height="16" fill="#3070c0"/></svg>')
(folder / "square.avif").write_bytes(base64.b64decode(sys.argv[2]))
(folder / "square.heif").write_bytes(base64.b64decode(sys.argv[3]))
for path in sorted(folder.iterdir()):
    loader = Gly.Loader.new(Gio.File.new_for_path(str(path)))
    loader.set_accepted_memory_formats(Gly.MemoryFormatSelection.R8G8B8)
    try:
        image = loader.load()
    except GLib.Error as error:
        print(path.suffix, "error", error.message)
        continue
    frame = image.next_frame()
    data, stride = frame.get_buf_bytes().get_data(), frame.get_stride()
    texture = GlyGtk4.frame_get_texture(frame)
    print(path.suffix, image.get_mime_type(), texture.get_width(), texture.get_height(),
          *data[8 * stride + 8 * 3:8 * stride + 8 * 3 + 3])
"""


def run_gly(tmp_path, **environment):
    images = tmp_path / "images"
    images.mkdir()
    result = subprocess.run([sys.executable, "-c", GLY_SCRIPT, str(images), AVIF, HEIF], capture_output=True,
                            text=True, timeout=120, env={**os.environ, **environment})
    assert result.returncode == 0, result.stderr
    return {line.split()[0]: line.split()[1:] for line in result.stdout.splitlines() if line.startswith(".")}, \
        result.stderr


@needs_bubblewrap
def test_gly_loads_images_in_its_sandbox(tmp_path):
    loaded, stderr = run_gly(tmp_path)
    # glycin says when it can't sandbox its loaders.
    assert "without sandbox" not in stderr, stderr
    assert set(loaded) == {".png", ".jpg", ".webp", ".jxl", ".svg", ".avif", ".heif"}
    for suffix, (mime_type, width, height, *pixel) in loaded.items():
        assert mime_type.startswith("image/") and (width, height) == ("16", "16"), (suffix, loaded[suffix])
        # The lossy formats come back close to the colour they were given.
        assert all(abs(int(got) - want) <= 12 for got, want in zip(pixel, (0x30, 0x70, 0xc0))), (suffix, pixel)


def test_gly_needs_bubblewrap_or_the_documented_opt_out(tmp_path):
    # With bwrap nowhere on PATH, glycin won't run its loaders unsandboxed by itself.
    loaded, _ = run_gly(tmp_path, PATH="/nonexistent")
    assert all(result[0] == "error" for result in loaded.values()), loaded
    # Its own switch for applications that accept the risk.
    shutil.rmtree(tmp_path / "images")
    loaded, stderr = run_gly(tmp_path, PATH="/nonexistent", GLYCIN_DISABLE_SANDBOX="i-know-the-risks")
    assert all(result[0] != "error" for result in loaded.values()), loaded
    assert "without sandbox" in stderr
