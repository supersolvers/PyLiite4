from PyLiite4 import Gio, Gtk, Xdp, XdpGtk4

from demos.workbench import workbench

portal = Xdp.Portal()
parent = XdpGtk4.parent_new_gtk(workbench.window)

button: Gtk.Button = workbench.builder.get_object("button")
entry: Gtk.Entry = workbench.builder.get_object("entry")


def on_compose_opened(portal: Xdp.Portal, result: Gio.AsyncResult) -> None:
    success = portal.compose_email_finish(result)

    if success:
        print("Success")
    else:
        print("Failure, verify that you have an email application.")


def on_clicked(_button: Gtk.Button) -> None:
    email_address = entry.get_text()

    portal.compose_email(
        parent,
        [email_address],  # addresses
        None,  # cc
        None,  # bcc
        "Email from Workbench",  # subject
        "Hello World!",  # body
        None,  # attachments
        Xdp.EmailFlags.NONE,  # flags
        None,  # cancellable
        on_compose_opened,  # callback
    )


button.clicked.connect(on_clicked)
