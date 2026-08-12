from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

file: Gio.File = Gio.File.new_for_uri(workbench.resolve("./image.png"))

picture: Gtk.Picture = workbench.builder.get_object("picture")
picture.set_file(file)
