# PyLiite4

Complete, typed Python bindings for GTK 4 and libadwaita, packaged with GTK itself.

PyLiite4 gives Python developers what PySide6 gives them for Qt: one install, typed APIs and the tools to build an
application. The toolkit is GTK, used the GTK way. GTK's concepts and names are kept; this isn't a Qt emulation layer.

```python
from PyLiite4.Gtk import Application, ApplicationWindow, Button


def on_click(button: Button) -> None:
    button.set_label("Clicked")


def on_activate(app: Application) -> None:
    button = Button(label="Hello")
    button.clicked.connect(on_click)
    ApplicationWindow(application=app, child=button).present()


app = Application(application_id="org.example.Hello")
app.activate.connect(on_activate)
app.run([])
```

## What you get

- **Modules:** `GLib`, `GObject`, `Gio`, `GdkPixbuf`, `Pango`, `PangoCairo`, `HarfBuzz`, `Graphene`, `Gdk`, `Gsk`,
  `Gtk`, `Adw`, `Rsvg` (librsvg, for SVG), and the libraries GTK applications commonly add: `GtkSource` (GtkSourceView, a code editor), `Soup` (HTTP clients and
  servers), `Xdp` and `XdpGtk4` (libportal, for desktop portals such as screenshots, the camera and file access),
  and `Gst`, `GstBase`, `GstAudio`, `GstVideo`, `GstPbutils` and `GstApp` (GStreamer, with gst-python's
  additions).
- **Type stubs** for every class, method, property, signal and constructor keyword, generated from GTK's GIR files.
  They also describe PyGObject's Python additions: `GLib.idle_add`, awaitable async methods, `Gio.ListStore[Item]`,
  `GLib.Variant`, `Gio.Settings` as a mapping, and pycairo contexts for drawing.
- **Signal objects** and **property attributes:** see below.
- **`pyliite4-ui`** turns a GtkBuilder `.ui` file into typed Python: a template becomes a typed composite widget.
- **`pyliite4-resources`** compiles a `.gresource.xml` file to a Python module. Importing it registers the resources.

The classes are PyGObject's own, extended in place. Objects created by GTK, such as those from `Gtk.Builder`, have the
same API, and PyGObject code and documentation still apply.

PyLiite4 also corrects APIs that crash, corrupt memory or can't be called through PyGObject as it stands:

- Signals in `.ui` files connect as GTK's C code connects them, including `object=` and swapped handlers, which
  PyGObject passes wrongly or refuses.
- `Gio.File.replace_contents_async()` no longer writes freed memory, and `Gsk.RoundedRect.init()` and its variants
  return a usable rectangle.
- `Gtk.CustomLayout.new()` keeps its callbacks alive; `Pango.extents_to_pixels()` no longer crashes.
- `Gsk.Path.get_start_point()`, `get_end_point()`, `get_closest_point()` and `Gsk.PathMeasure.get_point()` return
  `Gsk.PathPoint`s, which PyGObject can't allocate.
- `Gtk.Expression.evaluate(this)` returns the value, and `Pango.SCALE_*` exist.

## Signals

```python
handler = button.clicked.connect(on_click)      # returns the handler id
button.clicked.disconnect(on_click)             # or pass the handler id
button.clicked.emit()
with button.clicked.blocked(handler):           # g_signal_handler_block
    ...
entry.notify["text"].connect(on_text_changed)   # a signal detail
```

Callbacks receive the emitting object first: `def on_click(button): ...`. Declare signals on your own classes with
`changed = Signal(int)` on a `GObject.Object` subclass; `Signal` is `GObject.Signal`, and takes its `flags`,
`return_type` and `accumulator`.

A connected bound method doesn't keep its object alive, and the connection ends when the object goes away, as with
`g_signal_connect_object()`. Lambdas and functions are held until you disconnect them.

Where a name is both a method and a signal, the attribute does both: `widget.show()` and `widget.show.connect(fn)`.

