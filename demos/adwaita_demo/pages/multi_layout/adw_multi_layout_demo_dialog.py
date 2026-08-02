from PyLiite4 import Adw

from .adw_multi_layout_demo_dialog_ui import AdwMultiLayoutDemoDialogChildren, template


@template
class AdwMultiLayoutDemoDialog(AdwMultiLayoutDemoDialogChildren, Adw.Dialog):
    __gtype_name__ = "AdwMultiLayoutDemoDialog"


def adw_multi_layout_demo_dialog_new() -> Adw.Dialog:
    return AdwMultiLayoutDemoDialog()
