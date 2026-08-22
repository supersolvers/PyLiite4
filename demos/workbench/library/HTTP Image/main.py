import sys

from PyLiite4 import Gdk, Gio, GLib, Soup

from demos.workbench import workbench

# https://picsum.photos/
IMAGE_URL = "https://picsum.photos/800"


def on_receive_bytes(session: Soup.Session, result: Gio.AsyncResult, message: Soup.Message) -> None:
    try:
        bytes = session.send_and_read_finish(result)
    except GLib.Error as error:
        print(error.message, file=sys.stderr)
        return
    if message.get_status() != Soup.Status.OK:
        print(f"Got {message.get_status()}, {message.get_reason_phrase()}", file=sys.stderr)
        return
    texture = Gdk.Texture.new_from_bytes(bytes)
    workbench.builder.get_object("picture").set_paintable(texture)


def get_image_bytes(url: str) -> None:
    session = Soup.Session()
    message = Soup.Message(
        method="GET",
        uri=GLib.Uri.parse(url, GLib.UriFlags.NONE),
    )
    session.send_and_read_async(
        message, GLib.PRIORITY_DEFAULT, None, on_receive_bytes, message
    )


get_image_bytes(IMAGE_URL)
