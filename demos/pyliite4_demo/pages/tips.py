"""Tips shown on demand, with show_tip(): after a click, at a point, with markup, or until hidden."""

from typing import Any

from PyLiite4 import Adw, GObject, Gtk
from PyLiite4.Extras import hide_tip, show_tip

from ._layout import intro, scrolled_page

NAME = "tips"
TITLE = "Tips"
ICON = "dialog-information-symbolic"
SUMMARY = "show_tip() shows a tooltip when the application decides, where it decides"


class Page(Gtk.Box):
    def __init__(self, window: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.append(intro("Tips on Demand", "A widget's tooltip appears only while the pointer rests on it. "
                          "show_tip() shows one now, at a widget or a point in it, like QToolTip.showText. It takes "
                          "no focus, hides after a while, when the pointer moves off or on a key press, and is "
                          "announced to screen readers."))

        group = Adw.PreferencesGroup(title="Feedback")
        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.switch.notify["active"].connect(
            lambda switch, spec: show_tip(switch, "Switched on" if switch.get_active() else "Switched off"))
        row = Adw.ActionRow(title="Notifications", subtitle="Toggling it confirms with a tip, as Ziggy does")
        row.add_suffix(self.switch)
        row.set_activatable_widget(self.switch)
        group.add(row)

        self.copy_button = Gtk.Button(label="Copy", valign=Gtk.Align.CENTER)
        self.copy_button.clicked.connect(self.on_copy)
        row = Adw.ActionRow(title="Copy a token", subtitle="A tip with markup says what was copied")
        row.add_suffix(self.copy_button)
        group.add(row)

        self.sticky_button = Gtk.Button(label="Show", valign=Gtk.Align.CENTER)
        self.sticky_button.clicked.connect(
            lambda button: show_tip(button, "This tip stays until the pointer moves off, a key is pressed, or "
                                    "Hide is clicked", timeout=0))
        hide_button = Gtk.Button(label="Hide", valign=Gtk.Align.CENTER)
        hide_button.clicked.connect(lambda button: hide_tip())
        row = Adw.ActionRow(title="A tip that stays", subtitle="timeout=0 keeps it up")
        row.add_suffix(self.sticky_button)
        row.add_suffix(hide_button)
        group.add(row)
        self.append(group)

        self.append(Gtk.Label(label="Click anywhere in the area below: the tip appears where you clicked.",
                              xalign=0, wrap=True))
        self.area = Gtk.DrawingArea(content_height=160, css_classes=["card"])
        click = Gtk.GestureClick()
        click.connect("pressed", self.on_area_pressed)
        self.area.add_controller(click)
        self.append(self.area)

    def on_copy(self, button: Gtk.Button) -> None:
        value = GObject.Value()
        value.init(GObject.TYPE_STRING)
        value.set_string("demo-token-1234")
        button.get_clipboard().set(value)
        show_tip(button, "Copied <tt>demo-token-••••</tt> to the clipboard", use_markup=True)

    def on_area_pressed(self, gesture: Gtk.GestureClick, presses: int, x: float, y: float) -> None:
        show_tip(self.area, f"Clicked at {x:.0f}, {y:.0f}", (int(x), int(y)))


def build(window: Any) -> Gtk.Widget:
    return scrolled_page(Page(window))
