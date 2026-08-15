from PyLiite4 import Gtk

from demos.workbench import workbench

basic_label: Gtk.Label = workbench.builder.get_object("basic_label")

basic_label.add_css_class("my_custom_class")
