"""Drag-and-Drop
#Keywords: dnd, menu, popover, gesture

This demo shows dragging colors and widgets.
The items in this demo can be moved, recolored
and rotated.

The demo also has an example for creating a
menu-like popover without using a menu model.
"""

import math

from collections.abc import Callable

from PyLiite4 import Gdk, GLib, GObject, Graphene, Gsk, Gtk

n_items = 0


class CanvasItem(Gtk.Widget):
    __gtype_name__ = "CanvasItem"

    def __init__(self) -> None:
        global n_items
        super().__init__()

        self.r = 0.0
        self.angle = 0.0
        self.delta = 0.0
        self.editor: Gtk.Widget | None = None
        self.provider: Gtk.StyleProvider | None = None
        self.css_class: str | None = None
        self.scale_handler = 0

        n_items += 1

        text = f"Item {n_items}"
        self.label = Gtk.Label(label=text)
        self.label.add_css_class("canvasitem")

        self.fixed: Gtk.Fixed | None = Gtk.Fixed()
        self.fixed.set_parent(self)
        self.fixed.put(self.label, 0, 0)

        self.label.add_css_class("frame")

        id = f"item{n_items}"
        self.label.set_name(id)

        rgba = Gdk.RGBA()
        if theme_is_dark():
            rgba.parse("blue")
        else:
            rgba.parse("yellow")

        set_color(self, rgba)

        self.angle = 0

        # gtk_drop_target_new (G_TYPE_INVALID, ...): PyGObject refuses G_TYPE_INVALID, so the constructor is used.
        dest = Gtk.DropTarget(actions=Gdk.DragAction.COPY)
        dest.set_gtypes([Gdk.RGBA, GObject.TYPE_STRING])
        dest.drop.connect(item_drag_drop)
        self.label.add_controller(dest)

        gesture = Gtk.GestureRotate()
        gesture.angle_changed.connect(angle_changed)
        gesture.end.connect(rotate_done)
        self.add_controller(gesture)

        gesture = Gtk.GestureClick()
        gesture.released.connect(click_done)
        self.add_controller(gesture)

    def do_dispose(self) -> None:
        if self.fixed is not None:
            self.fixed.unparent()
            self.fixed = None
        if self.editor is not None:
            self.editor.unparent()
            self.editor = None

        Gtk.Widget.do_dispose(self)

    def do_map(self) -> None:
        Gtk.Widget.do_map(self)

        apply_transform(self)


CanvasItem.set_layout_manager_type(Gtk.BinLayout)
CanvasItem.set_css_name("item")


def unstyle_item(item: CanvasItem) -> None:
    if item.provider:
        Gtk.StyleContext.remove_provider_for_display(item.label.get_display(), item.provider)
        item.provider = None

    if item.css_class:
        item.label.remove_css_class(item.css_class)
        item.css_class = None


def set_color(item: CanvasItem, color: Gdk.RGBA) -> None:
    unstyle_item(item)

    str = color.to_string()
    name = item.label.get_name()
    css = f"#{name} {{ background: {str}; }}"

    provider = Gtk.CssProvider()
    provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(item.label.get_display(), provider, 700)
    item.provider = provider


def set_css(item: CanvasItem, class_: str) -> None:
    unstyle_item(item)

    item.label.add_css_class(class_)
    item.css_class = class_


def item_drag_drop(dest: Gtk.DropTarget, value: object, x: float, y: float) -> bool:
    label = dest.get_widget()
    item = label.get_parent().get_parent()

    if isinstance(value, Gdk.RGBA):
        set_color(item, value)
    elif isinstance(value, str):
        set_css(item, value)

    return True


def apply_transform(item: CanvasItem) -> None:
    # The label's bounds cover its CSS padding and border, so it turns about the middle of its whole box.
    ok, bounds = item.label.compute_bounds(item.label)
    if not ok:
        return

    x = bounds.get_width() / 2.
    y = bounds.get_height() / 2.

    item.r = math.sqrt(x * x + y * y)

    transform = Gsk.Transform.new().translate(Graphene.Point().init(item.r, item.r))
    transform = transform.rotate(item.angle + item.delta)
    transform = transform.translate(Graphene.Point().init(-x, -y))

    item.fixed.set_child_transform(item.label, transform)


def angle_changed(gesture: Gtk.GestureRotate, angle: float, delta: float) -> None:
    item = gesture.get_widget()

    item.delta = angle / math.pi * 180.0

    apply_transform(item)


