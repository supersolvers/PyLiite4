"""Choosing shortcuts with ShortcutRecorder, bound to the window's own actions as people set them."""

from typing import Any

from PyLiite4 import Adw, Gio, GLib, Gtk
from PyLiite4.Extras import ShortcutRecorder, show_tip

from ._layout import intro, scrolled_page

NAME = "shortcuts"
TITLE = "Shortcuts"
ICON = "input-keyboard-symbolic"
SUMMARY = "ShortcutRecorder records the next key combination, for set_accels_for_action()"

# (action, title, default shortcut)
ACTIONS = [("win.demo-greet", "Greet", "<Control>g"),
           ("win.demo-next-page", "Next page", "<Control>Page_Down"),
           ("win.demo-previous-page", "Previous page", "<Control>Page_Up")]


class Page(Gtk.Box):
    def __init__(self, window: Any) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.window = window
        self.append(intro("Choosing Shortcuts", "Click a shortcut and press a new one; Escape cancels and "
                          "Backspace disables it. ShortcutRecorder is the equivalent of QKeySequenceEdit, in the "
                          "form set_accels_for_action() takes. These shortcuts work at once, anywhere in this window."))

        for name, callback in (("demo-greet", lambda: window.toast("Hello from a shortcut")),
                               ("demo-next-page", lambda: self.step(1)),
                               ("demo-previous-page", lambda: self.step(-1))):
            action = Gio.SimpleAction(name=name)
            action.activate.connect(lambda action, parameter, callback=callback: callback())
            window.add_action(action)

        group = Adw.PreferencesGroup(title="Window")
        self.recorders: dict[str, ShortcutRecorder] = {}
        for action, title, default in ACTIONS:
            recorder = ShortcutRecorder(accelerator=default, valign=Gtk.Align.CENTER)
            recorder.validate.connect(self.on_validate, action)
            recorder.notify["accelerator"].connect(self.on_accelerator_changed, action)
            self.recorders[action] = recorder
            row = Adw.ActionRow(title=title)
            row.add_suffix(recorder)
            group.add(row)
            self.apply(action, default)
        self.append(group)

        reset = Gtk.Button(label="Reset to Defaults", halign=Gtk.Align.START)
        reset.clicked.connect(lambda button: self.reset())
        self.append(reset)

    def apply(self, action: str, accelerator: str) -> None:
        application = self.window.get_application()
        if application is not None:
            application.set_accels_for_action(action, [accelerator] if accelerator else [])

    def on_validate(self, recorder: ShortcutRecorder, accelerator: str, action: str) -> bool:
        for other, title, _ in ACTIONS:
            if other != action and self.recorders[other].accelerator == accelerator:
                show_tip(recorder, f"Already used for “{title}”")
                return False
        return True

    def on_accelerator_changed(self, recorder: ShortcutRecorder, spec: Any, action: str) -> None:
        self.apply(action, recorder.accelerator)
        if recorder.accelerator:
            ok, key, modifiers = Gtk.accelerator_parse(recorder.accelerator)
            show_tip(recorder, f"Press {GLib.markup_escape_text(Gtk.accelerator_get_label(key, modifiers))} to try "
                     "it", use_markup=True)

    def reset(self) -> None:
        for action, _, default in ACTIONS:
            self.recorders[action].accelerator = default

    def step(self, by: int) -> None:
        names = self.window.page_names()
        current = names.index(self.window.stack.get_visible_child_name())
        self.window.show_page(names[(current + by) % len(names)])


def build(window: Any) -> Gtk.Widget:
    return scrolled_page(Page(window))