## Properties

GObject properties are also attributes, so `button.label = "Save"` does the same as `button.set_label("Save")`, and
`box.margin_top` reads the property. `button.props.label` and the getters and setters still work. Use
`source.bind_property("active", target, "visible")` to keep two properties in step, and `notify["name"]` to follow one.

A method or signal of the same name takes priority. In a subclass, assigning to a name that is a property sets the
property, so `self.child = widget` on a `Gtk.Button` subclass changes the button's child. Declare the name on the class
first to keep it as a plain attribute.

## Writing a GTK application

### The main loop, threads and asyncio

GTK runs on one thread. A worker thread hands results back with `GLib.idle_add`, which runs a function on the main
loop:

```python
def finished(text: str) -> bool:
    label.set_label(text)
    return GLib.SOURCE_REMOVE

threading.Thread(target=lambda: GLib.idle_add(finished, compute())).start()
```

A signal emitted on a worker thread runs its handlers on that thread, so emit from the main loop instead.

To use asyncio, call `use_asyncio()` before `app.run()`. Coroutines then run on GLib's main loop, Gio's async methods
can be awaited by leaving out the callback, and `asyncio.to_thread` moves blocking work off it:

```python
async def load(app: Gtk.Application, path: str) -> None:
    ok, data, etag = await Gio.File.new_for_path(path).load_contents_async(None)
    summary = await asyncio.to_thread(parse, data)

use_asyncio()
app.activate.connect(lambda app: app.create_asyncio_task(load(app, "notes.txt")))
app.run([])
```

`create_asyncio_task` keeps the application running until the task ends.

### Custom widgets and drawing

Subclass `Gtk.Widget` and override its virtual methods: `do_snapshot` draws, `do_measure` gives the size, and
`do_size_allocate` places children. A snapshot takes render nodes directly, or a cairo context for one area. Import cairo from PyLiite4, as
`from PyLiite4 import cairo`, since bundled wheels keep their copy of pycairo private:

```python
class Swatch(Gtk.Widget):
    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        return 40, 60, -1, -1

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        bounds = Graphene.Rect().init(0, 0, self.get_width(), self.get_height())
        snapshot.append_color(self.colour, bounds)
        cr = snapshot.append_cairo(bounds)
        ...
```

Text is laid out with Pango: `self.create_pango_layout(text)` gives a layout to measure and to draw with
`snapshot.append_layout()`. Call `queue_draw()` or `queue_resize()` when the drawing or size changes.

### Lists

Keep the data in a `Gio.ListStore` of `GObject.Object` items, and show it with `Gtk.ListView`, `Gtk.GridView` or
`Gtk.ColumnView`. A factory makes and binds a widget for each visible row:

```python
store: Gio.ListStore[Fruit] = Gio.ListStore(item_type=Fruit)
factory = Gtk.SignalListItemFactory()
factory.setup.connect(lambda _, item: item.set_child(Gtk.Label()))
factory.bind.connect(lambda _, item: item.get_child().set_label(item.get_item().name))
view = Gtk.ListView(model=Gtk.SingleSelection(model=store), factory=factory)
```

Wrap the store in `Gtk.FilterListModel` or `Gtk.SortListModel` to filter or sort it. A store is a Python sequence:
`len(store)`, `store[0]`, `for item in store` and `store[1] = item` all work.

### Styling

GTK styles widgets with CSS. Give a widget a class with `add_css_class("warning")`, and load your style sheet once for
the display:

```python
provider = Gtk.CssProvider()
provider.load_from_resource("/org/example/App/style.css")
Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
```

libadwaita follows the system's light, dark and high-contrast settings; use its named colours, such as
`var(--accent-bg-color)`, rather than fixed ones. `Adw.StyleManager` reports the current scheme.

Fonts the application ships go into a GResource like its other files, and `register_font()` from
`PyLiite4.Extras` makes them usable without installing anything. It returns the families, which CSS `font-family`
then finds:

