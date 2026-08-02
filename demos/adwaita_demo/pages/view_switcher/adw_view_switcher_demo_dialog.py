from PyLiite4 import Adw

from .adw_view_switcher_demo_dialog_ui import AdwViewSwitcherDemoDialogChildren, template


@template
class AdwViewSwitcherDemoDialog(AdwViewSwitcherDemoDialogChildren, Adw.Dialog):
    __gtype_name__ = "AdwViewSwitcherDemoDialog"


def adw_view_switcher_demo_dialog_new() -> Adw.Dialog:
    return AdwViewSwitcherDemoDialog()
