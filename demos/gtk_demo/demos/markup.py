"""Text View/Markup
#Keywords: GtkTextView

GtkTextBuffer lets you define your own tags that can influence
text formatting in a variety of ways. In this example, we show
that GtkTextBuffer can load Pango markup and automatically generate
suitable tags.
"""

from PyLiite4 import Gio, Gtk

stack: Gtk.Stack | None = None
view: Gtk.TextView | None = None
view2: Gtk.TextView | None = None


def source_toggled(button: Gtk.CheckButton, _stack: Gtk.Stack) -> None:
    if button.get_active():
        stack.set_visible_child_name("source")
    else:
        buffer = view2.get_buffer()
        start, end = buffer.get_bounds()
        markup = buffer.get_text(start, end, False)

        buffer = view.get_buffer()
        start, end = buffer.get_bounds()
        buffer.begin_irreversible_action()
        buffer.delete(start, end)
        buffer.insert_markup(start, markup, -1)
        buffer.end_irreversible_action()

        stack.set_visible_child_name("formatted")


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window, stack, view, view2

    if not window:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_default_size(600, 680)

        window.close_request.connect(close_request)

        stack = Gtk.Stack()
        window.set_child(stack)

        show_source = Gtk.CheckButton.new_with_label("Source")
        show_source.set_valign(Gtk.Align.CENTER)
        show_source.toggled.connect(source_toggled, stack)

        header = Gtk.HeaderBar()
        header.pack_start(show_source)
        window.set_titlebar(header)

        window.set_title("Markup")

        view = Gtk.TextView()
        view.set_editable(False)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_left_margin(10)
        view.set_right_margin(10)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(view)

        stack.add_named(sw, "formatted")

        view2 = Gtk.TextView()
        view2.set_wrap_mode(Gtk.WrapMode.WORD)
        view2.set_left_margin(10)
        view2.set_right_margin(10)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(view2)

        stack.add_named(sw, "source")

        bytes = Gio.resources_lookup_data("/markup/markup.txt", Gio.ResourceLookupFlags.NONE)
        markup = bytes.get_data().decode()

        buffer = view.get_buffer()
        iter = buffer.get_start_iter()
        buffer.begin_irreversible_action()
        buffer.insert_markup(iter, markup, -1)
        buffer.end_irreversible_action()

        buffer = view2.get_buffer()
        iter = buffer.get_start_iter()
        buffer.begin_irreversible_action()
        buffer.insert(iter, markup, -1)
        buffer.end_irreversible_action()

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
