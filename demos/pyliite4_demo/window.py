"""The demo's window, built from window.ui by the template that pyliite4-ui generated in window_ui.py."""

from PyLiite4 import Adw, Gtk

from .pages import PAGES
from .window_ui import PyLiite4DemoWindowChildren, template


@template
class Window(PyLiite4DemoWindowChildren, Adw.ApplicationWindow):
    __gtype_name__ = "PyLiite4DemoWindow"

    def __init__(self, application: Adw.Application) -> None:
        super().__init__(application=application)
        self.titles: dict[str, str] = {}
        for page in PAGES:
            row = Gtk.ListBoxRow(name=page.NAME)
            box = Gtk.Box(spacing=12, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
            box.append(Gtk.Image(icon_name=page.ICON))
            box.append(Gtk.Label(label=page.TITLE, xalign=0, hexpand=True))
            row.set_child(box)
            row.set_tooltip_text(page.SUMMARY)
            self.sidebar.append(row)
            self.stack.add_named(page.build(self), page.NAME)
            self.titles[page.NAME] = page.TITLE
        self.show_page(PAGES[0].NAME)

    def page_names(self) -> list[str]:
        return list(self.titles)

    def show_page(self, name: str) -> None:
        """Show the page named ``name`` and select its row."""
        self.stack.set_visible_child_name(name)
        self.content_page.set_title(self.titles[name])
        row = self.sidebar.get_first_child()
        while row is not None:
            if isinstance(row, Gtk.ListBoxRow) and row.get_name() == name:
                self.sidebar.select_row(row)
            row = row.get_next_sibling()
        self.split_view.set_show_content(True)

    def toast(self, text: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=text, timeout=3))

    def on_sidebar_row_activated(self, sidebar: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        self.show_page(row.get_name())
