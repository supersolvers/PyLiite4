"""Benchmark/Scrolling
#Keywords: GtkScrolledWindow

This demo scrolls a view with various content.
"""

import os
import random

from PyLiite4 import Gdk, Gio, GLib, Graphene, Gsk, Gtk, GtkSource, Pango

tick_cb = 0
hadjustment: Gtk.Adjustment | None = None
vadjustment: Gtk.Adjustment | None = None
window: Gtk.Window | None = None
scrolledwindow: Gtk.ScrolledWindow | None = None
selected = 0

N_WIDGET_TYPES = 12


hincrement = 5
vincrement = 5


def scroll_cb(widget: Gtk.Widget, frame_clock: Gdk.FrameClock) -> bool:
    global hincrement, vincrement

    value = vadjustment.get_value()
    if (value + vincrement <= vadjustment.get_lower()
            or value + vincrement >= vadjustment.get_upper() - vadjustment.get_page_size()):
        vincrement = -vincrement

    vadjustment.set_value(value + vincrement)

    value = hadjustment.get_value()
    if (value + hincrement <= hadjustment.get_lower()
            or value + hincrement >= hadjustment.get_upper() - hadjustment.get_page_size()):
        hincrement = -hincrement

    hadjustment.set_value(value + hincrement)

    return GLib.SOURCE_CONTINUE


def create_icon_by_id(id: int) -> Gtk.Widget:
    from .fishbowl import create_icon_by_id
    return create_icon_by_id(id)


def populate_icons() -> None:
    global hincrement, vincrement

    grid = Gtk.Grid()
    grid.set_halign(Gtk.Align.CENTER)
    grid.set_margin_start(10)
    grid.set_margin_end(10)
    grid.set_margin_top(10)
    grid.set_margin_bottom(10)
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)

    for top in range(100):
        for left in range(15):
            grid.attach(create_icon_by_id(top * 15 + left), left, top, 1, 1)

    hincrement = 0
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(grid)


def fontify(format: str, buffer: GtkSource.Buffer) -> None:
    # The C demo highlights with GTK Demo's fontify.c; the Python launcher uses GtkSourceView for that.
    buffer.set_language(GtkSource.LanguageManager.get_default().get_language(format))
    buffer.set_highlight_syntax(True)


PLAIN_TEXT, HIGHLIGHTED_TEXT, UNDERLINED_TEXT = range(3)


def underlinify(buffer: Gtk.TextBuffer) -> None:
    tags = buffer.get_tag_table()
    tag = [Gtk.TextTag(name="error"), Gtk.TextTag(name="strikeout"), Gtk.TextTag(name="double")]
    tag[0].set_property("underline", Pango.Underline.ERROR)
    tag[1].set_property("strikethrough", True)
    tag[2].set_property("underline", Pango.Underline.DOUBLE)
    tag[2].set_property("underline-rgba", Gdk.RGBA(red=0.0, green=1.0, blue=1.0, alpha=1.0))
    tags.add(tag[0])
    tags.add(tag[1])
    tags.add(tag[2])

    end = buffer.get_start_iter()

    while True:
        end.forward_word_end()
        start = end.copy()
        start.backward_word_start()
        buffer.apply_tag(tag[random.randrange(0, 3)], start, end)
        if not end.forward_word_ends(3):
            break


def populate_text(resource: str, kind: int) -> None:
    global hincrement, vincrement

    content = Gio.resources_lookup_data(resource, Gio.ResourceLookupFlags.NONE).get_data().decode()

    # GtkSourceView does the highlighting here, so the buffer is a GtkSourceBuffer, a GtkTextBuffer subclass
    buffer = GtkSource.Buffer() if kind == HIGHLIGHTED_TEXT else Gtk.TextBuffer()
    buffer.set_text(content, -1)

    if kind == HIGHLIGHTED_TEXT:
        fontify("python3", buffer)
    elif kind == UNDERLINED_TEXT:
        underlinify(buffer)

    textview = Gtk.TextView()
    textview.set_buffer(buffer)

    hincrement = 0
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(textview)


def populate_emoji_text() -> None:
    global hincrement, vincrement

    s = []

    for i in range(500):
        if i % 2:
            s.append("<span underline=\"single\" underline_color=\"red\">x</span>")
        for j in range(30):
            s.append("💓")
            s.append("<span underline=\"single\" underline_color=\"red\">x</span>")
        s.append("\n")

    buffer = Gtk.TextBuffer()
    iter = buffer.get_start_iter()
    buffer.insert_markup(iter, "".join(s), -1)

    textview = Gtk.TextView()
    textview.set_buffer(buffer)

    hincrement = 0
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(textview)


