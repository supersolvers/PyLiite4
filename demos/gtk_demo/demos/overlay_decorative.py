"""Overlay/Decorative Overlay
#Keywords: GtkOverlay

Another example of an overlay with some decorative
and some interactive controls.
"""

from PyLiite4 import Gtk

tag: Gtk.TextTag | None = None


def margin_changed(adjustment: Gtk.Adjustment, text: Gtk.TextView) -> None:
    value = int(adjustment.get_value())
    text.set_left_margin(value)
    tag.set_property("pixels-above-lines", value)


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Widget:
    global window, tag

    if not window:
        window = Gtk.Window()
        window.set_default_size(500, 510)
        window.set_title("Decorative Overlay")

        overlay = Gtk.Overlay()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        text = Gtk.TextView()
        buffer = text.get_buffer()

        buffer.set_text("Dear diary...", -1)

        tag = buffer.create_tag("top-margin", pixels_above_lines=0)
        start = buffer.get_start_iter()
        end = start.copy()
        end.forward_word_end()
        buffer.apply_tag(tag, start, end)

        window.set_child(overlay)
        overlay.set_child(sw)
        sw.set_child(text)

        window.close_request.connect(close_request)

        image = Gtk.Picture.new_for_resource("/overlay2/decor1.png")
        overlay.add_overlay(image)
        image.set_can_target(False)
        image.set_halign(Gtk.Align.START)
        image.set_valign(Gtk.Align.START)

        image = Gtk.Picture.new_for_resource("/overlay2/decor2.png")
        overlay.add_overlay(image)
        image.set_can_target(False)
        image.set_halign(Gtk.Align.END)
        image.set_valign(Gtk.Align.END)

        adjustment = Gtk.Adjustment.new(0, 0, 100, 1, 1, 0)
        adjustment.value_changed.connect(margin_changed, text)

        scale = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, adjustment)
        scale.set_draw_value(False)
        scale.set_size_request(120, -1)
        scale.set_margin_start(20)
        scale.set_margin_end(20)
        scale.set_margin_bottom(20)
        overlay.add_overlay(scale)
        scale.set_halign(Gtk.Align.START)
        scale.set_valign(Gtk.Align.END)
        scale.set_tooltip_text("Margin")

        adjustment.set_value(100)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()

    return window
