"""GTK Demo

GTK Demo is a collection of useful examples to demonstrate
GTK widgets and features. It is a useful example in itself.

You can select examples in the sidebar or search for them by
typing a search term. Double-clicking or hitting the “Run” button
will run the demo. The source code and other resources used in the
demo are shown in this area.

You can also use the GTK Inspector, available from the menu on the
top right, to poke at the running demos, and see how they are put
together.
"""

import ast
import sys
from collections.abc import Callable
from pathlib import Path

from PyLiite4 import Gio, GLib, GObject, Gtk, GtkSource, Pango

from demos import gtk_demo

info_view: Gtk.TextView
source_view: GtkSource.View

current_file: str | None = None

notebook: Gtk.Notebook
selection: Gtk.SingleSelection
toplevel: Gtk.ApplicationWindow
search_bar: Gtk.SearchBar
search_entry: Gtk.SearchEntry
search_needle: list[str] | None = None

DemoFunc = Callable[[Gtk.Widget], Gtk.Widget | None]


class GtkDemo(GObject.Object):
    __gtype_name__ = "GtkDemo"

    def __init__(self, name: str | None, title: str, keywords: list[str] | None, filename: str | None,
                 func: DemoFunc | None) -> None:
        super().__init__()
        self._name = name
        self._title = title
        self._keywords = keywords
        self._filename = filename
        self.func = func
        self.children_model: Gio.ListStore | None = None

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def filename(self) -> str | None:
        return self._filename

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def name(self) -> str | None:
        return self._name

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def title(self) -> str:
        return self._title

    @GObject.Property(type=GObject.TYPE_STRV, flags=GObject.ParamFlags.READABLE)
    def keywords(self) -> list[str] | None:
        return self._keywords

    def run(self, window: Gtk.Widget) -> bool:
        if not self.func:
            return False

        result = self.func(window)
        if result is None:
            return False

        return True


def activate_about(action: Gio.SimpleAction, parameter: GLib.Variant | None, app: Gtk.Application) -> None:
    s = ""

    os_name = GLib.get_os_info("NAME")
    os_version = GLib.get_os_info("VERSION_ID")
    if os_name and os_version:
        s += f"OS\t{os_name} {os_version}\n\n"
    s += "System libraries\n"
    s += f"\tGLib\t{GLib.MAJOR_VERSION}.{GLib.MINOR_VERSION}.{GLib.MICRO_VERSION}\n"
    s += f"\tPango\t{Pango.version_string()}\n"
    s += f"\tGTK \t{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}\n"
    s += "\nA link can appear here: <http://www.gtk.org>"

    version = (f"{PACKAGE_VERSION}\nRunning against GTK "
               f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}")

    logo_file = Gio.File.new_for_uri("resource:///org/gtk/Demo4/icons/scalable/apps/org.gtk.Demo4.svg")
    logo = Gtk.IconPaintable.new_for_file(logo_file, 64, 1)
    show_about_dialog(app.get_active_window(),
                      program_name="GTK Demo",
                      version=version,
                      copyright="© 1997—2024 The GTK Team",
                      license_type=Gtk.License.LGPL_2_1,
                      website="http://www.gtk.org",
                      comments="Program to demonstrate GTK widgets",
                      authors=["The GTK Team"],
                      logo=logo,
                      title="About GTK Demo",
                      system_information=s)


_about_dialogs: dict[Gtk.Window | None, Gtk.AboutDialog] = {}


def show_about_dialog(parent: Gtk.Window | None, **properties: object) -> None:
    # gtk_show_about_dialog() is variadic, so not in the bindings. Like it, reuse one dialog per parent.
    dialog = _about_dialogs.get(parent)
    if dialog is None:
        dialog = Gtk.AboutDialog(hide_on_close=True, **properties)
        if parent is not None:
            dialog.set_modal(True)
            dialog.set_transient_for(parent)
            dialog.set_destroy_with_parent(True)
            parent.destroy.connect(lambda _parent: _about_dialogs.pop(parent, None))
        _about_dialogs[parent] = dialog
    dialog.present()


def activate_quit(action: Gio.SimpleAction, parameter: GLib.Variant | None, app: Gtk.Application) -> None:
    for win in list(app.get_windows()):
        win.destroy()


