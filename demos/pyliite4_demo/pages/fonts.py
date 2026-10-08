"""Fonts the application ships, made usable with register_font(): here, any font file you open."""

from typing import Any

from PyLiite4 import Adw, Gio, GLib, Gtk
from PyLiite4.Extras import register_font

from ._layout import intro, scrolled_page

NAME = "fonts"
TITLE = "Fonts"
ICON = "format-text-bold-symbolic"
SUMMARY = "register_font() makes a font from a file, a GResource or memory usable, without installing it"

SAMPLE = "The quick brown fox jumps over the lazy dog 0123456789"


class Page(Gtk.Box):
    def __init__(self, window: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.window = window
        self.append(intro("Fonts the Application Ships", "register_font() is the equivalent of "
                          "QFontDatabase.addApplicationFont: it takes a font's bytes, a path, or a Gio.File (a "
                          "resource:/// URI for a font in a GResource), and returns its families, which CSS and Pango "
                          "then find. Nothing is installed. Open any font file to try it."))

        open_button = Gtk.Button(label="Open Font File…", halign=Gtk.Align.START, css_classes=["suggested-action"])
        open_button.clicked.connect(lambda button: self.choose())
        self.append(open_button)

        self.sample = Gtk.Entry(text=SAMPLE)
        self.sample.changed.connect(lambda entry: self.refresh())
        self.append(self.sample)

        self.group = Adw.PreferencesGroup(title="Registered Families",
                                          description="Each row shows the sample in its family")
        self.empty = Adw.ActionRow(title="No fonts registered yet", css_classes=["dim-label"])
        self.group.add(self.empty)
        self.append(self.group)
        self.rows: dict[str, Adw.ActionRow] = {}

    def choose(self) -> None:
        fonts = Gtk.FileFilter(name="Fonts")
        for suffix in ("ttf", "otf", "ttc", "otc", "woff", "woff2"):
            fonts.add_suffix(suffix)
        filters = Gio.ListStore(item_type=Gtk.FileFilter)
        filters.append(fonts)
        dialog = Gtk.FileDialog(title="Open a Font", filters=filters, default_filter=fonts)
        dialog.open(self.window, None, self.on_chosen)

    def on_chosen(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return
        if file is not None:
            self.load(file)

    def load(self, source: bytes | Gio.File | str) -> list[str]:
        """Register the font at ``source`` and list its families. Returns them."""
        try:
            families = register_font(source)
        except (ValueError, FileNotFoundError) as error:
            self.window.toast(str(error))
            return []
        self.empty.set_visible(False)
        for family in families:
            if family not in self.rows:
                self.rows[family] = Adw.ActionRow(title=GLib.markup_escape_text(family))
                self.group.add(self.rows[family])
        self.refresh()
        self.window.toast(f"Registered {', '.join(families)}")
        return families

    def refresh(self) -> None:
        text = GLib.markup_escape_text(self.sample.get_text() or SAMPLE)
        for family, row in self.rows.items():
            row.set_subtitle(f'<span font_family="{GLib.markup_escape_text(family)}" size="x-large">{text}</span>')


def build(window: Any) -> Gtk.Widget:
    return scrolled_page(Page(window))
