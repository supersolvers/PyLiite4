from PyLiite4 import Adw, GObject


class AdwDemoSidebarItem(Adw.SidebarItem):
    __gtype_name__ = "AdwDemoSidebarItem"

    # A GtkWidget subtype in C; PyGObject's GType properties can't restrict the type.
    page_type = GObject.Property(type=GObject.TYPE_GTYPE, nick="page-type")

    def get_page_type(self) -> GObject.GType:
        return self.page_type
