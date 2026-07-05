"""Info Bars
#Keywords: GtkInfoBar

Info bar widgets are used to report important messages to the user.
"""

from PyLiite4 import GObject, Gtk


def on_bar_response(info_bar: Gtk.InfoBar, response_id: int, user_data: Gtk.Window) -> None:
    if response_id == Gtk.ResponseType.CLOSE:
        info_bar.set_revealed(False)
        return

    dialog = Gtk.AlertDialog(message="You clicked a button on an info bar")
    detail = f"Your response has been {response_id}"
    dialog.set_detail(detail)
    dialog.show(info_bar.get_root())


window: Gtk.Window | None = None


def close_request(win: Gtk.Window) -> bool:
    global window
    win.destroy()
    window = None
    return True


def do(do_widget: Gtk.Widget) -> Gtk.Window | None:
    global window

    if window is None:
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        actions.add_css_class("linked")

        window = Gtk.Window()
        window.set_display(do_widget.get_display())
        window.set_title("Info Bars")
        window.set_resizable(False)
        window.close_request.connect(close_request)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        vbox.set_margin_start(8)
        vbox.set_margin_end(8)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        window.set_child(vbox)

        bar = Gtk.InfoBar()
        vbox.append(bar)
        bar.set_message_type(Gtk.MessageType.INFO)
        label = Gtk.Label(label="This is an info bar with message type GTK_MESSAGE_INFO")
        label.set_wrap(True)
        label.set_xalign(0)
        bar.add_child(label)

        button = Gtk.ToggleButton.new_with_label("Message")
        bar.bind_property("revealed", button, "active",
                          GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        actions.append(button)

        bar = Gtk.InfoBar()
        vbox.append(bar)
        bar.set_message_type(Gtk.MessageType.WARNING)
        label = Gtk.Label(label="This is an info bar with message type GTK_MESSAGE_WARNING")
        label.set_wrap(True)
        label.set_xalign(0)
        bar.add_child(label)

        button = Gtk.ToggleButton.new_with_label("Warning")
        bar.bind_property("revealed", button, "active",
                          GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        actions.append(button)

        bar = Gtk.InfoBar()
        bar.add_button("_OK", Gtk.ResponseType.OK)
        bar.set_show_close_button(True)
        bar.response.connect(on_bar_response, window)
        vbox.append(bar)
        bar.set_message_type(Gtk.MessageType.QUESTION)
        label = Gtk.Label(label="This is an info bar with message type GTK_MESSAGE_QUESTION")
        label.set_wrap(True)
        label.set_xalign(0)
        bar.add_child(label)
        bar.set_default_response(Gtk.ResponseType.OK)

        button = Gtk.ToggleButton.new_with_label("Question")
        bar.bind_property("revealed", button, "active",
                          GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        actions.append(button)

        bar = Gtk.InfoBar()
        vbox.append(bar)
        bar.set_message_type(Gtk.MessageType.ERROR)
        label = Gtk.Label(label="This is an info bar with message type GTK_MESSAGE_ERROR")
        label.set_wrap(True)
        label.set_xalign(0)
        bar.add_child(label)

        button = Gtk.ToggleButton.new_with_label("Error")
        bar.bind_property("revealed", button, "active",
                          GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)

        actions.append(button)

        bar = Gtk.InfoBar()
        vbox.append(bar)
        bar.set_message_type(Gtk.MessageType.OTHER)
        label = Gtk.Label(label="This is an info bar with message type GTK_MESSAGE_OTHER")
        label.set_wrap(True)
        label.set_xalign(0)
        bar.add_child(label)

        button = Gtk.ToggleButton.new_with_label("Other")
        bar.bind_property("revealed", button, "active",
                          GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        actions.append(button)

        frame = Gtk.Frame(label="An example of different info bars")
        frame.set_margin_top(8)
        frame.set_margin_bottom(8)
        vbox.append(frame)

        actions.set_halign(Gtk.Align.CENTER)

        actions.set_margin_start(8)
        actions.set_margin_end(8)
        actions.set_margin_top(8)
        actions.set_margin_bottom(8)
        frame.set_child(actions)

    if not window.get_visible():
        window.set_visible(True)
    else:
        window.destroy()
        window = None

    return window
