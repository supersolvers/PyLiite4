from PyLiite4 import Adw, Gdk, Gio, GObject, Gtk

from demos.workbench import workbench


def create_box_widget() -> Gtk.Box:
    return Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
        spacing=6,
        margin_top=12,
        margin_bottom=12,
        margin_start=12,
        margin_end=12,
    )


def create_video_preview(file: Gio.File) -> Gtk.Box:
    widget = create_box_widget()
    video = Gtk.Video(file=file)
    widget.append(video)
    return widget


def create_text_preview(text: str) -> Gtk.Box:
    widget = create_box_widget()

    label = Gtk.Label(label=text, wrap=True)
    widget.append(label)
    return widget


def create_image_preview(value: Gio.File) -> Gtk.Box:
    widget = create_box_widget()

    picture = Gtk.Picture.new_for_file(value)
    picture.can_shrink = True
    picture.content_fit = Gtk.ContentFit.SCALE_DOWN
    widget.append(picture)
    return widget


def create_file_preview(file: Gio.File) -> Gtk.Box:
    widget = create_box_widget()

    file_info = file.query_info("standard::icon", 0, None)
    icon = Gtk.Image.new_from_gicon(file_info.get_icon())
    widget.append(icon)
    icon.icon_size = Gtk.IconSize.LARGE

    file_name = Gtk.Label(label=file.get_basename())
    widget.append(file_name)

    return widget


def on_drop(value: Gio.File) -> Gtk.Box | bool:
    if not isinstance(value, Gio.File):
        return False

    file_info = value.query_info("standard::content-type", 0, None)
    content_type = file_info.get_content_type()

    if content_type.startswith("image/"):
        return create_image_preview(value)
    elif content_type.startswith("video/"):
        return create_video_preview(value)
    else:
        return create_file_preview(value)


def on_string_drop(_self: Gtk.DropTarget, value: str, _x: float, _y: float) -> None:
    bin.set_child(create_text_preview(value))
    bin.remove_css_class("overlay-drag-area")


def on_file_drop(_self: Gtk.DropTarget, value: Gio.File, _x: float, _y: float) -> None:
    try:
        bin.set_child(on_drop(value))
    except Exception as err:
        print(err, "Unable to load preview")
    bin.remove_css_class("overlay-drag-area")


def add_class(cl: str) -> bool:
    bin.add_css_class(cl)
    return True


bin: Adw.Bin = workbench.builder.get_object("bin")

# Universal drop target for any String data
string_drop_target = Gtk.DropTarget.new(
    GObject.TYPE_STRING,
    Gdk.DragAction.COPY,
)

bin.add_controller(string_drop_target)

string_drop_target.drop.connect(on_string_drop)

# Drop Target for Files
file_drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
bin.add_controller(file_drop_target)
file_drop_target.drop.connect(on_file_drop)


# Drop Hover Effect

file_drop_target.enter.connect(lambda _target, _x, _y: add_class("overlay-drag-area"))

file_drop_target.leave.connect(lambda _target: bin.remove_css_class("overlay-drag-area"))

string_drop_target.enter.connect(lambda _target, _x, _y: add_class("overlay-drag-area"))

string_drop_target.leave.connect(lambda _target: bin.remove_css_class("overlay-drag-area"))
