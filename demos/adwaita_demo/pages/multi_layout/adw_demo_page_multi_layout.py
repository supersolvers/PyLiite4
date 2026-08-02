from PyLiite4 import Adw

from .adw_demo_page_multi_layout_ui import AdwDemoPageMultiLayoutChildren, template
from .adw_multi_layout_demo_dialog import adw_multi_layout_demo_dialog_new


@template
class AdwDemoPageMultiLayout(AdwDemoPageMultiLayoutChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageMultiLayout"

    def demo_run_cb(self, _action_name: str, _parameter: None) -> None:
        adw_multi_layout_demo_dialog_new().present(self)


AdwDemoPageMultiLayout.install_action("demo.run", None, AdwDemoPageMultiLayout.demo_run_cb)
