from PyLiite4 import Adw

from .adw_demo_page_view_switcher_ui import AdwDemoPageViewSwitcherChildren, template
from .adw_view_switcher_demo_dialog import adw_view_switcher_demo_dialog_new


@template
class AdwDemoPageViewSwitcher(AdwDemoPageViewSwitcherChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageViewSwitcher"

    def demo_run_cb(self, _action_name: str, _parameter: None) -> None:
        adw_view_switcher_demo_dialog_new().present(self)


AdwDemoPageViewSwitcher.install_action("demo.run", None, AdwDemoPageViewSwitcher.demo_run_cb)
