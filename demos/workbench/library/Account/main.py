from PyLiite4 import Adw, Gdk, Gio, Gtk, Xdp, XdpGtk4

from demos.workbench import workbench

portal = Xdp.Portal()
parent = XdpGtk4.parent_new_gtk(workbench.window)

revealer: Gtk.Revealer = workbench.builder.get_object("revealer")
button: Gtk.Button = workbench.builder.get_object("button")
avatar: Adw.Avatar = workbench.builder.get_object("avatar")
entry: Adw.EntryRow = workbench.builder.get_object("entry")
username: Gtk.Label = workbench.builder.get_object("username")
display: Gtk.Label = workbench.builder.get_object("name")


def on_information_recieved(_portal: Xdp.Portal, result: Gio.AsyncResult) -> None:
    result = portal.get_user_information_finish(result)

    """
    result is a GVariant dictionary containing the following fields
    id (s): the user ID
    name (s): the users real name
    image (s): the uri of an image file for the users avatar picture
    """

    user_info = result
    id = user_info["id"]
    name = user_info["name"]
    uri = user_info["image"]
    file = Gio.File.new_for_uri(uri)
    texture = Gdk.Texture.new_from_file(file)

    username.set_label(id)
    display.set_label(name)
    avatar.set_custom_image(texture)
    revealer.set_reveal_child(True)

    entry.set_text("")
    print("Information retrieved")


def on_clicked(_button: Gtk.Button) -> None:
    reason = entry.get_text()
    portal.get_user_information(
        parent, reason, Xdp.UserInformationFlags.NONE, None, on_information_recieved
    )


button.clicked.connect(on_clicked)
