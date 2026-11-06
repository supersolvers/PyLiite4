from gettext import gettext as _
from gettext import ngettext

from PyLiite4 import Adw

from .adw_demo_page_toasts_ui import AdwDemoPageToastsChildren, template


@template
class AdwDemoPageToasts(AdwDemoPageToastsChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageToasts"

    undo_toast: Adw.Toast | None = None
    toast_undo_items = 0

    def __init__(self) -> None:
        super().__init__()

        self.action_set_enabled("toast.dismiss", False)

    def add_toast(self, toast: Adw.Toast) -> None:
        toast_overlay = self.get_ancestor(Adw.ToastOverlay)

        assert isinstance(toast_overlay, Adw.ToastOverlay)
        toast_overlay.add_toast(toast)

    def toast_clicked_cb(self, _toast: Adw.Toast) -> None:
        toast = Adw.Toast.new(ngettext("Undoing deleting <span font_features='tnum=1'>%d</span> item…",
                                       "Undoing deleting <span font_features='tnum=1'>%d</span> items…",
                                       self.toast_undo_items) % self.toast_undo_items)

        toast.set_priority(Adw.ToastPriority.HIGH)

        self.add_toast(toast)

    def dismissed_cb(self, _toast: Adw.Toast) -> None:
        self.undo_toast = None
        self.toast_undo_items = 0

        self.action_set_enabled("toast.dismiss", False)

    def toast_add_cb(self, _action_name: str, _parameter: None) -> None:
        self.add_toast(Adw.Toast.new(_("Simple Toast")))

    def toast_add_with_button_cb(self, _action_name: str, _parameter: None) -> None:
        self.toast_undo_items += 1

        if self.undo_toast:
            title = ngettext("<span font_features='tnum=1'>%d</span> item deleted",
                             "<span font_features='tnum=1'>%d</span> items deleted",
                             self.toast_undo_items) % self.toast_undo_items

            self.undo_toast.set_title(title)

            # Adding the toast again restarts its timeout.
            self.add_toast(self.undo_toast)
        else:
            self.undo_toast = Adw.Toast.new(_("‘%s’ deleted") % "Lorem Ipsum")

            self.undo_toast.set_priority(Adw.ToastPriority.HIGH)
            self.undo_toast.set_button_label(_("_Undo"))

            self.undo_toast.button_clicked.connect(self.toast_clicked_cb)
            self.undo_toast.dismissed.connect(self.dismissed_cb)

            self.add_toast(self.undo_toast)

            self.action_set_enabled("toast.dismiss", True)

    def toast_add_with_long_title_cb(self, _action_name: str, _parameter: None) -> None:
        self.add_toast(Adw.Toast.new(_("Lorem ipsum dolor sit amet, "
                                       "consectetur adipiscing elit, "
                                       "sed do eiusmod tempor incididunt "
                                       "ut labore et dolore magnam aliquam "
                                       "quaerat voluptatem.")))

    def toast_dismiss_cb(self, _action_name: str, _parameter: None) -> None:
        if self.undo_toast:
            self.undo_toast.dismiss()

    def toast_dismiss_all_cb(self, _action_name: str, _parameter: None) -> None:
        toast_overlay = self.get_ancestor(Adw.ToastOverlay)

        assert isinstance(toast_overlay, Adw.ToastOverlay)
        toast_overlay.dismiss_all()

        self.undo_toast = None


AdwDemoPageToasts.install_action("toast.add", None, AdwDemoPageToasts.toast_add_cb)
AdwDemoPageToasts.install_action("toast.add-with-button", None, AdwDemoPageToasts.toast_add_with_button_cb)
AdwDemoPageToasts.install_action("toast.add-with-long-title", None, AdwDemoPageToasts.toast_add_with_long_title_cb)
AdwDemoPageToasts.install_action("toast.dismiss", None, AdwDemoPageToasts.toast_dismiss_cb)
AdwDemoPageToasts.install_action("toast.dismiss-all", None, AdwDemoPageToasts.toast_dismiss_all_cb)
