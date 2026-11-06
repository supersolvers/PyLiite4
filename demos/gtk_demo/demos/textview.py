"""Text View/Multiple Views

The GtkTextView widget displays a GtkTextBuffer. One GtkTextBuffer
can be displayed by multiple GtkTextViews. This demo has two views
displaying a single buffer, and shows off the widget's text
formatting features.
"""

from PyLiite4 import Gtk, Pango

from .paintable_animated import gtk_nuclear_animation_new

# PANGO_SCALE_XX_SMALL and PANGO_SCALE_X_LARGE are C macros, so not in the bindings.
PANGO_SCALE_XX_SMALL = 1 / (1.2 * 1.2 * 1.2)
PANGO_SCALE_X_LARGE = 1.2 * 1.2

window: Gtk.Window | None = None
easter_egg_window: Gtk.Window | None = None


def create_tags(buffer: Gtk.TextBuffer) -> None:
    # Tags can also be made with Gtk.TextTag() and added to the buffer's tag table: create_tag() is only a
    # convenience. Tags don't need a name either; a name of None makes an anonymous tag.
    #
    # A real app could also make a GtkTextTagTable in advance and share it between all the buffers with the same
    # tag set, rather than make new copies of the same tags for every buffer.
    #
    # Tags get default priorities in the order they are added to the tag table, so a tag added later overrides an
    # earlier one that affects the same text property. set_priority() changes a tag's priority.

    buffer.create_tag("heading", weight=Pango.Weight.BOLD, size=15 * Pango.SCALE)

    buffer.create_tag("italic", style=Pango.Style.ITALIC)

    buffer.create_tag("bold", weight=Pango.Weight.BOLD)

    # Points times Pango.SCALE.
    buffer.create_tag("big", size=20 * Pango.SCALE)

    buffer.create_tag("xx-small", scale=PANGO_SCALE_XX_SMALL)

    buffer.create_tag("x-large", scale=PANGO_SCALE_X_LARGE)

    buffer.create_tag("monospace", family="monospace")

    buffer.create_tag("blue_foreground", foreground="blue")

    buffer.create_tag("red_background", background="red")

    buffer.create_tag("big_gap_before_line", pixels_above_lines=30)

    buffer.create_tag("big_gap_after_line", pixels_below_lines=30)

    buffer.create_tag("double_spaced_line", pixels_inside_wrap=10)

    buffer.create_tag("not_editable", editable=False)

    buffer.create_tag("word_wrap", wrap_mode=Gtk.WrapMode.WORD)

    buffer.create_tag("char_wrap", wrap_mode=Gtk.WrapMode.CHAR)

    buffer.create_tag("no_wrap", wrap_mode=Gtk.WrapMode.NONE)

    buffer.create_tag("center", justification=Gtk.Justification.CENTER)

    buffer.create_tag("right_justify", justification=Gtk.Justification.RIGHT)

    buffer.create_tag("wide_margins", left_margin=50, right_margin=50)

    buffer.create_tag("strikethrough", strikethrough=True)

    buffer.create_tag("underline", underline=Pango.Underline.SINGLE)

    buffer.create_tag("double_underline", underline=Pango.Underline.DOUBLE)

    buffer.create_tag("superscript",
                      rise=10 * Pango.SCALE,  # 10 pixels
                      size=8 * Pango.SCALE)  # 8 points

    buffer.create_tag("subscript",
                      rise=-10 * Pango.SCALE,  # 10 pixels
                      size=8 * Pango.SCALE)  # 8 points

    buffer.create_tag("rtl_quote",
                      wrap_mode=Gtk.WrapMode.WORD,
                      direction=Gtk.TextDirection.RTL,
                      indent=30,
                      left_margin=20,
                      right_margin=20)


