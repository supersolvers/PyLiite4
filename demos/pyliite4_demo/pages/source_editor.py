"""GtkSourceView, which the wheel bundles: an editor showing this page's own source, coloured for Python."""

from pathlib import Path
from typing import Any

from PyLiite4 import Adw, Gtk

NAME = "source"
TITLE = "Source Editor"
ICON = "document-edit-symbolic"
SUMMARY = "GtkSourceView, bundled: syntax colouring, line numbers and a style that follows dark mode"


class Page(Gtk.Box):
    def __init__(self, window: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        from PyLiite4 import GtkSource

        GtkSource.init()
        manager = GtkSource.LanguageManager.get_default()
        self.buffer = GtkSource.Buffer(language=manager.get_language("python"))
        self.buffer.set_text(Path(__file__).read_text(), -1)
        self.buffer.place_cursor(self.buffer.get_start_iter())
        self.view = GtkSource.View(buffer=self.buffer, monospace=True, show_line_numbers=True,
                                   highlight_current_line=True, auto_indent=True, indent_width=4,
                                   insert_spaces_instead_of_tabs=True, tab_width=4, top_margin=6, bottom_margin=6)
        source_map = GtkSource.Map(view=self.view)
        editor = Gtk.Box()
        editor.append(Gtk.ScrolledWindow(child=self.view, hexpand=True, vexpand=True))
        editor.append(source_map)
        self.append(editor)

        self.position = Gtk.Label(xalign=0, margin_start=12, margin_end=12, margin_top=6, margin_bottom=6,
                                  css_classes=["dim-label", "caption", "numeric"])
        self.buffer.notify["cursor-position"].connect(lambda buffer, spec: self.show_position())
        self.append(self.position)
        self.show_position()

        style = Adw.StyleManager.get_default()
        style.notify["dark"].connect(lambda manager, spec: self.follow_style())
        self.follow_style()

    def follow_style(self) -> None:
        from PyLiite4 import GtkSource

        schemes = GtkSource.StyleSchemeManager.get_default()
        name = "Adwaita-dark" if Adw.StyleManager.get_default().get_dark() else "Adwaita"
        self.buffer.set_style_scheme(schemes.get_scheme(name) or schemes.get_scheme("classic"))

    def show_position(self) -> None:
        where = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        self.position.set_label(f"Line {where.get_line() + 1}, column {where.get_line_offset() + 1}")


def build(window: Any) -> Gtk.Widget:
    try:
        return Page(window)
    except (ImportError, ValueError):
        # GtkSourceView isn't there: a PyLiite4 on a system GTK without it. Bundled wheels have it.
        return Adw.StatusPage(icon_name=ICON, title="GtkSourceView Isn't Available",
                              description="This PyLiite4 uses a GTK without GtkSourceView 5. The bundled wheels "
                              "include it.")
