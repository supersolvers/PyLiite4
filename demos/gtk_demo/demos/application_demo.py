"""Application Class

Demonstrates a simple application.

This example uses GtkApplication, GtkApplicationWindow, GtkBuilder
as well as GMenu and GResource. Due to the way GtkApplication is structured,
it is run as a separate process.
"""

import sys
from pathlib import Path

from PyLiite4 import Gio, GLib, Gtk

name_seen = False
placeholder: Gtk.Widget | None = None
watch = 0


def on_name_appeared(connection: Gio.DBusConnection, name: str, name_owner: str) -> None:
    global name_seen
    name_seen = True


def on_name_vanished(connection: Gio.DBusConnection, name: str) -> None:
    global placeholder
    if not name_seen:
        return

    placeholder = None


def do(toplevel: Gtk.Widget) -> Gtk.Widget:
    global watch, placeholder

    if watch == 0:
        watch = Gio.bus_watch_name(Gio.BusType.SESSION,
                                   "org.gtk.Demo4.App",
                                   Gio.BusNameWatcherFlags.NONE,
                                   on_name_appeared,
                                   on_name_vanished)

    if placeholder is None:
        # The C demo runs ./gtk4-demo-application or the installed one; its port is a module of this package,
        # run with the same Python from the folder holding the demos package.
        command = [sys.executable, "-m", "demos.gtk_demo.demos.application"]
        try:
            GLib.spawn_async(command, working_directory=str(Path(__file__).resolve().parents[3]))
        except GLib.Error as error:
            GLib.log_default_handler("Gtk", GLib.LogLevelFlags.LEVEL_WARNING, error.message)

        placeholder = Gtk.Label(label="")
    else:
        Gio.bus_get_sync(Gio.BusType.SESSION, None).call_sync(
            "org.gtk.Demo4.App",
            "/org/gtk/Demo4/App",
            "org.gtk.Actions",
            "Activate",
            GLib.Variant("(sava{sv})", ("quit", [], {})),
            None,
            Gio.DBusCallFlags.NONE,
            GLib.MAXINT32,
            None)

    return placeholder