```python
families = register_font(Gio.File.new_for_uri("resource:///org/example/App/fonts/Inter.ttf"))
```

It also takes the font's bytes or a path. Text already laid out in those families is laid out again, so it can be
called at any time, though startup is the natural place.

### Input

Attach event controllers to a widget: `Gtk.EventControllerKey`, `Gtk.GestureClick`, `Gtk.EventControllerMotion`,
`Gtk.DropTarget` and others. Keyboard shortcuts are actions: add a `Gio.SimpleAction` to the application or window, and
give it accelerators with `app.set_accels_for_action("win.save", ["<Control>s"])`.

A widget's tooltip (`set_tooltip_text()`) appears only while the pointer rests on it. To show one when the
application decides, after a click or while a link is hovered, use `show_tip()` from `PyLiite4.Extras`:

```python
show_tip(switch, "Switched on")                     # below the widget
show_tip(view, "https://example.org", (x, y))       # at a point in it
```

It looks like a GTK tooltip, takes no focus, and hides after a while, when the pointer moves off the widget, or on a
key press or click. Its text is also announced to screen readers. The application has one such tip, as in Qt;
`Tip` is the widget itself, for keeping one of your own.

### UI files and templates

Describe a composite widget in a `.ui` file with a `<template>`, then let `pyliite4-ui` type it:

```bash
pyliite4-ui window.ui -o window_ui.py
```

```python
from window_ui import ExampleWindowChildren, template


@template
class ExampleWindow(ExampleWindowChildren, Adw.ApplicationWindow):
    __gtype_name__ = "ExampleWindow"

    def on_save_clicked(self, button: Gtk.Button) -> None:
        self.status.set_label("Saved")
```

`ExampleWindowChildren` types every object in the file that has an id, and `template` applies `Gtk.Template`. It binds
them and every signal handler and expression closure that the file names, and fails at import if the class has the
wrong parent, `__gtype_name__` or handlers. With `--resource /org/example/App/window.ui` the template is loaded from
that GResource path rather than embedded in the module. As in C, a handler with `object=` gets that object after the
signal's arguments, or, when swapped, first, and an expression closure gets the object it's evaluated for first. A `.ui` file without a template becomes a class with a typed attribute per object id, built with
`Gtk.Builder`.

Ship `.ui` files, CSS and icons as GResources, compiled with `pyliite4-resources app.gresource.xml -o app_resources.py`,
and load them by resource path.

### Testing

`PyLiite4.testing` is a pytest plugin, installed with PyLiite4 and off until `pytest --gtk` or `gtk = true` under
`[tool.pytest.ini_options]` turns it on. Each run then gets a private Xvfb display and D-Bus session, no portals,
in-memory settings and temporary XDG directories, so tests never reach the desktop. A test fails if it logs a GLib
warning or if one of its callbacks raises. The `gtkbot` fixture shows widgets and destroys them afterwards:

```python
def test_save(gtkbot):
    window = gtkbot.show(MyWindow())
    gtkbot.input.type(gtkbot.find(window, Gtk.Entry), "notes.txt")
    gtkbot.input.click(gtkbot.find(window, Gtk.Button, label="Save"))
    gtkbot.wait_until(lambda: Path("notes.txt").exists())
```

`gtkbot.input` sends real pointer and keyboard events through XTest, so they go through event controllers,
gestures and focus as a user's would. GTK 4 has no API of its own to inject events. It needs libXtst, and runs only
on the plugin's Xvfb. `gtkbot.click()`, `activate()`, `type_text()` and `press_key()` go through signals, actions and
shortcuts instead, which is quicker but skips event handling. The plugin also has `wait_until()`,
`expect_signal()`, `wait_signal()`, `find()` and `gtk_log` for expected warnings. Accessibility is recorded
in-process, so `Gtk.test_accessible_has_role()` and its kin work, and `gtkbot.announcements` lists what the test
announced to screen readers.

