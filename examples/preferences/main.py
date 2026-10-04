"""A preferences dialog where people choose the application's shortcuts, with ShortcutRecorder and tips.

Each row's ShortcutRecorder records the next key combination when clicked, as GNOME Settings does; Escape cancels and
Backspace disables the shortcut. Its accelerator goes straight to Gtk.Application.set_accels_for_action(), and its
validate signal refuses a shortcut another action already has, saying why with show_tip().

Run it from the repository root:

    python examples/preferences/main.py
"""

import sys
from typing import Any

from PyLiite4 import Adw, Gio, GLib, Gtk
from PyLiite4.Extras import ShortcutRecorder, show_tip

# Action, title, default shortcut.
SHORTCUTS = [("app.new-note", "New note", "<Control>n"),
             ("app.search", "Search", "<Control>f"),
             ("app.preferences", "Preferences", "<Control>comma"),
             ("app.quit", "Quit", "<Control>q")]


class Preferences(Adw.PreferencesDialog):
    def __init__(self, application: Adw.Application) -> None:
        super().__init__(title="Preferences")
        self.application = application
        self.recorders: dict[str, ShortcutRecorder] = {}
        group = Adw.PreferencesGroup(title="Shortcuts", description="Click a shortcut, then press the new one")
        for action, title, _ in SHORTCUTS:
            recorder = ShortcutRecorder(valign=Gtk.Align.CENTER)
            accelerators = application.get_accels_for_action(action)
            recorder.accelerator = accelerators[0] if accelerators else ""
            recorder.validate.connect(self.on_validate, action)
            recorder.notify["accelerator"].connect(self.on_changed, action)
            row = Adw.ActionRow(title=title)
            row.add_suffix(recorder)
            group.add(row)
            self.recorders[action] = recorder
        reset = Gtk.Button(label="Reset to Defaults", halign=Gtk.Align.START, margin_top=12)
        reset.clicked.connect(lambda button: self.reset())
        group.add(reset)
        page = Adw.PreferencesPage(title="General", icon_name="input-keyboard-symbolic")
        page.add(group)
        self.add(page)

    def on_validate(self, recorder: ShortcutRecorder, accelerator: str, action: str) -> bool:
        for other, title, _ in SHORTCUTS:
            if other != action and self.recorders[other].accelerator == accelerator:
                show_tip(recorder, f"“{title}” already uses it")
                return False
        return True

    def on_changed(self, recorder: ShortcutRecorder, spec: Any, action: str) -> None:
        accelerator = recorder.accelerator
        self.application.set_accels_for_action(action, [accelerator] if accelerator else [])
        if accelerator:
            ok, key, modifiers = Gtk.accelerator_parse(accelerator)
            label = GLib.markup_escape_text(Gtk.accelerator_get_label(key, modifiers))
            show_tip(recorder, f"Saved: <b>{label}</b>", use_markup=True)

    def reset(self) -> None:
        for action, _, default in SHORTCUTS:
            self.recorders[action].accelerator = default


class Window(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application) -> None:
        super().__init__(application=application, title="Notes", default_width=560, default_height=420)
        self.status = Adw.StatusPage(icon_name="input-keyboard-symbolic", title="Notes",
                                     description="Press Ctrl+, to choose the shortcuts")
        self.toasts = Adw.ToastOverlay(child=self.status)
        view = Adw.ToolbarView(content=self.toasts)
        header = Adw.HeaderBar()
        header.pack_end(Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text="Preferences",
                                   action_name="app.preferences"))
        view.add_top_bar(header)
        self.set_content(view)

    def toast(self, text: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=text, timeout=2))


def on_startup(app: Gio.Application) -> None:
    assert isinstance(app, Adw.Application)
    for action, title, default in SHORTCUTS:
        name = action.removeprefix("app.")
        simple = Gio.SimpleAction(name=name)
        if name == "preferences":
            simple.activate.connect(lambda action, parameter: Preferences(app).present(app.get_active_window()))
        elif name == "quit":
            simple.activate.connect(lambda action, parameter: app.quit())
        else:
            simple.activate.connect(window_toast, app, title)
        app.add_action(simple)
        app.set_accels_for_action(action, [default])


def window_toast(action: Gio.SimpleAction, parameter: GLib.Variant | None, app: Adw.Application, title: str) -> None:
    window = app.get_active_window()
    if isinstance(window, Window):
        window.toast(f"{title}!")


def on_activate(app: Gio.Application) -> None:
    assert isinstance(app, Adw.Application)
    (app.get_active_window() or Window(app)).present()


if __name__ == "__main__":
    application = Adw.Application(application_id="org.example.PyLiite4Preferences")
    application.startup.connect(on_startup)
    application.activate.connect(on_activate)
    sys.exit(application.run(sys.argv))
