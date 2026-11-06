"""SuggestionEntry: an entry that suggests completions from a list model, used by the Lists/Selections demo.

Ported from GTK Demo's suggestionentry.c and suggestionentry.h.
"""

from collections.abc import Callable
from typing import Any

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk

_EXPLICIT = GObject.ParamFlags.READWRITE | GObject.ParamFlags.EXPLICIT_NOTIFY


class MatchObject(GObject.Object):
    __gtype_name__ = "MatchObject"

    item = GObject.Property(type=GObject.Object, nick="Item", blurb="Item",
                            flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    string = GObject.Property(type=str, nick="String", blurb="String",
                              flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **properties: Any) -> None:
        self._match_start = 0
        self._match_end = 0
        self._score = 0
        super().__init__(**properties)

    @GObject.Property(type=GObject.TYPE_UINT, nick="Match Start", blurb="Match Start", flags=_EXPLICIT)
    def match_start(self) -> int:
        return self._match_start

    @match_start.setter
    def match_start(self, value: int) -> None:
        if self._match_start != value:
            self._match_start = value
            self.notify("match-start")

    @GObject.Property(type=GObject.TYPE_UINT, nick="Match End", blurb="Match End", flags=_EXPLICIT)
    def match_end(self) -> int:
        return self._match_end

    @match_end.setter
    def match_end(self, value: int) -> None:
        if self._match_end != value:
            self._match_end = value
            self.notify("match-end")

    @GObject.Property(type=GObject.TYPE_UINT, nick="Score", blurb="Score", flags=_EXPLICIT)
    def score(self) -> int:
        return self._score

    @score.setter
    def score(self, value: int) -> None:
        if self._score != value:
            self._score = value
            self.notify("score")

    def get_item(self) -> GObject.Object:
        return self.props.item

    def get_string(self) -> str:
        return self.props.string

    def get_match_start(self) -> int:
        return self._match_start

    def get_match_end(self) -> int:
        return self._match_end

    def get_score(self) -> int:
        return self._score

    def set_match(self, start: int, end: int, score: int) -> None:
        self.freeze_notify()

        self.set_property("match-start", start)
        self.set_property("match-end", end)
        self.set_property("score", score)

        self.thaw_notify()


def match_object_new(item: GObject.Object, string: str) -> MatchObject:
    return MatchObject(item=item, string=string)


SuggestionEntryMatchFunc = Callable[[MatchObject, str, Any], None]

# ----


def setup_item(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    label = Gtk.Label(xalign=0.0)
    list_item.set_child(label)


def bind_item(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    item = list_item.get_item()
    label = list_item.get_child()

    label.set_label(item.get_string())


def default_match_func(object: MatchObject, search: str, data: Any) -> None:
    tmp1 = GLib.utf8_normalize(object.get_string(), -1, GLib.NormalizeMode.ALL)
    tmp2 = GLib.utf8_casefold(tmp1, -1)

    tmp3 = GLib.utf8_normalize(search, -1, GLib.NormalizeMode.ALL)
    tmp4 = GLib.utf8_casefold(tmp3, -1)

    if tmp2.startswith(tmp4):
        object.set_match(0, len(search), 1)
    else:
        object.set_match(0, 0, 0)


def keyval_is_cursor_move(keyval: int) -> bool:
    if keyval == Gdk.KEY_Up or keyval == Gdk.KEY_KP_Up:
        return True

    if keyval == Gdk.KEY_Down or keyval == Gdk.KEY_KP_Down:
        return True

    if keyval == Gdk.KEY_Page_Up or keyval == Gdk.KEY_Page_Down:
        return True

    return False


PAGE_STEP = 10


class SuggestionEntry(Gtk.Widget, Gtk.Editable):
    __gtype_name__ = "SuggestionEntry"

    # C installs GtkEditable's properties with gtk_editable_install_properties() and forwards them to the
    # delegate with gtk_editable_delegate_get/set_property(); PyGObject has no way to override an interface
    # property, so they are declared here and forwarded by hand.
    text = GObject.Property(type=str, default="", flags=_EXPLICIT,
                            getter=lambda self: self.entry.get_text(),
                            setter=lambda self, value: self.entry.set_text(value))
    cursor_position = GObject.Property(type=int, minimum=0, maximum=65535, default=0,
                                       flags=GObject.ParamFlags.READABLE,
                                       getter=lambda self: self.entry.get_position())
    enable_undo = GObject.Property(type=bool, default=True, flags=_EXPLICIT,
                                   getter=lambda self: self.entry.get_enable_undo(),
                                   setter=lambda self, value: self.entry.set_enable_undo(value))
    selection_bound = GObject.Property(type=int, minimum=0, maximum=65535, default=0,
                                       flags=GObject.ParamFlags.READABLE,
                                       getter=lambda self: self.entry.get_property("selection-bound"))
    editable = GObject.Property(type=bool, default=True, flags=_EXPLICIT,
                                getter=lambda self: self.entry.get_editable(),
                                setter=lambda self, value: self.entry.set_editable(value))
    width_chars = GObject.Property(type=int, minimum=-1, maximum=GLib.MAXINT32, default=-1, flags=_EXPLICIT,
                                   getter=lambda self: self.entry.get_width_chars(),
                                   setter=lambda self, value: self.entry.set_width_chars(value))
    max_width_chars = GObject.Property(type=int, minimum=-1, maximum=GLib.MAXINT32, default=-1, flags=_EXPLICIT,
                                       getter=lambda self: self.entry.get_max_width_chars(),
                                       setter=lambda self, value: self.entry.set_max_width_chars(value))
    xalign = GObject.Property(type=GObject.TYPE_FLOAT, minimum=0.0, maximum=1.0, default=0.0, flags=_EXPLICIT,
                              getter=lambda self: self.entry.get_alignment(),
                              setter=lambda self, value: self.entry.set_alignment(value))

    def __init__(self, **properties: Any) -> None:
        self._model: Any = None
        self._factory: Gtk.ListItemFactory | None = None
        self.expression: Gtk.Expression | None = None

        self.filter: Gtk.Filter | None = None
        self.map_model: Gtk.MapListModel | None = None
        self.selection: Gtk.SingleSelection | None = None

        self.entry: Gtk.Text | None = None
        self.arrow: Gtk.Widget | None = None
        self.popup: Gtk.Popover | None = None
        self.list: Gtk.ListView | None = None

        self.search: str | None = None

        self.match_func: SuggestionEntryMatchFunc = default_match_func
        self.match_data: Any = None

        self.changed_id = 0

        self._use_filter = True
        self._show_arrow = False

        super().__init__()

        display = Gdk.Display.get_default()
        if not getattr(display, "suggestion_style", None):
            provider = Gtk.CssProvider()
            provider.load_from_resource("/listview_selections/suggestionentry.css")
            Gtk.StyleContext.add_provider_for_display(display, provider, 800)
            display.suggestion_style = provider

        self.add_css_class("suggestion")

        self.entry = Gtk.Text()
        self.entry.set_parent(self)
        self.entry.set_hexpand(True)
        self.init_delegate()
        self.changed_id = self.entry.notify["text"].connect(self.text_changed)

        self.popup = Gtk.Popover()
        self.popup.set_position(Gtk.PositionType.BOTTOM)
        self.popup.set_autohide(False)
        self.popup.set_has_arrow(False)
        self.popup.set_halign(Gtk.Align.START)
        self.popup.add_css_class("menu")
        self.popup.set_parent(self)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_max_content_height(400)
        sw.set_propagate_natural_height(True)

        self.popup.set_child(sw)
        self.list = Gtk.ListView()
        self.list.set_single_click_activate(True)
        self.list.activate.connect(self.row_activated)
        sw.set_child(self.list)

        self.set_default_factory()

        controller = Gtk.EventControllerKey()
        controller.set_name("gtk-suggestion-entry")
        controller.key_pressed.connect(self.key_pressed)
        self.entry.add_controller(controller)

        controller = Gtk.EventControllerFocus()
        controller.set_name("gtk-suggestion-entry")
        controller.leave.connect(self.focus_out)
        self.entry.add_controller(controller)

        for name, value in properties.items():
            self.set_property(name, value)

    model = GObject.Property(type=Gio.ListModel, nick="Model", blurb="Model for the displayed items",
                             flags=_EXPLICIT, getter=lambda self: self.get_model(),
                             setter=lambda self, value: self.set_model(value))
    factory = GObject.Property(type=Gtk.ListItemFactory, nick="Factory", blurb="Factory for populating list items",
                               flags=_EXPLICIT, getter=lambda self: self.get_factory(),
                               setter=lambda self, value: self.set_factory(value))
    # C also has an "expression" property, made with gtk_param_spec_expression(); GObject.Property doesn't
    # support GtkExpression, so it's only reachable through get_expression() and set_expression().
    placeholder_text = GObject.Property(type=str, nick="Placeholder text",
                                        blurb="Show text in the entry when it’s empty and unfocused",
                                        getter=lambda self: self.entry.get_placeholder_text(),
                                        setter=lambda self, value: self.entry.set_placeholder_text(value))
    popup_visible = GObject.Property(type=bool, default=False, nick="Popup visible",
                                     blurb="Whether the popup with suggestions is currently visible",
                                     flags=_EXPLICIT,
                                     getter=lambda self: bool(self.popup and self.popup.get_visible()),
                                     setter=lambda self, value: self.set_popup_visible(value))
    use_filter = GObject.Property(type=bool, default=True, nick="Use filter",
                                  blurb="Whether to filter the list for matches", flags=_EXPLICIT,
                                  getter=lambda self: self.get_use_filter(),
                                  setter=lambda self, value: self.set_use_filter(value))
    show_arrow = GObject.Property(type=bool, default=False, nick="Show arrow",
                                  blurb="Whether to show a clickable arrow for presenting the popup",
                                  flags=_EXPLICIT, getter=lambda self: self.get_show_arrow(),
                                  setter=lambda self, value: self.set_show_arrow(value))

    def do_get_delegate(self) -> Gtk.Editable:
        return self.entry

    def do_dispose(self) -> None:
        if self.changed_id:
            self.entry.notify["text"].disconnect(self.changed_id)
            self.changed_id = 0
        if self.entry is not None:
            self.finish_delegate()
            self.entry.unparent()
            self.entry = None
        if self.arrow is not None:
            self.arrow.unparent()
            self.arrow = None
        if self.popup is not None:
            self.popup.unparent()
            self.popup = None

        self.expression = None
        self._factory = None

        self._model = None
        self.map_model = None
        self.selection = None

        self.search = None

        Gtk.Widget.do_dispose(self)

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        result = self.entry.measure(orientation, for_size)

        if self.arrow and self.arrow.get_visible():
            arrow_min, arrow_nat, _, _ = self.arrow.measure(orientation, for_size)

        return result

    def do_size_allocate(self, width: int, height: int, baseline: int) -> None:
        arrow_min = arrow_nat = 0

        if self.arrow and self.arrow.get_visible():
            arrow_min, arrow_nat, _, _ = self.arrow.measure(Gtk.Orientation.HORIZONTAL, -1)

        allocation = Gdk.Rectangle()
        allocation.x, allocation.y, allocation.width, allocation.height = 0, 0, width - arrow_nat, height
        self.entry.size_allocate(allocation, baseline)

        if self.arrow and self.arrow.get_visible():
            allocation = Gdk.Rectangle()
            allocation.x, allocation.y, allocation.width, allocation.height = width - arrow_nat, 0, arrow_nat, height
            self.arrow.size_allocate(allocation, baseline)

        self.popup.set_size_request(self.get_width(), -1)
        self.popup.queue_resize()

        self.popup.present()

    def do_grab_focus(self) -> bool:
        return self.entry.grab_focus()

    def set_popup_visible(self, visible: bool) -> None:
        if self.popup.get_visible() == visible:
            return

        if self.selection.get_n_items() == 0:
            return

        if visible:
            if not self.entry.has_focus():
                self.entry.grab_focus_without_selecting()

            self.selection.set_selected(Gtk.INVALID_LIST_POSITION)
            self.popup.popup()
        else:
            self.popup.popdown()

        self.notify("popup-visible")

    def text_changed_idle(self) -> bool:
        if not self.map_model:
            return GLib.SOURCE_REMOVE

        text = self.entry.get_text()

        self.search = text

        self.update_map()

        matches = self.selection.get_n_items()

        self.set_popup_visible(matches > 0)

        return GLib.SOURCE_REMOVE

    def text_changed(self, editable: Gtk.Editable, pspec: GObject.ParamSpec) -> None:
        # Deferred to an idle, since GtkText sets the selection bounds after notify::text.
        GLib.idle_add(self.text_changed_idle)

    def accept_current_selection(self) -> None:
        item = self.selection.get_selected_item()
        if not item:
            return

        with self.entry.notify["text"].blocked(self.changed_id):
            self.entry.set_text(item.get_string())

            self.entry.set_position(-1)

    def row_activated(self, listview: Gtk.ListView, position: int) -> None:
        self.set_popup_visible(False)
        self.accept_current_selection()

    def key_pressed(self, controller: Gtk.EventControllerKey, keyval: int, keycode: int,
                    state: Gdk.ModifierType) -> bool:
        if state & (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.ALT_MASK | Gdk.ModifierType.CONTROL_MASK):
            return False

        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            self.set_popup_visible(False)
            self.accept_current_selection()
            self.search = self.entry.get_text()
            self.update_map()

            return True
        elif keyval == Gdk.KEY_Escape:
            if self.popup.get_mapped():
                self.set_popup_visible(False)

                with self.entry.notify["text"].blocked(self.changed_id):
                    self.entry.set_text(self.search if self.search else "")

                    self.entry.set_position(-1)

                return True
        elif keyval == Gdk.KEY_Right or keyval == Gdk.KEY_KP_Right:
            self.entry.set_position(-1)
            return True
        elif keyval == Gdk.KEY_Left or keyval == Gdk.KEY_KP_Left:
            return False
        elif keyval in (Gdk.KEY_Tab, Gdk.KEY_KP_Tab, Gdk.KEY_ISO_Left_Tab):
            self.set_popup_visible(False)
            return False  # Leaves normal focus handling undisturbed.

        matches = self.selection.get_n_items()
        selected = self.selection.get_selected()
        invalid = Gtk.INVALID_LIST_POSITION

        if keyval_is_cursor_move(keyval):
            if keyval == Gdk.KEY_Up or keyval == Gdk.KEY_KP_Up:
                if selected == 0:
                    selected = invalid
                elif selected == invalid:
                    selected = matches - 1
                else:
                    selected -= 1
            elif keyval == Gdk.KEY_Down or keyval == Gdk.KEY_KP_Down:
                if selected == matches - 1:
                    selected = invalid
                elif selected == invalid:
                    selected = 0
                else:
                    selected += 1
            elif keyval == Gdk.KEY_Page_Up:
                if selected == 0:
                    selected = invalid
                elif selected == invalid:
                    selected = matches - 1
                elif selected >= PAGE_STEP:
                    selected -= PAGE_STEP
                else:
                    selected = 0
            elif keyval == Gdk.KEY_Page_Down:
                if selected == matches - 1:
                    selected = invalid
                elif selected == invalid:
                    selected = 0
                elif selected + PAGE_STEP < matches:
                    selected += PAGE_STEP
                else:
                    selected = matches - 1

            self.list.scroll_to(selected, Gtk.ListScrollFlags.SELECT, None)
            return True

        return False

    def focus_out(self, controller: Gtk.EventControllerFocus) -> None:
        if not self.popup.get_mapped():
            return

        self.set_popup_visible(False)
        self.accept_current_selection()

    def set_default_factory(self) -> None:
        factory = Gtk.SignalListItemFactory()

        factory.setup.connect(setup_item)
        factory.bind.connect(bind_item)

        self.set_factory(factory)

    def get_model(self) -> Any:
        return self._model

    def selection_changed(self, selection: Gtk.SingleSelection, pspec: GObject.ParamSpec | None) -> None:
        self.accept_current_selection()

    def filter_func(self, item: MatchObject) -> bool:
        if self._use_filter:
            min_score = 1
        else:
            min_score = 0

        return item.get_score() >= min_score

    def map_func(self, item: GObject.Object) -> MatchObject:
        if self.expression:
            value = GObject.Value()
            self.expression.evaluate(item, value)
            string = value.get_value()
        elif isinstance(item, Gtk.StringObject):
            string = item.get_property("string")
        else:
            GLib.log_default_handler("SuggestionEntry", GLib.LogLevelFlags.LEVEL_CRITICAL,
                                     "Either SuggestionEntry:expression must be set "
                                     "or SuggestionEntry:model must be a GtkStringList")
            string = "No value"

        obj = match_object_new(item, string)

        if self.search:
            self.match_func(obj, self.search, self.match_data)
        else:
            obj.set_match(0, 0, 1)

        return obj

    def update_map(self) -> None:
        if self.map_model is not None:
            self.map_model.set_map_func(self.map_func)

    def set_model(self, model: Any) -> None:
        if self._model is model:
            return
        self._model = model

        if self.selection:
            self.selection.notify["selected"].disconnect(self.selection_changed)

        if model is None:
            self.list.set_model(None)
            self.selection = None
            self.map_model = None
            self.filter = None
        else:
            map_model = Gtk.MapListModel.new(model, None)
            self.map_model = map_model

            self.update_map()

            filter = Gtk.CustomFilter.new(self.filter_func)
            filter_model = Gtk.FilterListModel.new(self.map_model, filter)
            self.filter = filter

            sorter = Gtk.NumericSorter.new(Gtk.PropertyExpression.new(MatchObject, None, "score"))
            sorter.set_sort_order(Gtk.SortType.DESCENDING)
            sort_model = Gtk.SortListModel.new(filter_model, sorter)

            self.update_map()

            selection = Gtk.SingleSelection.new(sort_model)
            selection.set_autoselect(False)
            selection.set_can_unselect(True)
            selection.set_selected(Gtk.INVALID_LIST_POSITION)
            self.selection = selection
            self.list.set_model(selection)

        if self.selection:
            self.selection.notify["selected"].connect(self.selection_changed)
            self.selection_changed(self.selection, None)

        self.notify("model")

    def get_factory(self) -> Gtk.ListItemFactory | None:
        return self._factory

    def set_factory(self, factory: Gtk.ListItemFactory | None) -> None:
        if self._factory is factory:
            return
        self._factory = factory

        if self.list:
            self.list.set_factory(factory)

        self.notify("factory")

    def set_expression(self, expression: Gtk.Expression | None) -> None:
        assert expression is None or expression.get_value_type() == GObject.TYPE_STRING

        if self.expression == expression:
            return

        self.expression = expression

        self.update_map()

        # C notifies the "expression" property here. PyGObject can't declare a GtkExpression property.

    def get_expression(self) -> Gtk.Expression | None:
        return self.expression

    def set_use_filter(self, use_filter: bool) -> None:
        if self._use_filter == use_filter:
            return

        self._use_filter = use_filter

        self.filter.changed(Gtk.FilterChange.DIFFERENT)

        self.notify("use-filter")

    def get_use_filter(self) -> bool:
        return self._use_filter

    def arrow_clicked(self, *args: Any) -> None:
        visible = self.popup.get_visible()
        self.set_popup_visible(not visible)

    def set_show_arrow(self, show_arrow: bool) -> None:
        if self._show_arrow == show_arrow:
            return

        self._show_arrow = show_arrow

        if show_arrow:
            self.arrow = Gtk.Image.new_from_icon_name("pan-down-symbolic")
            self.arrow.set_tooltip_text("Show suggestions")
            self.arrow.set_parent(self)

            press = Gtk.GestureClick()
            press.released.connect(self.arrow_clicked)
            self.arrow.add_controller(press)
        else:
            if self.arrow is not None:
                self.arrow.unparent()
                self.arrow = None

        self.notify("show-arrow")

    def get_show_arrow(self) -> bool:
        return self._show_arrow

    def set_match_func(self, match_func: SuggestionEntryMatchFunc, user_data: Any = None) -> None:
        self.match_func = match_func
        self.match_data = user_data


SuggestionEntry.install_property_action("popup.show", "popup-visible")

# gtk_widget_class_add_binding_action() is variadic, so not in the bindings; it adds this shortcut.
SuggestionEntry.add_shortcut(Gtk.Shortcut(trigger=Gtk.KeyvalTrigger(keyval=Gdk.KEY_Down,
                                                                    modifiers=Gdk.ModifierType.ALT_MASK),
                                          action=Gtk.NamedAction(action_name="popup.show")))

SuggestionEntry.set_css_name("entry")


def suggestion_entry_new() -> SuggestionEntry:
    return SuggestionEntry()
