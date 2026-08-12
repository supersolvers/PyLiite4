from PyLiite4 import Gtk

from demos.workbench import workbench

interactive_box: Gtk.Box = workbench.builder.get_object("interactive_box")
button_append: Gtk.Button = workbench.builder.get_object("button_append")
button_prepend: Gtk.Button = workbench.builder.get_object("button_prepend")
button_remove: Gtk.Button = workbench.builder.get_object("button_remove")

count = 0


def append(_button: Gtk.Button | None = None) -> None:
    global count
    label = Gtk.Label(
        name="card",
        label=f"Item {count + 1}",
        css_classes=["card"],
    )
    interactive_box.append(label)
    count += 1


def prepend(_button: Gtk.Button) -> None:
    global count
    label = Gtk.Label(
        name="card",
        label=f"Item {count + 1}",
        css_classes=["card"],
    )
    interactive_box.prepend(label)
    count += 1


def remove(_button: Gtk.Button) -> None:
    global count
    if count:
        interactive_box.remove(interactive_box.get_last_child())
        count -= 1
    else:
        print("The box has no child widget to remove")


button_append.clicked.connect(append)
button_prepend.clicked.connect(prepend)
button_remove.clicked.connect(remove)


def on_horizontal_toggled(_check_button: Gtk.ToggleButton) -> None:
    if toggle_orientation_horizontal.get_active():
        interactive_box.set_orientation(Gtk.Orientation.HORIZONTAL)


def on_vertical_toggled(_check_button: Gtk.ToggleButton) -> None:
    if toggle_orientation_vertical.get_active():
        interactive_box.set_orientation(Gtk.Orientation.VERTICAL)


def on_highlight_toggled(_check_button: Gtk.CheckButton) -> None:
    if highlight.get_active():
        interactive_box.add_css_class("border")
    else:
        interactive_box.remove_css_class("border")


def on_hfill_toggled(_check_button: Gtk.ToggleButton) -> None:
    if halign_toggle_fill.get_active():
        interactive_box.set_halign(Gtk.Align.FILL)


def on_hstart_toggled(_check_button: Gtk.ToggleButton) -> None:
    if halign_toggle_start.get_active():
        interactive_box.set_halign(Gtk.Align.START)


def on_hcenter_toggled(_check_button: Gtk.ToggleButton) -> None:
    if halign_toggle_center.get_active():
        interactive_box.set_halign(Gtk.Align.CENTER)


def on_hend_toggled(_check_button: Gtk.ToggleButton) -> None:
    if halign_toggle_end.get_active():
        interactive_box.set_halign(Gtk.Align.END)


def on_vfill_toggled(_check_button: Gtk.ToggleButton) -> None:
    if valign_toggle_fill.get_active():
        interactive_box.set_valign(Gtk.Align.FILL)


def on_vstart_toggled(_check_button: Gtk.ToggleButton) -> None:
    if valign_toggle_start.get_active():
        interactive_box.set_valign(Gtk.Align.START)


def on_vcenter_toggled(_check_button: Gtk.ToggleButton) -> None:
    if valign_toggle_center.get_active():
        interactive_box.set_valign(Gtk.Align.CENTER)


def on_vend_toggled(_check_button: Gtk.ToggleButton) -> None:
    if valign_toggle_end.get_active():
        interactive_box.set_valign(Gtk.Align.END)


toggle_orientation_horizontal: Gtk.ToggleButton = workbench.builder.get_object(
    "toggle_orientation_horizontal",
)
toggle_orientation_vertical: Gtk.ToggleButton = workbench.builder.get_object(
    "toggle_orientation_vertical",
)
toggle_orientation_horizontal.toggled.connect(on_horizontal_toggled)
toggle_orientation_vertical.toggled.connect(on_vertical_toggled)

highlight: Gtk.CheckButton = workbench.builder.get_object("highlight")
highlight.toggled.connect(on_highlight_toggled)

halign_toggle_fill: Gtk.ToggleButton = workbench.builder.get_object("halign_toggle_fill")
halign_toggle_start: Gtk.ToggleButton = workbench.builder.get_object("halign_toggle_start")
halign_toggle_center: Gtk.ToggleButton = workbench.builder.get_object("halign_toggle_center")
halign_toggle_end: Gtk.ToggleButton = workbench.builder.get_object("halign_toggle_end")

halign_toggle_fill.toggled.connect(on_hfill_toggled)
halign_toggle_start.toggled.connect(on_hstart_toggled)
halign_toggle_center.toggled.connect(on_hcenter_toggled)
halign_toggle_end.toggled.connect(on_hend_toggled)

valign_toggle_fill: Gtk.ToggleButton = workbench.builder.get_object("valign_toggle_fill")
valign_toggle_start: Gtk.ToggleButton = workbench.builder.get_object("valign_toggle_start")
valign_toggle_center: Gtk.ToggleButton = workbench.builder.get_object("valign_toggle_center")
valign_toggle_end: Gtk.ToggleButton = workbench.builder.get_object("valign_toggle_end")

valign_toggle_fill.toggled.connect(on_vfill_toggled)
valign_toggle_start.toggled.connect(on_vstart_toggled)
valign_toggle_center.toggled.connect(on_vcenter_toggled)
valign_toggle_end.toggled.connect(on_vend_toggled)


append()
