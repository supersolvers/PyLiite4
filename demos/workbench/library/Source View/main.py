from PyLiite4 import Gtk, GtkSource

from demos.workbench import workbench

# Strictly speaking we don't _have_ to do this here since WorkBench does this for us.
# However, you _have_ to call this once during the startup in your application - e.g. in GApplication::startup
GtkSource.init()

# Workbench's Blueprint declares this view; it's built here because GtkSource's types exist only once it's imported.
buffer = GtkSource.Buffer()
scrolled_window: Gtk.ScrolledWindow = workbench.builder.get_object("scrolled_window")
scrolled_window.set_child(
    GtkSource.View(auto_indent=True, indent_width=2, show_line_numbers=True, monospace=True, buffer=buffer)
)

# Set the language we want to use
language_manager = GtkSource.LanguageManager.get_default()
language = language_manager.get_language("js")
buffer.set_language(language)

# The buffer holds the text that's used in the SourceView
buffer.set_text('print "Hello World"', -1)
