import random

from PyLiite4 import Adw, Gdk, Gio, GObject, Gtk

from .adw_tab_view_demo_page_ui import AdwTabViewDemoPageChildren, template

N_COLORS = 8

icon_names: list[str] | None = None


def init_icon_names(theme: Gtk.IconTheme) -> list[str]:
    global icon_names

    if icon_names is None:
        icon_names = theme.get_icon_names()

    return icon_names


def get_random_icon() -> Gio.Icon:
    display = Gdk.Display.get_default()
    theme = Gtk.IconTheme.get_for_display(display)

    return Gio.ThemedIcon.new(random.choice(init_icon_names(theme)))


def get_random_color() -> int:
    return random.randrange(N_COLORS) + 1


@template
class AdwTabViewDemoPage(AdwTabViewDemoPageChildren, Adw.Bin):
    __gtype_name__ = "AdwTabViewDemoPage"

    title = GObject.Property(type=str)
    icon = GObject.Property(type=Gio.Icon)

    def __init__(self, **properties: object) -> None:
        properties.setdefault("icon", get_random_icon())

        super().__init__(**properties)

        self.color = 0
        self.last_icon: Gio.Icon | None = None

        self.set_color(get_random_color())

    def set_color(self, color: int) -> None:
        if self.color == color:
            return

        if self.color > 0:
            self.remove_css_class(f"tab-page-color-{self.color}")

        if color > 0:
            self.add_css_class(f"tab-page-color-{color}")

        self.color = color

    def refresh_icon(self) -> None:
        self.icon = get_random_icon()

    def set_enable_icon(self, enable_icon: bool) -> None:
        if enable_icon:
            self.icon = self.last_icon
            self.last_icon = None
        else:
            self.last_icon = self.icon
            self.icon = None


def adw_tab_view_demo_page_new(title: str) -> AdwTabViewDemoPage:
    return AdwTabViewDemoPage(title=title)


def adw_tab_view_demo_page_new_duplicate(self: AdwTabViewDemoPage) -> AdwTabViewDemoPage:
    page = AdwTabViewDemoPage(title=self.title, icon=self.icon)

    page.set_color(self.color)

    return page
