"""Spinner

GtkSpinner allows to show that background activity is on-going.
"""

from PyLiite4 import Gtk

spinner_sensitive: Gtk.Spinner | None = None
spinner_unsensitive: Gtk.Spinner | None = None


def on_play_clicked(button: Gtk.Button | None, user_data: Gtk.Spinner | None = None) -> None:
    spinner_sensitive.start()
    spinner_unsensitive.start()


def on_stop_clicked(button: Gtk.Button, user_data: Gtk.Spinner | None = None) -> None:
    spinner_sensitive.stop()
    spinner_unsensitive.stop()


window: Gtk.Window | None = None


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window, spinner_sensitive, spinner_unsensitive

    if window is None:
        window = Gtk.Window()
        window.set_transient_for(do_widget)
        window.set_title("Spinner")
        window.set_resizable(False)
        window.destroy.connect(destroyed)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)

        window.set_child(vbox)

        # Sensitive
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        spinner = Gtk.Spinner()
        hbox.append(spinner)
        hbox.append(Gtk.Entry())
        vbox.append(hbox)
        spinner_sensitive = spinner

        # Disabled
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        spinner = Gtk.Spinner()
        hbox.append(spinner)
        hbox.append(Gtk.Entry())
        vbox.append(hbox)
        spinner_unsensitive = spinner
        hbox.set_sensitive(False)

        button = Gtk.Button.new_with_label("Play")
        button.clicked.connect(on_play_clicked, spinner)
        vbox.append(button)

        button = Gtk.Button.new_with_label("Stop")
        button.clicked.connect(on_stop_clicked, spinner)
        vbox.append(button)

        # Start by default to test for:
        # https://bugzilla.gnome.org/show_bug.cgi?id=598496
        on_play_clicked(None, None)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
