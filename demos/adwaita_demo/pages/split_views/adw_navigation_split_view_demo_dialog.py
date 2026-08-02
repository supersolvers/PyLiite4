from PyLiite4 import Adw

from .adw_navigation_split_view_demo_dialog_ui import AdwNavigationSplitViewDemoDialogChildren, template


@template
class AdwNavigationSplitViewDemoDialog(AdwNavigationSplitViewDemoDialogChildren, Adw.Dialog):
    __gtype_name__ = "AdwNavigationSplitViewDemoDialog"


def adw_navigation_split_view_demo_dialog_new() -> Adw.Dialog:
    return AdwNavigationSplitViewDemoDialog()
