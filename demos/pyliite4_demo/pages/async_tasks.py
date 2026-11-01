"""asyncio on GLib's main loop: awaited libsoup requests to a loopback server, cancelling, and work in a thread."""

import asyncio
import json
import time
from typing import Any

from PyLiite4 import Adw, Gio, GLib, Gtk, Soup

from ._layout import intro, scrolled_page

NAME = "async"
TITLE = "Async and Network"
ICON = "network-server-symbolic"
SUMMARY = "Coroutines on GLib's main loop: awaited libsoup requests, cancelling, asyncio.to_thread"


def count_primes(limit: int) -> int:
    """Blocking work, for a thread."""
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\0\0"
    for number in range(2, int(limit ** 0.5) + 1):
        if sieve[number]:
            sieve[number * number::number] = bytes(len(range(number * number, limit + 1, number)))
    return sum(sieve)


class Server:
    """A libsoup server on a loopback port: /now answers at once, /slow after ``slow_ms``, a second and a half."""

    def __init__(self) -> None:
        self.slow_ms = 1500
        self.server = Soup.Server()
        self.server.add_handler("/now", self.now)
        self.server.add_handler("/slow", self.slow)
        self.server.listen_local(0, Soup.ServerListenOptions.IPV4_ONLY)
        self.base = self.server.get_uris()[0].to_string().rstrip("/")

    def now(self, server: Soup.Server, message: Soup.ServerMessage, path: str, query: Any, *rest: Any) -> None:
        body = json.dumps({"time": time.strftime("%H:%M:%S"), "path": path}).encode()
        message.set_status(200, None)
        message.set_response("application/json", Soup.MemoryUse.COPY, body)

    def slow(self, server: Soup.Server, message: Soup.ServerMessage, path: str, query: Any, *rest: Any) -> None:
        message.pause()

        def answer() -> bool:
            self.now(server, message, path, query)
            message.unpause()
            return GLib.SOURCE_REMOVE
        GLib.timeout_add(self.slow_ms, answer)


class Page(Gtk.Box):
    def __init__(self, window: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.window = window
        self.append(intro("Async and Network", "With use_asyncio() before app.run(), coroutines run on GLib's main "
                          "loop: Gio's and libsoup's async methods are awaited by leaving out the callback, tasks are "
                          "cancelled as usual, and asyncio.to_thread moves blocking work off the loop. The requests "
                          "here go to a libsoup server on a loopback port, so they work offline."))
        self.server = Server()
        self.session = Soup.Session()
        self.task: asyncio.Task[Any] | None = None

        group = Adw.PreferencesGroup(title="Requests")
        self.fetch_button = Gtk.Button(label="Fetch", valign=Gtk.Align.CENTER)
        self.fetch_button.clicked.connect(lambda button: self.start(self.fetch("/now")))
        row = Adw.ActionRow(title="Quick request", subtitle=f"{self.server.base}/now")
        row.add_suffix(self.fetch_button)
        group.add(row)
        self.slow_button = Gtk.Button(label="Fetch", valign=Gtk.Align.CENTER)
        self.slow_button.clicked.connect(lambda button: self.start(self.fetch("/slow")))
        self.cancel_button = Gtk.Button(label="Cancel", valign=Gtk.Align.CENTER, sensitive=False)
        self.cancel_button.clicked.connect(lambda button: self.cancel())
        row = Adw.ActionRow(title="Slow request", subtitle="Answers after 1.5 s: cancel it meanwhile")
        row.add_suffix(self.slow_button)
        row.add_suffix(self.cancel_button)
        group.add(row)
        self.thread_button = Gtk.Button(label="Compute", valign=Gtk.Align.CENTER)
        self.thread_button.clicked.connect(lambda button: self.start(self.compute()))
        row = Adw.ActionRow(title="Work in a thread", subtitle="Counts the primes below five million with "
                            "asyncio.to_thread; the window stays responsive")
        row.add_suffix(self.thread_button)
        group.add(row)
        self.append(group)

        status = Gtk.Box(spacing=12)
        self.spinner = Adw.Spinner(visible=False)
        status.append(self.spinner)
        self.status = Gtk.Label(label="Nothing running", xalign=0, wrap=True, selectable=True)
        status.append(self.status)
        self.append(status)

    def start(self, coroutine: Any) -> None:
        if self.task is not None and not self.task.done():
            self.task.cancel()
        application = self.window.get_application()
        self.task = application.create_asyncio_task(self.run(coroutine))

    async def run(self, coroutine: Any) -> None:
        self.busy(True)
        try:
            self.status.set_label(await coroutine)
        except asyncio.CancelledError:
            self.status.set_label("Cancelled")
        except GLib.Error as error:
            self.status.set_label(f"Failed: {error.message}")
        finally:
            self.busy(False)

    def busy(self, busy: bool) -> None:
        self.spinner.set_visible(busy)
        self.cancel_button.set_sensitive(busy)
        for button in (self.fetch_button, self.slow_button, self.thread_button):
            button.set_sensitive(not busy)

    async def fetch(self, path: str) -> str:
        cancellable = Gio.Cancellable()
        message = Soup.Message.new("GET", self.server.base + path)
        try:
            data = await self.session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, cancellable)
        except asyncio.CancelledError:
            # Stop libsoup's request too, not just the coroutine.
            cancellable.cancel()
            raise
        answer = json.loads(bytes(data.get_data() or b""))
        return f"{message.get_status()} from {answer['path']}: the server's time is {answer['time']}"

    async def compute(self) -> str:
        started = time.monotonic()
        primes = await asyncio.to_thread(count_primes, 5_000_000)
        return f"{primes:,} primes below five million, in {time.monotonic() - started:.2f} s on a thread"

    def cancel(self) -> None:
        if self.task is not None and not self.task.done():
            self.task.cancel()


def build(window: Any) -> Gtk.Widget:
    return scrolled_page(Page(window))
