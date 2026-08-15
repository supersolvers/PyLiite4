from PyLiite4 import Gtk

from demos.workbench import workbench

shortcuts_window: Gtk.ShortcutsWindow = workbench.builder.get_object("shortcuts_window")
button: Gtk.Button = workbench.builder.get_object("button")

button.clicked.connect(lambda *_: shortcuts_window.present())
