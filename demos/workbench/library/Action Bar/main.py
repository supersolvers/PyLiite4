from PyLiite4 import Gtk

from demos.workbench import workbench

action_bar: Gtk.ActionBar = workbench.builder.get_object("action_bar")
button: Gtk.ToggleButton = workbench.builder.get_object("button")
start_widget: Gtk.Button = workbench.builder.get_object("start_widget")
end_widget: Gtk.Button = workbench.builder.get_object("end_widget")

button.notify["active"].connect(lambda *_: action_bar.set_revealed(not button.get_active()))

start_widget.clicked.connect(lambda *_: print("Start widget"))

end_widget.clicked.connect(lambda *_: print("End widget"))
