import json
import sys

from PyLiite4 import Gio, GLib, Gtk, Soup

from demos.workbench import workbench

http_session = Soup.Session()
article_text_view: Gtk.TextView = workbench.builder.get_object("article_text_view")
article_title: Gtk.Label = workbench.builder.get_object("article_title")


def fetch_wikipedia_todays_featured_article() -> None:
    # https://gjs-docs.gnome.org/glib20~2.0/glib.datetime
    date = GLib.DateTime.new_now_local()

    # https://api.wikimedia.org/wiki/Feed_API/Reference/Featured_content
    language = "en"
    url = f"https://api.wikimedia.org/feed/v1/wikipedia/{language}/featured/{date.format('%Y/%m/%d')}"
    message = Soup.Message.new("GET", url)

    http_session.send_and_read_async(
        message, GLib.PRIORITY_DEFAULT, None, on_receive_bytes, message
    )


def on_receive_bytes(session: Soup.Session, result: Gio.AsyncResult, message: Soup.Message) -> None:
    try:
        bytes = session.send_and_read_finish(result)
    except GLib.Error as error:
        print(error.message, file=sys.stderr)
        return

    if message.get_status() != Soup.Status.OK:
        print(f"HTTP Status {message.get_status()}")
        return

    decoded_text = bytes.get_data().decode("utf-8")
    json_dict = json.loads(decoded_text)
    article_text_view.get_buffer().set_text(json_dict["tfa"]["extract"], -1)
    article_title.set_label(json_dict["tfa"]["titles"]["normalized"])


fetch_wikipedia_todays_featured_article()