def populate_image() -> None:
    global hincrement, vincrement

    image = Gtk.Picture.new_for_resource("/sliding_puzzle/portland-rose.jpg")
    image.set_can_shrink(False)

    hincrement = 5
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(image)


def populate_list() -> None:
    global hincrement, vincrement
    from .listview_weather import create_weather_view

    list = create_weather_view()

    hincrement = 5
    vincrement = 0

    scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(list)


def populate_grid() -> None:
    global hincrement, vincrement
    from .listview_colors import create_color_grid, gtk_color_list_new

    list = create_color_grid()

    selection = Gtk.NoSelection.new(gtk_color_list_new(2097152))
    list.set_model(selection)

    hincrement = 0
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(list)


def populate_list2() -> None:
    global hincrement, vincrement
    from .listview_ucd import create_ucd_view

    list = create_ucd_view(None)

    hincrement = 0
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(list)


class Symbolic:
    def __init__(self, path: str) -> None:
        self.path = path
        self.paintable: Gdk.Paintable | None = None


symbolics = [Symbolic(path) for path in [
    "bookmark-new-symbolic.svg",
    "color-select-symbolic.svg",
    "document-open-recent-symbolic.svg",
    "document-open-symbolic.svg",
    "document-save-as-symbolic.svg",
    "document-save-symbolic.svg",
    "edit-clear-all-symbolic.svg",
    "edit-clear-symbolic-rtl.svg",
    "edit-clear-symbolic.svg",
    "edit-copy-symbolic.svg",
    "edit-cut-symbolic.svg",
    "edit-delete-symbolic.svg",
    "edit-find-symbolic.svg",
    "edit-paste-symbolic.svg",
    "edit-select-all-symbolic.svg",
    "find-location-symbolic.svg",
    "folder-new-symbolic.svg",
    "function-linear-symbolic.svg",
    "gesture-pinch-symbolic.svg",
    "gesture-rotate-anticlockwise-symbolic.svg",
    "gesture-rotate-clockwise-symbolic.svg",
    "gesture-stretch-symbolic.svg",
    "gesture-swipe-left-symbolic.svg",
    "gesture-swipe-right-symbolic.svg",
    "gesture-two-finger-swipe-left-symbolic.svg",
    "gesture-two-finger-swipe-right-symbolic.svg",
    "go-next-symbolic-rtl.svg",
    "go-next-symbolic.svg",
    "go-previous-symbolic-rtl.svg",
    "go-previous-symbolic.svg",
    "insert-image-symbolic.svg",
    "insert-object-symbolic.svg",
    "list-add-symbolic.svg",
    "list-remove-all-symbolic.svg",
    "list-remove-symbolic.svg",
    "media-eject-symbolic.svg",
    "media-playback-pause-symbolic.svg",
    "media-playback-start-symbolic.svg",
    "media-playback-stop-symbolic.svg",
    "media-record-symbolic.svg",
    "object-select-symbolic.svg",
    "open-menu-symbolic.svg",
    "pan-down-symbolic.svg",
    "pan-end-symbolic-rtl.svg",
    "pan-end-symbolic.svg",
    "pan-start-symbolic-rtl.svg",
    "pan-start-symbolic.svg",
    "pan-up-symbolic.svg",
    "system-run-symbolic.svg",
    "system-search-symbolic.svg",
    "value-decrease-symbolic.svg",
    "value-increase-symbolic.svg",
    "view-conceal-symbolic.svg",
    "view-grid-symbolic.svg",
    "view-list-symbolic.svg",
    "view-more-symbolic.svg",
    "view-refresh-symbolic.svg",
    "view-reveal-symbolic.svg",
    "window-close-symbolic.svg",
    "window-maximize-symbolic.svg",
    "window-minimize-symbolic.svg",
    "window-restore-symbolic.svg",
    "emoji-activities-symbolic.svg",
    "emoji-body-symbolic.svg",
    "emoji-flags-symbolic.svg",
    "emoji-food-symbolic.svg",
    "emoji-nature-symbolic.svg",
    "emoji-objects-symbolic.svg",
    "emoji-people-symbolic.svg",
    "emoji-recent-symbolic.svg",
    "emoji-symbols-symbolic.svg",
    "emoji-travel-symbolic.svg",
    "drive-harddisk-symbolic.svg",
    "printer-symbolic.svg",
    "emblem-important-symbolic.svg",
    "emblem-system-symbolic.svg",
    "face-smile-big-symbolic.svg",
    "face-smile-symbolic.svg",
    "application-x-executable-symbolic.svg",
    "text-x-generic-symbolic.svg",
    "folder-documents-symbolic.svg",
    "folder-download-symbolic.svg",
    "folder-music-symbolic.svg",
    "folder-pictures-symbolic.svg",
    "folder-publicshare-symbolic.svg",
    "folder-remote-symbolic.svg",
    "folder-saved-search-symbolic.svg",
    "folder-symbolic.svg",
    "folder-templates-symbolic.svg",
    "folder-videos-symbolic.svg",
    "network-server-symbolic.svg",
    "network-workgroup-symbolic.svg",
    "user-desktop-symbolic.svg",
    "user-home-symbolic.svg",
    "user-trash-symbolic.svg",
    "audio-volume-high-symbolic.svg",
    "audio-volume-low-symbolic.svg",
    "audio-volume-medium-symbolic.svg",
    "audio-volume-muted-symbolic.svg",
    "caps-lock-symbolic.svg",
    "changes-allow-symbolic.svg",
    "changes-prevent-symbolic.svg",
    "dialog-error-symbolic.svg",
    "dialog-information-symbolic.svg",
    "dialog-password-symbolic.svg",
    "dialog-question-symbolic.svg",
    "dialog-warning-symbolic.svg",
    "display-brightness-symbolic.svg",
    "media-playlist-repeat-symbolic.svg",
    "orientation-landscape-inverse-symbolic.svg",
    "orientation-landscape-symbolic.svg",
    "orientation-portrait-inverse-symbolic.svg",
    "orientation-portrait-symbolic.svg",
    "process-working-symbolic.svg",
    "switch-off-symbolic.svg",
    "switch-on-symbolic.svg",
]]

