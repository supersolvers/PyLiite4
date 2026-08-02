from PyLiite4 import Adw

from .adw_demo_page_navigation_view_ui import AdwDemoPageNavigationViewChildren, template
from .adw_navigation_view_demo_dialog import adw_navigation_view_demo_dialog_new


@template
class AdwDemoPageNavigationView(AdwDemoPageNavigationViewChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageNavigationView"

    def demo_run_cb(self, _action_name: str, _parameter: None) -> None:
        adw_navigation_view_demo_dialog_new().present(self)


AdwDemoPageNavigationView.install_action("demo.run", None, AdwDemoPageNavigationView.demo_run_cb)
