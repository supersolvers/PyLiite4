from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

picture_one: Gtk.Picture = workbench.builder.get_object("picture_one")
picture_two: Gtk.Picture = workbench.builder.get_object("picture_two")

file: Gio.File = Gio.File.new_for_uri(workbench.resolve("./image.png"))

picture_one.set_file(file)
picture_two.set_file(file)