def rotate_done(gesture: Gtk.Gesture, sequence: Gdk.EventSequence | None) -> None:
    item = gesture.get_widget()

    item.angle = item.angle + item.delta
    item.delta = 0


def click_done(gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
    item = gesture.get_widget()
    canvas = item.get_parent()

    last_child = canvas.get_last_child()
    if item != last_child:
        item.insert_after(canvas, last_child)


# GtkSettings treats `GTK_THEME=foo:dark` as theme name `foo`, variant `dark`, and GTK's embedded CSS files let
# `foo-dark` work as an alias for `foo:dark`.
def has_dark_suffix(theme: str) -> bool:
    return theme.endswith(":dark") or theme.endswith("-dark")


# The current theme is probably dark if its name ends in `:dark` or `-dark`, or if Settings:…prefer-dark-theme is
# True.
def theme_is_dark() -> bool:
    # Like GtkSettings, this first checks whether the environment variable overrides the theme.
    env_theme = GLib.getenv("GTK_THEME")
    if env_theme is not None:
        return has_dark_suffix(env_theme)

    # If not, Settings:…theme-name is tested in the same way, or :…prefer-dark-theme.
    settings = Gtk.Settings.get_default()
    theme = settings.get_property("gtk-theme-name") or ""
    prefer_dark = settings.get_property("gtk-application-prefer-dark-theme")
    dark = prefer_dark or has_dark_suffix(theme)
    return dark


def canvas_item_new() -> CanvasItem:
    return CanvasItem()


def canvas_item_get_drag_icon(item: CanvasItem) -> Gdk.Paintable:
    return Gtk.WidgetPaintable.new(item.fixed)


def canvas_item_is_editing(item: CanvasItem) -> bool:
    return item.editor is not None


def scale_changed(range: Gtk.Range, item: CanvasItem) -> None:
    item.angle = range.get_value()
    apply_transform(item)


def text_changed(editable: Gtk.Editable, pspec: GObject.ParamSpec, item: CanvasItem) -> None:
    item.label.set_text(editable.get_text())
    apply_transform(item)


def canvas_item_stop_editing(item: CanvasItem) -> None:
    if not item.editor:
        return

    scale = item.editor.get_last_child()
    scale.value_changed.disconnect(item.scale_handler)

    item.editor.get_parent().remove(item.editor)
    item.editor = None


def canvas_item_start_editing(item: CanvasItem) -> None:
    canvas = item.get_parent()

    if item.editor:
        return

    item.editor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

    entry = Gtk.Entry()

    entry.set_text(item.label.get_text())

    entry.set_width_chars(12)
    entry.notify["text"].connect(text_changed, item)
    entry.activate.connect(lambda entry: canvas_item_stop_editing(item))

    item.editor.append(entry)

    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 360, 1)
    scale.set_draw_value(False)
    scale.set_value(math.fmod(item.angle, 360))

    item.scale_handler = scale.value_changed.connect(scale_changed, item)

    item.editor.append(scale)

    ok, p = item.compute_point(canvas, Graphene.Point().init(0, 0))
    if not ok:
        p = Graphene.Point().init(0, 0)
    canvas.put(item.editor, p.x, p.y + 2 * item.r)
    entry.grab_focus()


def prepare(source: Gtk.DragSource, x: float, y: float) -> Gdk.ContentProvider | None:
    canvas = source.get_widget()
    item = canvas.pick(x, y, Gtk.PickFlags.DEFAULT)

    item = item.get_ancestor(CanvasItem) if item else None
    if not item:
        return None

    canvas.dragged_item = item

    ok, p = canvas.compute_point(item, Graphene.Point().init(x, y))
    if not ok:
        p = Graphene.Point().init(x, y)
    canvas.hotspot = (p.x, p.y)

    return Gdk.ContentProvider.new_for_value(GObject.Value(Gtk.Widget, item))


def drag_begin(source: Gtk.DragSource, drag: Gdk.Drag) -> None:
    canvas = source.get_widget()
    item = canvas.dragged_item
    hotspot = canvas.hotspot

    trash = canvas.trash
    trash_paintable = trash.get_paintable()
    trash_paintable.set_state(0)
    trash.set_visible(True)

    paintable = canvas_item_get_drag_icon(item)
    source.set_icon(paintable, int(hotspot[0]), int(hotspot[1]))

    item.set_opacity(0.3)


def drag_end(source: Gtk.DragSource, drag: Gdk.Drag, delete_data: bool) -> None:
    canvas = source.get_widget()
    item = canvas.dragged_item
    canvas.dragged_item = None

    item.set_opacity(1.0)

    trash = canvas.trash
    trash.set_visible(False)


