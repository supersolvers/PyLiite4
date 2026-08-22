from PyLiite4 import GLib, GObject, Gtk, WebKit  # type: ignore[attr-defined]  # PyLiite4 doesn't provide WebKit

from demos.workbench import workbench

button_back: Gtk.Button = workbench.builder.get_object("button_back")
button_forward: Gtk.Button = workbench.builder.get_object("button_forward")
button_reload: Gtk.Button = workbench.builder.get_object("button_reload")
button_stop: Gtk.Button = workbench.builder.get_object("button_stop")
url_bar: Gtk.Entry = workbench.builder.get_object("url_bar")
web_view: WebKit.WebView = workbench.builder.get_object("web_view")

# URL bar displays the current loaded page
web_view.bind_property(
    "uri",
    url_bar.get_buffer(),
    "text",
    GObject.BindingFlags.DEFAULT,
)


def on_activate(_entry: Gtk.Entry) -> None:
    url = url_bar.get_buffer().get_text()
    scheme = GLib.Uri.peek_scheme(url)
    if not scheme:
        url = f"http://{url}"

    web_view.load_uri(url)


def on_load_changed(_self: WebKit.WebView, load_event: WebKit.LoadEvent) -> None:
    match load_event:
        case WebKit.LoadEvent.STARTED:
            print("Page loading started")
        case WebKit.LoadEvent.FINISHED:
            print("Page loading has finished ")


def on_load_failed(_self: WebKit.WebView, _load_event: WebKit.LoadEvent, fail_url: str, error: GLib.Error) -> bool:
    # Loading failed as a result of calling stop_loading
    if error.matches(WebKit.NetworkError, WebKit.NetworkError.CANCELLED):
        return False

    web_view.load_alternate_html(
        error_page(fail_url, error.message),
        fail_url,
        None,
    )
    return False


def on_timeout() -> bool:
    url_bar.set_progress_fraction(0)
    return False


def on_estimated_load_progress(_widget: WebKit.WebView, _load_progress: GObject.ParamSpec) -> None:
    url_bar.set_progress_fraction(web_view.get_estimated_load_progress())
    if url_bar.get_progress_fraction() == 1:
        GLib.timeout_add(500, on_timeout)


def error_page(fail_url: str, msg: str) -> str:
    error = f"""
    <div style="text-align:center margin:24px">
    <h2>An error occurred while loading {fail_url}</h2>
    <p>{msg}</p>
    </div>
  """
    return error


web_view.load_uri("https://www.gnome.org/")

url_bar.activate.connect(on_activate)

button_forward.clicked.connect(lambda _: web_view.go_forward())
button_back.clicked.connect(lambda _: web_view.go_back())
button_reload.clicked.connect(lambda _: web_view.reload())
button_stop.clicked.connect(lambda _: web_view.stop_loading())

web_view.load_changed.connect(on_load_changed)
web_view.load_failed.connect(on_load_failed)
web_view.notify["estimated-load-progress"].connect(on_estimated_load_progress)