def insert_text(view: Gtk.TextView) -> None:
    widget = view
    buffer = view.get_buffer()

    icon_theme = Gtk.IconTheme.get_for_display(widget.get_display())
    icon = icon_theme.lookup_icon("drive-harddisk", None, 32, 1, widget.get_direction(), 0)
    nuclear = gtk_nuclear_animation_new(True)

    # The start of the buffer. Each insertion revalidates the iterator to point just after the inserted text.
    iter = buffer.get_iter_at_offset(0)

    buffer.begin_irreversible_action()
    buffer.insert(iter,
                  "The text widget can display text with all kinds of nifty attributes. "
                  "It also supports multiple views of the same buffer; this demo is "
                  "showing the same buffer in two places.\n\n")

    buffer.insert_with_tags_by_name(iter, "Font styles. ", "heading")

    buffer.insert(iter, "For example, you can have ")
    buffer.insert_with_tags_by_name(iter, "italic", "italic")
    buffer.insert(iter, ", ")
    buffer.insert_with_tags_by_name(iter, "bold", "bold")
    buffer.insert(iter, ", or ")
    buffer.insert_with_tags_by_name(iter, "monospace (typewriter)", "monospace")
    buffer.insert(iter, ", or ")
    buffer.insert_with_tags_by_name(iter, "big", "big")
    buffer.insert(iter, " text. ")
    buffer.insert(iter,
                  "It's best not to hardcode specific text sizes; you can use relative "
                  "sizes as with CSS, such as ")
    buffer.insert_with_tags_by_name(iter, "xx-small", "xx-small")
    buffer.insert(iter, " or ")
    buffer.insert_with_tags_by_name(iter, "x-large", "x-large")
    buffer.insert(iter,
                  " to ensure that your program properly adapts if the user changes the "
                  "default font size.\n\n")

    buffer.insert_with_tags_by_name(iter, "Colors. ", "heading")

    buffer.insert(iter, "Colors such as ")
    buffer.insert_with_tags_by_name(iter, "a blue foreground", "blue_foreground")
    buffer.insert(iter, " or ")
    buffer.insert_with_tags_by_name(iter, "a red background", "red_background")
    buffer.insert(iter, " or even ")
    buffer.insert_with_tags_by_name(iter, "a blue foreground on red background",
                                    "blue_foreground", "red_background")
    buffer.insert(iter, " (select that to read it) can be used.\n\n")

    buffer.insert_with_tags_by_name(iter, "Underline, strikethrough, and rise. ", "heading")

    buffer.insert_with_tags_by_name(iter, "Strikethrough", "strikethrough")
    buffer.insert(iter, ", ")
    buffer.insert_with_tags_by_name(iter, "underline", "underline")
    buffer.insert(iter, ", ")
    buffer.insert_with_tags_by_name(iter, "double underline", "double_underline")
    buffer.insert(iter, ", ")
    buffer.insert_with_tags_by_name(iter, "superscript", "superscript")
    buffer.insert(iter, ", and ")
    buffer.insert_with_tags_by_name(iter, "subscript", "subscript")
    buffer.insert(iter, " are all supported.\n\n")

    buffer.insert_with_tags_by_name(iter, "Images. ", "heading")

    buffer.insert(iter, "The buffer can have images in it: ")
    buffer.insert_paintable(iter, icon)
    buffer.insert_paintable(iter, nuclear)

    buffer.insert(iter, " for example.\n\n")

    buffer.insert_with_tags_by_name(iter, "Spacing. ", "heading")

    buffer.insert(iter, "You can adjust the amount of space before each line.\n")

    buffer.insert_with_tags_by_name(iter, "This line has a whole lot of space before it.\n",
                                    "big_gap_before_line", "wide_margins")
    buffer.insert_with_tags_by_name(iter,
                                    "You can also adjust the amount of space after each line; "
                                    "this line has a whole lot of space after it.\n",
                                    "big_gap_after_line", "wide_margins")

    buffer.insert_with_tags_by_name(iter,
                                    "You can also adjust the amount of space between wrapped lines; "
                                    "this line has extra space between each wrapped line in the same "
                                    "paragraph. To show off wrapping, some filler text: the quick "
                                    "brown fox jumped over the lazy dog. Blah blah blah blah blah "
                                    "blah blah blah blah.\n",
                                    "double_spaced_line", "wide_margins")

    buffer.insert(iter, "Also note that those lines have extra-wide margins.\n\n")

    buffer.insert_with_tags_by_name(iter, "Editability. ", "heading")

    buffer.insert_with_tags_by_name(iter,
                                    "This line is 'locked down' and can't be edited by the user - just "
                                    "try it! You can't delete this line.\n\n",
                                    "not_editable")

    buffer.insert_with_tags_by_name(iter, "Wrapping. ", "heading")

    buffer.insert(iter,
                  "This line (and most of the others in this buffer) is word-wrapped, "
                  "using the proper Unicode algorithm. Word wrap should work in all "
                  "scripts and languages that GTK supports. Let's make this a long "
                  "paragraph to demonstrate: blah blah blah blah blah blah blah blah "
                  "blah blah blah blah blah blah blah blah blah blah blah\n\n")

    buffer.insert_with_tags_by_name(iter,
                                    "This line has character-based wrapping, and can wrap between any two "
                                    "character glyphs. Let's make this a long paragraph to demonstrate: "
                                    "blah blah blah blah blah blah blah blah blah blah blah blah blah blah "
                                    "blah blah blah blah blah\n\n", "char_wrap")

    buffer.insert_with_tags_by_name(iter,
                                    "This line has all wrapping turned off, so it makes the horizontal "
                                    "scrollbar appear.\n\n\n", "no_wrap")

    buffer.insert_with_tags_by_name(iter, "Justification. ", "heading")

    buffer.insert_with_tags_by_name(iter, "\nThis line has center justification.\n", "center")

    buffer.insert_with_tags_by_name(iter, "This line has right justification.\n", "right_justify")

    buffer.insert_with_tags_by_name(iter,
                                    "\nThis line has big wide margins. Text text text text text text text "
                                    "text text text text text text text text text text text text text text "
                                    "text text text text text text text text text text text text text text "
                                    "text.\n", "wide_margins")

    buffer.insert_with_tags_by_name(iter, "Internationalization. ", "heading")

    buffer.insert(iter,
                  "You can put all sorts of Unicode text in the buffer.\n\nGerman "
                  "(Deutsch Süd) Grüß Gott\nGreek "
                  "(Ελληνικά) "
                  "Γειά σας\nHebrew      "
                  "שלום\nJapanese "
                  "(日本語)\n\nThe widget properly handles "
                  "bidirectional text, word wrapping, DOS/UNIX/Unicode paragraph separators, "
                  "grapheme boundaries, and so on using the Pango internationalization "
                  "framework.\n")

    buffer.insert(iter, "Here's a word-wrapped quote in a right-to-left language:\n")
    buffer.insert_with_tags_by_name(iter,
                                    "وقد بدأ "
                                    "ثلاث من "
                                    "أكثر المؤسسات "
                                    "تقدما في "
                                    "شبكة اكسيون "
                                    "برامجها "
                                    "كمنظمات "
                                    "لا تسعى للربح، "
                                    "ثم تحولت "
                                    "في السنوات "
                                    "الخمس الماضية "
                                    "إلى مؤسسات "
                                    "مالية منظمة، "
                                    "وباتت جزءا "
                                    "من النظام "
                                    "المالي في "
                                    "بلدانها، "
                                    "ولكنها تتخصص "
                                    "في خدمة قطاع "
                                    "المشروعات "
                                    "الصغيرة. وأحد "
                                    "أكثر هذه "
                                    "المؤسسات "
                                    "نجاحا هو "
                                    "»بانكوسول« "
                                    "في بوليفيا.\n\n",
                                    "rtl_quote")

    buffer.insert(iter, "You can put widgets in the buffer: Here's a button: ")
    buffer.create_child_anchor(iter)
    buffer.insert(iter, " and a menu: ")
    buffer.create_child_anchor(iter)
    buffer.insert(iter, " and a scale: ")
    buffer.create_child_anchor(iter)
    buffer.insert(iter, " finally a text entry: ")
    buffer.create_child_anchor(iter)
    buffer.insert(iter, ".\n")

    buffer.insert(iter,
                  "\n\nThis demo doesn't demonstrate all the GtkTextBuffer features; "
                  "it leaves out, for example: invisible/hidden text, tab stops, "
                  "application-drawn areas on the sides of the widget for displaying "
                  "breakpoints and such...")

    # The word_wrap tag covers the whole buffer.
    start, end = buffer.get_bounds()
    buffer.apply_tag_by_name("word_wrap", start, end)

    buffer.end_irreversible_action()