_symbolic_idx = 0


def create_symbolic() -> Gtk.Widget:
    global _symbolic_idx

    _symbolic_idx = (_symbolic_idx + 1) % len(symbolics)
    idx = _symbolic_idx
    if symbolics[idx].paintable is None:
        uri = "resource:///org/gtk/libgtk/icons/" + symbolics[idx].path
        file = Gio.File.new_for_uri(uri)
        symbolics[idx].paintable = Gtk.IconPaintable.new_for_file(file, 16, 1)

    image = Gtk.Image()
    image.set_icon_size(Gtk.IconSize.LARGE)
    image.set_from_paintable(symbolics[idx].paintable)

    return image


def populate_symbolics() -> None:
    global hincrement, vincrement

    grid = Gtk.Grid()
    grid.set_halign(Gtk.Align.CENTER)
    grid.set_margin_start(10)
    grid.set_margin_end(10)
    grid.set_margin_top(10)
    grid.set_margin_bottom(10)
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)

    for top in range(100):
        for left in range(15):
            grid.attach(create_symbolic(), left, top, 1, 1)

    hincrement = 0
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(grid)


_svg_idx = 0


def create_svg() -> Gtk.Widget:
    global _svg_idx

    _svg_idx = (_svg_idx + 1) % len(symbolics)
    idx = _svg_idx
    if symbolics[idx].paintable is None:
        path = "/org/gtk/libgtk/icons/" + symbolics[idx].path
        symbolics[idx].paintable = Gtk.Svg.new_from_resource(path)

    image = Gtk.Image()
    image.set_icon_size(Gtk.IconSize.LARGE)
    image.set_from_paintable(symbolics[idx].paintable)

    return image


def populate_svg() -> None:
    global hincrement, vincrement

    grid = Gtk.Grid()
    grid.set_halign(Gtk.Align.CENTER)
    grid.set_margin_start(10)
    grid.set_margin_end(10)
    grid.set_margin_top(10)
    grid.set_margin_bottom(10)
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)

    for top in range(100):
        for left in range(15):
            grid.attach(create_svg(), left, top, 1, 1)

    hincrement = 0
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(grid)


def create_squiggle() -> Gtk.Widget:
    builder = Gsk.PathBuilder.new()

    x = random.uniform(1, 16)
    y = random.uniform(1, 16)
    builder.move_to(x, y)
    for i in range(5):
        x = random.uniform(1, 16)
        y = random.uniform(1, 16)
        builder.line_to(x, y)
    builder.close()

    path = builder.to_path()
    stroke = Gsk.Stroke.new(1)

    snapshot = Gtk.Snapshot()
    snapshot.append_stroke(path, stroke, Gdk.RGBA(red=0, green=0, blue=0, alpha=1))
    paintable = snapshot.to_paintable(Graphene.Size().init(18, 18))

    image = Gtk.Image()
    image.set_icon_size(Gtk.IconSize.LARGE)
    image.set_from_paintable(paintable)

    return image


