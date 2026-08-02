from PyLiite4 import Adw, GObject, Gtk

from .adw_overlay_split_view_demo_dialog_ui import AdwOverlaySplitViewDemoDialogChildren, template


@template
class AdwOverlaySplitViewDemoDialog(AdwOverlaySplitViewDemoDialogChildren, Adw.Dialog):
    __gtype_name__ = "AdwOverlaySplitViewDemoDialog"

    def start_button_notify_active_cb(self, _button: Gtk.ToggleButton, _pspec: GObject.ParamSpec) -> None:
        start = self.start_button.get_active()

        self.split_view.set_sidebar_position(Gtk.PackType.START if start else Gtk.PackType.END)


def adw_overlay_split_view_demo_dialog_new() -> Adw.Dialog:
    return AdwOverlaySplitViewDemoDialog()
