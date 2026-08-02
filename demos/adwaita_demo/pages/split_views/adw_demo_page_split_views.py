from PyLiite4 import Adw

from .adw_demo_page_split_views_ui import AdwDemoPageSplitViewsChildren, template
from .adw_navigation_split_view_demo_dialog import adw_navigation_split_view_demo_dialog_new
from .adw_overlay_split_view_demo_dialog import adw_overlay_split_view_demo_dialog_new


@template
class AdwDemoPageSplitViews(AdwDemoPageSplitViewsChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageSplitViews"

    def demo_run_navigation_cb(self, _action_name: str, _parameter: None) -> None:
        adw_navigation_split_view_demo_dialog_new().present(self)

    def demo_run_overlay_cb(self, _action_name: str, _parameter: None) -> None:
        adw_overlay_split_view_demo_dialog_new().present(self)


AdwDemoPageSplitViews.install_action("demo.run-navigation", None, AdwDemoPageSplitViews.demo_run_navigation_cb)
AdwDemoPageSplitViews.install_action("demo.run-overlay", None, AdwDemoPageSplitViews.demo_run_overlay_cb)
