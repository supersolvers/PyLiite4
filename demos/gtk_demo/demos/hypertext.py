"""Text View/Hypertext
#Keywords: GtkTextView, GtkTextBuffer

Usually, tags modify the appearance of text in the view, e.g. making it
bold or colored or underlined. But tags are not restricted to appearance.
They can also affect the behavior of mouse and key presses, as this demo
shows.

We also demonstrate adding other things to a text view, such as
clickable icons and widgets which can also replace a character
(try copying the ghost text).
"""

from PyLiite4 import Gdk, GLib, Gtk, Pango

PANGO_SCALE_X_LARGE = 1.2 * 1.2  # a C macro, not in the introspection data


def insert_link(buffer: Gtk.TextBuffer, iter: Gtk.TextIter, text: str, page: int) -> None:
    """Inserts a piece of text into the buffer, giving it the usual
    appearance of a hyperlink in a web browser: blue and underlined.
    Additionally, attaches some data on the tag, to make it recognizable
    as a link.
    """
    tag = buffer.create_tag(None, foreground="blue", underline=Pango.Underline.SINGLE)
    tag.page = page
    buffer.insert_with_tags(iter, text, tag)


def say_word(gesture: Gtk.GestureClick, n_press: int, x: float, y: float, word: str) -> None:
    """Quick-and-dirty text-to-speech for a single word. If you don't hear
    anything, you are missing espeak-ng on your system.
    """
    argv = ["espeak-ng", word]

    try:
        GLib.spawn_async(argv, flags=GLib.SpawnFlags.SEARCH_PATH)
    except GLib.Error:
        pass


def show_page(text_view: Gtk.TextView, page: int) -> None:
    """Fills the buffer with text and interspersed links. In any real
    hypertext app, this method would parse a file to identify the links.
    """
    buffer = text_view.get_buffer()

    bold = buffer.create_tag(None, weight=Pango.Weight.BOLD, scale=PANGO_SCALE_X_LARGE)
    mono = buffer.create_tag(None, family="monospace")
    nobreaks = buffer.create_tag(None, allow_breaks=False)

    buffer.set_text("", 0)
    iter = buffer.get_iter_at_offset(0)
    buffer.begin_irreversible_action()
    if page == 1:
        buffer.insert(iter, "Some text to show that simple ")
        insert_link(buffer, iter, "hypertext", 3)
        buffer.insert(iter, " can easily be realized with ")
        insert_link(buffer, iter, "tags", 2)
        buffer.insert(iter, ".\n")
        buffer.insert(iter, "Of course you can also embed Emoji 😋, ")
        buffer.insert(iter, "icons ")

        theme = Gtk.IconTheme.get_for_display(text_view.get_display())
        icon = theme.lookup_icon("view-conceal-symbolic", None, 16, 1, Gtk.TextDirection.LTR, 0)
        buffer.insert_paintable(iter, icon)
        buffer.insert(iter, ", or even widgets ")
        anchor = buffer.create_child_anchor(iter)
        child = Gtk.LevelBar.new_for_interval(0, 100)
        child.set_value(50)
        child.set_size_request(100, -1)
        text_view.add_child_at_anchor(child, anchor)
        buffer.insert(iter, " and labels with ")
        anchor = Gtk.TextChildAnchor.new_with_replacement("👻")
        buffer.insert_child_anchor(iter, anchor)
        child = Gtk.Label(label="ghost")
        text_view.add_child_at_anchor(child, anchor)
        buffer.insert(iter, " text.")
    elif page == 2:
        mark = buffer.create_mark("mark", iter, True)

        buffer.insert_with_tags(iter, "tag", bold)
        buffer.insert(iter, " /")

        start = buffer.get_iter_at_mark(mark)
        buffer.apply_tag(nobreaks, start, iter)
        buffer.insert(iter, " ")

        buffer.move_mark(mark, iter)
        buffer.insert_with_tags(iter, "tag", mono)
        buffer.insert(iter, " /")

        start = buffer.get_iter_at_mark(mark)
        buffer.apply_tag(nobreaks, start, iter)
        buffer.insert(iter, " ")

        anchor = buffer.create_child_anchor(iter)
        child = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic")
        child.set_cursor_from_name("pointer")
        controller = Gtk.GestureClick()
        controller.pressed.connect(say_word, "tag")
        child.add_controller(controller)
        text_view.add_child_at_anchor(child, anchor)

        buffer.insert(iter, "\n"
                      "An attribute that can be applied to some range of text. For example, "
                      "a tag might be called “bold” and make the text inside the tag bold.\n"
                      "However, the tag concept is more general than that; "
                      "tags don't have to affect appearance. They can instead affect the "
                      "behavior of mouse and key presses, “lock” a range of text so the "
                      "user can't edit it, or countless other things.\n")
        insert_link(buffer, iter, "Go back", 1)

        buffer.delete_mark(mark)
    elif page == 3:
        mark = buffer.create_mark("mark", iter, True)

        buffer.insert_with_tags(iter, "hypertext", bold)
        buffer.insert(iter, " /")

        start = buffer.get_iter_at_mark(mark)
        buffer.apply_tag(nobreaks, start, iter)
        buffer.insert(iter, " ")

        buffer.move_mark(mark, iter)
        buffer.insert_with_tags(iter, "ˈhaɪ pərˌtɛkst", mono)
        buffer.insert(iter, " /")
        start = buffer.get_iter_at_mark(mark)
        buffer.apply_tag(nobreaks, start, iter)
        buffer.insert(iter, " ")

        anchor = buffer.create_child_anchor(iter)
        child = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic")
        child.set_cursor_from_name("pointer")
        controller = Gtk.GestureClick()
        controller.pressed.connect(say_word, "hypertext")
        child.add_controller(controller)
        text_view.add_child_at_anchor(child, anchor)

        buffer.insert(iter, "\n"
                      "Machine-readable text that is not sequential but is organized "
                      "so that related items of information are connected.\n")
        insert_link(buffer, iter, "Go back", 1)

        buffer.delete_mark(mark)
    buffer.end_irreversible_action()


