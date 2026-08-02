from PyLiite4 import Adw, Gtk, Pango

from .adw_demo_page_wrap_box_ui import AdwDemoPageWrapBoxChildren, template

LOREM_IPSUM = (
    "Lorem Ipsum Dolor Sit Amet Consectetur Adipiscing Elit Sed Do Eiusmod "
    "Tempor Incididunt Ut Labore Et Dolore Magnam Aliquam Quaerat Voluptatem "
    "Ut Enim Aeque Doleamus Animo Cum Corpore Dolemus Fieri Tamen Permagna "
    "Accessio Potest Si Aliquod Aeternum Ullus Investigandi Veri Nisi "
    "Inveneris Et Quaerendi Defatigatio Turpis Est Cum Esset Accusata Et "
    "Vituperata Ab Hortensio Qui Liber Cum Et Mortem Contemnit Qua Qui Est "
    "Imbutus Quietus Esse Numquam Potest Praeterea Bona Praeterita Grata "
    "Recordatione Renovata Delectant Est Autem Situm In"
)


def remove_tag_cb(_button: Gtk.Button, tag: Gtk.Widget) -> None:
    self = tag.get_ancestor(AdwDemoPageWrapBox)

    assert isinstance(self, AdwDemoPageWrapBox)
    self.wrap_box.remove(tag)


@template
class AdwDemoPageWrapBox(AdwDemoPageWrapBoxChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageWrapBox"

    def __init__(self) -> None:
        super().__init__()

        self.text = LOREM_IPSUM.split(" ")
        self.text_length = len(self.text)
        self.current_word = 0

        for _i in range(10):
            self.add_tag()

    def add_tag(self, _action_name: str | None = None, _parameter: None = None) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        label = Gtk.Label(label=self.text[self.current_word])
        close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic")

        label.set_xalign(0)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_hexpand(True)

        close_btn.add_css_class("flat")
        close_btn.add_css_class("circular")

        box.set_hexpand(False)
        box.add_css_class("tag")

        box.append(label)
        box.append(close_btn)

        close_btn.clicked.connect(remove_tag_cb, box)

        last_tag = self.add_btn.get_prev_sibling()

        self.wrap_box.insert_child_after(box, last_tag)

        self.current_word = (self.current_word + 1) % self.text_length


AdwDemoPageWrapBox.install_action("demo.add-tag", None, AdwDemoPageWrapBox.add_tag)
