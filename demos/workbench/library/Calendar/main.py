from PyLiite4 import Gtk

from demos.workbench import workbench

calendar: Gtk.Calendar = workbench.builder.get_object("calendar")

# calendar.get_date() returns a GLib.DateTime.
# https://docs.gtk.org/glib/struct.DateTime.html

calendar.notify["day"].connect(lambda *_: print(calendar.get_date().format("%e")))

calendar.notify["month"].connect(lambda *_: print(calendar.get_date().format("%B")))

calendar.notify["year"].connect(lambda *_: print(calendar.get_date().format("%Y")))

calendar.day_selected.connect(lambda *_: print(calendar.get_date().format_iso8601()))

calendar.mark_day(15)
