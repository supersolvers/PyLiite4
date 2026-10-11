"""A window template, a style sheet and an icon, shipped as GResources.

example.gresource.xml lists the files. pyliite4-resources compiles them into example_resources.py, and importing that
module registers them, so they are found by resource path wherever the application is installed. window_ui.py is
generated with --resource, so the template is loaded from the registered resources rather than embedded.

Nothing else needs loading by hand: the resources live under the application's base path,
/org/example/PyLiite4Resources, derived from its ID. Adw.Application loads style.css from there, and Gtk.Application
adds icons/ to the icon theme, so the window can use the icon by name.

Run it from the repository root:

    python examples/resources/main.py

After changing any of the files, regenerate both modules:

    cd examples/resources
    pyliite4-resources example.gresource.xml -o example_resources.py
    pyliite4-ui window.ui -o window_ui.py --resource /org/example/PyLiite4Resources/window.ui
"""

import sys

import example_resources  # noqa: F401  (registers the resources; import it before window_ui's template is used)
from window_ui import ExampleResourcesWindowChildren, template

from PyLiite4 import Adw, Gio, Gtk


# The ignore works around the stubs: mypy finds Gtk.Widget's realize() and Gtk.Native's at odds in any class that
# adds a base to a window class.
@template
class Window(ExampleResourcesWindowChildren, Adw.ApplicationWindow):
    __gtype_name__ = "ExampleResourcesWindow"

    likes = 0

    def on_like_clicked(self, button: Gtk.Button) -> None:
        self.likes += 1
        self.count_label.set_label(f"Liked {self.likes} time{'s' if self.likes > 1 else ''}")


def on_activate(app: Gio.Application) -> None:
    assert isinstance(app, Adw.Application)
    Window(application=app).present()


if __name__ == "__main__":
    application = Adw.Application(application_id="org.example.PyLiite4Resources")
    application.activate.connect(on_activate)
    sys.exit(application.run(sys.argv))
