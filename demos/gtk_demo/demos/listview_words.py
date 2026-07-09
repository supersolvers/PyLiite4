"""Lists/Words
#Keywords: GtkListView, GtkFilterListModel, GtkInscription

This demo shows filtering a long list - of words.

You should have the file `/usr/share/dict/words` installed for
this demo to work.
"""

from PyLiite4 import Gio, GLib, Gtk

window: Gtk.Window | None = None
progress: Gtk.ProgressBar | None = None

factory_text = (
    "<?xml version='1.0' encoding='UTF-8'?>\n"
    "<interface>\n"
    "  <template class='GtkListItem'>\n"
    "    <property name='child'>\n"
    "      <object class='GtkInscription'>\n"
    "        <property name='xalign'>0</property>\n"
    "        <binding name='text'>\n"
    "          <lookup name='string' type='GtkStringObject'>\n"
    "            <lookup name='item'>GtkListItem</lookup>\n"
    "          </lookup>\n"
    "        </binding>\n"
    "      </object>\n"
    "    </property>\n"
    "  </template>\n"
    "</interface>\n"
)


def update_title_cb(model: Gtk.FilterListModel, *_args: object) -> None:
    total = model.get_model().get_n_items()
    pending = model.get_pending()

    title = f"{model.get_n_items()} lines"

    progress.set_visible(pending != 0)
    progress.set_fraction((total - pending) / total if total > 0 else 0.)
    window.set_title(title)


def make_valid(data: bytes) -> str:
    """g_utf8_make_valid()"""
    return data.decode("utf-8", errors="replace")


def read_lines_cb(stream: Gio.BufferedInputStream, result: Gio.AsyncResult, stringlist: Gtk.StringList) -> None:
    try:
        n_filled = stream.fill_finish(result)
    except GLib.Error as error:
        print(f"Could not read data: {error.message}")
        return

    buffer = stream.peek_buffer()

    if n_filled == 0:
        if buffer:
            stringlist.take(make_valid(buffer))
        return

    lines = None
    # C skips the stream past each line in turn; skipping past all the complete lines at once is the same.
    end = buffer.rfind(b"\n")
    if end != -1:
        lines = [make_valid(line) for line in buffer[:end].split(b"\n") if line]
        try:
            stream.skip(end + 1, None)
        except GLib.Error:
            pass
    if end == -1:
        stream.set_buffer_size(stream.get_buffer_size() + 4096)
    elif lines:
        stringlist.splice(stringlist.get_n_items(), 0, lines)

    stream.fill_async(-1, GLib.PRIORITY_HIGH_IDLE, None, read_lines_cb, stringlist)


def file_is_open_cb(file: Gio.File, result: Gio.AsyncResult, data: Gtk.StringList) -> None:
    try:
        file_stream = file.read_finish(result)
    except GLib.Error as error:
        print(f"Could not open file: {error.message}")
        return

    stream = Gio.BufferedInputStream.new(file_stream)
    stream.fill_async(-1, GLib.PRIORITY_HIGH_IDLE, None, read_lines_cb, data)


def load_file(list: Gtk.StringList, file: Gio.File) -> None:
    list.splice(0, list.get_n_items(), None)
    file.read_async(GLib.PRIORITY_HIGH_IDLE, None, file_is_open_cb, list)


def open_response_cb(dialog: Gtk.FileDialog, result: Gio.AsyncResult, stringlist: Gtk.StringList) -> None:
    try:
        file = dialog.open_finish(result)
    except GLib.Error:
        file = None
    if file:
        load_file(stringlist, file)


def file_open_cb(button: Gtk.Widget, stringlist: Gtk.StringList) -> None:
    dialog = Gtk.FileDialog()
    dialog.open(button.get_root(), None, open_response_cb, stringlist)


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window, progress
    if window is None:
        file = Gio.File.new_for_path("/usr/share/dict/words")
        if file.query_exists(None):
            stringlist = Gtk.StringList.new(None)
            load_file(stringlist, file)
        else:
            words = ("lorem ipsum dolor sit amet consectetur adipisci elit sed eiusmod tempor incidunt labore et "
                     "dolore magna aliqua ut enim ad minim veniam quis nostrud exercitation ullamco laboris nisi ut "
                     "aliquid ex ea commodi consequat").split(" ")
            stringlist = Gtk.StringList.new(words)

        filter = Gtk.StringFilter.new(Gtk.PropertyExpression.new(Gtk.StringObject, None, "string"))
        filter_model = Gtk.FilterListModel.new(stringlist, filter)
        filter_model.set_incremental(True)

        window = Gtk.Window()
        window.set_default_size(400, 600)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        open_button = Gtk.Button.new_with_mnemonic("_Open")
        open_button.clicked.connect(file_open_cb, stringlist)
        header.pack_start(open_button)
        window.set_titlebar(header)

        window.set_display(do_widget.get_display())

        window.close_request.connect(close_request)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        window.set_child(vbox)

        search_entry = Gtk.SearchEntry()
        search_entry.bind_property("text", filter, "search", 0)
        vbox.append(search_entry)

        overlay = Gtk.Overlay()
        vbox.append(overlay)

        progress = Gtk.ProgressBar()
        progress.set_halign(Gtk.Align.FILL)
        progress.set_valign(Gtk.Align.START)
        progress.set_hexpand(True)
        overlay.add_overlay(progress)

        sw = Gtk.ScrolledWindow()
        sw.set_vexpand(True)
        overlay.set_child(sw)

        listview = Gtk.ListView.new(
            Gtk.NoSelection.new(filter_model),
            Gtk.BuilderListItemFactory.new_from_bytes(None, GLib.Bytes.new(factory_text.encode())))
        sw.set_child(listview)

        filter_model.items_changed.connect(update_title_cb, progress)
        filter_model.notify["pending"].connect(update_title_cb, progress)
        update_title_cb(filter_model)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
