import math

from PyLiite4 import GObject, Gtk

from demos.workbench import workbench

bar_continuous: Gtk.LevelBar = workbench.builder.get_object("bar_continuous")

bar_continuous.add_offset_value("full", 100)
bar_continuous.add_offset_value("half", 50)
bar_continuous.add_offset_value("low", 25)

bar_discrete: Gtk.LevelBar = workbench.builder.get_object("bar_discrete")

bar_discrete.add_offset_value("very-weak", 1)
bar_discrete.add_offset_value("weak", 2)
bar_discrete.add_offset_value("moderate", 4)
bar_discrete.add_offset_value("strong", 6)

entry: Gtk.PasswordEntry = workbench.builder.get_object("entry")
label_strength: Gtk.Label = workbench.builder.get_object("label_strength")


# This is not a secure way to estimate password strength
# Use appropriate solutions instead
# such as https://github.com/dropbox/zxcvbn
def estimate_password_strength(_entry: Gtk.PasswordEntry, _text: GObject.ParamSpec) -> None:
    level = min(math.ceil(len(entry.get_text()) / 2), 6)

    match level:
        case 1:
            label_strength.set_label("Very Weak")
            label_strength.set_css_classes(["very-weak-label"])
        case 2:
            label_strength.set_label("Weak")
            label_strength.set_css_classes(["weak-label"])
        case 3 | 4:
            label_strength.set_label("Moderate")
            label_strength.set_css_classes(["moderate-label"])
        case 5 | 6:
            label_strength.set_label("Strong")
            label_strength.set_css_classes(["strong-label"])
        case _:
            label_strength.set_label("")
            label_strength.set_css_classes([])

    bar_discrete.set_value(level)


entry.notify["text"].connect(estimate_password_strength)
