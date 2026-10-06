"""Testing a GTK application with PyLiite4.testing, the pytest plugin installed with PyLiite4.

notes.py is a small notes window; tests/test_notes.py tests it the way a person uses it, with real clicks and
typing (``gtkbot.input``), waits (``gtkbot.wait_until``) and widget lookups (``gtkbot.find``). pyproject.toml turns
the plugin on with ``gtk = true``, so each run gets a private display and D-Bus session, and a test fails if GTK logs
a warning or one of its callbacks raises. It's the equivalent of QTest with pytest-qt.

Run the application, then its tests, from the repository root:

    python examples/testing/main.py

    python -m pytest examples/testing
"""

import sys

from notes import NotesWindow

from PyLiite4 import Adw, Gio


def on_activate(app: Gio.Application) -> None:
    assert isinstance(app, Adw.Application)
    (app.get_active_window() or NotesWindow(app)).present()


if __name__ == "__main__":
    application = Adw.Application(application_id="org.example.PyLiite4Notes")
    application.activate.connect(on_activate)
    sys.exit(application.run(sys.argv))
