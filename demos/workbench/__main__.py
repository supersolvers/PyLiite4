"""Workbench's Library: browse the ported demos, run them and read their code.

Modelled on Workbench's own Library window (src/Library/ in Workbench): a search entry and a category filter over a
boxed list of demos with their descriptions. Activating a row runs the demo in a process of its own, as Workbench does, so
it starts clean every time; its button shows main.py, main.ui and main.css. Demos needing a namespace PyLiite4 doesn't provide are listed, but can't be activated.
"""

import sys
import traceback
from pathlib import Path

from PyLiite4 import Adw, Gio, GLib, GObject, Gtk, GtkSource

from demos.workbench import CATEGORIES, Demo, demos, run

ALL_CATEGORIES = "Any Category"
SOURCES = [("main.py", "Code", "python3"), ("main.ui", "UI", "xml"), ("main.css", "Style", "css")]


class EntryRow(Adw.ActionRow):
    """A demo in the list: its name and description, and a button to view its source."""

    __gtype_name__ = "WorkbenchEntryRow"

    triggered = GObject.Signal()
    source_requested = GObject.Signal()

    def __init__(self, demo: Demo) -> None:
        super().__init__(activatable=True, title=GLib.markup_escape_text(demo.name),
                         subtitle=GLib.markup_escape_text(demo.description))
        self.demo = demo
        self.category = CATEGORIES.get(demo.category, demo.category)

        source_button = Gtk.Button(icon_name="text-x-generic-symbolic", valign=Gtk.Align.CENTER,
                                   tooltip_text="View Source", css_classes=["flat"])
        source_button.clicked.connect(lambda _button: self.source_requested.emit())
        self.add_suffix(source_button)
        self.add_suffix(Gtk.Image(icon_name="go-next-symbolic", margin_start=6))
        self.activated.connect(lambda _row: self.triggered.emit())

        if demo.missing:
            self.set_sensitive(False)
            self.set_tooltip_text(f"Needs {', '.join(demo.missing)}, which PyLiite4 doesn't provide")

    def matches(self, category: str, search_term: str) -> bool:
        category_match = category == ALL_CATEGORIES or self.category == category
        search_match = (search_term == "" or search_term in self.demo.name.lower()
                        or search_term in self.demo.description.lower() or search_term in self.category.lower())
        return category_match and search_match


class SourceDialog(Adw.Dialog):
    """A demo's main.py, main.ui and main.css, each in a read-only source view."""

    __gtype_name__ = "WorkbenchSourceDialog"

    def __init__(self, demo: Demo) -> None:
        super().__init__(title=demo.name, content_width=760, content_height=640)
        stack = Adw.ViewStack()
        language_manager = GtkSource.LanguageManager.get_default()
        self.buffers: list[GtkSource.Buffer] = []
        for filename, title, language_id in SOURCES:
            path = demo.folder / filename
            if not path.exists():
                continue
            buffer = GtkSource.Buffer(language=language_manager.get_language(language_id), highlight_syntax=True)
            buffer.set_text(path.read_text())
            buffer.place_cursor(buffer.get_start_iter())
            self.buffers.append(buffer)
            view = GtkSource.View(buffer=buffer, editable=False, monospace=True, show_line_numbers=True,
                                  top_margin=6, bottom_margin=6, left_margin=6, right_margin=6)
            page = stack.add_titled(Gtk.ScrolledWindow(child=view, vexpand=True), filename, title)
            page.set_icon_name({"main.py": "text-x-script-symbolic", "main.ui": "text-x-generic-symbolic",
                                "main.css": "text-css-symbolic"}.get(filename))

        header_bar = Adw.HeaderBar(title_widget=Adw.ViewSwitcher(stack=stack, policy=Adw.ViewSwitcherPolicy.WIDE))
        toolbar_view = Adw.ToolbarView(content=stack)
        toolbar_view.add_top_bar(header_bar)
        self.set_child(toolbar_view)

        style_manager = Adw.StyleManager.get_default()
        style_manager.notify["dark"].connect(self.update_scheme)
        self.update_scheme(style_manager)

    def update_scheme(self, style_manager: Adw.StyleManager, *_args: object) -> None:
        scheme = GtkSource.StyleSchemeManager.get_default().get_scheme(
            "Adwaita-dark" if style_manager.get_dark() else "Adwaita")
        for buffer in self.buffers:
            buffer.set_style_scheme(scheme)


