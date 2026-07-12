"""Expander

GtkExpander allows to provide additional content that is initially hidden.
This is also known as "disclosure triangle".

This example also shows how to make the window resizable only if the expander
is expanded.
"""

from PyLiite4 import Gdk, Gtk

window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window
    if window is None:
        window = Gtk.Window(title="Expander", transient_for=do_widget.get_root())
        area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_start=10, margin_end=10,
                       margin_top=10, margin_bottom=10)
        window.set_child(area)
        area.append(Gtk.Label(label="<big><b>Something went wrong</b></big>", use_markup=True))
        area.append(Gtk.Label(label="Here are some more details but not the full story", wrap=False, vexpand=False))

        expander = Gtk.Expander(label="Details:", vexpand=True)
        sw = Gtk.ScrolledWindow(min_content_height=100, has_frame=True, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                vscrollbar_policy=Gtk.PolicyType.AUTOMATIC, propagate_natural_height=True,
                                vexpand=True)
        tv = Gtk.TextView(left_margin=10, right_margin=10, top_margin=10, bottom_margin=10, editable=False,
                          cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD, pixels_above_lines=2,
                          pixels_below_lines=2)
        buffer = tv.get_buffer()
        buffer.set_text("Finally, the full story with all details. "
                        "And all the inside information, including "
                        "error codes, etc etc. Pages of information, "
                        "you might have to scroll down to read it all, "
                        "or even resize the window - it works !\n"
                        "A second paragraph will contain even more "
                        "innuendo, just to make you scroll down or "
                        "resize the window.\n"
                        "Do it already!\n")

        start = buffer.get_end_iter()
        buffer.insert_paintable(start, Gdk.Texture.new_from_resource("/cursors/images/gtk_logo_cursor.png"))
        start.backward_char()
        tag = buffer.create_tag(None, pixels_above_lines=200, justification=Gtk.Justification.RIGHT)
        buffer.apply_tag(tag, start, buffer.get_end_iter())

        sw.set_child(tv)
        expander.set_child(sw)
        area.append(expander)
        expander.notify["expanded"].connect(lambda expander, _pspec: window.set_resizable(expander.get_expanded()))
        window.close_request.connect(close_request)

    if not window.get_visible():
        window.present()
        return window
    # Unlike C's weak pointer, destroying doesn't clear this reference, so clear it here.
    window.destroy()
    window = None
    return None