def follow_if_link(text_view: Gtk.TextView, iter: Gtk.TextIter) -> None:
    """Looks at all tags covering the position of iter in the text view,
    and if one of them is a link, follow it by showing the page identified
    by the data attached to it.
    """
    for tag in iter.get_tags():
        page = getattr(tag, "page", 0)

        if page != 0:
            show_page(text_view, page)
            break


def key_pressed(controller: Gtk.EventControllerKey, keyval: int, keycode: int, modifiers: Gdk.ModifierType,
                text_view: Gtk.TextView) -> bool:
    """Links can be activated by pressing Enter."""
    if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
        buffer = text_view.get_buffer()
        iter = buffer.get_iter_at_mark(buffer.get_insert())
        follow_if_link(text_view, iter)

    return Gdk.EVENT_PROPAGATE


def released_cb(gesture: Gtk.GestureClick, n_press: int, x: float, y: float, text_view: Gtk.TextView) -> None:
    if gesture.get_button() > 1:
        return

    tx, ty = text_view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))

    buffer = text_view.get_buffer()

    # we shouldn't follow a link if the user has selected something
    _, start, end = buffer.get_selection_bounds()
    if start.get_offset() != end.get_offset():
        return

    found, iter = text_view.get_iter_at_location(tx, ty)
    if found:
        follow_if_link(text_view, iter)


def motion_cb(controller: Gtk.EventControllerMotion, x: float, y: float, text_view: Gtk.TextView) -> None:
    tx, ty = text_view.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(x), int(y))

    set_cursor_if_appropriate(text_view, tx, ty)


hovering_over_link = False


def set_cursor_if_appropriate(text_view: Gtk.TextView, x: int, y: int) -> None:
    """Looks at all tags covering the position (x, y) in the text view,
    and if one of them is a link, change the cursor to the "hands" cursor
    typically used by web browsers.
    """
    global hovering_over_link
    hovering = False

    found, iter = text_view.get_iter_at_location(x, y)
    if found:
        for tag in iter.get_tags():
            page = getattr(tag, "page", 0)

            if page != 0:
                hovering = True
                break

    if hovering != hovering_over_link:
        hovering_over_link = hovering

        if hovering_over_link:
            text_view.set_cursor_from_name("pointer")
        else:
            text_view.set_cursor_from_name("text")


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window
    if window is None:
        window = Gtk.Window()
        window.set_title("Hypertext")
        window.set_display(do_widget.get_display())
        window.set_default_size(330, 330)
        window.set_resizable(False)
        window.close_request.connect(close_request)

        view = Gtk.TextView()
        view.set_wrap_mode(Gtk.WrapMode.WORD)
        view.set_top_margin(20)
        view.set_bottom_margin(20)
        view.set_left_margin(20)
        view.set_right_margin(20)
        view.set_pixels_below_lines(10)
        controller = Gtk.EventControllerKey()
        controller.key_pressed.connect(key_pressed, view)
        view.add_controller(controller)

        controller = Gtk.GestureClick()
        controller.released.connect(released_cb, view)
        view.add_controller(controller)

        controller = Gtk.EventControllerMotion()
        controller.motion.connect(motion_cb, view)
        view.add_controller(controller)

        buffer = view.get_buffer()
        buffer.set_enable_undo(True)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        window.set_child(sw)
        sw.set_child(view)

        show_page(view, 1)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
