"""DemoImage, an image that can be copied, pasted and dragged, from the GTK Demo's demoimage.c."""

from gettext import gettext as _

from PyLiite4 import Gdk, Gio, GLib, GObject, Gtk


def get_image_paintable(image: Gtk.Image) -> Gdk.Paintable | None:
    storage_type = image.get_storage_type()
    if storage_type == Gtk.ImageType.PAINTABLE:
        return image.get_paintable()
    if storage_type == Gtk.ImageType.ICON_NAME:
        icon_name = image.get_icon_name()
        icon_theme = Gtk.IconTheme.get_for_display(image.get_display())
        icon = icon_theme.lookup_icon(icon_name,
                                      None,
                                      48, 1,
                                      image.get_direction(),
                                      0)
        if icon is None:
            return None
        return icon

    GLib.log_default_handler("Gtk", GLib.LogLevelFlags.LEVEL_WARNING,
                             f"Image storage type {int(storage_type)} not handled")
    return None


def update_drag_icon(demo: "DemoImage", icon: Gtk.DragIcon) -> None:
    storage_type = demo.image.get_storage_type()
    if storage_type == Gtk.ImageType.PAINTABLE:
        paintable = demo.image.get_paintable()
        image = Gtk.Image.new_from_paintable(paintable)
    elif storage_type == Gtk.ImageType.ICON_NAME:
        icon_name = demo.image.get_icon_name()
        image = Gtk.Image.new_from_icon_name(icon_name)
    else:
        GLib.log_default_handler("Gtk", GLib.LogLevelFlags.LEVEL_WARNING,
                                 f"Image storage type {int(storage_type)} not handled")
        return

    image.set_pixel_size(demo.image.get_pixel_size())

    icon.set_child(image)


def drag_begin(source: Gtk.DragSource, drag: Gdk.Drag) -> None:
    demo = source.get_widget()

    update_drag_icon(demo, Gtk.DragIcon.get_for_drag(drag))


def prepare_drag(source: Gtk.DragSource, x: float, y: float) -> Gdk.ContentProvider:
    demo = source.get_widget()
    paintable = get_image_paintable(demo.image)

    # Textures can be serialized and paintables can't, so textures are a special case.
    # (gdk_content_provider_new_typed() takes varargs; new_for_value() with a typed GValue does the same.)
    if isinstance(paintable, Gdk.Texture):
        return Gdk.ContentProvider.new_for_value(GObject.Value(Gdk.Texture, paintable))
    else:
        return Gdk.ContentProvider.new_for_value(GObject.Value(Gdk.Paintable, paintable))


def drag_drop(dest: Gtk.DropTarget, value: Gdk.Paintable, x: float, y: float) -> bool:
    demo = dest.get_widget()
    paintable = value

    demo.image.set_from_paintable(paintable)

    return True


def copy_image(widget: "DemoImage", action_name: str, parameter: GLib.Variant | None) -> None:
    clipboard = widget.get_clipboard()
    demo = widget
    paintable = get_image_paintable(demo.image)

    # Textures can be serialized and paintables can't, so textures are a special case.
    if isinstance(paintable, Gdk.Texture):
        value = GObject.Value(Gdk.Texture, paintable)
    else:
        value = GObject.Value(Gdk.Paintable, paintable)
    clipboard.set(value)


def paste_image_cb(clipboard: Gdk.Clipboard, result: Gio.AsyncResult, demo: "DemoImage") -> None:
    try:
        value = clipboard.read_value_finish(result)
    except GLib.Error:
        value = None
    if value is None:
        demo.error_bell()
        return

    demo.image.set_from_paintable(value)


def paste_image(widget: "DemoImage", action_name: str, parameter: GLib.Variant | None) -> None:
    clipboard = widget.get_clipboard()

    if clipboard.get_formats().contain_gtype(Gdk.Texture.__gtype__):
        type = Gdk.Texture.__gtype__
    else:
        type = Gdk.Paintable.__gtype__

    clipboard.read_value_async(type,
                               GLib.PRIORITY_DEFAULT,
                               None,
                               paste_image_cb,
                               widget)


def pressed_cb(gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
    demo = gesture.get_widget()

    demo.popover.popup()


class DemoImage(Gtk.Widget):
    __gtype_name__ = "DemoImage"

    def __init__(self, **properties: object) -> None:
        self.image = Gtk.Image()
        self.image.set_pixel_size(48)

        super().__init__(**properties)

        self.image.set_parent(self)

        menu = Gio.Menu()
        item = Gio.MenuItem.new(_("_Copy"), "clipboard.copy")
        menu.append_item(item)

        item = Gio.MenuItem.new(_("_Paste"), "clipboard.paste")
        menu.append_item(item)

        self.popover = Gtk.PopoverMenu.new_from_model(menu)
        self.popover.set_parent(self)

        source = Gtk.DragSource()
        source.prepare.connect(prepare_drag)
        source.drag_begin.connect(drag_begin)
        self.add_controller(source)

        dest = Gtk.DropTarget.new(Gdk.Paintable.__gtype__, Gdk.DragAction.COPY)
        dest.drop.connect(drag_drop)
        self.add_controller(dest)

        gesture = Gtk.GestureClick()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.pressed.connect(pressed_cb)
        self.add_controller(gesture)

    def do_dispose(self) -> None:
        if self.image is not None:
            self.image.unparent()
            self.image = None
        if self.popover is not None:
            self.popover.unparent()
            self.popover = None

        Gtk.Widget.do_dispose(self)

    @GObject.Property(type=str, nick="Icon name", blurb="Icon name")
    def icon_name(self) -> str | None:
        return self.image.get_icon_name()

    @icon_name.setter
    def icon_name(self, value: str | None) -> None:
        self.image.set_from_icon_name(value)


DemoImage.set_layout_manager_type(Gtk.BinLayout)
DemoImage.install_action("clipboard.copy", None, copy_image)
DemoImage.install_action("clipboard.paste", None, paste_image)


def demo_image_new(icon_name: str) -> DemoImage:
    return DemoImage(icon_name=icon_name)
