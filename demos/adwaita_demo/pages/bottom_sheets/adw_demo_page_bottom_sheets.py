from PyLiite4 import Adw

from .adw_demo_page_bottom_sheets_ui import AdwDemoPageBottomSheetsChildren, template


@template
class AdwDemoPageBottomSheets(AdwDemoPageBottomSheetsChildren, Adw.Bin):
    __gtype_name__ = "AdwDemoPageBottomSheets"