def drag_cancel(source: Gtk.DragSource, drag: Gdk.Drag, reason: Gdk.DragCancelReason) -> bool:
    canvas = source.get_widget()
    trash = canvas.trash
    trash.set_visible(False)

    return False


def drag_drop(target: Gtk.DropTarget, item: CanvasItem, x: float, y: float) -> bool:
    canvas = item.get_parent()
    last_child = canvas.get_last_child()
    if item != last_child:
        item.insert_after(canvas, last_child)

    canvas.move(item, x - item.r, y - item.r)

    return True


def drop_in_trash(target: Gtk.DropTarget, item: Gtk.Widget, x: float, y: float, trash_paintable: Gtk.Svg) -> bool:
    trash = target.get_widget()
    canvas = item.get_parent()

    trash_paintable.set_state(0)

    canvas.remove(item)

    trash.set_visible(False)

    return True


def enter_trash(target: Gtk.DropTarget, x: float, y: float, trash_paintable: Gtk.Svg) -> Gdk.DragAction:
    widget = target.get_widget()

    trash_paintable.set_frame_clock(widget.get_frame_clock())
    trash_paintable.set_state(1)
    return Gdk.DragAction.MOVE


def leave_trash(target: Gtk.DropTarget, trash_paintable: Gtk.Svg) -> None:
    trash_paintable.set_state(0)


def new_item_cb(button: Gtk.Button, canvas: Gtk.Fixed) -> None:
    popover = button.get_ancestor(Gtk.Popover)
    _, rect = popover.get_pointing_to()

    item = canvas_item_new()
    canvas.put(item, rect.x, rect.y)
    apply_transform(item)

    button.get_ancestor(Gtk.Popover).popdown()


def edit_cb(button: Gtk.Button | None, child: CanvasItem) -> None:
    item = child

    if button:
        button.get_ancestor(Gtk.Popover).popdown()

    if not canvas_item_is_editing(item):
        canvas_item_start_editing(item)


def delete_cb(button: Gtk.Button, child: Gtk.Widget) -> None:
    canvas = child.get_parent()

    canvas.remove(child)

    button.get_ancestor(Gtk.Popover).popdown()


def show_context_menu(widget: Gtk.Widget, child: Gtk.Widget | None, x: int, y: int) -> None:
    menu = Gtk.Popover()
    menu.set_parent(widget)
    menu.set_has_arrow(False)
    rect = Gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = x, y, 1, 1
    menu.set_pointing_to(rect)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    menu.set_child(box)

    item = Gtk.Button.new_with_label("New")
    item.set_has_frame(False)
    item.clicked.connect(new_item_cb, widget)
    box.append(item)

    item = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    box.append(item)

    item = Gtk.Button.new_with_label("Edit")
    item.set_has_frame(False)
    item.set_sensitive(child is not None and child != widget)
    item.clicked.connect(edit_cb, child)
    box.append(item)

    item = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    box.append(item)

    item = Gtk.Button.new_with_label("Delete")
    item.set_has_frame(False)
    item.set_sensitive(child is not None and child != widget)
    item.clicked.connect(delete_cb, child)
    box.append(item)

    menu.popup()


