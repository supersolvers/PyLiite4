"""Links

GtkLabel can show hyperlinks. The default action is to call
gtk_show_uri() on their URI, but it is possible to override
this with a custom handler.
"""

from PyLiite4 import Gtk, Pango


def activate_link(label: Gtk.Label, uri: str) -> bool:
    if uri == "keynav":
        dialog = Gtk.AlertDialog(message="Keyboard navigation")
        dialog.set_detail("The term ‘keynav’ is a shorthand for "
                          "keyboard navigation and refers to the process of using "
                          "a program (exclusively) via keyboard input.")
        dialog.show(label.get_root())

        return True

    return False


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
        window.set_display(do_widget.get_display())
        window.set_title("Links")
        window.set_resizable(False)
        window.close_request.connect(close_request)

        label = Gtk.Label(label="Some <a href=\"http://en.wikipedia.org/wiki/Text\""
                                "title=\"plain text\">text</a> may be marked up "
                                "as hyperlinks, which can be clicked "
                                "or activated via <a href=\"keynav\">keynav</a> "
                                "and they work fine with other markup, like when "
                                "linking to <a href=\"http://www.flathub.org/\"><b>"
                                "<span letter_spacing=\"1024\" underline=\"none\" color=\"pink\" "
                                "background=\"darkslategray\">Flathub</span>"
                                "</b></a>.")
        label.set_use_markup(True)
        label.set_max_width_chars(40)
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD)
        label.activate_link.connect(activate_link)
        label.set_margin_start(20)
        label.set_margin_end(20)
        label.set_margin_top(20)
        label.set_margin_bottom(20)
        window.set_child(label)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
