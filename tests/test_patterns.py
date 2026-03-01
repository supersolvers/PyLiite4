"""The GTK ways of doing what a PySide6 application does, run for real in a window."""

import asyncio
import io
import threading

from PyLiite4 import GLib, GObject, Gdk, Gio, Graphene, Gtk, cairo, use_asyncio


def spin(condition, seconds=5):
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + seconds * 1_000_000
    while not condition() and GLib.get_monotonic_time() < deadline:
        context.iteration(False)
    return condition()


def in_application(body):
    """Run ``body(app)`` while a Gtk.Application runs, and re-raise what it raises."""
    assert Gtk.init_check(), "no display: run the tests under xvfb-run"
    application = Gtk.Application(application_id="org.example.PyLiite4Patterns",
                                  flags=Gio.ApplicationFlags.NON_UNIQUE)
    result = {}

    def activated(app):
        try:
            result["value"] = body(app)
        except BaseException as error:
            # An exception can't cross the main loop, and would leave it running forever.
            result["error"] = error
        finally:
            app.quit()

    application.activate.connect(activated)
    application.run([])
    if "error" in result:
        raise result["error"]
    return result.get("value")


def show(app, child, width=120, height=80):
    window = Gtk.ApplicationWindow(application=app, child=child, default_width=width, default_height=height)
    window.present()
    assert spin(lambda: child.get_mapped() and child.get_width() > 0)
    return window


def pixels(widget):
    """The widget as a cairo image surface, rendered by GTK."""
    paintable = Gtk.WidgetPaintable.new(widget)
    assert spin(lambda: paintable.get_intrinsic_width() > 0)
    node = {}

    def render_node():
        snapshot = Gtk.Snapshot()
        paintable.snapshot(snapshot, paintable.get_intrinsic_width(), paintable.get_intrinsic_height())
        node["root"] = snapshot.to_node()
        return node["root"] is not None

    assert spin(render_node)
    texture = widget.get_native().get_renderer().render_texture(node["root"], None)
    return cairo.ImageSurface.create_from_png(io.BytesIO(texture.save_to_png_bytes().get_data()))


def colour_at(surface, x, y):
    data, stride = surface.get_data(), surface.get_stride()
    blue, green, red, _alpha = data[y * stride + x * 4:y * stride + x * 4 + 4]
    return red, green, blue


def test_worker_thread_reports_through_idle_add():
    def body(app):
        label = Gtk.Label(label="working")
        show(app, label)
        main_thread = threading.get_ident()
        seen = []

        def finished(text):
            seen.append(threading.get_ident())
            label.set_label(text)
            return GLib.SOURCE_REMOVE

        threading.Thread(target=lambda: GLib.idle_add(finished, "done")).start()
        assert spin(lambda: label.get_label() == "done")
        assert seen == [main_thread]

    in_application(body)


def test_asyncio_runs_on_the_glib_main_loop(tmp_path):
    path = tmp_path / "note.txt"
    path.write_text("hello")
    loop = use_asyncio()
    result = {}

    async def work(app, label):
        file = Gio.File.new_for_path(str(path))
        ok, data, _etag = await file.load_contents_async(None)
        result["data"] = (ok, bytes(data))
        result["thread"] = await asyncio.to_thread(threading.get_ident)
        await asyncio.sleep(0.01)
        label.set_label("loaded")
        result["loop"] = asyncio.get_running_loop()
        app.quit()

    def activated(app):
        label = Gtk.Label()
        Gtk.ApplicationWindow(application=app, child=label).present()
        app.create_asyncio_task(work(app, label))

    assert Gtk.init_check()
    application = Gtk.Application(application_id="org.example.PyLiite4Async", flags=Gio.ApplicationFlags.NON_UNIQUE)
    application.activate.connect(activated)
    application.run([])
    assert result["data"] == (True, b"hello")
    assert result["thread"] != threading.get_ident()
    assert result["loop"] is loop


class Swatch(Gtk.Widget):
    """A custom widget: it draws with a snapshot and asks for its size by measuring."""

    def __init__(self, colour):
        super().__init__()
        self.colour = colour

    def do_measure(self, orientation, for_size):
        return 40, 60, -1, -1

    def do_snapshot(self, snapshot):
        width, height = self.get_width(), self.get_height()
        snapshot.append_color(self.colour, Graphene.Rect().init(0, 0, width / 2, height))
        cr = snapshot.append_cairo(Graphene.Rect().init(width / 2, 0, width / 2, height))
        cr.set_source_rgb(0, 0, 1)
        cr.paint()


def test_custom_widget_draws_with_snapshot():
    def body(app):
        colour = Gdk.RGBA()
        assert colour.parse("#ff0000")
        swatch = Swatch(colour)
        box = Gtk.Box()
        box.append(swatch)
        show(app, box)
        assert swatch.measure(Gtk.Orientation.HORIZONTAL, -1)[:2] == (40, 60)
        surface = pixels(swatch)
        width, height = surface.get_width(), surface.get_height()
        assert colour_at(surface, width // 4, height // 2) == (255, 0, 0)
        assert colour_at(surface, 3 * width // 4, height // 2) == (0, 0, 255)

    in_application(body)


class Fruit(GObject.Object):
    name = GObject.Property(type=str, default="")

    def __init__(self, name):
        super().__init__(name=name)


def test_list_view_shows_a_list_store():
    def body(app):
        store: Gio.ListStore[Fruit] = Gio.ListStore(item_type=Fruit)
        for name in ("apple", "pear", "plum"):
            store.append(Fruit(name))
        factory = Gtk.SignalListItemFactory()
        factory.setup.connect(lambda _factory, item: item.set_child(Gtk.Label()))
        factory.bind.connect(lambda _factory, item: item.get_child().set_label(item.get_item().name))
        view = Gtk.ListView(model=Gtk.SingleSelection(model=store), factory=factory)
        show(app, view, height=200)

        def labels():
            found, child = [], view.get_first_child()
            while child:
                label = child.get_first_child()
                if isinstance(label, Gtk.Label) and label.get_mapped():
                    found.append(label.get_label())
                child = child.get_next_sibling()
            return found

        assert spin(lambda: labels() == ["apple", "pear", "plum"])
        store[1] = Fruit("quince")
        assert spin(lambda: labels() == ["apple", "quince", "plum"])
        assert [fruit.name for fruit in store] == ["apple", "quince", "plum"]

    in_application(body)


def test_style_classes_come_from_a_css_provider():
    def body(app):
        provider = Gtk.CssProvider()
        provider.load_from_string(".warning-box { background-color: #00ff00; }")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        box = Gtk.Box(width_request=40, height_request=40)
        box.add_css_class("warning-box")
        outer = Gtk.Box()
        outer.append(box)
        show(app, outer)
        surface = pixels(box)
        assert colour_at(surface, surface.get_width() // 2, surface.get_height() // 2) == (0, 255, 0)

    in_application(body)


def test_event_controller_replaces_an_event_filter():
    def body(app):
        entry = Gtk.Entry()
        show(app, entry)
        pressed = []
        controller = Gtk.EventControllerKey()
        controller.key_pressed.connect(lambda _c, keyval, _code, _state: pressed.append(keyval) or True)
        entry.add_controller(controller)
        assert controller.key_pressed.emit(Gdk.KEY_Escape, 9, Gdk.ModifierType.NO_MODIFIER_MASK)
        assert pressed == [Gdk.KEY_Escape]

    in_application(body)
