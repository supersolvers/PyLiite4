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
    # A square with an icon has already been played.
    image: Gtk.Image = button.get_child()
    if image.get_icon_name():
        return
    # The player's move is a cross.
    image.set_from_icon_name("cross-large-symbolic")
    # The computer answers on a random free square.
    pc_is_thinking = True
    while pc_is_thinking:
        pc_is_thinking_row = str(randint(0, 2))
        pc_is_thinking_col = str(randint(0, 2))
        temp: Gtk.Button = workbench.builder.get_object(
            f"button{pc_is_thinking_row}{pc_is_thinking_col}"
        )
        temp_image: Gtk.Image = temp.get_child()
        if not temp_image.get_icon_name():
            # The computer's move is a circle.
            temp_image.set_from_icon_name("circle-outline-thick-symbolic")
            pc_is_thinking = False
            step += 2

        if step >= 8:
            pc_is_thinking = False


for id in button_ids:
    button: Gtk.Button = workbench.builder.get_object(id)
    button.clicked.connect(on_clicked)

step = 1