def activate_inspector(action: Gio.SimpleAction, parameter: GLib.Variant | None, app: Gtk.Application) -> None:
    Gtk.Window.set_interactive_debugging(True)


def activate_run(action: Gio.SimpleAction, parameter: GLib.Variant | None, window: Gtk.Window) -> None:
    row = selection.get_selected_item()
    demo = row.get_item()

    demo.run(window)


def update_style_scheme(buffer: GtkSource.Buffer) -> None:
    # Where C highlights with its own fontify.c, GtkSourceView does it, in Adwaita's light or dark colours.
    settings = Gtk.Settings.get_default()
    dark = (settings.get_property("gtk-interface-color-scheme") == Gtk.InterfaceColorScheme.DARK
            or settings.get_property("gtk-application-prefer-dark-theme"))
    manager = GtkSource.StyleSchemeManager.get_default()
    buffer.set_style_scheme(manager.get_scheme("Adwaita-dark" if dark else "Adwaita"))


def update_style_schemes(settings: Gtk.Settings, pspec: GObject.ParamSpec) -> None:
    for i in range(notebook.get_n_pages()):
        child = notebook.get_nth_page(i)
        if isinstance(child, Gtk.ScrolledWindow):
            child = child.get_child()
        if isinstance(child, GtkSource.View):
            update_style_scheme(child.get_buffer())


def fontify(format: str, buffer: GtkSource.Buffer) -> None:
    buffer.set_language(GtkSource.LanguageManager.get_default().get_language(format))
    buffer.set_highlight_syntax(True)
    update_style_scheme(buffer)


def display_image(format: str | None, resource: str, label: Gtk.Widget) -> Gtk.Widget:
    image = Gtk.Picture.new_for_resource(resource)
    image.set_halign(Gtk.Align.CENTER)
    image.set_valign(Gtk.Align.CENTER)
    sw = Gtk.ScrolledWindow()
    sw.set_child(image)

    image.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])

    return sw


def display_images(format: str | None, resource_dir: str, label: Gtk.Label) -> Gtk.Widget | None:
    try:
        resources = Gio.resources_enumerate_children(resource_dir, Gio.ResourceLookupFlags.NONE)
    except GLib.Error:
        return None

    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    grid = Gtk.FlowBox()
    grid.set_selection_mode(Gtk.SelectionMode.NONE)
    grid.set_valign(Gtk.Align.START)
    sw.set_child(grid)

    for resource in resources:
        resource_name = f"{resource_dir}/{resource}"

        image_label = Gtk.Label(label=resource)
        widget = display_image(None, resource_name, image_label)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.append(widget)
        box.append(image_label)
        grid.insert(box, -1)

    label.set_label("Images")

    grid.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])

    return sw


def display_text(format: str | None, resource: str, label: Gtk.Widget) -> Gtk.Widget:
    data = Gio.resources_lookup_data(resource, Gio.ResourceLookupFlags.NONE).get_data()
    text = data.decode("utf-8")

    textview = GtkSource.View()
    textview.set_left_margin(20)
    textview.set_right_margin(20)
    textview.set_top_margin(20)
    textview.set_bottom_margin(20)
    textview.set_editable(False)
    textview.set_cursor_visible(False)
    # Word wrapping and some space between lines make the text easier to read.
    textview.set_wrap_mode(Gtk.WrapMode.WORD)
    textview.set_pixels_above_lines(2)
    textview.set_pixels_below_lines(2)
    textview.set_monospace(True)

    buffer = GtkSource.Buffer()
    buffer.set_text(text, -1)

    if format:
        fontify(format, buffer)

    textview.set_buffer(buffer)

    textview.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])

    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    sw.set_child(textview)

    return sw


def display_video(format: str | None, resource: str, label: Gtk.Widget) -> Gtk.Widget:
    video = Gtk.Video.new_for_resource(resource)
    video.set_loop(True)

    video.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])

    return video


def display_nothing(resource: str) -> Gtk.Widget:
    widget = Gtk.Label(label=f"The contents of the resource at '{resource}' cannot be displayed")
    widget.set_wrap(True)

    return widget


