"""Entry/Undo and Redo

GtkEntry can provide basic Undo/Redo support using standard keyboard
accelerators such as Control+z to undo and Control+Shift+z to redo.
Additionally, Control+y can be used to redo.

Use gtk_entry_set_enable_undo() to enable undo/redo support.
"""

from collections.abc import Callable

from PyLiite4 import Gtk

# The window, held weakly as g_object_add_weak_pointer() holds it in C: GTK keeps a window until it is
# destroyed, so a strong reference here would keep a destroyed window around.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Undo and Redo")
        window.set_resizable(False)
        window_ref = window.weak_ref()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_start(18)
        vbox.set_margin_end(18)
        vbox.set_margin_top(18)
        vbox.set_margin_bottom(18)
        window.set_child(vbox)

        label = Gtk.Label()
        label.set_markup("Use Control+z or Control+Shift+z to undo or redo changes")
        vbox.append(label)

        # Create our entry
        entry = Gtk.Entry()
        entry.set_enable_undo(True)
        vbox.append(entry)

        entry.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
