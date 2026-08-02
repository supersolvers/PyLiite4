from PyLiite4 import Adw

from .adw_navigation_view_demo_dialog_ui import AdwNavigationViewDemoDialogChildren, template


@template
class AdwNavigationViewDemoDialog(AdwNavigationViewDemoDialogChildren, Adw.Dialog):
    __gtype_name__ = "AdwNavigationViewDemoDialog"


def adw_navigation_view_demo_dialog_new() -> Adw.Dialog:
    return AdwNavigationViewDemoDialog()
