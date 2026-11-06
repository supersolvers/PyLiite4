"""Entry/Completion

GtkEntryCompletion provides a mechanism for adding support for
completion in GtkEntry.
"""

from collections.abc import Callable

from PyLiite4 import Gtk

# The window, held weakly as g_object_add_weak_pointer() holds it in C: GTK keeps a window until it is
# destroyed, so a strong reference here would keep a destroyed window around.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


# Creates a tree model containing the completions.
def create_completion_model() -> Gtk.TreeModel:
    strings = [
        "GNOME",
        "gnominious",
        "Gnomonic projection",
        "Gnosophy",
        "total",
        "totally",
        "toto",
        "tottery",
        "totterer",
        "Totten trust",
        "Tottenham hotspurs",
        "totipotent",
        "totipotency",
        "totemism",
        "totem pole",
        "Totara",
        "totalizer",
        "totalizator",
        "totalitarianism",
        "total parenteral nutrition",
        "total eclipse",
        "Totipresence",
        "Totipalmi",
        "zombie",
        "aæx",
        "aæy",
        "aæz",
    ]

    store = Gtk.ListStore(str)

    for string in strings:
        iter = store.append()
        store.set(iter, 0, string)

    return store


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Completion")
        window.set_resizable(False)
        window_ref = window.weak_ref()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_start(18)
        vbox.set_margin_end(18)
        vbox.set_margin_top(18)
        vbox.set_margin_bottom(18)
        window.set_child(vbox)

        label = Gtk.Label()
        label.set_markup("Try writing <b>total</b> or <b>gnome</b> for example.")
        vbox.append(label)

        entry = Gtk.Entry()
        vbox.append(entry)

        entry.update_relation([Gtk.AccessibleRelation.LABELLED_BY], [[label]])
        entry.update_property([Gtk.AccessibleProperty.AUTOCOMPLETE], [Gtk.AccessibleAutocomplete.LIST])

        completion = Gtk.EntryCompletion()

        entry.set_completion(completion)

        completion_model = create_completion_model()
        completion.set_model(completion_model)

        completion.set_text_column(0)

        completion.set_inline_completion(True)
        completion.set_inline_selection(True)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
