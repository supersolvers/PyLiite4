import logging
import random
from gettext import gettext as _

from PyLiite4 import Adw, Gdk, Gio, GLib, Gtk

from .adw_demo_page_avatar_ui import AdwDemoPageAvatarChildren, template


def create_random_name() -> str:
    first_names = [
        "Adam",
        "Adrian",
        "Anna",
        "Charlotte",
        "Frédérique",
        "Ilaria",
        "Jakub",
        "Jennyfer",
        "Julia",
        "Justin",
        "Mario",
        "Miriam",
        "Mohamed",
        "Nourimane",
        "Owen",
        "Peter",
        "Petra",
        "Rachid",
        "Rebecca",
        "Sarah",
        "Thibault",
        "Wolfgang",
    ]
    last_names = [
        "Bailey",
        "Berat",
        "Chen",
        "Farquharson",
        "Ferber",
        "Franco",
        "Galinier",
        "Han",
        "Lawrence",
        "Lepied",
        "Lopez",
        "Mariotti",
        "Rossi",
        "Urasawa",
        "Zwickelman",
    ]

    return f"{random.choice(first_names)} {random.choice(last_names)}"


@template
class AdwDemoPageAvatar(AdwDemoPageAvatarChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageAvatar"

    def __init__(self) -> None:
        super().__init__()

        name = create_random_name()
        self.text.set_text(name)

        self.populate_contacts()
        self.avatar_remove_cb()

    def populate_contacts(self) -> None:
        for _i in range(30):
            name = create_random_name()
            contact = Adw.ActionRow()
            avatar = Adw.Avatar.new(40, name, True)

            avatar.set_margin_top(12)
            avatar.set_margin_bottom(12)

            contact.set_title(name)
            contact.add_prefix(avatar)
            self.contacts.append(contact)

    def avatar_open_dialog_cb(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            file = None

        if file:
            try:
                info = file.query_info(Gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME,
                                       Gio.FileQueryInfoFlags.NONE,
                                       None)
            except GLib.Error:
                info = None

            if info:
                self.file_chooser_label.set_label(info.get_display_name())

            self.action_set_enabled("avatar.remove", True)

            try:
                texture = Gdk.Texture.new_from_file(file)
            except GLib.Error as error:
                logging.critical("Failed to create texture from file: %s", error.message)
                texture = None

            self.avatar.set_custom_image(texture)

    def avatar_open_cb(self, _action_name: str, _parameter: None) -> None:
        root = self.get_root()
        dialog = Gtk.FileDialog()

        dialog.set_title(_("Select an Avatar"))

        assert isinstance(root, Gtk.Window)
        dialog.open(root,
                    None,
                    self.avatar_open_dialog_cb)

    def avatar_remove_cb(self, _action_name: str | None = None, _parameter: None = None) -> None:
        self.file_chooser_label.set_label(_("(None)"))
        self.action_set_enabled("avatar.remove", False)
        self.avatar.set_custom_image(None)

    def avatar_save_dialog_cb(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.save_finish(result)
        except GLib.Error:
            file = None

        if file:
            texture = self.avatar.draw_to_texture(self.get_scale_factor())

            texture.save_to_png(file.peek_path())

    def avatar_save_cb(self, _action_name: str, _parameter: None) -> None:
        root = self.get_root()
        dialog = Gtk.FileDialog()

        dialog.set_title(_("Save Avatar"))

        assert isinstance(root, Gtk.Window)
        dialog.save(root,
                    None,
                    self.avatar_save_dialog_cb)


AdwDemoPageAvatar.install_action("avatar.open", None, AdwDemoPageAvatar.avatar_open_cb)
AdwDemoPageAvatar.install_action("avatar.remove", None, AdwDemoPageAvatar.avatar_remove_cb)
AdwDemoPageAvatar.install_action("avatar.save", None, AdwDemoPageAvatar.avatar_save_cb)
