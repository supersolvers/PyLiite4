import sys
from gettext import gettext as _

from PyLiite4 import Adw, Gdk, Gio, GLib, GObject, Gtk

from .adw_tab_view_demo_page import (AdwTabViewDemoPage, adw_tab_view_demo_page_new,
                                     adw_tab_view_demo_page_new_duplicate)
from .adw_tab_view_demo_window_ui import AdwTabViewDemoWindowChildren, template

next_page = 1


def window_new(action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
    window = adw_tab_view_demo_window_new()

    window.prepopulate()

    window.present()


def text_to_tooltip(binding: GObject.Binding, title: str) -> str:
    return _("Elaborate tooltip for <b>%s</b>") % GLib.markup_escape_text(title or "")


def get_indicator_icon(page: Adw.TabPage) -> Gio.Icon:
    muted = getattr(page, "adw_tab_view_demo_muted", False)

    if muted:
        return Gio.ThemedIcon.new("tab-audio-muted-symbolic")
    else:
        return Gio.ThemedIcon.new("tab-audio-playing-symbolic")


def get_indicator_tooltip(page: Adw.TabPage) -> str:
    muted = getattr(page, "adw_tab_view_demo_muted", False)

    if muted:
        return _("Unmute Tab")
    else:
        return _("Mute Tab")


@template
class AdwTabViewDemoWindow(AdwTabViewDemoWindowChildren, Adw.Window):
    __gtype_name__ = "AdwTabViewDemoWindow"

    def __init__(self) -> None:
        super().__init__()

        self.menu_page: Adw.TabPage | None = None
        self.in_dispose = False

        action_map = Gio.SimpleActionGroup()
        add_action_entries(action_map, self.action_entries())
        self.insert_action_group("win", action_map)

        self.tab_action_group: Gio.SimpleActionGroup | None = Gio.SimpleActionGroup()
        add_action_entries(self.tab_action_group, self.tab_action_entries())

        self.insert_action_group("tab", self.tab_action_group)

        self.tab_bar.setup_extra_drop_target(Gdk.DragAction.COPY, [GObject.TYPE_STRING])
        self.tab_overview.setup_extra_drop_target(Gdk.DragAction.COPY, [GObject.TYPE_STRING])

        display = self.get_display()
        style_manager = Adw.StyleManager.get_for_display(display)

        # Bound methods, so that the connections end with the window, as g_signal_connect_object() does.
        style_manager.notify["dark"].connect(self.invalidate_thumbnails_cb)
        style_manager.notify["high-contrast"].connect(self.invalidate_thumbnails_cb)

    def action_entries(self) -> list[tuple]:
        return [
            ("window-new", window_new),
            ("tab-new", self.tab_new),
        ]

    def tab_action_entries(self) -> list[tuple]:
        return [
            ("pin", self.tab_pin),
            ("unpin", self.tab_unpin),
            ("close", self.tab_close),
            ("close-other", self.tab_close_other),
            ("close-before", self.tab_close_before),
            ("close-after", self.tab_close_after),
            ("move-to-new-window", self.tab_move_to_new_window),
            ("needs-attention", None, None, "false", self.tab_change_needs_attention),
            ("loading", None, None, "false", self.tab_change_loading),
            ("indicator", None, None, "false", self.tab_change_indicator),
            ("icon", None, None, "false", self.tab_change_icon),
            ("refresh-icon", self.tab_refresh_icon),
            ("duplicate", self.tab_duplicate),
        ]

    def invalidate_thumbnails_cb(self, _style_manager: Adw.StyleManager, _pspec: GObject.ParamSpec) -> None:
        self.view.invalidate_thumbnails()

    def add_page(self, parent: Adw.TabPage | None, content: AdwTabViewDemoPage) -> Adw.TabPage:
        page = self.view.add_page(content, parent)

        content.bind_property("title",
                              page, "title",
                              GObject.BindingFlags.SYNC_CREATE)
        content.bind_property("title",
                              page, "tooltip",
                              GObject.BindingFlags.SYNC_CREATE,
                              text_to_tooltip)
        content.bind_property("icon",
                              page, "icon",
                              GObject.BindingFlags.SYNC_CREATE)

        page.set_indicator_activatable(True)
        page.set_thumbnail_xalign(0.5)
        page.set_thumbnail_yalign(0.5)

        return page

    def create_tab_cb(self, _overview: Adw.TabOverview) -> Adw.TabPage:
        global next_page

        title = _("Tab %d") % next_page

        content = adw_tab_view_demo_page_new(title)
        page = self.add_page(None, content)

        next_page += 1

        return page

    def tab_new(self, action: Gio.SimpleAction | None, parameter: GLib.Variant | None) -> None:
        page = self.create_tab_cb(self.tab_overview)
        content = page.get_child()

        self.view.set_selected_page(page)

        content.grab_focus()

    def get_current_page(self) -> Adw.TabPage:
        if self.menu_page:
            return self.menu_page

        return self.view.get_selected_page()

    def tab_pin(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        self.view.set_page_pinned(self.get_current_page(), True)

    def tab_unpin(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        self.view.set_page_pinned(self.get_current_page(), False)

    def tab_close(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        self.view.close_page(self.get_current_page())

    def tab_close_other(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        self.view.close_other_pages(self.get_current_page())

    def tab_close_before(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        self.view.close_pages_before(self.get_current_page())

    def tab_close_after(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        self.view.close_pages_after(self.get_current_page())

    def tab_move_to_new_window(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        window = adw_tab_view_demo_window_new()

        self.view.transfer_page(self.menu_page,
                                window.view,
                                0)

        window.present()

    def tab_change_needs_attention(self, action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        need_attention = parameter.get_boolean()

        self.get_current_page().set_needs_attention(need_attention)
        action.set_state(GLib.Variant.new_boolean(need_attention))

    def tab_change_loading(self, action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        loading = parameter.get_boolean()

        self.get_current_page().set_loading(loading)
        action.set_state(GLib.Variant.new_boolean(loading))

    def tab_change_indicator(self, action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        indicator = parameter.get_boolean()
        icon = None

        if indicator:
            icon = get_indicator_icon(self.get_current_page())
            tooltip = get_indicator_tooltip(self.get_current_page())
        else:
            tooltip = ""

        self.get_current_page().set_indicator_icon(icon)
        self.get_current_page().set_indicator_tooltip(tooltip)
        action.set_state(GLib.Variant.new_boolean(indicator))

    def tab_change_icon(self, action: Gio.SimpleAction, parameter: GLib.Variant) -> None:
        enable_icon = parameter.get_boolean()
        page = self.get_current_page()
        child = page.get_child()

        assert isinstance(child, AdwTabViewDemoPage)
        child.set_enable_icon(enable_icon)

        action.set_state(GLib.Variant.new_boolean(enable_icon))

    def tab_refresh_icon(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        page = self.get_current_page()
        child = page.get_child()

        assert isinstance(child, AdwTabViewDemoPage)
        child.refresh_icon()

    def tab_duplicate(self, action: Gio.SimpleAction, parameter: GLib.Variant | None) -> None:
        parent = self.get_current_page()
        parent_content = parent.get_child()

        assert isinstance(parent_content, AdwTabViewDemoPage)
        content = adw_tab_view_demo_page_new_duplicate(parent_content)
        page = self.add_page(parent, content)

        page.set_indicator_icon(parent.get_indicator_icon())
        page.set_indicator_tooltip(parent.get_indicator_tooltip())
        page.set_loading(parent.get_loading())
        page.set_needs_attention(parent.get_needs_attention())

        page.adw_tab_view_demo_muted = getattr(parent, "adw_tab_view_demo_muted", False)

        self.view.set_selected_page(page)

    def set_tab_action_enabled(self, name: str, enabled: bool) -> None:
        assert self.tab_action_group is not None
        action = self.tab_action_group.lookup_action(name)

        assert isinstance(action, Gio.SimpleAction)

        action.set_enabled(enabled)

    def set_tab_action_state(self, name: str, state: bool) -> None:
        assert self.tab_action_group is not None
        action = self.tab_action_group.lookup_action(name)

        assert isinstance(action, Gio.SimpleAction)

        action.set_state(GLib.Variant.new_boolean(state))

    def page_detached_cb(self, _view: Adw.TabView, page: Adw.TabPage, _position: int) -> None:
        if self.in_dispose:
            return

        if not self.view.get_n_pages() and not self.tab_overview.get_open():
            self.close()

    def setup_menu_cb(self, view: Adw.TabView, page: Adw.TabPage | None) -> None:
        prev = None
        can_close_before = can_close_after = True
        pinned = False
        has_icon = False

        self.menu_page = page

        n_pages = self.view.get_n_pages()

        if page:
            pos = self.view.get_page_position(page)

            if pos > 0:
                prev = self.view.get_nth_page(pos - 1)

            pinned = page.get_pinned()
            prev_pinned = prev is not None and prev.get_pinned()

            can_close_before = not pinned and prev is not None and not prev_pinned
            can_close_after = pos < n_pages - 1

            has_icon = page.get_icon() is not None

        self.set_tab_action_enabled("pin", not page or not pinned)
        self.set_tab_action_enabled("unpin", not page or pinned)
        self.set_tab_action_enabled("close", not page or not pinned)
        self.set_tab_action_enabled("close-before", can_close_before)
        self.set_tab_action_enabled("close-after", can_close_after)
        self.set_tab_action_enabled("close-other", can_close_before or can_close_after)
        self.set_tab_action_enabled("move-to-new-window", not page or (not pinned and n_pages > 1))
        self.set_tab_action_enabled("refresh-icon", has_icon)

        if page:
            self.set_tab_action_state("icon", has_icon)
            self.set_tab_action_state("loading", page.get_loading())
            self.set_tab_action_state("needs-attention", page.get_needs_attention())
            self.set_tab_action_state("indicator", page.get_indicator_icon() is not None)

    def create_window_cb(self, _view: Adw.TabView) -> Adw.TabView:
        window = adw_tab_view_demo_window_new()

        window.present()

        return window.view

    def indicator_activated_cb(self, _view: Adw.TabView, page: Adw.TabPage) -> None:
        muted = getattr(page, "adw_tab_view_demo_muted", False)

        page.adw_tab_view_demo_muted = not muted

        icon = get_indicator_icon(page)
        tooltip = get_indicator_tooltip(page)

        page.set_indicator_icon(icon)
        page.set_indicator_tooltip(tooltip)

    def extra_drag_drop_cb(self, _widget: Gtk.Widget, page: Adw.TabPage, value: GObject.Value | str) -> bool:
        page.set_title(value.get_string() if isinstance(value, GObject.Value) else value)

        return Gdk.EVENT_STOP

    def do_dispose(self) -> None:
        self.in_dispose = True

        self.tab_action_group = None

        Adw.Window.do_dispose(self)

    def prepopulate(self) -> None:
        self.tab_new(None, None)
        self.tab_new(None, None)
        self.tab_new(None, None)

        self.view.invalidate_thumbnails()


def add_action_entries(action_map: Gio.ActionMap, entries: list[tuple]) -> None:
    """g_action_map_add_action_entries(): (name, activate) or (name, activate, parameter_type, state, change_state)."""
    for name, activate, parameter_type, state, change_state in (entry + (None,) * (5 - len(entry))
                                                                 for entry in entries):
        parameter = GLib.VariantType.new(parameter_type) if parameter_type else None
        if state is not None:
            action = Gio.SimpleAction.new_stateful(name, parameter, GLib.Variant.parse(None, state, None, None))
        else:
            action = Gio.SimpleAction.new(name, parameter)
        if activate is not None:
            action.activate.connect(activate)
        if change_state is not None:
            action.change_state.connect(change_state)
        action_map.add_action(action)


def add_binding_action(widget_class: type[Gtk.Widget], keyval: int, mods: Gdk.ModifierType, action_name: str) -> None:
    """gtk_widget_class_add_binding_action(), which is variadic and so not in the bindings."""
    widget_class.add_shortcut(Gtk.Shortcut(trigger=Gtk.KeyvalTrigger(keyval=keyval, modifiers=mods),
                                           action=Gtk.NamedAction(action_name=action_name)))


MOD = Gdk.ModifierType.META_MASK if sys.platform == "darwin" else Gdk.ModifierType.CONTROL_MASK
add_binding_action(AdwTabViewDemoWindow, Gdk.KEY_t, MOD, "win.tab-new")
add_binding_action(AdwTabViewDemoWindow, Gdk.KEY_n, MOD, "win.window-new")
add_binding_action(AdwTabViewDemoWindow, Gdk.KEY_w, MOD, "tab.close")


def adw_tab_view_demo_window_new() -> AdwTabViewDemoWindow:
    return AdwTabViewDemoWindow()