class Library(Adw.ApplicationWindow):
    """The library window: Workbench's Library.blp, built in code."""

    __gtype_name__ = "WorkbenchLibrary"

    def __init__(self, application: Adw.Application) -> None:
        super().__init__(application=application, title="Workbench — Library", default_width=700,
                         default_height=700)
        self.toast_overlay = Adw.ToastOverlay()

        header_bar = Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Workbench — Library"))
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        heading.append(Gtk.Image(icon_name="view-grid-symbolic", pixel_size=128, margin_top=24, margin_bottom=32,
                                 css_classes=["dim-label"]))
        heading.append(Gtk.Label(label="Learn, Test, Remix", css_classes=["title-1"]))

        filters = Gtk.Box(spacing=6)
        self.search_entry = Gtk.SearchEntry(search_delay=100, placeholder_text="Search demos", hexpand=True,
                                            margin_top=32)
        self.dropdown_category = Gtk.DropDown(
            valign=Gtk.Align.END, model=Gtk.StringList(strings=[ALL_CATEGORIES, *CATEGORIES.values()]))
        filters.append(self.search_entry)
        filters.append(self.dropdown_category)
        heading.append(filters)
        box.append(heading)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.rows: list[EntryRow] = []
        for demo in demos():
            row = EntryRow(demo)
            row.triggered.connect(self.open_demo)
            row.source_requested.connect(self.show_source)
            self.listbox.append(row)
            self.rows.append(row)
        box.append(self.listbox)

        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, margin_top=12,
                         margin_bottom=24)
        self.results_empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, visible=False, margin_top=46,
                                     margin_bottom=70, spacing=6)
        self.results_empty.append(Gtk.Label(label="No results", css_classes=["title-3"]))
        button_reset = Gtk.Button(label="Reset filters", halign=Gtk.Align.CENTER, css_classes=["pill"])
        button_reset.clicked.connect(self.reset)
        self.results_empty.append(button_reset)
        footer.append(self.results_empty)
        footer.append(Gtk.Label(
            label="All examples are dedicated to the public domain\nand <b>can be used freely</b> under the terms "
                  "of <a href=\"https://creativecommons.org/publicdomain/zero/1.0/\">CC0 1.0</a>",
            use_markup=True, justify=Gtk.Justification.CENTER, css_classes=["caption"]))
        box.append(footer)

        self.scrolled_window = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            child=Adw.Clamp(maximum_size=576, margin_start=12, margin_end=12, child=box))
        toolbar_view.set_content(self.scrolled_window)
        self.toast_overlay.set_child(toolbar_view)
        self.set_content(self.toast_overlay)

        self.search_entry.set_key_capture_widget(self)
        self.search_entry.search_changed.connect(self.update_list)
        self.dropdown_category.notify["selected"].connect(self.update_list)

    def update_list(self, *_args: object) -> None:
        selected = self.dropdown_category.get_selected_item()
        category = selected.get_string() if isinstance(selected, Gtk.StringObject) else ALL_CATEGORIES
        search_term = self.search_entry.get_text().lower()
        results_found = False
        for row in self.rows:
            is_match = row.matches(category, search_term)
            row.set_visible(is_match)
            results_found = results_found or is_match
        self.results_empty.set_visible(not results_found)

    def reset(self, *_args: object) -> None:
        self.scrolled_window.get_vadjustment().set_value(0)
        self.search_entry.set_text("")
        self.dropdown_category.set_selected(0)

    def open_demo(self, row: EntryRow) -> None:
        launcher = Gio.SubprocessLauncher(flags=Gio.SubprocessFlags.STDERR_PIPE)
        launcher.set_cwd(str(Path(__file__).resolve().parent.parent.parent))
        process = launcher.spawnv([sys.executable, "-m", "demos.workbench", "--run", row.demo.name])
        process.communicate_utf8_async(None, None, self.demo_finished, row.demo)

    def demo_finished(self, process: Gio.Subprocess, result: Gio.AsyncResult, demo: Demo) -> None:
        _ok, _stdout, stderr = process.communicate_utf8_finish(result)
        sys.stderr.write(stderr or "")
        if not process.get_successful():
            last = next((line for line in reversed((stderr or "").splitlines()) if line.strip()), "it crashed")
            title = GLib.markup_escape_text(f"{demo.name} failed: {last}")
            self.toast_overlay.add_toast(Adw.Toast(title=title, timeout=5))

    def show_source(self, row: EntryRow) -> None:
        SourceDialog(row.demo).present(self)


def activate(application: Adw.Application) -> None:
    library = next((window for window in application.get_windows() if isinstance(window, Library)), None)
    (library or Library(application)).present()


def run_one(application: Adw.Application, name: str, failures: list[str]) -> None:
    """For --run: show one demo, and exit when its window closes."""
    demo = next((demo for demo in demos() if demo.name == name), None)
    try:
        if demo is None:
            raise LookupError(f"No demo named {name}")
        run(demo, application)
    except Exception:
        failures.append(traceback.format_exc())
        sys.stderr.write(failures[-1])


def main() -> int:
    application = Adw.Application(application_id="org.example.PyLiite4.Workbench",
                                  flags=Gio.ApplicationFlags.NON_UNIQUE)
    if len(sys.argv) == 3 and sys.argv[1] == "--run":
        failures: list[str] = []
        application.activate.connect(run_one, sys.argv[2], failures)
        status = application.run(sys.argv[:1])
        return 1 if failures else status
    application.activate.connect(activate)
    return application.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
