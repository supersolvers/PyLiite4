from PyLiite4 import Gtk

from demos.workbench import workbench

checkbox_1: Gtk.CheckButton = workbench.builder.get_object("checkbox_1")
checkbox_2: Gtk.CheckButton = workbench.builder.get_object("checkbox_2")

checkbox_1.toggled.connect(
    lambda *_: print(
        "Notifications Enabled" if checkbox_1.get_active() else "Notifications Disabled"
    ),
)

checkbox_2.toggled.connect(
    lambda *_: print(
        "Changes will be auto-saved"
        if checkbox_2.get_active()
        else "Changes will not be auto-saved"
    ),
)
