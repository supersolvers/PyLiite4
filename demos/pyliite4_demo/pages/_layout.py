"""The layout the pages share: a heading, a few lines saying what the page shows, then its content."""

from PyLiite4 import Adw, Gtk


def intro(title: str, text: str) -> Gtk.Box:
    """A heading and a paragraph saying what the page shows."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    box.append(Gtk.Label(label=title, xalign=0, css_classes=["title-2"]))
    box.append(Gtk.Label(label=text, xalign=0, wrap=True, css_classes=["dim-label"]))
    return box


def scrolled_page(page: Gtk.Box) -> Gtk.ScrolledWindow:
    """``page``, clamped to a readable width and scrolled."""
    page.set_margin_top(24)
    page.set_margin_bottom(24)
    page.set_margin_start(12)
    page.set_margin_end(12)
    return Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                              child=Adw.Clamp(maximum_size=760, child=page))
