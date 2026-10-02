"""Translating an application with gettext, in Python code and in .ui files.

Strings are marked for translation in Python with _() and ngettext(), and in window.ui with translatable="yes".
xgettext extracts them all into po/pyliite4-translations.pot. Each language has a .po file with the translations,
here only po/de.po for German, compiled to locale/de/LC_MESSAGES/pyliite4-translations.mo. ./update-translations.sh
redoes all three steps; it needs GNU gettext.

Two gettext implementations read the catalogue: Python's gettext module for the strings in this file, and the C
library's, which GtkBuilder uses for window.ui. Each needs bindtextdomain() and textdomain(), below.

Run it in German from the repository root:

    LANGUAGE=de python examples/translations/main.py

LANGUAGE chooses the language. The C library ignores it in the C or POSIX locale, so if LANG is unset or C, also
set it to any UTF-8 locale that `locale -a` lists, such as LANG=en_US.UTF-8.
"""

import gettext
import locale
import sys
from pathlib import Path

DOMAIN = "pyliite4-translations"
# An installed application would use $prefix/share/locale.
LOCALE_DIR = Path(__file__).resolve().parent / "locale"

# Set the locale, and bind the domain, before GTK builds any interface.
try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass  # an unknown locale in the environment: carry on untranslated
locale.bindtextdomain(DOMAIN, LOCALE_DIR)  # for GtkBuilder
locale.textdomain(DOMAIN)
gettext.bindtextdomain(DOMAIN, LOCALE_DIR)  # for _() below
gettext.textdomain(DOMAIN)
_ = gettext.gettext
ngettext = gettext.ngettext

from window_ui import WindowObjects  # noqa: E402

from PyLiite4 import Gio, Gtk  # noqa: E402


def on_activate(app: Gio.Application) -> None:
    assert isinstance(app, Gtk.Application)
    ui = WindowObjects()
    greetings = 0

    def on_greet(button: Gtk.Button) -> None:
        nonlocal greetings
        greetings += 1
        # ngettext picks the plural form for the language: some have one form, others three or more.
        count = ngettext("You greeted {count} time", "You greeted {count} times", greetings).format(count=greetings)
        # Keep _() out of f-strings: xgettext doesn't look inside them.
        hello = _("Hello, world!")
        ui.greeting.set_label(f"{hello} {count}")

    ui.greet_button.clicked.connect(on_greet)
    # Translators: the window's title
    Gtk.ApplicationWindow(application=app, title=_("Translations"), child=ui.content).present()


if __name__ == "__main__":
    application = Gtk.Application(application_id="org.example.PyLiite4Translations")
    application.activate.connect(on_activate)
    sys.exit(application.run(sys.argv))
