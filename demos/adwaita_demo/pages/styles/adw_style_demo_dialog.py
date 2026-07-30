from PyLiite4 import Adw, GObject, Gtk

from .adw_style_demo_dialog_ui import AdwStyleDemoDialogChildren, template


@template
class AdwStyleDemoDialog(AdwStyleDemoDialogChildren, Adw.Dialog):
    __gtype_name__ = "AdwStyleDemoDialog"

    # Objects outside the <template> element, which pyliite4-ui doesn't bind.
    status_page_dialog: Adw.Dialog = Gtk.Template.Child()
    sidebar_dialog: Adw.Dialog = Gtk.Template.Child()
    split_view: Adw.NavigationSplitView = Gtk.Template.Child()

    progress = GObject.Property(type=bool, default=False)

    def status_page_cb(self, _action_name: str, _parameter: None) -> None:
        self.status_page_dialog.present(self)

    def sidebar_cb(self, _action_name: str, _parameter: None) -> None:
        self.sidebar_dialog.present(self)

    def dummy_cb(self, _action_name: str, _parameter: None) -> None:
        pass

    def get_devel_style(self) -> bool:
        root = self.get_root()

        if not isinstance(root, Gtk.Widget):
            return False

        return root.has_css_class("devel")

    def set_devel_style(self, devel: bool) -> None:
        root = self.get_root()

        if not isinstance(root, Gtk.Widget):
            return

        if devel:
            root.add_css_class("devel")
        else:
            root.remove_css_class("devel")

    devel = GObject.Property(type=bool, default=False, getter=get_devel_style, setter=set_devel_style)

    def sidebar_forward_cb(self, _list_box: Gtk.ListBox, _row: Gtk.ListBoxRow) -> None:
        self.split_view.set_show_content(True)

    def do_root(self) -> None:
        Adw.Dialog.do_root(self)

        if self.get_devel_style():
            self.notify("devel")

    def do_unroot(self) -> None:
        has_devel = self.get_devel_style()

        Adw.Dialog.do_unroot(self)

        if has_devel:
            self.notify("devel")


AdwStyleDemoDialog.install_property_action("style.devel", "devel")
AdwStyleDemoDialog.install_property_action("style.progress", "progress")
AdwStyleDemoDialog.install_action("style.status-page", None, AdwStyleDemoDialog.status_page_cb)
AdwStyleDemoDialog.install_action("style.sidebar", None, AdwStyleDemoDialog.sidebar_cb)
AdwStyleDemoDialog.install_action("style.dummy", None, AdwStyleDemoDialog.dummy_cb)


def adw_style_demo_dialog_new() -> Adw.Dialog:
    return AdwStyleDemoDialog()
