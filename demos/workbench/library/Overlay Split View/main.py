from PyLiite4 import Adw, Gtk

from demos.workbench import workbench

split_view: Adw.OverlaySplitView = workbench.builder.get_object("split_view")
start_toggle: Gtk.ToggleButton = workbench.builder.get_object("start_toggle")
end_toggle: Gtk.ToggleButton = workbench.builder.get_object("end_toggle")

start_toggle.toggled.connect(lambda _toggle: split_view.set_sidebar_position(Gtk.PackType.START))

end_toggle.toggled.connect(lambda _toggle: split_view.set_sidebar_position(Gtk.PackType.END))