display_funcs: list[tuple[str, str | None, Callable[[str | None, str, Gtk.Label], Gtk.Widget | None]]] = [
    (".gif", None, display_image),
    (".jpg", None, display_image),
    (".png", None, display_image),
    (".svg", None, display_image),
    (".c", "c", display_text),
    (".css", "css", display_text),
    (".glsl", None, display_text),
    (".h", "c", display_text),
    (".py", "python3", display_text),
    (".txt", None, display_text),
    (".ui", "xml", display_text),
    (".webm", None, display_video),
    ("images/", None, display_images),
]


def add_data_tab(demoname: str) -> None:
    resource_dir = f"/{demoname}"
    try:
        resources = Gio.resources_enumerate_children(resource_dir, Gio.ResourceLookupFlags.NONE)
    except GLib.Error:
        return

    for resource in resources:
        resource_name = f"{resource_dir}/{resource}"

        label = Gtk.Label(label=resource)

        for extension, format, display_func in display_funcs:
            if resource_name.endswith(extension):
                widget = display_func(format, resource_name, label)
                break
        else:
            widget = display_nothing(resource_name)

        notebook.append_page(widget, label)
        notebook.get_page(widget).set_property("tab-expand", False)


def remove_data_tabs() -> None:
    for i in range(notebook.get_n_pages() - 1, 1, -1):
        notebook.remove_page(i)


def lookup_source(filename: str) -> str:
    try:
        return Gio.resources_lookup_data(f"/sources/{filename}", Gio.ResourceLookupFlags.NONE).get_data().decode()
    except GLib.Error:
        # The launcher itself isn't one of the demos, so it isn't in the resource.
        if filename == Path(__file__).name:
            return Path(__file__).read_text()
        raise


def load_file(demoname: str, filename: str) -> None:
    global current_file

    if current_file == filename:
        return

    remove_data_tabs()

    add_data_tab(demoname)

    current_file = filename

    info_buffer = Gtk.TextBuffer()
    info_buffer.create_tag("title", size=18 * 1024, pixels_below_lines=10)

    source_buffer = GtkSource.Buffer()

    info_buffer.begin_irreversible_action()
    source_buffer.begin_irreversible_action()

    try:
        source = lookup_source(filename)
    except GLib.Error as err:
        GLib.log_default_handler("Gtk-Demo", GLib.LogLevelFlags.LEVEL_WARNING,
                                 f"Cannot open source for {filename}: {err.message}")
        return

    # Where C reads the info from the file's header comment, Python has the module's docstring.
    lines = source.splitlines()
    module = ast.parse(source)
    body_start = 0
    docstring = ast.get_docstring(module, clean=True) or ""
    if docstring:
        body_start = module.body[0].end_lineno or 0

    title, _, rest = docstring.partition("\n")
    # Of a title like "Lists/Weather", show only the last part.
    title = title.rsplit("/", 1)[-1].partition("::")[0].strip()

    start = info_buffer.get_start_iter()
    if title:
        info_buffer.insert_with_tags_by_name(start, title, "title")

    in_para = False
    for line in rest.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        if line:
            if in_para:
                info_buffer.insert(start, " ")
            info_buffer.insert(start, line)
            in_para = True
        else:
            info_buffer.insert(start, "\n")
            in_para = False

    # Skip blank lines after the docstring, then read the program body.
    body = lines[body_start:]
    while body and not body[0].strip():
        body.pop(0)
    source_buffer.set_text("\n".join(body))

    fontify("python3", source_buffer)

    source_buffer.end_irreversible_action()
    source_view.set_buffer(source_buffer)

    info_buffer.end_irreversible_action()
    info_view.set_buffer(info_buffer)


def activate_cb(widget: Gtk.ListView, position: int, window: Gtk.Window) -> None:
    model = widget.get_model()
    row = model.get_item(position)
    demo = row.get_item()

    demo.run(window)


def selection_cb(sel: Gtk.SingleSelection, pspec: GObject.ParamSpec | None) -> None:
    row = sel.get_selected_item()

    notebook.set_sensitive(row is not None)

    if row is None:
        toplevel.set_title("No match")

        return

    demo = row.get_item()

    if demo.filename:
        load_file(demo.name, demo.filename)

    action = toplevel.lookup_action("run")
    action.set_enabled(demo.func is not None)

    toplevel.set_title(demo.title)