def find_anchor(iter: Gtk.TextIter) -> bool:
    while iter.forward_char():
        if iter.get_child_anchor():
            return True
    return False


def attach_widgets(text_view: Gtk.TextView) -> None:
    buffer = text_view.get_buffer()

    iter = buffer.get_start_iter()

    i = 0
    while find_anchor(iter):
        anchor = iter.get_child_anchor()

        if i == 0:
            widget = Gtk.Button.new_with_label("Click Me")

            widget.clicked.connect(easter_egg_callback)
        elif i == 1:
            options = ["Option 1", "Option 2", "Option 3"]

            widget = Gtk.DropDown.new_from_strings(options)
        elif i == 2:
            widget = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, None)
            widget.set_range(0, 100)
            widget.set_size_request(100, -1)
        elif i == 3:
            widget = Gtk.Entry()
            widget.set_width_chars(10)
        else:
            raise AssertionError("not reached")

        text_view.add_child_at_anchor(widget, anchor)

        i += 1


def destroyed(win: Gtk.Window) -> None:
    global window
    window = None


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_default_size(450, 450)
        window.destroy.connect(destroyed)

        window.set_title("Multiple Views")

        vpaned = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        window.set_child(vpaned)

        # For convenience, both views use the buffer the first one creates. The buffer could also be made on its
        # own with Gtk.TextBuffer(), and a view made for it later.
        view1 = Gtk.TextView()
        buffer = view1.get_buffer()
        view2 = Gtk.TextView.new_with_buffer(buffer)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vpaned.set_start_child(sw)
        vpaned.set_resize_start_child(False)
        vpaned.set_shrink_start_child(True)

        sw.set_child(view1)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        vpaned.set_end_child(sw)
        vpaned.set_resize_end_child(True)
        vpaned.set_shrink_end_child(True)

        sw.set_child(view2)

        create_tags(buffer)
        insert_text(view1)

        attach_widgets(view1)
        attach_widgets(view2)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window


