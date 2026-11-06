# Pango is a text layout library; one of its uses is formatting text.
# https://gjs-docs.gnome.org/pango10~1.0/
from PyLiite4 import Gtk, Pango

from demos.workbench import workbench

label: Gtk.Label = workbench.builder.get_object("label")


def update_attributes() -> None:
    # A Pango.AttrList styles the label.
    label.set_attributes(rainbow_attributes(label.get_label()))


# Builds a Pango.AttrList that styles the label in rainbow colors. It takes the text to know its length and where its
# spaces are.
def rainbow_attributes(text: str) -> Pango.AttrList:
    rainbow_colors = (
        "#D00",
        "#C50",
        "#E90",
        "#090",
        "#24E",
        "#55E",
        "#C3C",
    )

    # The colors, repeated until there's one for every letter.
    color_array: list[str] = []
    i = 0
    while i < len(text):
        color_array += rainbow_colors
        i = len(color_array)

    # A counter separate from `i` in the loop below, so that spaces don't "consume" a color.
    color_idx = 0

    attr_list_string = ""
    for i in range(len(text)):
        if text[i] != " ":
            start_idx = i
            end_idx = i + 1

            color = color_array[color_idx]
            color_idx += 1
            # The format of this string is linked below.
            attr_list_string += f"{start_idx} {end_idx} foreground {color},"

    # The string's syntax is described at
    # https://docs.gtk.org/Pango/method.AttrList.to_string.html
    return Pango.attr_list_from_string(attr_list_string)


label.notify["label"].connect(lambda _, __: update_attributes())
update_attributes()