def populate_squiggles() -> None:
    global hincrement, vincrement

    grid = Gtk.Grid()
    grid.set_halign(Gtk.Align.CENTER)
    grid.set_margin_start(10)
    grid.set_margin_end(10)
    grid.set_margin_top(10)
    grid.set_margin_bottom(10)
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)

    for top in range(100):
        for left in range(15):
            grid.attach(create_squiggle(), left, top, 1, 1)

    hincrement = 0
    vincrement = 5

    scrolledwindow.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolledwindow.set_child(grid)


def set_widget_type(type: int) -> None:
    global tick_cb, selected

    if tick_cb:
        window.remove_tick_callback(tick_cb)

    if scrolledwindow.get_child():
        scrolledwindow.set_child(None)

    selected = type

    if selected == 0:
        window.set_title("Scrolling icons")
        populate_icons()
    elif selected == 1:
        window.set_title("Scrolling plain text")
        populate_text("/sources/font_features.py", PLAIN_TEXT)
    elif selected == 2:
        window.set_title("Scrolling colored text")
        populate_text("/sources/font_features.py", HIGHLIGHTED_TEXT)
    elif selected == 3:
        window.set_title("Scrolling text with underlines")
        populate_text("/org/gtk/Demo4/Moby-Dick.txt", UNDERLINED_TEXT)
    elif selected == 4:
        window.set_title("Scrolling text with Emoji")
        populate_emoji_text()
    elif selected == 5:
        window.set_title("Scrolling a big image")
        populate_image()
    elif selected == 6:
        window.set_title("Scrolling a list")
        populate_list()
    elif selected == 7:
        window.set_title("Scrolling a columned list")
        populate_list2()
    elif selected == 8:
        window.set_title("Scrolling a grid")
        populate_grid()
    elif selected == 9:
        window.set_title("Scrolling symbolics")
        populate_symbolics()
    elif selected == 10:
        window.set_title("Scrolling SVG")
        populate_svg()
    elif selected == 11:
        window.set_title("Scrolling squiggles")
        populate_squiggles()
    else:
        raise AssertionError("not reached")

    tick_cb = window.add_tick_callback(scroll_cb)


def iconscroll_next_clicked_cb(source: Gtk.Button) -> None:
    if selected + 1 >= N_WIDGET_TYPES:
        new_index = 0
    else:
        new_index = selected + 1

    set_widget_type(new_index)


def iconscroll_prev_clicked_cb(source: Gtk.Button) -> None:
    if selected - 1 < 0:
        new_index = N_WIDGET_TYPES - 1
    else:
        new_index = selected - 1

    set_widget_type(new_index)


def update_fps(label: Gtk.Label) -> bool:
    frame_clock = label.get_frame_clock()

    # C reads the frame clock of an unrealized label too; it is None there in Python
    fps = frame_clock.get_fps() if frame_clock else 0.0
    label.set_label(f"{fps:.2f} fps")

    return GLib.SOURCE_CONTINUE


def close_request(win: Gtk.Window) -> bool:
    global window, tick_cb
    win.destroy()
    window = None
    tick_cb = 0
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, scrolledwindow, hadjustment, vadjustment, tick_cb

    if window is None:
        builder = Gtk.Builder({
            "iconscroll_prev_clicked_cb": iconscroll_prev_clicked_cb,
            "iconscroll_next_clicked_cb": iconscroll_next_clicked_cb,
        })

        builder.add_from_resource("/iconscroll/iconscroll.ui")
        window = builder.get_object("window")
        window.close_request.connect(close_request)
        window.set_display(do_widget.get_display())

        scrolledwindow = builder.get_object("scrolledwindow")
        window.realize()
        hadjustment = builder.get_object("hadjustment")
        vadjustment = builder.get_object("vadjustment")
        if os.environ.get("ICONSCROLL"):
            set_widget_type(max(0, min(int(os.environ["ICONSCROLL"]), N_WIDGET_TYPES)))
        else:
            set_widget_type(0)

        label = builder.get_object("fps_label")
        id = GLib.timeout_add(500, update_fps, label, priority=GLib.PRIORITY_HIGH)
        label.unrealize.connect(lambda label: GLib.source_remove(id))

    if not window.get_visible():
        window.set_visible(True)
    else:
        close_request(window)

    return window
