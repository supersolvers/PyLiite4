from gettext import gettext as _

from PyLiite4 import Adw, GObject

from .adw_demo_page_banners_ui import AdwDemoPageBannersChildren, template


@template
class AdwDemoPageBanners(AdwDemoPageBannersChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageBanners"

    def __init__(self) -> None:
        super().__init__()

        self.update_button_cb()

    def update_button_cb(self, *_args: object) -> None:
        editable = self.button_label_row

        if editable.get_editable():
            self.banner.set_button_label(editable.get_text())
        else:
            self.banner.set_button_label(None)

    def banner_activate_cb(self, _action_name: str, _parameter: None) -> None:
        toast_overlay = self.get_ancestor(Adw.ToastOverlay)
        toast = Adw.Toast.new(_("Banner action triggered"))

        assert isinstance(toast_overlay, Adw.ToastOverlay)
        toast_overlay.add_toast(toast)

    def button_style_notify_active_cb(self, _row: Adw.SwitchRow, _pspec: GObject.ParamSpec) -> None:
        if self.button_style_row.get_active():
            self.banner.set_button_style(Adw.BannerButtonStyle.SUGGESTED)
        else:
            self.banner.set_button_style(Adw.BannerButtonStyle.DEFAULT)


AdwDemoPageBanners.install_action("demo.activate", None, AdwDemoPageBanners.banner_activate_cb)
