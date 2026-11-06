from PyLiite4 import Gtk, GtkSource

from demos.workbench import workbench

# Workbench already does this, so it isn't strictly needed here, but an application has to call it once during
# startup, for example in the Gio.Application's startup handler.
GtkSource.init()

# Workbench's Blueprint declares this view; it's built here because GtkSource's types exist only once it's imported.
buffer = GtkSource.Buffer()
scrolled_window: Gtk.ScrolledWindow = workbench.builder.get_object("scrolled_window")
scrolled_window.set_child(
    GtkSource.View(auto_indent=True, indent_width=2, show_line_numbers=True, monospace=True, buffer=buffer)
)

# The buffer's language sets its syntax highlighting.
language_manager = GtkSource.LanguageManager.get_default()
language = language_manager.get_language("js")
buffer.set_language(language)

# The buffer holds the text that the SourceView shows.
buffer.set_text('print "Hello World"', -1)
