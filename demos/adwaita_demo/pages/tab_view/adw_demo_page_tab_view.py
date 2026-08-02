from PyLiite4 import Adw, Gtk

from .adw_demo_page_tab_view_ui import AdwDemoPageTabViewChildren, template
from .adw_tab_view_demo_window import adw_tab_view_demo_window_new


@template
class AdwDemoPageTabView(AdwDemoPageTabViewChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageTabView"

    def demo_run_cb(self, _action_name: str, _parameter: None) -> None:
        window = adw_tab_view_demo_window_new()
        root = self.get_root()

        window.prepopulate()

        assert isinstance(root, Gtk.Window)
        window.set_transient_for(root)
        window.present()


AdwDemoPageTabView.install_action("demo.run", None, AdwDemoPageTabView.demo_run_cb)