def filter_demo(demo: GtkDemo) -> bool:
    # A demo shows only if every needle matches its title or one of its keywords.
    for needle in search_needle or []:
        if not demo.title:
            return False

        if GLib.str_match_string(needle, demo.title, True):
            continue

        if demo.keywords and any(needle in keyword for keyword in demo.keywords):
            continue

        return False

    return True


def demo_filter_by_name(row: Gtk.TreeListRow) -> bool:
    # An empty search shows every row.
    if not search_needle or not search_needle[0]:
        return True

    # A row shows if it or any of its parents matches.
    parent = row
    while parent is not None:
        if filter_demo(parent.get_item()):
            return True
        parent = parent.get_parent()

    # It also shows if any of its children matches.
    children = row.get_children()
    if children is not None:
        for demo in children:
            if filter_demo(demo):
                return True

    return False


def demo_search_changed_cb(entry: Gtk.SearchEntry, filter: Gtk.Filter) -> None:
    global search_needle

    text = entry.get_text()

    search_needle = None

    if text:
        search_needle, _alternates = GLib.str_tokenize_and_fold(text, None)

    filter.changed(Gtk.FilterChange.DIFFERENT)


def demo_can_run(window: Gtk.Widget, name: str) -> bool:
    return True


def gtk_demos() -> list[tuple[GtkDemo, list[GtkDemo]]]:
    """The demos as GTK's geninclude.py arranges them: sorted by title, with "Parent/Child" titles under a parent."""
    demos = []
    parents: dict[str, list[GtkDemo]] = {}
    for demo in gtk_demo.all_demos():
        d = GtkDemo(demo.name, demo.title, demo.keywords, demo.filename, demo.run)
        if "/" in demo.title:
            parent_name = demo.title[:demo.title.index("/")]
            if parent_name not in parents:
                parents[parent_name] = []
                demos.append((GtkDemo(None, parent_name, [], None, None), parents[parent_name]))
            d._title = demo.title[demo.title.rindex("/") + 1:]
            parents[parent_name].append(d)
        else:
            demos.append((d, []))
    return sorted(demos, key=lambda entry: entry[0].title)


def create_demo_model(window: Gtk.Widget) -> Gio.ListModel:
    store = Gio.ListStore(item_type=GtkDemo)

    window.realize()

    d = GtkDemo("main", "GTK Demo", None, Path(__file__).name, None)

    store.append(d)

    for d, children in gtk_demos():
        if demo_can_run(window, d.name):
            store.append(d)

        if children:
            d.children_model = Gio.ListStore(item_type=GtkDemo)

            for child in children:
                if demo_can_run(window, child.name):
                    d.children_model.append(child)

    return store


def get_child_model(item: GtkDemo) -> Gio.ListModel | None:
    return item.children_model


def clear_search(bar: Gtk.SearchBar, pspec: GObject.ParamSpec) -> None:
    if not bar.get_search_mode():
        entry = bar.get_child()
        entry.set_text("")


def search_results_update(filter_model: Gtk.FilterListModel, pspec: GObject.ParamSpec, entry: Gtk.Entry) -> None:
    n_items = filter_model.get_n_items()

    if len(entry.get_text()) > 0:
        if n_items > 0:
            text = f"{n_items} search result" if n_items == 1 else f"{n_items} search results"
        else:
            text = "No search results"

        entry.update_property([Gtk.AccessibleProperty.DESCRIPTION], [text])
    else:
        entry.reset_property(Gtk.AccessibleProperty.DESCRIPTION)


def create_source_view(textview: Gtk.TextView) -> GtkSource.View:
    """A GtkSourceView in place of main.ui's source text view, with the same settings."""
    view = GtkSource.View()
    for prop in ("left-margin", "right-margin", "top-margin", "bottom-margin", "editable", "cursor-visible",
                 "monospace", "wrap-mode", "pixels-above-lines", "pixels-below-lines"):
        view.set_property(prop, textview.get_property(prop))
    view.update_property([Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.DESCRIPTION],
                         ["Source", "The source code of the demo"])
    textview.get_parent().set_child(view)
    return view


