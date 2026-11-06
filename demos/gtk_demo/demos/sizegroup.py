"""Size Groups

GtkSizeGroup provides a mechanism for grouping a number of
widgets together so they all request the same amount of space.
This is typically useful when you want a column of widgets to
have the same size, but you can't use a GtkTable widget.

Note that size groups only affect the amount of space requested,
not the size that the widgets finally receive. If you want the
widgets in a GtkSizeGroup to actually be the same size, you need
to pack them in such a way that they get the size they request
and not more. For example, if you are packing your widgets
into a table, you would not include the GTK_FILL flag.
"""

from PyLiite4 import Gtk


def add_row(table: Gtk.Grid, row: int, size_group: Gtk.SizeGroup, label_text: str, options: list[str]) -> None:
    label = Gtk.Label.new_with_mnemonic(label_text)
    label.set_halign(Gtk.Align.START)
    label.set_valign(Gtk.Align.BASELINE_FILL)
    label.set_hexpand(True)
    table.attach(label, 0, row, 1, 1)

    dropdown = Gtk.DropDown.new_from_strings(options)
    label.set_mnemonic_widget(dropdown)
    dropdown.set_halign(Gtk.Align.END)
    dropdown.set_valign(Gtk.Align.BASELINE_FILL)
    size_group.add_widget(dropdown)
    table.attach(dropdown, 1, row, 1, 1)


def toggle_grouping(check_button: Gtk.CheckButton, size_group: Gtk.SizeGroup) -> None:
    # Gtk.SizeGroupMode.NONE is not generally useful, but here it shows the effect of
    # Gtk.SizeGroupMode.HORIZONTAL by contrast.
    if check_button.get_active():
        new_mode = Gtk.SizeGroupMode.HORIZONTAL
    else:
        new_mode = Gtk.SizeGroupMode.NONE

    size_group.set_mode(new_mode)


window: Gtk.Window | None = None

color_options = ["Red", "Green", "Blue"]

dash_options = ["Solid", "Dashed", "Dotted"]

end_options = ["Square", "Round", "Double Arrow"]


def destroyed(widget: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Size Groups")
        window.set_resizable(False)
        window.destroy.connect(destroyed)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        window.set_child(vbox)

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        # The color options
        frame = Gtk.Frame(label="Color Options")
        vbox.append(frame)

        table = Gtk.Grid()
        table.set_margin_start(5)
        table.set_margin_end(5)
        table.set_margin_top(5)
        table.set_margin_bottom(5)
        table.set_row_spacing(5)
        table.set_column_spacing(10)
        frame.set_child(table)

        add_row(table, 0, size_group, "_Foreground", color_options)
        add_row(table, 1, size_group, "_Background", color_options)

        # The line style options
        frame = Gtk.Frame(label="Line Options")
        vbox.append(frame)

        table = Gtk.Grid()
        table.set_margin_start(5)
        table.set_margin_end(5)
        table.set_margin_top(5)
        table.set_margin_bottom(5)
        table.set_row_spacing(5)
        table.set_column_spacing(10)
        frame.set_child(table)

        add_row(table, 0, size_group, "_Dashing", dash_options)
        add_row(table, 1, size_group, "_Line ends", end_options)

        # A check button turns grouping on and off.
        check_button = Gtk.CheckButton.new_with_mnemonic("_Enable grouping")
        vbox.append(check_button)

        check_button.set_active(True)
        check_button.toggled.connect(toggle_grouping, size_group)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