### Coming from PySide6

| PySide6 | GTK |
| --- | --- |
| `QThread`, queued connections | `GLib.idle_add`, or asyncio with `use_asyncio()` |
| `paintEvent`, `QPainter` | `do_snapshot` with `Gtk.Snapshot`, or cairo through `append_cairo` |
| `sizeHint`, `QSizePolicy` | `do_measure`, `hexpand`/`vexpand`, `halign`/`valign` |
| `QFontMetrics` | `Pango.Layout` |
| `QFontDatabase.addApplicationFont`, `addApplicationFontFromData` | `PyLiite4.Extras.register_font` |
| Style sheets, `QPalette` | CSS classes and `Gtk.CssProvider`; libadwaita colours |
| `eventFilter`, `keyPressEvent` | Event controllers |
| `QToolTip.showText` | `PyLiite4.Extras.show_tip` |
| `QAction`, `QShortcut` | `Gio.SimpleAction` and accelerators |
| `QAbstractItemModel`, `QListWidget`, delegates | `Gio.ListStore`, list views and item factories |
| `QSettings` | `Gio.Settings` with a schema |
| `pyside6-uic` | `.ui` templates and `pyliite4-ui` |
| `pyside6-rcc` | GResources and `pyliite4-resources` |
| `QSignalBlocker` | `signal.blocked(handler)` |
| `QTest.mouseClick`, `keyClick`, `keyClicks` | `gtkbot.input.click`, `key`, `type` |
| `QSignalSpy`, `qtbot.waitSignal` | `gtkbot.expect_signal`, `wait_signal` |
| `qtbot.waitUntil`, `qWait` | `gtkbot.wait_until`, `wait` |

### Known PyGObject limitations

These come from PyGObject or from GTK's annotations, and PyLiite4 doesn't work around them yet:

- A `Gtk.Template` widget with signal handlers that GTK creates itself, for example from a GType in a `.ui` file or
  with `GObject.new()`, can crash when it's collected. Create such widgets from Python.
- A Python `Gtk.LayoutManager` set with `set_layout_manager_type()` gets the wrong `self`; call `set_layout_manager()`
  with an instance instead.
- A Python object kept only by GTK, such as an item in a `Gio.ListStore`, can lose its Python wrapper, and with it
  any `weakref` to it. Its attributes survive.
- Data passed to `connect()` is held strongly. Passing an object that owns the emitter makes a reference cycle
  that keeps both alive; pass `obj.weak_ref()` instead.
- Signals with out arguments, such as `Gtk.SpinButton::input`, can't be handled from Python.
- `Gdk.Surface.destroy()` drops a reference it doesn't own, and `Pango.GlyphString.glyphs` reads past its first
  glyph; avoid both.
- `Gdk.ContentProvider.get_value()` can't be called; variadic C functions such as
  `gtk_widget_class_add_binding_action()` aren't available (use `add_shortcut()`).

## Demos

`demos/` holds Python ports of GTK Demo (111 demos), libadwaita's demo (21 pages) and Workbench's demo library (116),
each tested by `tests/test_demos.py`. Run `python -m demos.gtk_demo`, `python -m demos.adwaita_demo` or `python -m
demos.workbench` from the repository root; see `demos/README.md`.

## Installing

Bundled wheels contain GTK, libadwaita, PyGObject and the Adwaita icons, and need nothing else from the system except
glibc, the C++ runtime and graphics drivers:

```bash
pip install PyLiite4-0.1.0-cp313-cp313-manylinux_2_34_x86_64.whl
```

The plain package uses the system's GTK and PyGObject instead:

```bash
pip install .
```

### Platform support

| | Status |
| --- | --- |
| Linux x86-64, bundled | Python 3.10 to 3.14, glibc 2.34 or newer (Ubuntu 22.04, Debian 12, RHEL 9 and later) |
| Linux, system GTK | Python 3.10 or newer; PyGObject must be installable |
| Windows, macOS | Not implemented |

