from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

path: str = Gio.File.new_for_uri(workbench.resolve("workbench.png")).get_path()

icon1: Gtk.Image = workbench.builder.get_object("icon1")
icon1.set_from_file(path)
icon2: Gtk.Image = workbench.builder.get_object("icon2")
icon2.set_from_file(path)
icon3: Gtk.Image = workbench.builder.get_object("icon3")
icon3.set_from_file(path)
