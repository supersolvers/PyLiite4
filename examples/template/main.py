"""A composite widget defined by a .ui template.

counter.ui describes the widget's children and names their signal handlers. pyliite4-ui turns it into counter_ui.py,
which types the children (``self.value_label: Gtk.Label``) and provides the ``template`` decorator. The decorator
checks at import that the class has the parent, ``__gtype_name__`` and handlers that the file names.

Run it from the repository root:

    python examples/template/main.py

After editing counter.ui, regenerate the module:

    pyliite4-ui examples/template/counter.ui -o examples/template/counter_ui.py
"""

import sys

from counter_ui import ExampleCounterChildren, template

from PyLiite4 import Adw, GObject, Gio, Gtk


@template
class Counter(ExampleCounterChildren, Gtk.Box):
    __gtype_name__ = "ExampleCounter"

    # A GObject property: other code can bind to it, or follow it with counter.notify["value"].
    value = GObject.Property(type=int, default=0)

    def __init__(self) -> None:
        super().__init__()
        self.notify["value"].connect(self.on_value_changed)

    def on_increment_clicked(self, button: Gtk.Button) -> None:
        self.value += 1

    def on_decrement_clicked(self, button: Gtk.Button) -> None:
        self.value -= 1

    def on_reset_clicked(self, button: Gtk.Button) -> None:
        self.value = 0

    def on_value_changed(self, counter: GObject.Object, spec: GObject.ParamSpec) -> None:
        self.value_label.set_label(str(self.value))
        self.reset_button.set_sensitive(self.value != 0)


def on_activate(app: Gio.Application) -> None:
    assert isinstance(app, Adw.Application)
    view = Adw.ToolbarView(content=Counter())
    view.add_top_bar(Adw.HeaderBar())
    Adw.ApplicationWindow(application=app, title="Counter", default_width=320, default_height=240,
                          content=view).present()


if __name__ == "__main__":
    application = Adw.Application(application_id="org.example.PyLiite4Template")
    application.activate.connect(on_activate)
    sys.exit(application.run(sys.argv))
