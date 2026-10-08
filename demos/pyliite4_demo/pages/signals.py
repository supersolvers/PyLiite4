"""PyLiite4's signals and properties: declared on a class of our own, bound, followed, emitted and blocked."""

from typing import Any

from PyLiite4 import Adw, GObject, Gtk, Signal

from ._layout import intro, scrolled_page

NAME = "signals"
TITLE = "Signals and Properties"
ICON = "emblem-system-symbolic"
SUMMARY = "Signals as attributes, properties bound and followed, and handlers blocked for a while"


class Thermostat(GObject.Object):
    """A model with a property and a signal of its own, declared the PyLiite4 way."""

    __gtype_name__ = "PyLiite4DemoThermostat"

    temperature = GObject.Property(type=float, default=20.0, minimum=0.0, maximum=40.0)
    limit = GObject.Property(type=float, default=30.0)
    overheated = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.notify["temperature"].connect(self.on_temperature)

    def on_temperature(self, thermostat: GObject.Object, spec: GObject.ParamSpec) -> None:
        if self.temperature > self.limit:
            self.overheated.emit(self.temperature)


class Page(Gtk.Box):
    def __init__(self, window: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.append(intro("Signals and Properties", "Signals are attributes: thermostat.overheated.connect(), "
                          ".emit() and .blocked(handler). Properties are attributes too, bound to widgets with "
                          "bind_property() and followed with notify[\"temperature\"]. The class below declares both "
                          "with Signal(float) and GObject.Property."))
        self.thermostat = Thermostat()
        self.events: list[str] = []
        self.banner = Adw.Banner(title="Overheated!", button_label="Cool Down")
        self.banner.button_clicked.connect(lambda banner: self.set_temperature(20.0))

        group = Adw.PreferencesGroup(title="Thermostat")
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 40, 0.5)
        self.scale.set_hexpand(True)
        self.scale.set_draw_value(True)
        # Two-way: dragging the scale sets the property, and setting the property moves the scale.
        self.thermostat.bind_property("temperature", self.scale.get_adjustment(), "value",
                                      GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        row = Adw.ActionRow(title="Temperature", subtitle="Above 30 °C emits overheated")
        row.add_suffix(self.scale)
        group.add(row)

        self.reading = Gtk.Label(css_classes=["title-3", "numeric"])
        self.thermostat.notify["temperature"].connect(lambda thermostat, spec: self.show_reading())
        self.show_reading()
        row = Adw.ActionRow(title="Reading", subtitle="Follows notify[\"temperature\"]")
        row.add_suffix(self.reading)
        group.add(row)

        self.mute = Gtk.Switch(valign=Gtk.Align.CENTER)
        row = Adw.ActionRow(title="Mute the alarm", subtitle="Changes made while muted run inside "
                            "thermostat.overheated.blocked(handler)")
        row.add_suffix(self.mute)
        row.set_activatable_widget(self.mute)
        group.add(row)
        self.append(group)

        self.handler = self.thermostat.overheated.connect(self.on_overheated)
        self.append(self.banner)

        presets = Gtk.Box(spacing=6, css_classes=["linked"], halign=Gtk.Align.START)
        for value in (15.0, 25.0, 35.0):
            button = Gtk.Button(label=f"Set {value:.0f} °C")
            button.clicked.connect(lambda button, value=value: self.set_temperature(value))
            presets.append(button)
        self.append(presets)

        self.log = Gtk.Label(xalign=0, wrap=True, css_classes=["monospace", "dim-label"])
        self.append(self.log)

    def set_temperature(self, value: float) -> None:
        if self.mute.get_active():
            with self.thermostat.overheated.blocked(self.handler):
                self.thermostat.temperature = value
        else:
            self.thermostat.temperature = value

    def show_reading(self) -> None:
        self.reading.set_label(f"{self.thermostat.temperature:.1f} °C")
        if self.thermostat.temperature <= self.thermostat.limit:
            self.banner.set_revealed(False)

    def on_overheated(self, thermostat: Thermostat, temperature: float) -> None:
        self.banner.set_title(f"Overheated: {temperature:.1f} °C")
        self.banner.set_revealed(True)
        self.events.append(f"overheated({temperature:.1f})")
        self.log.set_label("Emitted: " + ", ".join(self.events[-4:]))


def build(window: Any) -> Gtk.Widget:
    return scrolled_page(Page(window))
