"""PyLiite4 Demo: a tour of what PyLiite4 adds to GTK, one page each.

The other collections in demos/ are ports of GTK's and libadwaita's own demos. This one shows PyLiite4 itself: the
widgets of ``PyLiite4.Extras`` (formatted text, tips shown on demand, a shortcut recorder, fonts the application
ships), PyLiite4's signals and properties, asyncio on GLib's main loop, and libraries the wheel bundles, such as
GtkSourceView and libsoup. The window is a .ui template, typed with pyliite4-ui; tests/test_pyliite4_demo.py drives
every page with PyLiite4.testing.

Run it from the repository root:

    python -m demos.pyliite4_demo
"""

import sys

from PyLiite4 import Adw, Gio, use_asyncio

from .window import Window

__all__ = ["main", "open_window", "page_names", "show_page"]


def open_window(app: Adw.Application) -> Window:
    """Open the demo's window for ``app`` and return it."""
    window = Window(app)
    window.present()
    return window


def page_names(window: Window) -> list[str]:
    return window.page_names()


def show_page(window: Window, name: str) -> None:
    window.show_page(name)


def main(argv: list[str]) -> int:
    # Before run(), so the pages' coroutines run on GLib's main loop.
    use_asyncio()
    app = Adw.Application(application_id="org.pyliite4.Demo", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
    app.activate.connect(lambda app: (app.get_active_window() or open_window(app)).present())
    return int(app.run(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
