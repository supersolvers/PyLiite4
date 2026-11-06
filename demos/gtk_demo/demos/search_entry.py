"""Entry/Search Entry

GtkSearchEntry provides an entry that is ready for search.

Search entries have their "search-changed" signal delayed and
should be used when the search operation is slow, such as big
datasets to search, or online searches.

GtkSearchBar allows have a hidden search entry that 'springs
into action' upon keyboard input.
"""

from PyLiite4 import GObject, Gtk


def search_changed_cb(entry: Gtk.SearchEntry, result_label: Gtk.Label) -> None:
    text = entry.get_text()
    result_label.set_text(text or "")


window: Gtk.Window | None = None


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_title("Type to Search")
        window.set_transient_for(do_widget)
        window.set_resizable(False)
        window.set_size_request(200, -1)
        window.destroy.connect(destroyed)

        header = Gtk.HeaderBar()
        window.set_titlebar(header)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        window.set_child(vbox)

        entry = Gtk.SearchEntry()
        entry.set_halign(Gtk.Align.CENTER)
        searchbar = Gtk.SearchBar()
        searchbar.connect_entry(entry)
        searchbar.set_show_close_button(False)
        searchbar.set_child(entry)
        vbox.append(searchbar)

        # Typing in the window goes to the search bar.
        searchbar.set_key_capture_widget(window)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        box.set_margin_start(18)
        box.set_margin_end(18)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        vbox.append(box)

        # Toggle button
        button = Gtk.ToggleButton()
        button.set_icon_name("system-search-symbolic")
        button.bind_property("active", searchbar, "search-mode-enabled", GObject.BindingFlags.BIDIRECTIONAL)
        header.pack_end(button)

        # Result
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.append(hbox)

        label = Gtk.Label(label="Searching for:")
        label.set_xalign(0.0)
        hbox.append(label)

        label = Gtk.Label(label="")
        hbox.append(label)

        entry.search_changed.connect(search_changed_cb, label)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