def pressed_cb(gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
    widget = gesture.get_widget()
    child = widget.pick(x, y, Gtk.PickFlags.DEFAULT)
    child = child.get_ancestor(CanvasItem) if child else None

    if gesture.get_current_event().triggers_context_menu():
        show_context_menu(widget, child, int(x), int(y))


def released_cb(gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
    widget = gesture.get_widget()
    child = widget.pick(x, y, Gtk.PickFlags.DEFAULT)

    if not child:
        return

    item = child.get_ancestor(CanvasItem)
    if not item:
        event = gesture.get_current_event()

        if event.get_event_type() == Gdk.EventType.TOUCH_END:
            show_context_menu(widget, None, int(x), int(y))

        return

    if gesture.get_current_button() == Gdk.BUTTON_PRIMARY:
        if canvas_item_is_editing(item):
            canvas_item_stop_editing(item)
        else:
            canvas_item_start_editing(item)


def canvas_new() -> Gtk.Fixed:
    canvas = Gtk.Fixed()
    canvas.set_hexpand(True)
    canvas.set_vexpand(True)

    source = Gtk.DragSource()
    source.set_actions(Gdk.DragAction.MOVE)
    source.prepare.connect(prepare)
    source.drag_begin.connect(drag_begin)
    source.drag_end.connect(drag_end)
    source.drag_cancel.connect(drag_cancel)
    canvas.add_controller(source)

    dest = Gtk.DropTarget.new(Gtk.Widget, Gdk.DragAction.MOVE)
    dest.drop.connect(drag_drop)
    canvas.add_controller(dest)

    gesture = Gtk.GestureClick()
    gesture.set_button(0)
    gesture.pressed.connect(pressed_cb)
    gesture.released.connect(released_cb)
    canvas.add_controller(gesture)

    trash_paintable = Gtk.Svg.new_from_resource("/dnd/user-trash-opening.gpa")
    trash_paintable.play()
    trash = Gtk.Image.new_from_paintable(trash_paintable)
    trash.set_pixel_size(64)
    trash.add_css_class("trash")

    canvas.put(trash, 20, 20)
    trash.set_visible(False)

    dest = Gtk.DropTarget.new(Gtk.Widget, Gdk.DragAction.MOVE)

    dest.enter.connect(enter_trash, trash_paintable)
    dest.leave.connect(leave_trash, trash_paintable)

    dest.drop.connect(drop_in_trash, trash_paintable)
    trash.add_controller(dest)
    canvas.trash = trash
    canvas.dragged_item = None

    return canvas


def css_drag_prepare(source: Gtk.DragSource, x: float, y: float, button: Gtk.Widget) -> Gdk.ContentProvider:
    class_ = button.css_class

    paintable = Gtk.WidgetPaintable.new(button)
    source.set_icon(paintable, 0, 0)

    return Gdk.ContentProvider.new_for_value(GObject.Value(GObject.TYPE_STRING, class_))


def css_button_new(class_: str) -> Gtk.Widget:
    button = Gtk.Image()
    button.set_size_request(48, 32)
    button.add_css_class(class_)
    button.css_class = class_

    source = Gtk.DragSource()
    source.prepare.connect(css_drag_prepare, button)
    button.add_controller(source)

    return button


class ColorSwatch(Gtk.Widget):
    __gtype_name__ = "ColorSwatch"

    def __init__(self) -> None:
        super().__init__()
        self.color = Gdk.RGBA()

        source = Gtk.DragSource()
        source.prepare.connect(color_swatch_drag_prepare, self)
        self.add_controller(source)

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        w = self.get_width()
        h = self.get_height()

        snapshot.append_color(self.color, Graphene.Rect().init(0, 0, w, h))

    def do_measure(self, orientation: Gtk.Orientation, for_size: int) -> tuple[int, int, int, int]:
        if orientation == Gtk.Orientation.HORIZONTAL:
            return 48, 48, -1, -1
        else:
            return 32, 32, -1, -1


ColorSwatch.set_css_name("colorswatch")


def color_swatch_drag_prepare(source: Gtk.DragSource, x: float, y: float,
                              swatch: ColorSwatch) -> Gdk.ContentProvider:
    return Gdk.ContentProvider.new_for_value(GObject.Value(Gdk.RGBA, swatch.color))


def color_swatch_new(color: str) -> ColorSwatch:
    swatch = ColorSwatch()

    swatch.color.parse(color)

    return swatch


# The window, held weakly as g_object_add_weak_pointer() holds it in C: GTK keeps a window until it is
# destroyed, so a strong reference here would keep a destroyed window around.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref, n_items
    window = window_ref()
    if window is None:
        colors = [
            "red", "green", "blue", "magenta", "orange", "gray", "black", "yellow",
            "white", "gray", "brown", "pink", "cyan", "bisque", "gold", "maroon",
            "navy", "orchid", "olive", "peru", "salmon", "silver", "wheat",
        ]

        button = Gtk.ColorDialogButton.new(Gtk.ColorDialog())
        del button

        provider = Gtk.CssProvider()
        provider.load_from_resource("/dnd/dnd.css")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)

        css = ""
        for color in colors:
            css += f".canvasitem.{color} {{ background: {color}; }}\n"

        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, 800)

        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Drag-and-Drop")
        window.set_default_size(640, 480)
        window_ref = window.weak_ref()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        window.set_child(box)

        box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.append(box2)

        canvas = canvas_new()
        box2.append(canvas)

        n_items = 0

        x = 150
        y = 100
        for i in range(3):
            item = canvas_item_new()
            canvas.put(item, x, y)
            apply_transform(item)

            x += 150
            y += 100

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        box.append(sw)

        box3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box3.add_css_class("linked")
        sw.set_child(box3)

        for color in colors:
            box3.append(color_swatch_new(color))

        box3.append(css_button_new("rainbow1"))
        box3.append(css_button_new("rainbow2"))
        box3.append(css_button_new("rainbow3"))

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
