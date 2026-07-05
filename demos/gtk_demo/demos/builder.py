"""Builder
#Keywords: GMenu, GtkPopoverMenuBar, GtkBuilder, GtkShortcutController, toolbar

Demonstrates a traditional interface, loaded from a XML description,
and shows how to connect actions to the menu items and toolbar buttons.
"""

from collections.abc import Callable

from PyLiite4 import Gdk, Gio, GLib, Gtk


def quit_activate(action: Gio.SimpleAction, parameter: GLib.Variant | None,
                  user_data: Callable[[], Gtk.Window]) -> None:
    window = user_data()
    window.destroy()


def about_activate(action: Gio.SimpleAction, parameter: GLib.Variant | None,
                   user_data: Callable[[], Gtk.Window]) -> None:
    window = user_data()
    about_dlg: Gtk.Window = window.about
    about_dlg.present()


def remove_timeout(status: Gtk.Label) -> None:
    id = getattr(status, "timeout", 0)
    if id:
        GLib.source_remove(id)
        status.timeout = 0


def pop_message(status: Gtk.Label) -> int:
    status.set_label("")
    status.timeout = 0

    return GLib.SOURCE_REMOVE


def status_message(status: Gtk.Label, text: str) -> None:
    id = getattr(status, "timeout", 0)
    if id:
        GLib.source_remove(id)

    status.set_text(text)

    id = GLib.timeout_add(5000, pop_message, status)

    status.timeout = id


def help_activate(action: Gio.SimpleAction, parameter: GLib.Variant | None,
                  user_data: Callable[[], Gtk.Window]) -> None:
    window = user_data()
    status = window.status
    status_message(status, "Help not available")


def not_implemented(action: Gio.SimpleAction, parameter: GLib.Variant | None,
                    user_data: Callable[[], Gtk.Window]) -> None:
    window = user_data()
    text = f"Action “{action.get_name()}” not implemented"
    status = window.status
    status_message(status, text)


win_entries = [
    ("new", not_implemented, None, None, None),
    ("open", not_implemented, None, None, None),
    ("save", not_implemented, None, None, None),
    ("save-as", not_implemented, None, None, None),
    ("copy", not_implemented, None, None, None),
    ("cut", not_implemented, None, None, None),
    ("paste", not_implemented, None, None, None),
    ("quit", quit_activate, None, None, None),
    ("about", about_activate, None, None, None),
    ("help", help_activate, None, None, None),
]

# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref

    window = window_ref()
    if window is None:
        builder = Gtk.Builder.new_from_resource("/builder/demo.ui")

        window = builder.get_object("window1")
        window.set_display(do_widget.get_display())
        window_ref = window.weak_ref()
        actions = Gio.SimpleActionGroup()
        # The window is passed weakly: the window holds the actions, so a strong reference would keep it alive after
        # it's destroyed.
        actions.add_action_entries(win_entries, window.weak_ref())
        window.insert_action_group("win", actions)

        controller = Gtk.ShortcutController()
        controller.set_scope(Gtk.ShortcutScope.GLOBAL)
        window.add_controller(controller)
        for keyval, modifiers, action in [
            (Gdk.KEY_n, Gdk.ModifierType.CONTROL_MASK, "win.new"),
            (Gdk.KEY_o, Gdk.ModifierType.CONTROL_MASK, "win.open"),
            (Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK, "win.save"),
            (Gdk.KEY_s, Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK, "win.save-as"),
            (Gdk.KEY_q, Gdk.ModifierType.CONTROL_MASK, "win.quit"),
            (Gdk.KEY_c, Gdk.ModifierType.CONTROL_MASK, "win.copy"),
            (Gdk.KEY_x, Gdk.ModifierType.CONTROL_MASK, "win.cut"),
            (Gdk.KEY_v, Gdk.ModifierType.CONTROL_MASK, "win.paste"),
            (Gdk.KEY_F1, 0, "win.help"),
            (Gdk.KEY_F7, 0, "win.about"),
        ]:
            controller.add_shortcut(Gtk.Shortcut.new(Gtk.KeyvalTrigger.new(keyval, modifiers),
                                                     Gtk.NamedAction.new(action)))

        about = builder.get_object("aboutdialog1")
        about.set_transient_for(window)
        about.set_hide_on_close(True)
        window.about = about
        # As g_object_set_data_full() with gtk_window_destroy: the dialog goes with the window.
        window.weak_ref(about.destroy)

        status = builder.get_object("statusbar1")
        window.status = status
        status.destroy.connect(remove_timeout)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