Bundled wheels include GStreamer plugins for free formats such as Ogg, Opus, Vorbis, Theora, VP8/9 and WAV, but no
patent-encumbered codecs like H.264 or AAC. They also include translations and the IBus input-method client, which
talks to the IBus daemon on the user's system. HTTPS uses the bundled OpenSSL with the system's CA certificates, found
at the usual path for Debian, Fedora, openSUSE or Alpine, or wherever `SSL_CERT_FILE` points. SVG images load through
librsvg. Formats that need glycin, such as HEIF and JPEG XL, aren't supported.

## License

PyLiite4 is licensed under the GNU Lesser General Public License, version 3 only (`LGPL-3.0-only`). See
[LICENSE](LICENSE) and [COPYING.GPL3](COPYING.GPL3), whose terms the LGPL builds on.

Bundled wheels also contain about 95 other projects under their own licenses, among them GTK, GLib and
GStreamer (LGPL), X11 and Cairo (MIT and LGPL or MPL) and the Rust crates that librsvg compiles in. Their license
texts are in `PyLiite4/_bundled/licenses/`. `NOTICES.txt` there lists every project with its version, license and
source archive, and `components.json` lists which bundled file comes from which project. The wheel metadata includes
the same list as `THIRD-PARTY-NOTICES.txt`.

None of the bundled libraries is GPL-only. Some packages also contain GPL programs, but the wheel takes only their
LGPL, BSD or dual-licensed libraries. To keep it that way, the build fails when a project that mentions the GPL isn't
on a reviewed list in `tools/third_party.py`.

The source archive of every bundled project, at the exact version in the wheels, is published with each release,
next to the wheels.

## Development

```bash
python3 tools/generate.py
```

regenerates `src/PyLiite4/<Namespace>.py` and `.pyi` from the GIR files, so the stubs match the GTK version installed
when they were generated.

```bash
xvfb-run -a env -u WAYLAND_DISPLAY GDK_BACKEND=x11 PYTHONPATH=src python3 -m pytest
```

runs the tests in a virtual display. They need `pytest` and `mypy`.

```bash
python3 tools/build_wheel.py
```

builds a bundled wheel from this machine's GTK in `dist/`, usable only on this glibc or newer. It needs `patchelf`.

### Release wheels

Release wheels are built from source in a `manylinux_2_34` root, without a container engine. This needs `bwrap`, and
`Xvfb` for testing:

```bash
tools/manylinux/fetch_root.py /path/to/root
```

```bash
tools/manylinux/enter.sh /path/to/root /project/tools/manylinux/build_stack.sh
```

```bash
tools/manylinux/enter.sh /path/to/root /project/tools/manylinux/build_wheels.sh cp310 cp311 cp312 cp313 cp314
```

```bash
tools/manylinux/verify_in_root.sh /path/to/root dist/PyLiite4-0.1.0-cp314-cp314-manylinux_2_34_x86_64.whl cp314
```

The stack build records finished packages, so running it again resumes after a failure.

Each wheel build traces every bundled file to the project it came from: the meson install logs for the stack built
from source, the source RPMs for AlmaLinux packages, and PyPI and crates.io for Python packages and Rust crates. The
build fails if a file has no project, a project has no license texts, or a project mentions the GPL and hasn't been
reviewed. `build_wheels.sh` also copies every project's source archive, with `SHA256SUMS`, into `dist/sources/`,
which is published with the release. Downloaded source RPMs and sdists are kept in `build/third-party/`.

```bash
tools/verify_wheel.sh dist/PyLiite4-*.whl
```

installs that wheel in a clean venv and runs the tests in a `bwrap` sandbox with the system's GTK stack hidden.

```bash
dbus-run-session -- tools/verify_wayland.sh dist/PyLiite4-0.1.0-cp314-cp314-manylinux_2_34_x86_64.whl
```

does the same on Wayland, with a headless `kwin_wayland` as the compositor.
