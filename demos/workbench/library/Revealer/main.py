from PyLiite4 import Gio, Gtk

from demos.workbench import workbench

button_slide: Gtk.ToggleButton = workbench.builder.get_object("button_slide")
button_crossfade: Gtk.ToggleButton = workbench.builder.get_object("button_crossfade")
revealer_slide: Gtk.Revealer = workbench.builder.get_object("revealer_slide")
revealer_crossfade: Gtk.Revealer = workbench.builder.get_object("revealer_crossfade")
image1: Gtk.Picture = workbench.builder.get_object("image1")
image2: Gtk.Picture = workbench.builder.get_object("image2")

image1.set_file(Gio.File.new_for_uri(workbench.resolve("./image1.png")))
image2.set_file(Gio.File.new_for_uri(workbench.resolve("./image2.png")))

button_slide.toggled.connect(lambda *_: revealer_slide.set_reveal_child(button_slide.get_active()))

button_crossfade.toggled.connect(lambda *_: revealer_crossfade.set_reveal_child(button_crossfade.get_active()))

revealer_slide.notify["child-revealed"].connect(
    lambda *_: print("Slide Revealer Shown" if revealer_slide.get_child_revealed() else "Slide Revealer Hidden")
)
