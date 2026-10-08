"""Formatted text with RichView: a reply streamed in a few words at a time, with links, a table and code."""

import re
from typing import Any

from PyLiite4 import GLib, Gtk
from PyLiite4.Extras import RichView

NAME = "rich-text"
TITLE = "Formatted Text"
ICON = "format-justify-left-symbolic"
SUMMARY = "RichView shows HTML-subset markup, and keeps the selection while text streams in"

REPLY = """<h3>Rich text from markup</h3>
<p>RichView shows <b>formatted text</b> from an HTML subset, roughly Qt's rich text, with Pango markup's tags too:
<i>italic</i>, <s>struck</s>, <code>inline code</code> and <span style="color:#c01c28">colour</span>. Links such as
<a href="https://docs.gtk.org/gtk4/">GTK's documentation</a> emit <code>activate-link</code> when clicked.</p>
<ul><li>Each call to <code>set_markup()</code> re-renders only from the first block that changed.</li>
<li>So a reply arriving a few words at a time keeps your selection: select some text while it streams.</li></ul>
<blockquote><p>Unknown tags show as text, and <code>&lt;script&gt;</code> is dropped with its content.</p></blockquote>
<pre>view = RichView()
view.set_markup("&lt;p&gt;Hello, &lt;b&gt;world&lt;/b&gt;&lt;/p&gt;")</pre>
<table><tr><th>Qt</th><th>PyLiite4</th></tr>
<tr><td>QTextBrowser.setHtml</td><td>RichView.set_markup</td></tr>
<tr><td>anchorClicked</td><td>activate-link</td></tr>
<tr><td>highlighted</td><td>hover-link</td></tr></table>
<hr><p>Copying gives tables as tab-separated text.</p>"""

# Tags whole, words with their trailing space, and runs of space: the pieces a reply streams in.
_PIECES = re.compile(r"<[^>]+>|[^<\s]+\s*|\s+")


class Page(Gtk.Box):
    def __init__(self, window: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=18, margin_start=18,
                         margin_end=18)
        self.window = window
        self.pieces = _PIECES.findall(REPLY)
        self.shown = 0
        self.timer = 0

        buttons = Gtk.Box(spacing=6)
        self.stream_button = Gtk.Button(label="Stream the Reply", css_classes=["suggested-action"])
        self.stream_button.clicked.connect(lambda button: self.stream())
        buttons.append(self.stream_button)
        show_all = Gtk.Button(label="Show All")
        show_all.clicked.connect(lambda button: self.show_all())
        buttons.append(show_all)
        self.hovered = Gtk.Label(xalign=1, hexpand=True, ellipsize=3, css_classes=["dim-label", "caption"])
        buttons.append(self.hovered)
        self.append(buttons)

        self.view = RichView(left_margin=6, right_margin=6, top_margin=6, bottom_margin=18)
        self.view.hover_link.connect(lambda view, uri: self.hovered.set_label(uri or ""))
        self.view.activate_link.connect(self.on_activate_link)
        self.append(Gtk.ScrolledWindow(child=self.view, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.show_all()

    def stream(self) -> None:
        """Show the reply again from nothing, a few pieces every 40 ms, as a model's reply arrives."""
        if self.timer:
            GLib.Source.remove(self.timer)
        self.shown = 0
        self.view.set_markup("")
        self.stream_button.set_sensitive(False)
        self.timer = GLib.timeout_add(40, self.tick)

    def tick(self) -> bool:
        self.shown = min(len(self.pieces), self.shown + 3)
        self.view.set_markup("".join(self.pieces[:self.shown]))
        if self.shown < len(self.pieces):
            return GLib.SOURCE_CONTINUE
        self.timer = 0
        self.stream_button.set_sensitive(True)
        return GLib.SOURCE_REMOVE

    def show_all(self) -> None:
        if self.timer:
            GLib.Source.remove(self.timer)
            self.timer = 0
        self.shown = len(self.pieces)
        self.view.set_markup(REPLY)
        self.stream_button.set_sensitive(True)

    def on_activate_link(self, view: RichView, uri: str) -> bool:
        # Returning False lets RichView open the link; the toast just says so.
        self.window.toast(f"Opening {uri}")
        return False


def build(window: Any) -> Gtk.Widget:
    return Page(window)
