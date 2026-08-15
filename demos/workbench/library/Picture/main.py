from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

picture_fill: Gtk.Picture = workbench.builder.get_object("picture_fill")
picture_contain: Gtk.Picture = workbench.builder.get_object("picture_contain")
picture_cover: Gtk.Picture = workbench.builder.get_object("picture_cover")
picture_scale_down: Gtk.Picture = workbench.builder.get_object("picture_scale_down")

file = Gio.File.new_for_uri(workbench.resolve("./keys.png"))

picture_fill.set_file(file)
picture_contain.set_file(file)
picture_cover.set_file(file)
picture_scale_down.set_file(file)
