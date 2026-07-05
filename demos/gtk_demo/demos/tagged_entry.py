"""Entry/Tagged Entry

This example shows how to build a complex composite
entry using GtkText, outside of GTK.

This tagged entry can display tags and other widgets
inside the entry area.
"""

from PyLiite4 import Gtk

from .demotaggedentry import DemoTaggedEntry, DemoTaggedEntryTag, demo_tagged_entry_new, demo_tagged_entry_tag_new

window: Gtk.Window | None = None
spinner: Gtk.Spinner | None = None


def closed_cb(tag: DemoTaggedEntryTag, entry: DemoTaggedEntry) -> None:
    entry.remove_tag(tag)


def add_tag(button: Gtk.Button, entry: DemoTaggedEntry) -> None:
    tag = demo_tagged_entry_tag_new("Blue")
    tag.add_css_class("blue")
    tag.set_has_close_button(True)
    tag.button_clicked.connect(closed_cb, entry)

    if spinner is None:
        entry.add_tag(tag)
    else:
        entry.insert_tag_after(tag, spinner.get_prev_sibling())


def toggle_spinner(button: Gtk.CheckButton, entry: DemoTaggedEntry) -> None:
    global spinner

    if spinner is not None:
        entry.remove_tag(spinner)
        spinner = None
    else:
        spinner = Gtk.Spinner()
        spinner.start()
        entry.add_tag(spinner)


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Tagged Entry")
        window.set_default_size(260, -1)
        window.set_resizable(False)

        window.destroy.connect(destroyed)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        window.set_child(box)

        entry = demo_tagged_entry_new()
        box.append(entry)

        box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box2.set_halign(Gtk.Align.END)
        box.append(box2)

        button = Gtk.Button.new_with_mnemonic("Add _Tag")
        button.clicked.connect(add_tag, entry)
        box2.append(button)

        button = Gtk.CheckButton.new_with_mnemonic("_Spinner")
        button.toggled.connect(toggle_spinner, entry)
        box2.append(button)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
