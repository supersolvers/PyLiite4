"""A chat window whose replies stream into a RichView, from an asyncio task that a Stop button cancels.

It shows RichView, PyLiite4's view of formatted text: each reply is markup that grows a few words at a time, and
RichView re-renders only its end, so you can select and copy while it streams. The reply comes from an async
generator on GLib's main loop (use_asyncio), standing in for a model or a network stream.

Run it from the repository root:

    python examples/chat/main.py
"""

import asyncio
import html
import re
import sys
from collections.abc import AsyncIterator

from PyLiite4 import Adw, Gio, GLib, Gtk, use_asyncio
from PyLiite4.Extras import RichView

REPLY = """<p>Here is what <b>RichView</b> can show, as a reply streams in:</p>
<ul><li>lists, <i>emphasis</i> and <code>inline code</code></li>
<li>links, such as <a href="https://docs.gtk.org/gtk4/">GTK's documentation</a></li></ul>
<pre>async for piece in reply(question):
    view.set_markup(shown + piece)</pre>
<table><tr><th>You asked</th><th>Length</th></tr><tr><td>{question}</td><td>{length} characters</td></tr></table>
<p>Select some text while it streams: the selection stays.</p>"""


async def reply(question: str) -> AsyncIterator[str]:
    """The reply to ``question``, a few pieces at a time, as a model's would arrive."""
    text = REPLY.format(question=html.escape(question), length=len(question))
    for piece in re.findall(r"<[^>]+>|[^<\s]+\s*|\s+", text):
        await asyncio.sleep(0.02)
        yield piece


class Window(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application) -> None:
        super().__init__(application=application, title="Chat", default_width=640, default_height=640)
        self.messages: list[str] = []
        self.task: asyncio.Task[None] | None = None

        self.view = RichView(left_margin=12, right_margin=12, top_margin=12, bottom_margin=12, vexpand=True)
        self.view.activate_link.connect(self.on_activate_link)
        scroller = Gtk.ScrolledWindow(child=self.view, hscrollbar_policy=Gtk.PolicyType.NEVER)

        self.entry = Gtk.Entry(placeholder_text="Ask something", hexpand=True)
        self.entry.activate.connect(lambda entry: self.send())
        self.send_button = Gtk.Button(label="Send", css_classes=["suggested-action"])
        self.send_button.clicked.connect(lambda button: self.send())
        self.stop_button = Gtk.Button(label="Stop", visible=False)
        self.stop_button.clicked.connect(lambda button: self.stop())
        bar = Gtk.Box(spacing=6, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        for widget in (self.entry, self.send_button, self.stop_button):
            bar.append(widget)

        self.toasts = Adw.ToastOverlay(child=scroller)
        view = Adw.ToolbarView(content=self.toasts)
        view.add_top_bar(Adw.HeaderBar())
        view.add_bottom_bar(bar)
        self.set_content(view)
        self.entry.grab_focus()

    def render(self, extra: str = "") -> None:
        self.view.set_markup("".join(self.messages) + extra)

    def send(self) -> None:
        question = self.entry.get_text().strip()
        if not question or self.task is not None:
            return
        self.entry.set_text("")
        self.messages.append(f'<p><b>You:</b> {html.escape(question)}</p>')
        self.render()
        application = self.get_application()
        assert application is not None
        self.task = application.create_asyncio_task(self.stream(question))

    async def stream(self, question: str) -> None:
        self.send_button.set_visible(False)
        self.stop_button.set_visible(True)
        shown = ""
        try:
            async for piece in reply(question):
                shown += piece
                self.render(f"<blockquote>{shown}</blockquote>")
        except asyncio.CancelledError:
            shown += " <i>(stopped)</i>"
            raise
        finally:
            self.messages.append(f"<blockquote>{shown}</blockquote>")
            self.render()
            self.task = None
            self.send_button.set_visible(True)
            self.stop_button.set_visible(False)

    def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()

    def on_activate_link(self, view: RichView, uri: str) -> bool:
        self.toasts.add_toast(Adw.Toast(title=f"Opening {GLib.markup_escape_text(uri)}"))
        # False lets RichView open it, with Gtk.UriLauncher.
        return False


def on_activate(app: Gio.Application) -> None:
    assert isinstance(app, Adw.Application)
    (app.get_active_window() or Window(app)).present()


if __name__ == "__main__":
    # Set this up before run(): the streaming replies need GLib's main loop to run their coroutines.
    use_asyncio()
    application = Adw.Application(application_id="org.example.PyLiite4Chat")
    application.activate.connect(on_activate)
    sys.exit(application.run(sys.argv))
