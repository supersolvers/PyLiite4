"""List Box/Complex

GtkListBox allows lists with complicated layouts, using
regular widgets supporting sorting and filtering.
"""

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk

avatar_texture_other: Gdk.Texture | None = None
window: Gtk.Window | None = None


class GtkMessage(GObject.Object):
    __gtype_name__ = "GtkMessage"

    def __init__(self) -> None:
        super().__init__()
        self.id = 0
        self.sender_name = ""
        self.sender_nick = ""
        self.message = ""
        self.time = 0
        self.reply_to = 0
        self.resent_by: str | None = None
        self.n_favorites = 0
        self.n_reshares = 0

    def parse(self, str: str) -> None:
        strv = str.split("|")

        i = 0
        self.id = int(strv[i]); i += 1  # noqa: E702
        self.sender_name = strv[i]; i += 1  # noqa: E702
        self.sender_nick = strv[i]; i += 1  # noqa: E702
        self.message = strv[i]; i += 1  # noqa: E702
        self.time = int(strv[i]); i += 1  # noqa: E702
        if i < len(strv):
            self.reply_to = int(strv[i]); i += 1  # noqa: E702
            if i < len(strv):
                if strv[i]:
                    self.resent_by = strv[i]
                i += 1
                if i < len(strv):
                    self.n_favorites = int(strv[i]); i += 1  # noqa: E702
                    if i < len(strv):
                        self.n_reshares = int(strv[i]); i += 1  # noqa: E702


def gtk_message_new(str: str) -> GtkMessage:
    msg = GtkMessage()
    msg.parse(str)
    return msg


def template_ui() -> str:
    # PyGObject's templates can't connect swapped="yes" handlers. A template callback is a method, so it gets
    # the row anyway, and the template is loaded without the flag.
    data = Gio.resources_lookup_data("/listbox/listbox.ui", Gio.ResourceLookupFlags.NONE)
    return data.get_data().decode().replace(' swapped="yes"', "")


@Gtk.Template(string=template_ui())
class GtkMessageRow(Gtk.ListBoxRow):
    __gtype_name__ = "GtkMessageRow"

    details_revealer: Gtk.Revealer = Gtk.Template.Child()
    avatar_image: Gtk.Image = Gtk.Template.Child()
    extra_buttons_box: Gtk.Widget = Gtk.Template.Child()
    content_label: Gtk.Label = Gtk.Template.Child()
    source_name: Gtk.Label = Gtk.Template.Child()
    source_nick: Gtk.Label = Gtk.Template.Child()
    short_time_label: Gtk.Label = Gtk.Template.Child()
    detailed_time_label: Gtk.Label = Gtk.Template.Child()
    resent_box: Gtk.Box = Gtk.Template.Child()
    resent_by_button: Gtk.LinkButton = Gtk.Template.Child()
    n_favorites_label: Gtk.Label = Gtk.Template.Child()
    n_reshares_label: Gtk.Label = Gtk.Template.Child()
    expand_button: Gtk.Button = Gtk.Template.Child()

    message: GtkMessage

    def update(self) -> None:
        self.source_name.set_text(self.message.sender_name)
        self.source_nick.set_text(self.message.sender_nick)
        self.content_label.set_text(self.message.message)
        t = GLib.DateTime.new_from_unix_utc(self.message.time)
        s = t.format("%e %b %y")
        self.short_time_label.set_text(s)
        s = t.format("%X - %e %b %Y")
        self.detailed_time_label.set_text(s)

        self.n_favorites_label.set_visible(self.message.n_favorites != 0)
        s = f"<b>{self.message.n_favorites}</b>\nFavorites"
        self.n_favorites_label.set_markup(s)

        self.n_reshares_label.set_visible(self.message.n_reshares != 0)
        s = f"<b>{self.message.n_reshares}</b>\nReshares"
        self.n_reshares_label.set_markup(s)

        self.resent_box.set_visible(self.message.resent_by is not None)
        if self.message.resent_by:
            self.resent_by_button.set_label(self.message.resent_by)

        if self.message.sender_nick == "GTKtoolkit":
            self.avatar_image.set_from_icon_name("org.gtk.Demo4")
        else:
            self.avatar_image.set_from_paintable(avatar_texture_other)

    def expand(self) -> None:
        expand = not self.details_revealer.get_reveal_child()

        self.details_revealer.set_reveal_child(expand)
        if expand:
            self.expand_button.set_label("Hide")
        else:
            self.expand_button.set_label("Expand")

    @Gtk.Template.Callback()
    def expand_clicked(self, button: Gtk.Button) -> None:
        self.expand()

    @Gtk.Template.Callback()
    def reshare_clicked(self, button: Gtk.Button) -> None:
        self.message.n_reshares += 1
        self.update()

    @Gtk.Template.Callback()
    def favorite_clicked(self, button: Gtk.Button) -> None:
        self.message.n_favorites += 1
        self.update()

    def do_state_flags_changed(self, previous_state_flags: Gtk.StateFlags) -> None:
        flags = self.get_state_flags()

        visible = bool(flags & (Gtk.StateFlags.PRELIGHT | Gtk.StateFlags.SELECTED))
        self.extra_buttons_box.set_visible(visible)

        Gtk.ListBoxRow.do_state_flags_changed(self, previous_state_flags)


def gtk_message_row_new(message: GtkMessage) -> GtkMessageRow:
    row = GtkMessageRow()
    row.message = message
    row.update()

    return row


def gtk_message_row_sort(a: GtkMessageRow, b: GtkMessageRow, data: object) -> int:
    return b.message.time - a.message.time


def row_activated(listbox: Gtk.ListBox, row: GtkMessageRow) -> None:
    row.expand()


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global avatar_texture_other, window

    if window is None:
        avatar_texture_other = Gdk.Texture.new_from_resource("/listbox/apple-red.png")

        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("List Box — Complex")
        window.set_default_size(400, 600)
        window.close_request.connect(close_request)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        window.set_child(vbox)
        label = Gtk.Label(label="Messages from GTK and friends")
        vbox.append(label)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        vbox.append(scrolled)
        listbox = Gtk.ListBox()
        scrolled.set_child(listbox)

        listbox.set_sort_func(gtk_message_row_sort, listbox)
        listbox.set_activate_on_single_click(False)
        listbox.row_activated.connect(row_activated)

        data = Gio.resources_lookup_data("/listbox/messages.txt", Gio.ResourceLookupFlags.NONE)
        lines = data.get_data().decode().split("\n")

        for line in lines:
            if not line:
                break
            message = gtk_message_new(line)
            row = gtk_message_row_new(message)
            listbox.insert(row, -1)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