def recursive_attach_view(depth: int, view: Gtk.TextView, anchor: Gtk.TextChildAnchor) -> None:
    if depth > 4:
        return

    child_view = Gtk.TextView.new_with_buffer(view.get_buffer())
    child_view.set_size_request(260 - 20 * depth, -1)

    # The frame puts a black border around each child view.
    frame = Gtk.Frame()
    frame.set_child(child_view)

    view.add_child_at_anchor(frame, anchor)

    recursive_attach_view(depth + 1, child_view, anchor)


def easter_egg_destroyed(win: Gtk.Window) -> None:
    global easter_egg_window
    easter_egg_window = None


def easter_egg_callback(button: Gtk.Widget) -> None:
    global easter_egg_window

    if easter_egg_window is not None:
        easter_egg_window.present()
        return

    buffer = Gtk.TextBuffer()

    iter = buffer.get_start_iter()

    buffer.insert(iter, "This buffer is shared by a set of nested text views.\n Nested view:\n")
    anchor = buffer.create_child_anchor(iter)
    buffer.insert(iter, "\nDon't do this in real applications, please.\n")

    view = Gtk.TextView.new_with_buffer(buffer)

    recursive_attach_view(0, view, anchor)

    easter_egg_window = Gtk.Window()
    easter_egg_window.set_transient_for(button.get_root())
    easter_egg_window.set_modal(True)
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

    easter_egg_window.set_child(sw)
    sw.set_child(view)

    easter_egg_window.destroy.connect(easter_egg_destroyed)

    easter_egg_window.set_default_size(300, 400)

    easter_egg_window.present()
