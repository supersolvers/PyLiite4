from PyLiite4 import Adw

from .adw_demo_page_clamp_ui import AdwDemoPageClampChildren, template


@template
class AdwDemoPageClamp(AdwDemoPageClampChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageClamp"
