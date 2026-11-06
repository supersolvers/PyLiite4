"""Path/Fill and Stroke

This demo shows how to use GskPath to draw shapes that are (a bit)
more complex than a rounded rectangle.

It also demonstrates printing to a stream with GtkPrintDialog.

Finally, it shows how to use GtkPopoverBin to add a context menu
to a widget that does not have one.
"""

from PyLiite4 import Gdk, Gio, GLib, GObject, Graphene, Gsk, Gtk, cairo


class GtkLogoPaintable(GObject.Object, Gdk.Paintable):
    __gtype_name__ = "GtkLogoPaintable"

    def __init__(self) -> None:
        super().__init__()
        self.width = 0
        self.height = 0
        self.path: list[Gsk.Path] = []
        self.color: list[Gdk.RGBA] = []

        self.stroke_path: Gsk.Path | None = None
        self.stroke1: Gsk.Stroke | None = None
        self.stroke2: Gsk.Stroke | None = None
        self.stroke_color = Gdk.RGBA()

    def do_get_intrinsic_width(self) -> int:
        return self.width

    def do_get_intrinsic_height(self) -> int:
        return self.height

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: float, height: float) -> None:
        for i in range(3):
            snapshot.push_fill(self.path[i], Gsk.FillRule.WINDING)
            snapshot.append_color(self.color[i], Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()
        for i in range(3):
            snapshot.push_stroke(self.stroke_path, self.stroke1)
            snapshot.append_color(self.stroke_color, Graphene.Rect().init(0, 0, width, height))
            snapshot.pop()

        snapshot.push_stroke(self.stroke_path, self.stroke2)
        snapshot.append_color(self.stroke_color, Graphene.Rect().init(0, 0, width, height))
        snapshot.pop()

    def do_get_flags(self) -> Gdk.PaintableFlags:
        return Gdk.PaintableFlags.STATIC_CONTENTS | Gdk.PaintableFlags.STATIC_SIZE


def parse_color(spec: str) -> Gdk.RGBA:
    color = Gdk.RGBA()
    color.parse(spec)
    return color


def gtk_logo_paintable_new() -> Gdk.Paintable:
    self = GtkLogoPaintable()

    # The paths and colors come from gtk-logo.svg.
    self.path = [
        Gsk.Path.parse("m3.12,66.17 -2.06,-51.46 32.93,24.7 v55.58 l-30.87,-28.82 z"),
        Gsk.Path.parse("m34,95 49.4,-20.58 4.12,-51.46 -53.52,16.47 v55.58 z"),
        Gsk.Path.parse("m1.06,14.71 32.93,24.7 53.52,-16.47 -36.75,-21.88 -49.7,13.65 z"),
    ]

    self.color = [parse_color("#e40000"), parse_color("#7fe719"), parse_color("#729fcf")]

    self.stroke_path = Gsk.Path.parse("m50.6,51.3 -47.3,14 z l33,23 z v-50")
    self.stroke1 = Gsk.Stroke.new(2.12)
    self.stroke2 = Gsk.Stroke.new(1.25)
    self.stroke_color = parse_color("#ffffff")

    _, bounds = self.path[0].get_stroke_bounds(self.stroke1)
    _, bounds2 = self.path[1].get_stroke_bounds(self.stroke1)
    bounds = bounds.union(bounds2)
    _, bounds2 = self.path[2].get_stroke_bounds(self.stroke1)
    bounds = bounds.union(bounds2)
    _, bounds2 = self.stroke_path.get_stroke_bounds(self.stroke2)
    bounds = bounds.union(bounds2)

    self.width = int(bounds.origin.x + bounds.size.width)
    self.height = int(bounds.origin.y + bounds.size.height)

    return self


class write_cairo:
    """cairo writes the PDF to a file-like object; C passes it a write function writing to the stream."""

    def __init__(self, stream: Gio.OutputStream) -> None:
        self.stream = stream

    def write(self, data: bytes) -> int:
        try:
            self.stream.write_all(data, None)
        except GLib.Error as error:
            print(f"Error writing pdf stream: {error.message}")
            raise
        return len(data)


def print_ready(dialog: Gtk.PrintDialog, result: Gio.AsyncResult, data: Gtk.Picture) -> None:
    try:
        stream = dialog.print_finish(result)
    except GLib.Error as error:
        print(f"Failed to get output stream: {error.message}")
        return

    snapshot = Gtk.Snapshot()
    paintable = data.get_paintable()
    paintable.snapshot(snapshot, 100, 100)
    node = snapshot.to_node()

    surface = cairo.PDFSurface(write_cairo(stream), 100, 100)
    cr = cairo.Context(surface)

    node.draw(cr)

    del cr
    surface.finish()

    try:
        stream.close(None)
    except GLib.Error as error:
        if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
            print(f"Error from close: {error.message}")


def print_(picture: Gtk.Widget) -> None:
    dialog = Gtk.PrintDialog()

    dialog.print(picture.get_root(), None, None, print_ready, picture)


def get_menu() -> Gio.MenuModel:
    menu = Gio.Menu()
    item = Gio.MenuItem.new("Print", "widget.print")
    menu.append_item(item)
    item = Gio.MenuItem.new("About", "app.about")
    menu.append_item(item)

    return menu


def activate_print(action: Gio.SimpleAction, parameter: GLib.Variant | None, user_data: Gtk.Widget) -> None:
    print_(user_data)


def get_actions(widget: Gtk.Widget) -> Gio.ActionGroup:
    entries = [
        ("print", activate_print),
    ]

    actions = Gio.SimpleActionGroup()
    actions.add_action_entries(entries, widget)

    return actions


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window

    if not window:
        window = Gtk.Window()
        window.set_resizable(False)
        window.set_default_size(100, 100)
        window.set_title("Fill and Stroke")

        window.set_application(Gio.Application.get_default())

        header = Gtk.HeaderBar()
        button = Gtk.Button.new_from_icon_name("printer-symbolic")
        header.pack_start(button)
        label = Gtk.Label(label="Fill and Stroke")
        label.add_css_class("title")
        header.set_title_widget(label)
        window.set_titlebar(header)
        window.close_request.connect(close_request)

        paintable = gtk_logo_paintable_new()
        picture = Gtk.Picture.new_for_paintable(paintable)
        picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        picture.set_can_shrink(False)

        bin = Gtk.PopoverBin()

        actions = get_actions(picture)
        bin.insert_action_group("widget", actions)

        bin.set_child(picture)

        menu = get_menu()
        bin.set_menu_model(menu)

        bin.set_handle_input(True)

        button.clicked.connect(lambda button: print_(picture))

        window.set_child(bin)

    if not window.get_visible():
        window.present()
    else:
        window.destroy()

    return window
