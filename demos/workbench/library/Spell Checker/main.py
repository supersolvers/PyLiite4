from PyLiite4 import Gtk, GtkSource, Spelling  # type: ignore[attr-defined]  # PyLiite4 doesn't provide Spelling

from demos.workbench import workbench

GtkSource.init()

buffer: GtkSource.Buffer = workbench.builder.get_object("buffer")
text_view: Gtk.TextView = workbench.builder.get_object("text_view")

# Spell checking
checker = Spelling.Checker.get_default()
checker.set_language("en_US")
adapter = Spelling.TextBufferAdapter.new(buffer, checker)
extra_menu = adapter.get_menu_model()

text_view.set_extra_menu(extra_menu)
text_view.insert_action_group("spelling", adapter)

adapter.set_enabled(True)
