from PyLiite4 import Adw

from .adw_demo_page_lists_ui import AdwDemoPageListsChildren, template


@template
class AdwDemoPageLists(AdwDemoPageListsChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageLists"

    def entry_apply_cb(self, _row: Adw.EntryRow) -> None:
        toast_overlay = self.get_ancestor(Adw.ToastOverlay)
        toast = Adw.Toast.new("Changes applied")

        assert isinstance(toast_overlay, Adw.ToastOverlay)
        toast_overlay.add_toast(toast)
