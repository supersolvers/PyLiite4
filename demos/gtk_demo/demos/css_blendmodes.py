"""Theming/CSS Blend Modes

You can blend multiple backgrounds using the CSS blend modes available.
"""

from collections.abc import Callable

from PyLiite4 import Gdk, Gio, Gtk

# The available blend modes.
blend_modes = [
    ("Color", "color"),
    ("Color (burn)", "color-burn"),
    ("Color (dodge)", "color-dodge"),
    ("Darken", "darken"),
    ("Difference", "difference"),
    ("Exclusion", "exclusion"),
    ("Hard Light", "hard-light"),
    ("Hue", "hue"),
    ("Lighten", "lighten"),
    ("Luminosity", "luminosity"),
    ("Multiply", "multiply"),
    ("Normal", "normal"),
    ("Overlay", "overlay"),
    ("Saturate", "saturation"),
    ("Screen", "screen"),
    ("Soft Light", "soft-light"),
]


def update_css_for_blend_mode(provider: Gtk.CssProvider, blend_mode: str) -> None:
    bytes = Gio.resources_lookup_data("/css_blendmodes/css_blendmodes.css", Gio.ResourceLookupFlags.NONE)

    # The file is a printf format, which Python's % formatting reads the same way.
    css = bytes.get_data().decode() % (blend_mode, blend_mode, blend_mode)

    provider.load_from_string(css)


def row_activated(listbox: Gtk.ListBox, row: Gtk.ListBoxRow, provider: Gtk.CssProvider) -> None:
    blend_mode = blend_modes[row.get_index()][1]

    update_css_for_blend_mode(provider, blend_mode)


def setup_listbox(builder: Gtk.Builder, provider: Gtk.StyleProvider) -> None:
    normal_row = None
    listbox = Gtk.ListBox()
    builder.get_object("scrolledwindow").set_child(listbox)

    listbox.row_activated.connect(row_activated, provider)

    for name, id in blend_modes:
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=name, xalign=0.0)

        row.set_child(label)
        listbox.insert(row, -1)

        # The row selected first is "normal".
        if id == "normal":
            normal_row = row

    listbox.select_row(normal_row)
    normal_row.activate.emit()

    normal_row.grab_focus()


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()
    if window is None:
        builder = Gtk.Builder.new_from_resource("/css_blendmodes/blendmodes.ui")

        window = builder.get_object("window")
        window.set_transient_for(do_widget)
        window_ref = window.weak_ref()

        # The CSS provider for the window
        provider = Gtk.CssProvider()

        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        setup_listbox(builder, provider)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
