from PyLiite4 import Adw

from .adw_demo_page_welcome_ui import AdwDemoPageWelcomeChildren, template


@template
class AdwDemoPageWelcome(AdwDemoPageWelcomeChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageWelcome"
