from PyLiite4 import Adw

from .adw_demo_page_styles_ui import AdwDemoPageStylesChildren, template
from .adw_style_demo_dialog import adw_style_demo_dialog_new


@template
class AdwDemoPageStyles(AdwDemoPageStylesChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageStyles"

    def demo_run_cb(self, _action_name: str, _parameter: None) -> None:
        adw_style_demo_dialog_new().present(self)


AdwDemoPageStyles.install_action("demo.run", None, AdwDemoPageStyles.demo_run_cb)
