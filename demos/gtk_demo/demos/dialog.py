"""Dialogs
#Keywords: GtkMessageDialog

Dialogs are used to pop up transient windows for information
and user feedback.
"""

from collections.abc import Callable
from dataclasses import dataclass
from gettext import gettext as _
from gettext import ngettext

from PyLiite4 import Gtk

# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None
entry1: Gtk.Entry | None = None
entry2: Gtk.Entry | None = None

i = 1


def message_dialog_clicked(button: Gtk.Button) -> None:
    global i

    # gtk_message_dialog_new() and gtk_message_dialog_format_secondary_text() take printf-style varargs,
    # so the dialog is made with its properties.
    dialog = Gtk.MessageDialog(transient_for=window_ref(),
                               modal=True, destroy_with_parent=True,
                               message_type=Gtk.MessageType.INFO,
                               buttons=Gtk.ButtonsType.OK_CANCEL,
                               text="Test message")
    secondary = ngettext("Has been shown once", "Has been shown %d times", i)
    # printf ignores an argument the format doesn't use; % doesn't.
    dialog.set_property("secondary-text", secondary % i if "%d" in secondary else secondary)
    dialog.response.connect(lambda dialog, response: dialog.destroy())
    dialog.present()
    i += 1


@dataclass
class ResponseData:
    local_entry1: Gtk.Entry
    local_entry2: Gtk.Entry
    global_entry1: Gtk.Entry
    global_entry2: Gtk.Entry


def on_dialog_response(dialog: Gtk.Dialog, response: int, data: ResponseData) -> None:
    if response == Gtk.ResponseType.OK:
        data.global_entry1.set_text(data.local_entry1.get_text())
        data.global_entry2.set_text(data.local_entry2.get_text())

    dialog.destroy()


def interactive_dialog_clicked(button: Gtk.Button) -> None:
    # gtk_dialog_new_with_buttons() takes varargs: GTK_DIALOG_USE_HEADER_BAR is the use-header-bar property,
    # and the buttons are added after.
    dialog = Gtk.Dialog(title="Interactive Dialog",
                        transient_for=window_ref(),
                        modal=True, destroy_with_parent=True, use_header_bar=True)
    dialog.add_button(_("_OK"), Gtk.ResponseType.OK)
    dialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)

    dialog.set_default_response(Gtk.ResponseType.OK)

    content_area = dialog.get_content_area()

    table = Gtk.Grid()
    table.set_hexpand(True)
    table.set_vexpand(True)
    table.set_halign(Gtk.Align.CENTER)
    table.set_valign(Gtk.Align.CENTER)
    content_area.append(table)
    table.set_row_spacing(6)
    table.set_column_spacing(6)

    label = Gtk.Label.new_with_mnemonic("_Entry 1")
    table.attach(label, 0, 0, 1, 1)
    local_entry1 = Gtk.Entry()
    local_entry1.set_text(entry1.get_text())
    table.attach(local_entry1, 1, 0, 1, 1)
    label.set_mnemonic_widget(local_entry1)

    label = Gtk.Label.new_with_mnemonic("E_ntry 2")
    table.attach(label, 0, 1, 1, 1)

    local_entry2 = Gtk.Entry()
    local_entry2.set_text(entry2.get_text())
    table.attach(local_entry2, 1, 1, 1, 1)
    label.set_mnemonic_widget(local_entry2)

    data = ResponseData(local_entry1, local_entry2, entry1, entry2)

    dialog.response.connect(on_dialog_response, data)

    dialog.present()


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref, entry1, entry2
    window = window_ref()

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Dialogs")
        window.set_resizable(False)
        window_ref = window.weak_ref()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        window.set_child(vbox)

        # Standard message dialog
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vbox.append(hbox)
        button = Gtk.Button.new_with_mnemonic("_Message Dialog")
        button.clicked.connect(message_dialog_clicked)
        hbox.append(button)

        vbox.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Interactive dialog
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vbox.append(hbox)
        vbox2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        button = Gtk.Button.new_with_mnemonic("_Interactive Dialog")
        button.clicked.connect(interactive_dialog_clicked)
        hbox.append(vbox2)
        vbox2.append(button)

        table = Gtk.Grid()
        table.set_row_spacing(4)
        table.set_column_spacing(4)
        hbox.append(table)

        label = Gtk.Label.new_with_mnemonic("_Entry 1")
        table.attach(label, 0, 0, 1, 1)

        entry1 = Gtk.Entry()
        table.attach(entry1, 1, 0, 1, 1)
        label.set_mnemonic_widget(entry1)

        label = Gtk.Label.new_with_mnemonic("E_ntry 2")
        table.attach(label, 0, 1, 1, 1)

        entry2 = Gtk.Entry()
        table.attach(entry2, 1, 1, 1, 1)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