def create_window(app: Gtk.Application) -> Gtk.Window:
    global notebook, info_view, source_view, toplevel, search_bar, search_entry, selection, current_file

    builder = Gtk.Builder.new_from_resource("/ui/main.ui")

    window = builder.get_object("window")

    app.add_window(window)

    action = Gio.SimpleAction.new("run", None)
    action.activate.connect(activate_run, window)
    window.add_action(action)

    current_file = None
    notebook = builder.get_object("notebook")

    info_view = builder.get_object("info-textview")
    source_view = create_source_view(builder.get_object("source-textview"))
    toplevel = window
    listview = builder.get_object("listview")
    listview.activate.connect(activate_cb, window)
    search_bar = builder.get_object("searchbar")
    search_bar.notify["search-mode-enabled"].connect(clear_search)

    listmodel = create_demo_model(window)
    treemodel = Gtk.TreeListModel.new(listmodel, False, True, get_child_model)
    filter_model = Gtk.FilterListModel(model=treemodel)
    filter = Gtk.CustomFilter.new(demo_filter_by_name)
    filter_model.set_filter(filter)

    search_entry = builder.get_object("search-entry")
    search_entry.search_changed.connect(demo_search_changed_cb, filter)
    filter_model.notify["n-items"].connect(search_results_update, search_entry)

    selection = Gtk.SingleSelection(model=filter_model)
    selection.notify["selected-item"].connect(selection_cb)
    listview.set_model(selection)

    selection_cb(selection, None)

    settings = Gtk.Settings.get_default()
    settings.notify["gtk-interface-color-scheme"].connect(update_style_schemes)
    settings.notify["gtk-application-prefer-dark-theme"].connect(update_style_schemes)

    return window


def activate(app: Gtk.Application) -> None:
    windows = app.get_windows()
    if windows:
        window = windows[0]
    else:
        window = create_window(app)

    window.present()


def auto_quit(app: Gtk.Application) -> bool:
    app.quit()
    return GLib.SOURCE_REMOVE


def list_demos() -> None:
    for d, children in gtk_demos():
        if d.name:
            print(d.name)
        for c in children:
            if c.name:
                print(c.name)


def command_line(app: Gtk.Application, cmdline: Gio.ApplicationCommandLine) -> int:
    options = cmdline.get_options_dict()
    name = options.lookup_value("run", GLib.VariantType.new("s"))
    name = name.get_string() if name is not None else None
    autoquit = options.contains("autoquit")
    list = options.contains("list")
    func = None

    if autoquit:
        GLib.timeout_add_seconds(1, auto_quit, app)

    if not name and not list:
        app.activate()
        return 0

    create_window(app)

    if list:
        list_demos()
        app.quit()
        return 0

    window = app.get_windows()[0]

    for d, children in gtk_demos():
        if d.name == name:
            func = d.func
            break
        found = next((c for c in children if c.name == name), None)
        if found is not None:
            func = found.func
            break
    else:
        cmdline.printerr_literal(f"No example named {name}\n")
        app.quit()
        return 1

    if func:
        demo = func(window)

        if isinstance(demo, Gtk.Window):
            demo.set_transient_for(window)
            window.set_visible(False)

            demo.destroy.connect(lambda _demo: app.quit())

    return 0


PACKAGE_VERSION = f"{Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}"


def main(argv: list[str]) -> int:
    gtk_demo.register_resources()

    app = Gtk.Application(application_id="org.gtk.Demo4",
                          flags=Gio.ApplicationFlags.NON_UNIQUE | Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    app.set_version(PACKAGE_VERSION)

    for name, callback in (("about", activate_about), ("quit", activate_quit), ("inspector", activate_inspector)):
        action = Gio.SimpleAction.new(name, None)
        action.activate.connect(callback, app)
        app.add_action(action)

    for action_and_target, accelerators in (("app.about", ["F1"]), ("app.quit", ["<Control>q"])):
        app.set_accels_for_action(action_and_target, accelerators)

    app.add_main_option("run", 0, GLib.OptionFlags.NONE, GLib.OptionArg.STRING, "Run an example", "EXAMPLE")
    app.add_main_option("list", 0, GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "List examples", None)
    app.add_main_option("autoquit", 0, GLib.OptionFlags.NONE, GLib.OptionArg.NONE, "Quit after a delay", None)

    app.command_line.connect(command_line)
    app.activate.connect(activate)

    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
