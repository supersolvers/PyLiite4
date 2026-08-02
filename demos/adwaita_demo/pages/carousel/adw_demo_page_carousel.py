from gettext import gettext as _

from PyLiite4 import Adw, GObject, Gtk

from .adw_demo_page_carousel_ui import AdwDemoPageCarouselChildren, template


@template
class AdwDemoPageCarousel(AdwDemoPageCarouselChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageCarousel"

    # Expression closures, which pyliite4-ui doesn't bind: it only looks at <signal> handlers.
    @Gtk.Template.Callback()
    def get_orientation_name(self, item: Adw.EnumListItem) -> str | None:
        match item.get_value():
            case Gtk.Orientation.HORIZONTAL:
                return _("Horizontal")
            case Gtk.Orientation.VERTICAL:
                return _("Vertical")
            case _:
                return None

    def notify_orientation_cb(self, _row: Adw.ComboRow, _pspec: GObject.ParamSpec) -> None:
        orientation = self.orientation_row.get_selected()

        self.box.set_orientation(Gtk.Orientation(1 - orientation))
        self.carousel.set_orientation(Gtk.Orientation(orientation))

    @Gtk.Template.Callback()
    def get_indicators_name(self, value: Gtk.StringObject) -> str | None:
        assert isinstance(value, Gtk.StringObject)

        style = value.get_string()

        if style == "dots":
            return _("Dots")

        if style == "lines":
            return _("Lines")

        return None

    def notify_indicators_cb(self, _row: Adw.ComboRow, _pspec: GObject.ParamSpec) -> None:
        obj = self.indicators_row.get_selected_item()

        assert isinstance(obj, Gtk.StringObject)
        self.indicators_stack.set_visible_child_name(obj.get_string())

    def carousel_return_cb(self, _action_name: str, _parameter: None) -> None:
        self.carousel.scroll_to(self.carousel.get_nth_page(0), True)


AdwDemoPageCarousel.install_action("carousel.return", None, AdwDemoPageCarousel.carousel_return_cb)
