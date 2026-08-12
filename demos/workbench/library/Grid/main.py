from random import randint

from PyLiite4 import Gtk

from demos.workbench import workbench

button_ids = [
    "button00",
    "button01",
    "button02",
    "button10",
    "button11",
    "button12",
    "button20",
    "button21",
    "button22",
]


def on_clicked(button: Gtk.Button) -> None:
    global step
    # check access for user action
    image: Gtk.Image = button.get_child()
    if image.get_icon_name():
        return
    # store and show user action
    image.set_from_icon_name("cross-large-symbolic")
    # calculate pc reaction
    pc_is_thinking = True
    while pc_is_thinking:
        pc_is_thinking_row = str(randint(0, 2))
        pc_is_thinking_col = str(randint(0, 2))
        # make pc reaction if possible
        temp: Gtk.Button = workbench.builder.get_object(
            f"button{pc_is_thinking_row}{pc_is_thinking_col}"
        )
        temp_image: Gtk.Image = temp.get_child()
        if not temp_image.get_icon_name():
            # store and show pc reaction
            temp_image.set_from_icon_name("circle-outline-thick-symbolic")
            pc_is_thinking = False
            step += 2

        if step >= 8:
            pc_is_thinking = False


for id in button_ids:
    button: Gtk.Button = workbench.builder.get_object(id)
    button.clicked.connect(on_clicked)

step = 1
