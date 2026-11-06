from PyLiite4 import Adw, Gdk, GObject, Gtk

from demos.workbench import workbench


def on_drop(_drop: Gtk.DropTarget, value: Gtk.ListBoxRow, _x: float, y: float) -> bool:
    target_row = list.get_row_at_y(y)
    target_index = target_row.get_index()

    # A drop without a value or a target row isn't accepted.
    if not value or not target_row:
        return False

    list.remove(value)
    list.insert(value, target_index)
    target_row.set_state_flags(Gtk.StateFlags.NORMAL, True)

    # Returning True accepts the drop.
    return True


def on_prepare(_source: Gtk.DragSource, x: float, y: float, row: Adw.ActionRow) -> Gdk.ContentProvider:
    global drag_x, drag_y
    drag_x = x
    drag_y = y

    value = GObject.Value()
    value.init(Gtk.ListBoxRow)
    value.set_object(row)

    return Gdk.ContentProvider.new_for_value(value)


def on_drag_begin(_source: Gtk.DragSource, drag: Gdk.Drag, row: Adw.ActionRow) -> None:
    global drag_x, drag_y
    allocation = row.get_allocation()
    drag_widget = Gtk.ListBox()

    drag_widget.set_size_request(allocation.width, allocation.height)
    drag_widget.add_css_class("boxed-list")

    drag_row = Adw.ActionRow(title=row.get_title())
    drag_row.add_prefix(
        Gtk.Image(
            icon_name="list-drag-handle-symbolic",
            css_classes=["dim-label"],
        ),
    )

    drag_widget.append(drag_row)
    drag_widget.drag_highlight_row(drag_row)

    icon = Gtk.DragIcon.get_for_drag(drag)
    icon.set_child(drag_widget)

    drag.set_hotspot(drag_x, drag_y)


list: Gtk.ListBox = workbench.builder.get_object("list")
drop_target = Gtk.DropTarget.new(Gtk.ListBoxRow, Gdk.DragAction.MOVE)

list.add_controller(drop_target)

# Each row is a drag source, and is highlighted while a drag is over it.
for row in list:
    drop_controller = Gtk.DropControllerMotion()

    drag_source = Gtk.DragSource(
        actions=Gdk.DragAction.MOVE,
    )

    row.add_controller(drag_source)
    row.add_controller(drop_controller)

    # Dragging
    drag_source.prepare.connect(on_prepare, row)

    drag_source.drag_begin.connect(on_drag_begin, row)

    # The row under a drag is highlighted.
    drop_controller.enter.connect(lambda _target, _x, _y, row: list.drag_highlight_row(row), row)

    drop_controller.leave.connect(lambda _target: list.drag_unhighlight_row())


# Dropping
drop_target.drop.connect(on_drop)
