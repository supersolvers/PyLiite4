from PyLiite4 import Adw

from .adw_demo_page_toggles_ui import AdwDemoPageTogglesChildren, template


@template
class AdwDemoPageToggles(AdwDemoPageTogglesChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageToggles"
