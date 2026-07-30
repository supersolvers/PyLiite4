from PyLiite4 import Adw

from .adw_demo_page_spinner_ui import AdwDemoPageSpinnerChildren, template


@template
class AdwDemoPageSpinner(AdwDemoPageSpinnerChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageSpinner"
