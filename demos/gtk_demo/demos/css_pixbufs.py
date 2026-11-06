"""Theming/Animated Backgrounds

This demo is in honour of a classic Pixbufs demo.

It is done exclusively with CSS as the background of the window.
"""

from collections.abc import Callable

from PyLiite4 import Gdk, Gio, GLib, Gtk, Pango


def show_parsing_error(provider: Gtk.CssProvider, section: Gtk.CssSection, error: GLib.Error,
                       buffer: Gtk.TextBuffer) -> None:
    start_location = section.get_start_location()
    _ok, start = buffer.get_iter_at_line_index(start_location.lines, start_location.line_bytes)
    end_location = section.get_end_location()
    _ok, end = buffer.get_iter_at_line_index(end_location.lines, end_location.line_bytes)

    if error.domain == GLib.quark_to_string(Gtk.css_parser_warning_quark()):
        tag_name = "warning"
    else:
        tag_name = "error"

    buffer.apply_tag_by_name(tag_name, start, end)


def css_text_changed(buffer: Gtk.TextBuffer, provider: Gtk.CssProvider) -> None:
    start = buffer.get_start_iter()
    end = buffer.get_end_iter()
    buffer.remove_all_tags(start, end)

    text = buffer.get_text(start, end, False)
    provider.load_from_string(text)


def clear_provider(provider: Gtk.StyleProvider) -> None:
    Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), provider)


def apply_css(widget: Gtk.Widget, provider: Gtk.StyleProvider) -> None:
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, GLib.MAXUINT32)
    # g_object_set_data_full(): the provider goes when the widget does.
    widget.weak_ref(clear_provider, provider)


# The window, held weakly as C's weak pointer does: GTK keeps a window until it is destroyed.
window_ref: Callable[[], Gtk.Window | None] = lambda: None


def do(do_widget: Gtk.Widget) -> Gtk.Window:
    global window_ref
    window = window_ref()
    if window is None:
        window = Gtk.Window()
        window.set_title("Animated Backgrounds")
        window.set_transient_for(do_widget)
        window.set_default_size(400, 300)
        window.add_css_class("demo")
        window_ref = window.weak_ref()

        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        window.set_child(paned)

        # A filler for the start child, so the paned has a handle.
        child = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        paned.set_start_child(child)

        text = Gtk.TextBuffer()
        text.create_tag("warning", underline=Pango.Underline.SINGLE)
        text.create_tag("error", underline=Pango.Underline.ERROR)

        provider = Gtk.CssProvider()

        container = Gtk.ScrolledWindow()
        paned.set_end_child(container)
        child = Gtk.TextView.new_with_buffer(text)
        container.set_child(child)
        text.changed.connect(css_text_changed, provider)

        bytes = Gio.resources_lookup_data("/css_pixbufs/gtk.css", Gio.ResourceLookupFlags.NONE)
        text.set_text(bytes.get_data().decode(), -1)

        provider.parsing_error.connect(show_parsing_error, child.get_buffer())

        apply_css(window, provider)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
