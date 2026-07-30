from PyLiite4 import Adw

from .adw_demo_page_buttons_ui import AdwDemoPageButtonsChildren, template


@template
class AdwDemoPageButtons(AdwDemoPageButtonsChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageButtons"
