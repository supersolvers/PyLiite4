from PyLiite4 import Gdk, Gio, GLib, Gtk

from demos.workbench import workbench

box_menu_parent: Gtk.Box = workbench.builder.get_object("box_menu_parent")
label_emoji: Gtk.Label = workbench.builder.get_object("label_emoji")
gesture_click: Gtk.GestureClick = workbench.builder.get_object("gesture_click")
popover_menu: Gtk.PopoverMenu = workbench.builder.get_object("popover_menu")


def on_right_click(x: float, y: float) -> None:
    position = Gdk.Rectangle()
    position.x = x
    position.y = y
    popover_menu.set_pointing_to(position)
    popover_menu.popup()


gesture_click.pressed.connect(lambda _gesture, _n_press, x, y: on_right_click(x, y))

mood_group = Gio.SimpleActionGroup()
box_menu_parent.insert_action_group("mood", mood_group)


def on_action(parameter: GLib.Variant) -> None:
    emoji = parameter.get_string()
    label_emoji.set_label(emoji)


emoji_action = Gio.SimpleAction(
    name="emoji",
    parameter_type=GLib.VariantType("s"),
)

emoji_action.activate.connect(lambda _action, parameter: on_action(parameter))
mood_group.add_action(emoji_action)
