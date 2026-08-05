from PyLiite4 import Adw, Gtk

from .adw_demo_preferences_dialog_ui import AdwDemoPreferencesDialogChildren, template


@template
class AdwDemoPreferencesDialog(AdwDemoPreferencesDialogChildren, Adw.PreferencesDialog):
    __gtype_name__ = "AdwDemoPreferencesDialog"

    # Objects outside the <template> element, which pyliite4-ui doesn't bind.
    subpage1: Adw.NavigationPage = Gtk.Template.Child()
    subpage2: Adw.NavigationPage = Gtk.Template.Child()

    def subpage1_activated_cb(self, _sender: Gtk.Widget) -> None:
        self.push_subpage(self.subpage1)

    def subpage2_activated_cb(self, _sender: Gtk.Widget) -> None:
        self.push_subpage(self.subpage2)

    def toast_show_cb(self, _action_name: str, _parameter: None) -> None:
        self.add_toast(Adw.Toast.new("Example Toast"))


AdwDemoPreferencesDialog.install_action("toast.show", None, AdwDemoPreferencesDialog.toast_show_cb)


def adw_demo_preferences_dialog_new() -> Adw.Dialog:
    return AdwDemoPreferencesDialog()
