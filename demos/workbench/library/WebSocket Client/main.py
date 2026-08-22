import sys

from PyLiite4 import Gio, GLib, Gtk, Soup

from demos.workbench import workbench

builder = workbench.builder

button_connect: Gtk.Button = builder.get_object("button_connect")
button_disconnect: Gtk.Button = builder.get_object("button_disconnect")
button_send: Gtk.Button = builder.get_object("button_send")
entry_url: Gtk.Entry = builder.get_object("entry_url")
entry_message: Gtk.Entry = builder.get_object("entry_message")

connection: Soup.WebsocketConnection | None = None


def on_open() -> None:
    print("open")
    button_connect.set_sensitive(False)
    button_disconnect.set_sensitive(True)
    button_send.set_sensitive(True)


def on_closed(_self: Soup.WebsocketConnection) -> None:
    print("closed")
    global connection
    connection = None
    button_connect.set_sensitive(True)
    button_disconnect.set_sensitive(False)
    button_send.set_sensitive(False)


def on_error(_self: Soup.WebsocketConnection, err: GLib.Error) -> None:
    print("error")
    print(err, file=sys.stderr)


def on_message(_self: Soup.WebsocketConnection, data_type: Soup.WebsocketDataType, message: GLib.Bytes) -> None:
    if data_type != Soup.WebsocketDataType.TEXT:
        return
    text = message.get_data().decode("utf-8")
    print("received:", text)


def send(text: str) -> None:
    connection.send_message(
        Soup.WebsocketDataType.TEXT,
        GLib.Bytes(text.encode("utf-8")),
    )
    print("sent:", text)


def on_button_send_clicked(_button: Gtk.Button) -> None:
    text = entry_message.get_text()
    send(text)


def on_connected(session: Soup.Session, result: Gio.AsyncResult) -> None:
    global connection
    try:
        connection = session.websocket_connect_finish(result)
    except GLib.Error as error:
        on_error(None, error)
        return
    connection.closed.connect(on_closed)
    connection.error.connect(on_error)
    connection.message.connect(on_message)

    on_open()


def connect(_button: Gtk.Button) -> None:
    session = Soup.Session()
    message = Soup.Message(
        method="GET",
        uri=GLib.Uri.parse(entry_url.get_text(), GLib.UriFlags.NONE),
    )

    session.websocket_connect_async(message, None, [], GLib.PRIORITY_DEFAULT, None, on_connected)


button_connect.clicked.connect(connect)
button_disconnect.clicked.connect(lambda _: connection.close(Soup.WebsocketCloseCode.NORMAL, None))
button_send.clicked.connect(on_button_send_clicked)
