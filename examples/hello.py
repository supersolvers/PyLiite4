"""A small PyLiite4 application."""

import sys

from PyLiite4 import Signal
from PyLiite4.GObject import Object
from PyLiite4.Gtk import Application, ApplicationWindow, Box, Button, Label, Orientation


class Counter(Object):
    changed = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.value = 0

    def increment(self) -> None:
        self.value += 1
        self.changed.emit(self.value)


def on_activate(app: Application) -> None:
    counter = Counter()
    label = Label(label="Not clicked yet")
    button = Button(label="Click me")
    button.clicked.connect(lambda _button: counter.increment())
    counter.changed.connect(lambda _counter, value: label.set_text(f"Clicked {value} times"))

    box = Box(orientation=Orientation.VERTICAL, spacing=12, margin_top=24, margin_bottom=24,
              margin_start=24, margin_end=24)
    box.append(label)
    box.append(button)

    window = ApplicationWindow(application=app, title="PyLiite4", child=box)
    window.present()


if __name__ == "__main__":
    application = Application(application_id="org.example.PyLiite4Hello")
    application.activate.connect(on_activate)
    sys.exit(application.run(sys.argv))
