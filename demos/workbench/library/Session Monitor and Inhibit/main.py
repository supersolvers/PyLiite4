import sys

from PyLiite4 import Adw, Gio, GLib, Gtk, Xdp, XdpGtk4

from demos.workbench import workbench

portal = Xdp.Portal()
parent = XdpGtk4.parent_new_gtk(workbench.window)
entry: Adw.EntryRow = workbench.builder.get_object("entry")
switch_row_logout: Adw.SwitchRow = workbench.builder.get_object("switch_row_logout")
switch_row_idle: Adw.SwitchRow = workbench.builder.get_object("switch_row_idle")
button_start: Gtk.Button = workbench.builder.get_object("button_start")
button_stop: Gtk.Button = workbench.builder.get_object("button_stop")
ids: list[int] = []


def on_session_inhibited(portal: Xdp.Portal, result: Gio.AsyncResult) -> None:
    try:
        identity = portal.session_inhibit_finish(result)
    except GLib.Error as error:
        print(error, file=sys.stderr)
        return
    ids.append(identity)


def inhibit_session(flag: Xdp.InhibitFlags) -> None:
    reason = entry.get_text()
    portal.session_inhibit(parent, reason, flag, None, on_session_inhibited)


def on_session_started(portal: Xdp.Portal, result: Gio.AsyncResult) -> None:
    try:
        success = portal.session_monitor_start_finish(result)
    except GLib.Error as error:
        print(error, file=sys.stderr)
        return
    if success:
        button_start.set_sensitive(False)
        button_stop.set_sensitive(True)
        if switch_row_logout.get_active():
            inhibit_session(Xdp.InhibitFlags.LOGOUT)
        if switch_row_idle.get_active():
            inhibit_session(Xdp.InhibitFlags.IDLE)
        """
    Xdp Portal also supports inhibition of Suspend and User Switch
    using the flags SUSPEND and USER_SWITCH respectively. But these
    actions cannot be inhibited on GNOME as they do not end user's
    session.
    """


def on_session_state_changed(_self: Xdp.Portal, screensaver_active: bool,
                             session_state: Xdp.LoginSessionState) -> None:
    if screensaver_active:
        print("Screensaver is active")
    match session_state:
        case Xdp.LoginSessionState.RUNNING:
            print("Session: Running")
        case Xdp.LoginSessionState.QUERY_END:
            print("Session: Query End")
            portal.session_monitor_query_end_response()
        case Xdp.LoginSessionState.ENDING:
            print("Session: Ending")


def stop_session(_button: Gtk.Button) -> None:
    global ids
    for identity in ids:
        portal.session_uninhibit(identity)
    ids = []
    portal.session_monitor_stop()
    button_start.set_sensitive(True)
    button_stop.set_sensitive(False)


button_start.clicked.connect(
    lambda _: portal.session_monitor_start(parent, Xdp.SessionMonitorFlags.NONE, None, on_session_started)
)
button_stop.clicked.connect(stop_session)
portal.session_state_changed.connect(on_session_state_changed)
