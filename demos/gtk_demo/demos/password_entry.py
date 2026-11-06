"""Entry/Password Entry

GtkPasswordEntry provides common functionality of
entries that are used to enter passwords and other
secrets.

It will display a warning if CapsLock is on, and it
can optionally provide a way to see the text.
"""

from PyLiite4 import GObject, Gtk

entry: Gtk.PasswordEntry | None = None
entry2: Gtk.PasswordEntry | None = None
button: Gtk.Button | None = None


def update_button(object: GObject.Object, pspec: GObject.ParamSpec) -> None:
    text = entry.get_text()
    text2 = entry2.get_text()

    button.set_sensitive(text != "" and text == text2)


def button_pressed(widget: Gtk.Button, win: Gtk.Window) -> None:
    global window
    win.destroy()
    # C's weak pointer clears itself; this module's reference keeps the window alive, so drop it.
    window = None


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window, entry, entry2, button

    if not window:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(False)
        window.set_titlebar(header)
        window.set_title("Choose a Password")
        window.set_resizable(False)
        window.set_deletable(False)

        window.close_request.connect(close_request)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        window.set_child(box)

        entry = Gtk.PasswordEntry()
        entry.set_show_peek_icon(True)
        entry.set_property("placeholder-text", "Password")
        entry.set_property("activates-default", True)
        entry.update_property([Gtk.AccessibleProperty.LABEL], ["Password"])
        entry.notify["text"].connect(update_button)
        box.append(entry)

        entry2 = Gtk.PasswordEntry()
        entry2.set_show_peek_icon(True)
        entry2.set_property("placeholder-text", "Confirm")
        entry2.set_property("activates-default", True)
        entry2.update_property([Gtk.AccessibleProperty.LABEL], ["Confirm"])
        entry2.notify["text"].connect(update_button)
        box.append(entry2)

        button = Gtk.Button.new_with_mnemonic("_Done")
        button.add_css_class("suggested-action")
        button.clicked.connect(button_pressed, window)
        button.set_sensitive(False)
        header.pack_end(button)

        window.set_default_widget(button)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
