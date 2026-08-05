import sys

from PyLiite4 import Adw, Gdk, Gtk

from .adw_demo_sidebar_item import AdwDemoSidebarItem
from .adw_demo_window_ui import AdwDemoWindowChildren, template
# Register the page types that the sidebar items name, as g_type_ensure() does.
from .pages.about.adw_demo_page_about import AdwDemoPageAbout  # noqa: F401
from .pages.alerts.adw_demo_page_alerts import AdwDemoPageAlerts  # noqa: F401
from .pages.animations.adw_demo_page_animations import AdwDemoPageAnimations  # noqa: F401
from .pages.avatar.adw_demo_page_avatar import AdwDemoPageAvatar  # noqa: F401
from .pages.banners.adw_demo_page_banners import AdwDemoPageBanners  # noqa: F401
from .pages.bottom_sheets.adw_demo_page_bottom_sheets import AdwDemoPageBottomSheets  # noqa: F401
from .pages.buttons.adw_demo_page_buttons import AdwDemoPageButtons  # noqa: F401
from .pages.carousel.adw_demo_page_carousel import AdwDemoPageCarousel  # noqa: F401
from .pages.clamp.adw_demo_page_clamp import AdwDemoPageClamp  # noqa: F401
from .pages.lists.adw_demo_page_lists import AdwDemoPageLists  # noqa: F401
from .pages.multi_layout.adw_demo_page_multi_layout import AdwDemoPageMultiLayout  # noqa: F401
from .pages.navigation_view.adw_demo_page_navigation_view import AdwDemoPageNavigationView  # noqa: F401
from .pages.spinner.adw_demo_page_spinner import AdwDemoPageSpinner  # noqa: F401
from .pages.split_views.adw_demo_page_split_views import AdwDemoPageSplitViews  # noqa: F401
from .pages.styles.adw_demo_page_styles import AdwDemoPageStyles  # noqa: F401
from .pages.tab_view.adw_demo_page_tab_view import AdwDemoPageTabView  # noqa: F401
from .pages.toasts.adw_demo_page_toasts import AdwDemoPageToasts  # noqa: F401
from .pages.toggles.adw_demo_page_toggles import AdwDemoPageToggles  # noqa: F401
from .pages.view_switcher.adw_demo_page_view_switcher import AdwDemoPageViewSwitcher  # noqa: F401
from .pages.welcome.adw_demo_page_welcome import AdwDemoPageWelcome  # noqa: F401
from .pages.wrap_box.adw_demo_page_wrap_box import AdwDemoPageWrapBox  # noqa: F401


@template
class AdwDemoWindow(AdwDemoWindowChildren, Adw.ApplicationWindow):
    __gtype_name__ = "AdwDemoWindow"

    active_item: Adw.SidebarItem | None = None

    def __init__(self, **properties: object) -> None:
        super().__init__(**properties)

        self.update_content()

    def update_content(self) -> None:
        item = self.sidebar.get_selected_item()

        if self.active_item == item:
            return

        self.active_item = item

        if not item:
            self.split_view.set_content(Adw.NavigationPage(title=""))
            return

        assert isinstance(item, AdwDemoSidebarItem)

        # Construct through the Python class, so that its __init__() runs: GObject.new() would skip it.
        child = item.get_page_type().pytype()
        title = item.get_title()

        self.split_view.set_content(Adw.NavigationPage.new(child, title))

    def search_activated_cb(self, _entry: Gtk.SearchEntry) -> None:
        self.sidebar.grab_focus()

    def sidebar_activated_cb(self, _sidebar: Adw.Sidebar, index: int) -> None:
        self.update_content()
        self.split_view.set_show_content(True)

    def adaptive_preview_cb(self, _action_name: str, _parameter: None) -> None:
        open = self.get_adaptive_preview()

        self.set_adaptive_preview(not open)




def add_binding_action(widget_class: type[Gtk.Widget], keyval: int, mods: Gdk.ModifierType, action_name: str) -> None:
    """gtk_widget_class_add_binding_action(), which is variadic and so not in the bindings."""
    widget_class.add_shortcut(Gtk.Shortcut(trigger=Gtk.KeyvalTrigger(keyval=keyval, modifiers=mods),
                                           action=Gtk.NamedAction(action_name=action_name)))


if sys.platform == "darwin":
    add_binding_action(AdwDemoWindow, Gdk.KEY_w, Gdk.ModifierType.META_MASK, "window.close")
else:
    add_binding_action(AdwDemoWindow, Gdk.KEY_w, Gdk.ModifierType.CONTROL_MASK, "window.close")

AdwDemoWindow.install_action("window.adaptive-preview", None, AdwDemoWindow.adaptive_preview_cb)


def adw_demo_window_new(application: Gtk.Application) -> Gtk.Window:
    return AdwDemoWindow(application=application)
