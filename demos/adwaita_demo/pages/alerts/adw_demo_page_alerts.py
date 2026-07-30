from gettext import gettext as _

from PyLiite4 import Adw, Gio

from .adw_demo_page_alerts_ui import AdwDemoPageAlertsChildren, template


@template
class AdwDemoPageAlerts(AdwDemoPageAlertsChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageAlerts"

    last_toast: Adw.Toast | None = None

    def toast_dismissed_cb(self, toast: Adw.Toast) -> None:
        if toast == self.last_toast:
            self.last_toast = None

    def alert_cb(self, dialog: Adw.AlertDialog, result: Gio.AsyncResult) -> None:
        toast_overlay = self.get_ancestor(Adw.ToastOverlay)
        response = dialog.choose_finish(result)
        toast = Adw.Toast.new(_("Dialog response: %s") % response)
        toast.dismissed.connect(self.toast_dismissed_cb)

        if self.last_toast is not None:
            self.last_toast.dismiss()
        self.last_toast = toast

        assert isinstance(toast_overlay, Adw.ToastOverlay)
        toast_overlay.add_toast(toast)

    def demo_alert_dialog_cb(self, _action_name: str, _parameter: None) -> None:
        dialog = Adw.AlertDialog.new(_("Save Changes?"),
                                     _("Open document contains unsaved changes. Changes which are not saved will be permanently lost."))

        dialog.add_response("cancel", _("_Cancel"))
        dialog.add_response("discard", _("_Discard"))
        dialog.add_response("save", _("_Save"))

        dialog.set_response_appearance("discard",
                                       Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("save",
                                       Adw.ResponseAppearance.SUGGESTED)

        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        dialog.choose(self, None, lambda dialog, result: self.alert_cb(dialog, result))


AdwDemoPageAlerts.install_action("demo.alert-dialog", None, AdwDemoPageAlerts.demo_alert_dialog_cb)
